# -*- coding: utf-8 -*-
"""ReAct 大脑层：在 plan 执行中引入"观察→反思→纠错"循环。

混合式架构：顶层仍是 Plan-and-Solve（planner 不动），每个 step 执行后由 LLM 反思决策。
硬上限防死循环；反思失败三级降级；失败超限触发 RCA。

ReActAgent 包装 TaskExecutor：executor._run_single_step 降级为单动作执行器，
ReActAgent 在其上叠加 EXECUTE→REFLECT→DECIDE 微循环（retry/fix/abort）。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from insight_aitest.modules.ai.backend.persistence.models import Role, TaskStatus

if TYPE_CHECKING:
    from insight_aitest.modules.ai.backend.agent.executor import TaskExecutor
    from insight_aitest.platform.services.llm.client import LLMClient
    from insight_aitest.platform.services.llm.config import LLMConfig


@dataclass
class StepBudget:
    retry_budget: int = 2
    fix_budget: int = 2
    consecutive_fail_limit: int = 3


@dataclass
class ReActConfig:
    enabled: bool = True
    max_iterations: int = 8
    budget: StepBudget = field(default_factory=StepBudget)
    reflection_model: str | None = None
    observation_max_chars: int = 2000

    @classmethod
    def from_dict(cls, d: dict | None) -> "ReActConfig":
        if not d:
            return cls()
        budget_d = d.get("budget") or {}
        return cls(
            enabled=d.get("enabled", True),
            max_iterations=d.get("max_iterations", 8),
            budget=StepBudget(
                retry_budget=budget_d.get("retry", 2),
                fix_budget=budget_d.get("fix", 2),
                consecutive_fail_limit=budget_d.get("consecutive_fail", 3),
            ),
            reflection_model=d.get("reflection_model"),
            observation_max_chars=d.get("observation_max_chars", 2000),
        )


@dataclass
class TraceEntry:
    step_index: int
    iteration: int
    action: dict
    observation: dict
    reflection: dict | None
    decision: str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "step_index": self.step_index,
            "iteration": self.iteration,
            "action": self.action,
            "observation": self.observation,
            "reflection": self.reflection,
            "decision": self.decision,
            "timestamp": self.timestamp,
        }


@dataclass
class ReActEvent:
    type: str  # thought|action|observation|reflection|decision|done|error|aborted
    data: dict[str, Any]


# ===== 反思 prompt 与 RCA prompt =====

_REFLECTION_PROMPT = """你是测试 Agent 的反思器。刚执行完一个动作，请判断下一步该怎么走。

动作：{action_desc}
结果：{observation}
本步历史：{step_history}
全局进度：第 {step_index}/{total_steps} 步

请输出 JSON（不要额外解释）：
{{
  "thought": "你对这次结果的分析（1-2句）",
  "decision": "continue | retry | fix | abort",
  "reasoning": "为什么选这个决策",
  "confidence": 0.0-1.0
}}

决策规则：
- continue: 通过，或失败但属预期（如负面测试断言失败）
- retry: 瞬时/环境性失败（超时、连接拒绝、元素未找到），重试有意义
- fix: 逻辑性失败（断言不匹配、status_code 错误），需修改用例
- abort: 无法恢复（权限拒绝、用例不存在、连续失败超限），停止整个任务
"""

_RCA_PROMPT = """你是测试 Agent 的根因分析师。任务执行被中止（abort），请基于执行轨迹给出根因分析。

中止原因：{reason}
被中止的步骤：第 {step_index} 步
执行轨迹（仅本步）：
{evidence}

请输出 JSON（不要额外解释）：
{{
  "root_cause": "一句话根因",
  "analysis": "2-3句详细分析",
  "recommendation": "后续建议（如：检查环境、人工修复用例）"
}}"""


# 用于 _fallback_reflection 判定瞬时/环境性失败的关键词
_TRANSIENT_KEYWORDS = (
    "timeout",
    "timed out",
    "connection",
    "connect",
    "refused",
    "element not found",
    "unreachable",
    "临时",
    "超时",
    "连接",
)


class ReActAgent:
    """ReAct 大脑层：包装 TaskExecutor，叠加 EXECUTE→REFLECT→DECIDE 循环。

    每步执行后：
    - 通过（passed）→ 跳过反思，continue；
    - 否则 → LLM 反思决策（continue/retry/fix/abort），受 budget 硬约束。
    """

    def __init__(
        self,
        executor: "TaskExecutor",
        llm: "LLMClient",
        config: "LLMConfig",
        react_config: ReActConfig,
    ) -> None:
        self.executor = executor
        self.llm = llm
        self.config = config
        self.react_config = react_config

    # ===== 主入口 =====

    def run(
        self,
        task_id: int,
        plan: list[dict],
        task_db,
        queue: asyncio.Queue | None = None,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        """执行整个 plan：逐 step 调 _run_step_react，按决策 retry/fix/abort。"""
        _emit = self._make_emit(queue, loop)

        total = len(plan)
        trace: list[TraceEntry] = []
        case_ids: list[int] = []
        batch_id: str | None = None  # write_cases_batch 等批量 skill 产出的批次标识
        step_results: list[dict] = []
        any_failed = False
        prev_result: dict | None = None
        # 跨步骤累积统计（iterations/retries/fixes），供 react_stats 输出与 max_iterations 强制
        stats = {"iterations": 0, "retries": 0, "fixes": 0}

        for i, step in enumerate(plan):
            # 取消检查
            current = task_db.get_task(task_id)
            if current is not None and current.status == TaskStatus.CANCELLED:
                _emit(ReActEvent("aborted", {"step_index": i, "reason": "cancelled"}))
                return

            skill_id = step.get("skill", "")
            desc = step.get("desc", skill_id)
            # $prev 解析（复用 executor 的实现，跨步骤传递 prev_result）
            from insight_aitest.modules.ai.backend.agent.executor import _resolve_prev

            params = _resolve_prev(step.get("params", {}), prev_result)
            loop_cfg = step.get("loop") or {}

            # 仅执行类 skill 且开启 loop 才进入反思循环；否则单次执行
            from insight_aitest.modules.ai.backend.agent.executor import _EXEC_SKILLS

            reflect_enabled = skill_id in _EXEC_SKILLS and bool(loop_cfg.get("enabled"))

            if reflect_enabled:
                decision, obs = self._run_step_react(
                    i, skill_id, desc, params, task_db, task_id, _emit, total, trace, stats
                )
            else:
                # 非反思路径：直接执行一次（转发 executor 事件为 ReActEvent）
                def _exec_emit(event):
                    _emit(ReActEvent(event.type, event.data))

                obs = self.executor._run_single_step(
                    i, skill_id, params, task_db, task_id, _exec_emit, total
                )
                # 非执行类 skill（rag_search/write_cases/generation 等）不在反思循环里。
                # 保留旧 executor 的 continue-on-error 语义：错误只记入 trace、
                # 由下方 any_failed/case_ids 决定最终 status，不在中途 abort。
                # abort 仅用于反思循环的预算耗尽 / LLM 显式 abort 决策。
                decision = "continue"

            # 汇总本步
            step_entry = {
                "step_index": i,
                "skill": skill_id,
                "desc": desc,
                "decision": decision,
            }
            if isinstance(obs, dict):
                step_entry.update(obs)
            step_results.append(step_entry)
            if isinstance(obs, dict):
                if "error" in obs:
                    any_failed = True
                if "case_id" in obs:
                    case_ids.append(obs["case_id"])
                # 取第一个含 batch_id 的 step 结果顶到顶层（write_cases_batch 产物）
                if batch_id is None and obs.get("batch_id"):
                    batch_id = obs["batch_id"]
                prev_result = obs
            else:
                prev_result = None

            if decision == "abort":
                reason = stats.pop("abort_reason", None) or "执行被中止（aborted）"
                self._do_abort(i, task_id, task_db, _emit, trace, reason, stats)
                return

        # 完成
        result_summary = {
            "steps": step_results,
            "case_ids": case_ids,
            "trace": [t.to_dict() for t in trace],
            "summary": f"共执行 {total} 步，生成 {len(case_ids)} 条用例",
            "react_stats": {
                "total_iterations": stats["iterations"],
                "total_retries": stats["retries"],
                "total_fixes": stats["fixes"],
            },
        }
        if batch_id is not None:
            result_summary["batch_id"] = batch_id
        final_status = TaskStatus.FAILED if any_failed and not case_ids else TaskStatus.DONE
        task_db.update_task_status(task_id, final_status, result=result_summary)

        # 持久化任务完成消息（修复上下文丢失）
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
            _emit(ReActEvent("done", {"result": result_summary}))
        else:
            _emit(ReActEvent("error", {"result": result_summary, "message": "部分步骤执行失败"}))

    # ===== EXECUTE→REFLECT→DECIDE 微循环 =====

    def _run_step_react(
        self,
        step_index,
        skill_id,
        desc,
        params,
        task_db,
        task_id,
        _emit,
        total,
        trace,
        stats: dict,
    ) -> tuple[str, dict]:
        """单步的反思循环。返回 (decision, last_observation)。

        stats 是跨步骤共享的可变计数器（{"iterations","retries","fixes"}）：
        - 每轮 while 累加 iterations；
        - retry/fix 时累加对应计数；
        - 超过 max_iterations 提前返回 "abort"。
        """
        budget = self.react_config.budget
        max_iterations = self.react_config.max_iterations
        counters = {"consecutive_fails": 0}
        iteration = 0
        last_obs: dict = {}

        while True:
            iteration += 1
            stats["iterations"] += 1
            # 全局反思轮次超限 → 中止整个任务（防死循环）
            if stats["iterations"] > max_iterations:
                stats["abort_reason"] = "max_iterations_reached"
                trace.append(
                    TraceEntry(
                        step_index=step_index,
                        iteration=iteration,
                        action={"skill": skill_id, "desc": desc, "params": params},
                        observation=last_obs,
                        reflection=None,
                        decision="abort",
                    )
                )
                return "abort", last_obs
            # —— EXECUTE ——
            _emit(
                ReActEvent(
                    "action",
                    {
                        "step_index": step_index,
                        "iteration": iteration,
                        "skill": skill_id,
                        "desc": desc,
                    },
                )
            )

            def _exec_emit(event):
                _emit(ReActEvent(event.type, event.data))

            obs = self.executor._run_single_step(
                step_index, skill_id, params, task_db, task_id, _exec_emit, total
            )
            last_obs = obs if isinstance(obs, dict) else {"raw": obs}

            # observation 事件扁平化：status/failures/case_id 等字段提到顶层，
            # 与 action/decision 事件保持一致，并供前端 taskStore 直接读 data.status。
            _emit(
                ReActEvent(
                    "observation",
                    {
                        "step_index": step_index,
                        "iteration": iteration,
                        "skill": skill_id,
                        **self._truncate(obs),
                    },
                )
            )

            # —— 通过：跳过反思，直接 continue ——
            if isinstance(obs, dict) and obs.get("status") == "passed":
                trace.append(
                    TraceEntry(
                        step_index=step_index,
                        iteration=iteration,
                        action={"skill": skill_id, "desc": desc, "params": params},
                        observation=last_obs,
                        reflection=None,
                        decision="continue",
                    )
                )
                return "continue", last_obs

            # —— 失败 ——
            counters["consecutive_fails"] += 1
            # 连续失败超限 → abort
            if counters["consecutive_fails"] >= budget.consecutive_fail_limit:
                trace.append(
                    TraceEntry(
                        step_index=step_index,
                        iteration=iteration,
                        action={"skill": skill_id, "desc": desc, "params": params},
                        observation=last_obs,
                        reflection=None,
                        decision="abort",
                    )
                )
                return "abort", last_obs

            # —— REFLECT ——
            reflection = self._reflect(step_index, iteration, desc, last_obs, trace, total, _emit)
            decision = reflection.get("decision", "continue")
            if decision not in ("continue", "retry", "fix", "abort"):
                # _fallback_reflection 返回完整 reflection dict，这里只需 decision 字符串。
                # 旧实现误把整个 dict 赋给 decision，导致下游字符串比较失效、事件里塞进 dict。
                decision = self._fallback_reflection(last_obs, counters)["decision"]

            # 预算感知的决策重映射（spec A3）：
            # - retry 预算耗尽 → 不再 retry，重映射到 fix（若还有 fix 预算）否则 abort
            # - fix 预算耗尽 → 不再 fix，重映射到 continue（接受失败）或 abort
            #   （continue 让 any_failed 自然决定任务终态；避免无意义的重复 EXECUTE）
            if decision == "retry" and stats["retries"] >= budget.retry_budget:
                decision = (
                    "fix"
                    if stats["fixes"] < budget.fix_budget and budget.fix_budget > 0
                    else "abort"
                )
            elif decision == "fix" and (
                stats["fixes"] >= budget.fix_budget or budget.fix_budget <= 0
            ):
                # fix 耗尽：断言失败属预期时 continue，否则 abort。默认 continue（由 any_failed 收口）
                decision = "continue"

            _emit(
                ReActEvent(
                    "decision",
                    {
                        "step_index": step_index,
                        "iteration": iteration,
                        "decision": decision,
                        "reasoning": reflection.get("reasoning", ""),
                    },
                )
            )

            trace.append(
                TraceEntry(
                    step_index=step_index,
                    iteration=iteration,
                    action={"skill": skill_id, "desc": desc, "params": params},
                    observation=last_obs,
                    reflection=reflection,
                    decision=decision,
                )
            )

            # —— DECIDE ——
            if decision == "continue":
                return "continue", last_obs
            if decision == "abort":
                return "abort", last_obs
            if decision == "retry":
                # 到这里 retry 预算必然未耗尽（上方已重映射），直接重执行
                stats["retries"] += 1
                continue
            if decision == "fix":
                # 到这里 fix 预算必然未耗尽（上方已重映射）
                self._do_fix(
                    step_index,
                    iteration,
                    last_obs,
                    params,
                    task_db,
                    task_id,
                    _emit,
                    skill_id,
                )
                stats["fixes"] += 1
                # 无论修复是否成功都 re-loop 重新执行
                continue
            # 兜底
            return "continue", last_obs

    # ===== 反思 =====

    def _reflect(self, step_index, iteration, desc, obs, trace, total, _emit) -> dict:
        """调 LLM 反思，返回 reflection dict（含 decision）。失败则降级。"""
        step_history = [t.to_dict() for t in trace if t.step_index == step_index]
        prompt = _REFLECTION_PROMPT.format(
            action_desc=desc,
            observation=self._truncate(obs),
            step_history=self._truncate(step_history),
            step_index=step_index + 1,
            total_steps=total,
        )
        _emit(
            ReActEvent(
                "reflection",
                {"step_index": step_index, "phase": "thinking", "prompt": prompt[:500]},
            )
        )
        try:
            raw = self.llm.chat([{"role": "user", "content": prompt}])
        except Exception as e:
            _emit(
                ReActEvent(
                    "reflection", {"step_index": step_index, "phase": "error", "error": str(e)}
                )
            )
            return self._fallback_reflection(obs, {})

        from insight_aitest.modules.testcase.backend.generator.analyzer import _extract_json

        data = _extract_json(raw)
        if not isinstance(data, dict):
            _emit(
                ReActEvent(
                    "reflection",
                    {
                        "step_index": step_index,
                        "phase": "fallback",
                        "reason": "LLM 未返回合法 JSON",
                    },
                )
            )
            return self._fallback_reflection(obs, {})
        _emit(
            ReActEvent("reflection", {"step_index": step_index, "phase": "result", "result": data})
        )
        return data

    def _fallback_reflection(self, obs: dict, budget: dict) -> dict:
        """启发式降级反思：LLM 不可用/输出非法时用规则判决策。"""
        text = ""
        if isinstance(obs, dict):
            text = str(obs.get("error", "")) + " " + str(obs.get("failures", ""))
        low = text.lower()
        if any(k in low for k in _TRANSIENT_KEYWORDS):
            return {
                "thought": "疑似瞬时/环境失败",
                "decision": "retry",
                "reasoning": "降级：检测到超时/连接类关键词",
                "confidence": 0.4,
            }
        if isinstance(obs, dict) and "error" in obs:
            return {
                "thought": "引擎级错误，无法自动恢复",
                "decision": "abort",
                "reasoning": "降级：error 类失败",
                "confidence": 0.4,
            }
        if isinstance(obs, dict) and obs.get("status") == "failed":
            return {
                "thought": "断言失败，尝试修复用例",
                "decision": "fix",
                "reasoning": "降级：status=failed",
                "confidence": 0.4,
            }
        return {
            "thought": "无法判定，继续下一步",
            "decision": "continue",
            "reasoning": "降级：默认 continue",
            "confidence": 0.3,
        }

    # ===== 修复 =====

    def _do_fix(
        self, step_index, iteration, obs, params, task_db, task_id, _emit, skill_id
    ) -> bool:
        """analyze_failure + fix_api_case/fix_ui_case，返回是否修复成功。

        case_type 由被执行的 skill_id 推导（execute_ui_case → ui，否则 api），
        不依赖执行结果里是否带 case_type 字段（执行 skill 不保证输出该字段）。
        """
        from insight_aitest.modules.ai.backend.agent.skills import SKILLS

        case_id = obs.get("case_id") if isinstance(obs, dict) else None
        run_id = obs.get("run_id") if isinstance(obs, dict) else None
        failures = obs.get("failures", []) if isinstance(obs, dict) else []

        # 按 skill_id 派发 fix skill：execute_ui_case → fix_ui_case，其余 → fix_api_case
        case_type = "ui" if skill_id == "execute_ui_case" else "api"
        fix_skill_id = "fix_ui_case" if case_type == "ui" else "fix_api_case"

        analyze_skill = SKILLS.get("analyze_failure")
        if analyze_skill is None or case_id is None:
            return False

        # —— analyze ——
        _emit(
            ReActEvent(
                "action",
                {
                    "step_index": step_index,
                    "iteration": iteration,
                    "skill": "analyze_failure",
                    "desc": "分析失败原因",
                },
            )
        )
        analyze_params = {"case_id": case_id, "run_id": run_id, "failures": failures}
        try:
            analysis = analyze_skill.execute(analyze_params, self.executor.ctx)
        except Exception as e:
            _emit(
                ReActEvent(
                    "observation",
                    {
                        "step_index": step_index,
                        "iteration": iteration,
                        "skill": "analyze_failure",
                        "error": str(e),
                    },
                )
            )
            return False
        _emit(
            ReActEvent(
                "observation",
                {
                    "step_index": step_index,
                    "iteration": iteration,
                    "skill": "analyze_failure",
                    "result": analysis,
                },
            )
        )

        # —— fix ——
        fix_skill = SKILLS.get(fix_skill_id)
        if fix_skill is None:
            return False
        _emit(
            ReActEvent(
                "action",
                {
                    "step_index": step_index,
                    "iteration": iteration,
                    "skill": fix_skill_id,
                    "desc": "修复用例",
                },
            )
        )
        fix_params = {"case_id": case_id, "analysis": analysis}
        try:
            fix_result = fix_skill.execute(fix_params, self.executor.ctx)
        except Exception as e:
            _emit(
                ReActEvent(
                    "observation",
                    {
                        "step_index": step_index,
                        "iteration": iteration,
                        "skill": fix_skill_id,
                        "error": str(e),
                    },
                )
            )
            return False
        _emit(
            ReActEvent(
                "observation",
                {
                    "step_index": step_index,
                    "iteration": iteration,
                    "skill": fix_skill_id,
                    "result": fix_result,
                },
            )
        )
        return bool(fix_result.get("fixed")) if isinstance(fix_result, dict) else False

    # ===== 中止 + RCA =====

    def _do_abort(self, step_index, task_id, task_db, _emit, trace, reason, stats=None) -> None:
        """生成 RCA，更新任务为 FAILED，发出 aborted 事件。"""
        rca = self._generate_rca(step_index, trace, reason)
        result = {
            "aborted": True,
            "reason": reason,
            "rca": rca,
            "trace": [t.to_dict() for t in trace],
        }
        if stats is not None:
            result["react_stats"] = {
                "total_iterations": stats["iterations"],
                "total_retries": stats["retries"],
                "total_fixes": stats["fixes"],
            }
        task_db.update_task_status(task_id, TaskStatus.FAILED, result=result)
        _emit(ReActEvent("aborted", {"step_index": step_index, "reason": reason, "rca": rca}))

    def _generate_rca(self, step_index, trace, reason) -> dict:
        """调 LLM 生成根因分析；失败返回模板。"""
        evidence = [t.to_dict() for t in trace if t.step_index == step_index]
        prompt = _RCA_PROMPT.format(
            reason=reason,
            step_index=step_index + 1,
            evidence=self._truncate(evidence),
        )
        try:
            raw = self.llm.chat([{"role": "user", "content": prompt}])
        except Exception:
            return {
                "root_cause": reason,
                "analysis": "LLM 不可用，无法生成详细分析",
                "recommendation": "请人工检查执行轨迹",
            }

        from insight_aitest.modules.testcase.backend.generator.analyzer import _extract_json

        data = _extract_json(raw)
        if not isinstance(data, dict):
            return {
                "root_cause": reason,
                "analysis": raw[:500] if isinstance(raw, str) else "",
                "recommendation": "请人工检查执行轨迹",
            }
        return data

    # ===== 辅助 =====

    def _make_emit(self, queue, loop):
        """构造 _emit(ReActEvent)，无 queue/loop 时为 no-op。"""

        def _emit(event: ReActEvent) -> None:
            if queue is not None and loop is not None:
                asyncio.run_coroutine_threadsafe(queue.put(event), loop).result()

        return _emit

    def _truncate(self, obj) -> Any:
        """把 observation/历史裁剪到 observation_max_chars（避免 prompt 爆长）。"""
        limit = self.react_config.observation_max_chars
        try:
            import json

            s = json.dumps(obj, ensure_ascii=False, default=str)
        except Exception:
            s = str(obj)
        if len(s) <= limit:
            return obj
        return {"_truncated": True, "preview": s[:limit]}
