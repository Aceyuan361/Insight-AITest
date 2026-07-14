# tests/ai/test_reactor.py
# -*- coding: utf-8 -*-
"""ReActAgent 核心测试。"""
from insight_aitest.modules.ai.backend.agent.reactor import (
    ReActConfig, StepBudget, TraceEntry, ReActEvent
)


def test_react_config_defaults():
    cfg = ReActConfig()
    assert cfg.enabled is True
    assert cfg.max_iterations == 8
    assert cfg.budget.retry_budget == 2
    assert cfg.budget.fix_budget == 2
    assert cfg.budget.consecutive_fail_limit == 3
    assert cfg.observation_max_chars == 2000


def test_react_config_from_dict():
    cfg = ReActConfig.from_dict({
        "enabled": False, "max_iterations": 5,
        "budget": {"retry": 1, "fix": 3, "consecutive_fail": 2},
    })
    assert cfg.enabled is False
    assert cfg.max_iterations == 5
    assert cfg.budget.retry_budget == 1
    assert cfg.budget.fix_budget == 3
    assert cfg.budget.consecutive_fail_limit == 2


def test_trace_entry_serializable():
    entry = TraceEntry(
        step_index=0, iteration=1,
        action={"skill": "execute_api_case", "desc": "测登录"},
        observation={"status": "failed"},
        reflection={"thought": "token 过期", "decision": "fix"},
        decision="fix",
    )
    d = entry.to_dict()
    assert d["decision"] == "fix"
    assert d["action"]["skill"] == "execute_api_case"


# ===== ReActAgent 核心行为测试（TDD） =====

from unittest.mock import MagicMock  # noqa: E402
from insight_aitest.modules.ai.backend.agent.reactor import ReActAgent  # noqa: E402
from insight_aitest.modules.ai.backend.agent.executor import TaskExecutor  # noqa: E402
from insight_aitest.modules.ai.backend.agent.skills import SkillContext, SkillSpec  # noqa: E402
from insight_aitest.modules.ai.backend.persistence.models import TaskStatus  # noqa: E402


def _make_ctx():
    return SkillContext(
        llm=MagicMock(), config=MagicMock(), retriever=MagicMock(),
        generator=MagicMock(), case_db=MagicMock(),
    )


def _make_task_db():
    db = MagicMock()
    db.get_task.return_value = MagicMock(status=TaskStatus.RUNNING)
    return db


class FakeLLM:
    """可控反思 LLM：每次 chat 返回固定 decision JSON。"""
    def __init__(self, decisions):
        self.decisions = decisions
        self.call_idx = 0
    def chat(self, messages, **kwargs):
        dec = self.decisions[min(self.call_idx, len(self.decisions) - 1)]
        self.call_idx += 1
        return f'{{"thought":"t","decision":"{dec}","reasoning":"r","confidence":0.8}}'


def _inject_skills(monkeypatch, exec_module, exec_fn, fix_fn=None, analyze_fn=None):
    monkeypatch.setitem(exec_module.SKILLS, "execute_api_case",
        SkillSpec(id="execute_api_case", name="执行", description="", params_description="", execute=exec_fn))
    if fix_fn:
        monkeypatch.setitem(exec_module.SKILLS, "fix_api_case",
            SkillSpec(id="fix_api_case", name="修复", description="", params_description="", execute=fix_fn))
    if analyze_fn:
        monkeypatch.setitem(exec_module.SKILLS, "analyze_failure",
            SkillSpec(id="analyze_failure", name="分析", description="", params_description="", execute=analyze_fn))


def test_react_continue_on_pass(monkeypatch):
    """首次 pass → 跳过反思 → continue（不调 LLM）。"""
    from insight_aitest.modules.ai.backend.agent import executor as exec_mod
    def fake_exec(params, ctx):
        return {"status": "passed", "case_id": 1}
    _inject_skills(monkeypatch, exec_mod, fake_exec)
    llm = FakeLLM(["continue"])
    executor = TaskExecutor(_make_ctx())
    agent = ReActAgent(executor, llm, MagicMock(), ReActConfig())
    task_db = _make_task_db()
    plan = [{"skill": "execute_api_case", "desc": "测登录", "params": {}}]
    agent.run(task_id=1, plan=plan, task_db=task_db)
    assert llm.call_idx == 0  # LLM not called
    status_call = task_db.update_task_status.call_args_list[-1]
    assert status_call.args[1] == TaskStatus.DONE


def test_react_fix_then_pass(monkeypatch):
    """失败 → 反思 fix → 修复 → 重执行 pass。"""
    from insight_aitest.modules.ai.backend.agent import executor as exec_mod
    call = {"n": 0}
    def fake_exec(params, ctx):
        call["n"] += 1
        return {"status": "passed"} if call["n"] >= 2 else {"status": "failed", "failures": [{"msg": "401"}], "case_id": 1, "run_id": 1}
    def fake_analyze(params, ctx):
        return {"root_cause": "token 过期", "analysis": "", "suggested_fix": ""}
    def fake_fix(params, ctx):
        return {"case_id": 1, "fixed": True, "content": {}}
    _inject_skills(monkeypatch, exec_mod, fake_exec, fix_fn=fake_fix, analyze_fn=fake_analyze)
    llm = FakeLLM(["fix", "continue"])
    executor = TaskExecutor(_make_ctx())
    agent = ReActAgent(executor, llm, MagicMock(), ReActConfig())
    task_db = _make_task_db()
    plan = [{"skill": "execute_api_case", "desc": "测登录", "params": {}, "loop": {"enabled": True}}]
    agent.run(task_id=1, plan=plan, task_db=task_db)
    assert call["n"] == 2
    status_call = task_db.update_task_status.call_args_list[-1]
    assert status_call.args[1] == TaskStatus.DONE


def test_react_abort_on_consecutive_failures(monkeypatch):
    """连续失败超 consecutive_fail_limit → abort。"""
    from insight_aitest.modules.ai.backend.agent import executor as exec_mod
    def fake_exec(params, ctx):
        return {"status": "failed", "failures": [{"msg": "503"}], "case_id": 1, "run_id": 1}
    _inject_skills(monkeypatch, exec_mod, fake_exec)
    llm = FakeLLM(["retry", "retry", "retry"])
    executor = TaskExecutor(_make_ctx())
    cfg = ReActConfig(budget=StepBudget(retry_budget=1, fix_budget=0, consecutive_fail_limit=3))
    agent = ReActAgent(executor, llm, MagicMock(), cfg)
    task_db = _make_task_db()
    plan = [{"skill": "execute_api_case", "desc": "测支付", "params": {}, "loop": {"enabled": True}}]
    agent.run(task_id=1, plan=plan, task_db=task_db)
    status_call = task_db.update_task_status.call_args_list[-1]
    assert status_call.args[1] == TaskStatus.FAILED


def test_react_fix_ui_case(monkeypatch):
    """UI 用例失败 → fix → 调 fix_ui_case（非 fix_api_case）。"""
    from insight_aitest.modules.ai.backend.agent import executor as exec_mod
    from insight_aitest.modules.ai.backend.agent.skills import SkillSpec
    call = {"n": 0, "fix_called": {"api": 0, "ui": 0}}
    def fake_exec(params, ctx):
        call["n"] += 1
        return {"status": "passed"} if call["n"] >= 2 else {"status": "failed", "failures": [{"msg": "元素未找到"}], "case_id": 5, "run_id": 1}
    def fake_analyze(params, ctx):
        return {"root_cause": "元素定位变化", "analysis": "", "suggested_fix": ""}
    def fake_fix_ui(params, ctx):
        call["fix_called"]["ui"] += 1
        return {"case_id": 5, "fixed": True, "content": {}}
    def fake_fix_api(params, ctx):
        call["fix_called"]["api"] += 1
        return {"case_id": 5, "fixed": True}
    monkeypatch.setitem(exec_mod.SKILLS, "execute_ui_case", SkillSpec(id="execute_ui_case", name="执行", description="", params_description="", execute=fake_exec))
    monkeypatch.setitem(exec_mod.SKILLS, "analyze_failure", SkillSpec(id="analyze_failure", name="分析", description="", params_description="", execute=fake_analyze))
    monkeypatch.setitem(exec_mod.SKILLS, "fix_ui_case", SkillSpec(id="fix_ui_case", name="修复UI", description="", params_description="", execute=fake_fix_ui))
    monkeypatch.setitem(exec_mod.SKILLS, "fix_api_case", SkillSpec(id="fix_api_case", name="修复API", description="", params_description="", execute=fake_fix_api))
    llm = FakeLLM(["fix", "continue"])
    executor = TaskExecutor(_make_ctx())
    agent = ReActAgent(executor, llm, MagicMock(), ReActConfig())
    task_db = _make_task_db()
    plan = [{"skill": "execute_ui_case", "desc": "测UI", "params": {}, "loop": {"enabled": True}}]
    agent.run(task_id=1, plan=plan, task_db=task_db)
    assert call["fix_called"]["ui"] == 1
    assert call["fix_called"]["api"] == 0


def test_react_max_iterations_enforced(monkeypatch):
    """max_iterations 超限 → abort，reason 为 max_iterations_reached，且 react_stats 含迭代计数。"""
    from insight_aitest.modules.ai.backend.agent import executor as exec_mod
    def fake_exec(params, ctx):
        return {"status": "failed", "failures": [{"msg": "断言失败"}], "case_id": 9, "run_id": 1}
    _inject_skills(monkeypatch, exec_mod, fake_exec)
    # 一直要求 retry，迫使循环只能靠 max_iterations 收口
    llm = FakeLLM(["retry"])
    executor = TaskExecutor(_make_ctx())
    cfg = ReActConfig(
        max_iterations=1,
        budget=StepBudget(retry_budget=99, fix_budget=0, consecutive_fail_limit=99),
    )
    agent = ReActAgent(executor, llm, MagicMock(), cfg)
    task_db = _make_task_db()
    plan = [{"skill": "execute_api_case", "desc": "测限流", "params": {}, "loop": {"enabled": True}}]
    agent.run(task_id=1, plan=plan, task_db=task_db)
    status_call = task_db.update_task_status.call_args_list[-1]
    assert status_call.args[1] == TaskStatus.FAILED
    result = status_call.kwargs["result"]
    assert result["aborted"] is True
    assert "max_iterations" in result["reason"] or result["reason"] == "max_iterations_reached"
    stats = result["react_stats"]
    assert stats["total_iterations"] >= 1
    assert stats["total_retries"] >= 1


# ===== 代码审查修复回归测试 =====

def _capture_events(agent):
    """劫持 agent._make_emit，返回 (emit_fn, events_list)。"""
    events: list[ReActEvent] = []
    def _emit(event: ReActEvent) -> None:
        events.append(event)
    agent._make_emit = lambda queue, loop: _emit
    return _emit, events


def test_c1_unknown_decision_falls_back_to_string(monkeypatch):
    """C1: LLM 返回非法 decision（如 'banana'）→ 降级为合法字符串，不应是 dict。"""
    from insight_aitest.modules.ai.backend.agent import executor as exec_mod
    def fake_exec(params, ctx):
        # 持续失败，触发反思；error 字段会让降级反思返回 "abort"
        return {"error": "engine boom", "case_id": 1, "run_id": 1}
    _inject_skills(monkeypatch, exec_mod, fake_exec)

    # FakeLLM 返回非法 decision 字符串
    class BadDecisionLLM:
        def chat(self, messages, **kwargs):
            return '{"thought":"t","decision":"banana","reasoning":"r","confidence":0.8}'

    llm = BadDecisionLLM()
    executor = TaskExecutor(_make_ctx())
    agent = ReActAgent(executor, llm, MagicMock(), ReActConfig())
    _, events = _capture_events(agent)
    task_db = _make_task_db()
    plan = [{"skill": "execute_api_case", "desc": "测", "params": {}, "loop": {"enabled": True}}]
    agent.run(task_id=1, plan=plan, task_db=task_db)

    # 所有 decision 事件里的 decision 必须是合法字符串，绝不可能是 dict
    decision_events = [e for e in events if e.type == "decision"]
    assert decision_events, "应至少有一个 decision 事件"
    for e in decision_events:
        d = e.data["decision"]
        assert isinstance(d, str), f"decision 必须是字符串，实际 {type(d).__name__}: {d!r}"
        assert d in ("continue", "retry", "fix", "abort"), f"非法 decision: {d!r}"
    # error 类失败降级为 abort
    assert decision_events[0].data["decision"] == "abort"


def test_i1_observation_event_flat_shape(monkeypatch):
    """I1: _run_step_react 的 observation 事件扁平化——status/failures 在顶层。"""
    from insight_aitest.modules.ai.backend.agent import executor as exec_mod
    def fake_exec(params, ctx):
        return {"status": "failed", "failures": [{"msg": "401"}], "case_id": 2, "run_id": 1}
    def fake_analyze(params, ctx):
        return {"root_ause": "token", "analysis": "", "suggested_fix": ""}
    def fake_fix(params, ctx):
        return {"case_id": 2, "fixed": True, "content": {}}
    _inject_skills(monkeypatch, exec_mod, fake_exec, fix_fn=fake_fix, analyze_fn=fake_analyze)
    llm = FakeLLM(["fix", "continue"])  # 第一次失败 fix，修复后 pass
    executor = TaskExecutor(_make_ctx())
    agent = ReActAgent(executor, llm, MagicMock(), ReActConfig())
    _, events = _capture_events(agent)
    task_db = _make_task_db()
    plan = [{"skill": "execute_api_case", "desc": "测", "params": {}, "loop": {"enabled": True}}]
    agent.run(task_id=1, plan=plan, task_db=task_db)

    obs_events = [e for e in events if e.type == "observation"]
    assert obs_events, "应有 observation 事件"
    # 找到 execute_api_case 的 observation（status 在顶层的）
    exec_obs = [e for e in obs_events if e.data.get("skill") == "execute_api_case"]
    assert exec_obs, "execute_api_case 的 observation 缺失"
    data = exec_obs[0].data
    # 扁平：status/failures 在顶层，不应再嵌套在 data["observation"] 下
    assert data["status"] == "failed"
    assert data["failures"] == [{"msg": "401"}]
    assert "observation" not in data, "observation 字段不应再嵌套（旧 bug）"
    # skill + iteration 在顶层
    assert data["skill"] == "execute_api_case"
    assert "iteration" in data and isinstance(data["iteration"], int)


def test_i2_do_fix_observation_has_iteration(monkeypatch):
    """I2: _do_fix 的 analyze/fix observation 事件必须带 iteration。"""
    from insight_aitest.modules.ai.backend.agent import executor as exec_mod
    def fake_exec(params, ctx):
        return {"status": "failed", "failures": [{"msg": "x"}], "case_id": 3, "run_id": 1}
    def fake_analyze(params, ctx):
        return {"root_cause": "rc", "analysis": "a", "suggested_fix": "s"}
    def fake_fix(params, ctx):
        return {"case_id": 3, "fixed": True, "content": {}}
    _inject_skills(monkeypatch, exec_mod, fake_exec, fix_fn=fake_fix, analyze_fn=fake_analyze)
    llm = FakeLLM(["fix", "continue"])
    executor = TaskExecutor(_make_ctx())
    agent = ReActAgent(executor, llm, MagicMock(), ReActConfig())
    _, events = _capture_events(agent)
    task_db = _make_task_db()
    plan = [{"skill": "execute_api_case", "desc": "测", "params": {}, "loop": {"enabled": True}}]
    agent.run(task_id=1, plan=plan, task_db=task_db)

    fix_obs = [e for e in events if e.type == "observation"
               and e.data.get("skill") in ("analyze_failure", "fix_api_case")]
    assert len(fix_obs) == 2, f"应有两个 fix 路径 observation，实际 {len(fix_obs)}"
    skills = {e.data["skill"] for e in fix_obs}
    assert skills == {"analyze_failure", "fix_api_case"}
    for e in fix_obs:
        # I2 核心：iteration 必须在顶层
        assert "iteration" in e.data, f"observation 事件缺 iteration: {e.data}"
        assert isinstance(e.data["iteration"], int)
        assert "step_index" in e.data
        # 扁平：result 或 error 在顶层
        assert ("result" in e.data) or ("error" in e.data)


def test_i3_non_reflect_path_continue_on_error(monkeypatch):
    """I3: 非反思步骤出错 → continue（不中途 abort），多步继续执行。

    旧 executor 是 continue-on-error；C3 回归 bug 会把单步错误升级为 abort 整个任务。
    """
    from insight_aitest.modules.ai.backend.agent import executor as exec_mod
    from insight_aitest.modules.ai.backend.agent.skills import SkillSpec
    calls = {"n": 0}
    def fake_exec(params, ctx):
        calls["n"] += 1
        # 第一步（write_cases 类，无 loop.enabled）出错；第二步正常
        if calls["n"] == 1:
            return {"error": "boom"}
        return {"case_id": 7}
    # 注入非执行类 skill（write_cases），使其能被 _run_single_step 找到
    monkeypatch.setitem(exec_mod.SKILLS, "write_cases",
        SkillSpec(id="write_cases", name="写用例", description="", params_description="", execute=fake_exec))
    llm = FakeLLM([])  # 非反思路径不调 LLM
    executor = TaskExecutor(_make_ctx())
    agent = ReActAgent(executor, llm, MagicMock(), ReActConfig())
    task_db = _make_task_db()
    # 两步都没开 loop.enabled → 都走非反思路径
    plan = [
        {"skill": "write_cases", "desc": "写用例", "params": {}},
        {"skill": "write_cases", "desc": "再写", "params": {}},
    ]
    agent.run(task_id=1, plan=plan, task_db=task_db)

    # 关键断言：两步都被执行（第一步错误没有中止后续步骤）
    assert calls["n"] == 2, f"第一步错误不应中止任务；应执行 2 步，实际 {calls['n']}"
    # 最终状态：有 case_id 生成 → DONE（即便有错误）
    status_call = task_db.update_task_status.call_args_list[-1]
    assert status_call.args[1] == TaskStatus.DONE


def test_m2_retry_budget_exhausted_aborts_without_pointless_reexec(monkeypatch):
    """M2: retry 预算耗尽后不再无意义重执行，直接 abort 省 token。

    旧实现：retry_budget 耗尽后 continue 重 EXECUTE（结果不变），直到
    consecutive_fail_limit 触发，浪费 LLM/执行调用。
    新实现：预算耗尽立即 abort，reason=retry_budget_exhausted。
    """
    from insight_aitest.modules.ai.backend.agent import executor as exec_mod
    exec_calls = {"n": 0}
    def fake_exec(params, ctx):
        exec_calls["n"] += 1
        return {"status": "failed", "failures": [{"msg": "503"}], "case_id": 1, "run_id": 1}
    _inject_skills(monkeypatch, exec_mod, fake_exec)
    # LLM 持续要求 retry
    llm = FakeLLM(["retry", "retry", "retry"])
    executor = TaskExecutor(_make_ctx())
    # retry_budget=1：第一次 retry 消耗预算，第二次 retry 决策时预算已耗尽 → 立即 abort
    cfg = ReActConfig(budget=StepBudget(retry_budget=1, fix_budget=0, consecutive_fail_limit=10))
    agent = ReActAgent(executor, llm, MagicMock(), cfg)
    task_db = _make_task_db()
    plan = [{"skill": "execute_api_case", "desc": "测支付", "params": {}, "loop": {"enabled": True}}]
    agent.run(task_id=1, plan=plan, task_db=task_db)

    # 最终 FAILED（abort）
    status_call = task_db.update_task_status.call_args_list[-1]
    assert status_call.args[1] == TaskStatus.FAILED
    # EXECUTE 只被调 2 次：iter1（首次执行）+ iter2（retry 执行），iter2 后预算耗尽 abort，
    # 不再有第 3 次无意义的重执行
    assert exec_calls["n"] == 2, f"预算耗尽后不应重执行，期望 2 次，实际 {exec_calls['n']}"


def test_m2_fix_budget_exhausted_remaps_to_continue(monkeypatch):
    """M2 + spec A3: fix 预算耗尽后，LLM 决策 fix 被重映射为 continue（接受失败）。

    spec A3：fix_budget 耗尽 → 反思只能 continue 或 abort。这里实现选 continue
    （由 any_failed/case_ids 决定任务终态），避免无意义的重复 EXECUTE。
    """
    from insight_aitest.modules.ai.backend.agent import executor as exec_mod
    exec_calls = {"n": 0}
    def fake_exec(params, ctx):
        exec_calls["n"] += 1
        return {"status": "failed", "failures": [{"msg": "断言失败"}], "case_id": 1, "run_id": 1}
    def fake_analyze(params, ctx):
        return {"root_cause": "x", "analysis": "", "suggested_fix": ""}
    def fake_fix(params, ctx):
        return {"case_id": 1, "fixed": True, "content": {}}
    _inject_skills(monkeypatch, exec_mod, fake_exec, fix_fn=fake_fix, analyze_fn=fake_analyze)
    # LLM 持续要求 fix
    llm = FakeLLM(["fix", "fix", "fix"])
    executor = TaskExecutor(_make_ctx())
    # fix_budget=1：第一次 fix 消耗预算；第二次 fix 决策时预算耗尽 → 重映射 continue
    cfg = ReActConfig(budget=StepBudget(retry_budget=0, fix_budget=1, consecutive_fail_limit=10))
    agent = ReActAgent(executor, llm, MagicMock(), cfg)
    task_db = _make_task_db()
    plan = [{"skill": "execute_api_case", "desc": "测登录", "params": {}, "loop": {"enabled": True}}]
    agent.run(task_id=1, plan=plan, task_db=task_db)

    # EXECUTE 只被调 2 次：iter1（首次）+ iter2（fix 后重执行），之后 fix 耗尽 → continue（不再重执行）
    assert exec_calls["n"] == 2, f"预算耗尽后不应重执行，期望 2 次，实际 {exec_calls['n']}"
    # 终态：有 case_id（obs 带 case_id:1），any_failed 但有 case → DONE（continue-on-error 语义）
    status_call = task_db.update_task_status.call_args_list[-1]
    assert status_call.args[1] == TaskStatus.DONE


def test_m2_retry_exhausted_remaps_to_fix_when_fix_available(monkeypatch):
    """M2 + spec A3: retry 预算耗尽但 fix 预算有余 → retry 重映射为 fix（保留恢复路径）。"""
    from insight_aitest.modules.ai.backend.agent import executor as exec_mod
    exec_calls = {"n": 0}
    fix_calls = {"n": 0}
    def fake_exec(params, ctx):
        exec_calls["n"] += 1
        return {"status": "failed", "failures": [{"msg": "503"}], "case_id": 1, "run_id": 1}
    def fake_analyze(params, ctx):
        return {"root_cause": "x", "analysis": "", "suggested_fix": ""}
    def fake_fix(params, ctx):
        fix_calls["n"] += 1
        return {"case_id": 1, "fixed": True, "content": {}}
    _inject_skills(monkeypatch, exec_mod, fake_exec, fix_fn=fake_fix, analyze_fn=fake_analyze)
    # LLM 一直要求 retry
    llm = FakeLLM(["retry", "retry", "retry", "retry"])
    executor = TaskExecutor(_make_ctx())
    # retry_budget=1, fix_budget=2：iter1 retry 消耗；iter2 retry 耗尽→重映射 fix；iter3 fix 后重执行仍 fail→retry 又耗尽→fix；iter4 fix 耗尽→retry 耗尽→abort
    cfg = ReActConfig(budget=StepBudget(retry_budget=1, fix_budget=2, consecutive_fail_limit=10))
    agent = ReActAgent(executor, llm, MagicMock(), cfg)
    task_db = _make_task_db()
    plan = [{"skill": "execute_api_case", "desc": "测支付", "params": {}, "loop": {"enabled": True}}]
    agent.run(task_id=1, plan=plan, task_db=task_db)

    # 至少触发过 fix（说明 retry→fix 重映射生效）
    assert fix_calls["n"] >= 1, "retry 耗尽应重映射到 fix（fix 预算有余时）"
    # 最终 abort（retry 和 fix 预算都耗尽）
    status_call = task_db.update_task_status.call_args_list[-1]
    assert status_call.args[1] == TaskStatus.FAILED
