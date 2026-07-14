# -*- coding: utf-8 -*-
"""Agent Task 执行器（降级为单动作执行器 + 顺序 fallback）。

原本在后台线程中执行 Task 的 plan，包含 $prev 解析和修复循环。ReAct 大脑层（ReActAgent）
上线后，修复循环逻辑已上移至 reactor.py；本模块退化为：
- run()：顺序执行 plan 的 fallback 模式（无反思，单步失败 continue-on-error）。
- _run_single_step：执行单个 skill，返回 observation dict，供 ReActAgent 复用。

通过 asyncio.Queue 推送事件供 SSE endpoint 消费（复用 RagAgent 的 thread→queue 模式）。
$prev 模板：step params 中 case_id == "$prev" → 取上一步结果中的 case_id。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from insight_aitest.modules.ai.backend.agent.skills import SKILLS, SkillContext
from insight_aitest.modules.ai.backend.persistence.models import Role, TaskStatus

# 执行类 skill（可被 ReActAgent 反思/重试/修复）
_EXEC_SKILLS = {"execute_api_case", "execute_ui_case"}


@dataclass
class TaskEvent:
    """执行器发出的 SSE 事件。"""

    type: str  # step_start | step_done | step_error | done | error
    data: dict[str, Any]


def _resolve_prev(step_params: dict, prev_result: dict | None) -> dict:
    """把 params 里 case_id == "$prev" 替换为上一步结果的 case_id。

    轻量模板：只识别 "$prev" 这一个占位符，不引表达式引擎。
    """
    if prev_result is None:
        return step_params
    resolved = dict(step_params)
    for k, v in resolved.items():
        if v == "$prev" and "case_id" in prev_result:
            resolved[k] = prev_result["case_id"]
    return resolved


class TaskExecutor:
    """在后台线程中执行 Task 的 plan。"""

    def __init__(self, ctx: SkillContext) -> None:
        self.ctx = ctx

    def run(
        self,
        task_id: int,
        plan: list[dict],
        task_db,
        queue: asyncio.Queue | None = None,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        """执行 task 的所有步骤。

        queue/loop 用于 SSE 推送（可选，测试时不传则不推送）。
        task_db 是 AIDatabase 实例（更新 task 状态）。
        """

        def _emit(event: TaskEvent) -> None:
            if queue is not None and loop is not None:
                asyncio.run_coroutine_threadsafe(queue.put(event), loop).result()

        total = len(plan)
        case_ids: list[int] = []
        batch_id: str | None = None  # write_cases_batch 等批量 skill 产出的批次标识
        step_results: list[dict] = []
        any_failed = False
        prev_result: dict | None = None  # 上一步结果（供 $prev 解析）

        for i, step in enumerate(plan):
            # 取消检查：每步开始前查 task 状态，CANCELLED 则立即停止
            current = task_db.get_task(task_id)
            if current is not None and current.status == TaskStatus.CANCELLED:
                _emit(TaskEvent("cancelled", {"step_index": i}))
                return

            skill_id = step.get("skill", "")
            skill = SKILLS.get(skill_id)
            desc = step.get("desc", skill.name if skill else skill_id)
            params = _resolve_prev(step.get("params", {}), prev_result)

            if skill is None:
                _emit(
                    TaskEvent("step_error", {"step_index": i, "error": f"未知 skill: {skill_id}"})
                )
                any_failed = True
                prev_result = None
                continue

            # 顺序执行（修复循环逻辑已上移至 ReActAgent）
            result = self._run_single_step(i, skill_id, params, task_db, task_id, _emit, total)

            step_results.append({"step_index": i, "skill": skill_id, "desc": desc, **result})
            # 汇总（_run_single_step 现在直接返回 observation dict）
            if "error" in result:
                any_failed = True
            if isinstance(result, dict):
                if "case_id" in result:
                    case_ids.append(result["case_id"])
                # 取第一个含 batch_id 的 step 结果顶到顶层（write_cases_batch 产物）
                if batch_id is None and result.get("batch_id"):
                    batch_id = result["batch_id"]
                prev_result = result
            else:
                prev_result = None

        # 完成
        result_summary = {
            "steps": step_results,
            "case_ids": case_ids,
            "summary": f"共执行 {total} 步，生成 {len(case_ids)} 条用例",
        }
        if batch_id is not None:
            result_summary["batch_id"] = batch_id
        final_status = TaskStatus.FAILED if any_failed and not case_ids else TaskStatus.DONE
        task_db.update_task_status(task_id, final_status, result=result_summary)

        # 持久化任务完成消息（修复上下文丢失：后续 agent_chat 可加载历史）
        try:
            task = task_db.get_task(task_id)
            if task is not None and task.conversation_id is not None:
                status_text = "✅ 任务执行完成" if final_status == TaskStatus.DONE else "❌ 任务执行失败"
                task_db.add_message(
                    task.conversation_id,
                    Role.ASSISTANT,
                    f"{status_text}\n\n{result_summary['summary']}",
                    task_id=task_id,
                )
        except Exception:
            pass  # 消息持久化失败不应影响已提交的任务终态

        if final_status == TaskStatus.DONE:
            _emit(TaskEvent("done", {"result": result_summary}))
        else:
            _emit(TaskEvent("error", {"result": result_summary, "message": "部分步骤执行失败"}))

    # ===== 单步执行（降级为单动作执行器，供 ReActAgent 复用） =====

    def _run_single_step(
        self, step_index, skill_id, params, task_db, task_id, _emit, total
    ) -> dict:
        """执行单个 skill，返回 observation dict（skill 结果或 {"error": ...}）。

        skill 在内部按 skill_id 查 SKILLS（不再由调用方传入）。_emit 是接受 TaskEvent
        的回调，用于推送 step_start/step_done/step_error。
        """
        skill = SKILLS.get(skill_id)
        task_db.update_task_status(task_id, TaskStatus.RUNNING)
        task_db.update_task_step(task_id, step_index)
        _emit(
            TaskEvent(
                "step_start",
                {
                    "step_index": step_index,
                    "skill": skill_id,
                    "desc": skill.name if skill else skill_id,
                    "total": total,
                    "current": step_index + 1,
                },
            )
        )
        if skill is None:
            err = f"未知 skill: {skill_id}"
            task_db.update_task_step(task_id, step_index, {"error": err})
            _emit(
                TaskEvent("step_error", {"step_index": step_index, "skill": skill_id, "error": err})
            )
            return {"error": err}
        try:
            result = skill.execute(params, self.ctx)
            task_db.update_task_step(task_id, step_index, result)
            _emit(
                TaskEvent(
                    "step_done", {"step_index": step_index, "skill": skill_id, "result": result}
                )
            )
            return result
        except Exception as e:
            err_msg = f"步骤执行失败: {e}"
            task_db.update_task_step(task_id, step_index, {"error": err_msg})
            _emit(
                TaskEvent(
                    "step_error", {"step_index": step_index, "skill": skill_id, "error": str(e)}
                )
            )
            return {"error": str(e)}
