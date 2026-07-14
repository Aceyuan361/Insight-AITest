# -*- coding: utf-8 -*-
"""TaskExecutor 顺序执行 / $prev 解析测试。

修复循环逻辑（execute→analyze→fix→re-execute）已上移至 ReActAgent（reactor.py），
对应测试见 tests/ai/test_reactor.py::test_react_fix_then_pass。本文件保留：
- $prev 模板解析（case_id 跨步骤引用）
- 顺序执行 fallback：断言失败（status:"failed"）不计入 any_failed（任务仍 DONE）
"""
from __future__ import annotations

from unittest.mock import MagicMock

from insight_aitest.modules.ai.backend.agent.executor import TaskExecutor, _resolve_prev
from insight_aitest.modules.ai.backend.agent.skills import SkillContext
from insight_aitest.modules.ai.backend.persistence.models import TaskStatus


def _make_ctx():
    return SkillContext(
        llm=MagicMock(),
        config=MagicMock(),
        retriever=MagicMock(),
        generator=MagicMock(),
        case_db=MagicMock(),
        project_id=None,
        version_id=None,
        api_run_db=MagicMock(),
        http_transport=None,
    )


def _make_task_db():
    """Mock AIDatabase：记录 update_task_status / update_task_step 调用。"""
    db = MagicMock()
    return db


# ===== $prev 模板解析 =====


def test_resolve_prev_replaces_placeholder():
    prev = {"case_id": 99, "status": "passed"}
    params = {"case_id": "$prev", "extra": "keep"}
    out = _resolve_prev(params, prev)
    assert out["case_id"] == 99
    assert out["extra"] == "keep"


def test_resolve_prev_no_prev_result():
    out = _resolve_prev({"case_id": "$prev"}, None)
    assert out["case_id"] == "$prev"  # 无上一步，原样返回


def test_resolve_prev_no_placeholder():
    out = _resolve_prev({"case_id": 5}, {"case_id": 99})
    assert out["case_id"] == 5  # 无占位符，不变


# ===== 无 loop 的 execute 失败 → 不影响 any_failed =====


def test_exec_fail_without_loop_does_not_fail_task(monkeypatch):
    """无 loop 的 execute_api_case 断言失败 → status=failed 但任务不因它 FAILED。"""
    from insight_aitest.modules.ai.backend.agent import executor as exec_mod
    from insight_aitest.modules.ai.backend.agent.skills import SkillSpec

    def fail(params, ctx):
        return {"case_id": 1, "run_id": 1, "status": "failed", "failures": []}

    monkeypatch.setitem(
        exec_mod.SKILLS, "execute_api_case",
        SkillSpec(id="execute_api_case", name="执行", description="", params_description="", execute=fail),
    )

    plan = [{"skill": "execute_api_case", "desc": "执行", "params": {"case_id": 1}}]
    task_db = _make_task_db()
    ex = TaskExecutor(_make_ctx())
    ex.run(task_id=1, plan=plan, task_db=task_db)

    # 断言失败不算 error，有 case_id → DONE
    status_call = task_db.update_task_status.call_args_list[-1]
    assert status_call.args[1] == TaskStatus.DONE


# ===== $prev 跨步骤引用 =====


def test_prev_reference_across_steps(monkeypatch):
    """write_api_case 产出 case_id → 后续 execute_api_case 用 $prev 引用它。"""
    from insight_aitest.modules.ai.backend.agent import executor as exec_mod
    from insight_aitest.modules.ai.backend.agent.skills import SkillSpec

    written_case_id = {"id": None}
    exec_case_id = {"id": None}

    def write(params, ctx):
        written_case_id["id"] = 77
        return {"case_id": 77, "title": "新用例", "type": "api"}

    def execute_skill(params, ctx):
        exec_case_id["id"] = params["case_id"]  # 应被 $prev 解析为 77
        return {"case_id": params["case_id"], "run_id": 1, "status": "passed", "failures": []}

    monkeypatch.setitem(
        exec_mod.SKILLS, "write_api_case",
        SkillSpec(id="write_api_case", name="写", description="", params_description="", execute=write),
    )
    monkeypatch.setitem(
        exec_mod.SKILLS, "execute_api_case",
        SkillSpec(id="execute_api_case", name="执行", description="", params_description="", execute=execute_skill),
    )

    plan = [
        {"skill": "write_api_case", "desc": "生成用例", "params": {"query": "登录"}},
        {"skill": "execute_api_case", "desc": "执行用例", "params": {"case_id": "$prev"}},
    ]
    task_db = _make_task_db()
    ex = TaskExecutor(_make_ctx())
    ex.run(task_id=1, plan=plan, task_db=task_db)

    assert written_case_id["id"] == 77
    assert exec_case_id["id"] == 77  # $prev 被正确解析


# ===== batch_id 汇总到 result（两阶段生成闭环）=====


def test_executor_aggregates_batch_id_to_result(monkeypatch):
    """write_cases_batch 产出的 batch_id 应顶到 result_summary 顶层。

    验证 Step 3：executor.run 遍历 step_results 时提取第一个 batch_id，
    放进最终 result_summary["batch_id"]，供前端 CaseReviewCard 加载。
    """
    from insight_aitest.modules.ai.backend.agent import executor as exec_mod
    from insight_aitest.modules.ai.backend.agent.skills import SkillSpec

    def batch_skill(params, ctx):
        # 模拟 _write_cases_batch 的返回（含 batch_id）
        return {
            "case_ids": [10, 11, 12],
            "generated": 3,
            "failed": 0,
            "batch_id": "batch-1-1700000000",
        }

    monkeypatch.setitem(
        exec_mod.SKILLS, "write_cases_batch",
        SkillSpec(id="write_cases_batch", name="批量生成", description="",
                  params_description="", execute=batch_skill),
    )

    plan = [{"skill": "write_cases_batch", "desc": "批量生成", "params": {"test_points": []}}]
    task_db = _make_task_db()
    ex = TaskExecutor(_make_ctx())
    ex.run(task_id=1, plan=plan, task_db=task_db)

    # 取最后一次 update_task_status 的 result 参数
    status_call = task_db.update_task_status.call_args_list[-1]
    assert status_call.args[1] == TaskStatus.DONE
    result = status_call.kwargs.get("result") or status_call.args[2]
    # batch_id 顶到顶层（Step 3 新增的汇总逻辑）
    assert result["batch_id"] == "batch-1-1700000000"
    # step 结果保留原始 case_ids 数组（在 steps[0] 里）
    assert result["steps"][0]["case_ids"] == [10, 11, 12]


def test_executor_no_batch_id_when_skill_lacks_it(monkeypatch):
    """普通 skill（无 batch_id）执行后 result_summary 不应含 batch_id 键。"""
    from insight_aitest.modules.ai.backend.agent import executor as exec_mod
    from insight_aitest.modules.ai.backend.agent.skills import SkillSpec

    def plain_skill(params, ctx):
        return {"case_id": 5, "title": "普通用例"}

    monkeypatch.setitem(
        exec_mod.SKILLS, "write_functional_case",
        SkillSpec(id="write_functional_case", name="写", description="",
                  params_description="", execute=plain_skill),
    )

    plan = [{"skill": "write_functional_case", "desc": "生成", "params": {"query": "x"}}]
    task_db = _make_task_db()
    ex = TaskExecutor(_make_ctx())
    ex.run(task_id=1, plan=plan, task_db=task_db)

    status_call = task_db.update_task_status.call_args_list[-1]
    result = status_call.kwargs.get("result") or status_call.args[2]
    assert "batch_id" not in result
