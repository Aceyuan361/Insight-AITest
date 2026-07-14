# -*- coding: utf-8 -*-
"""Agent 执行闭环 e2e 真实测试（live）。

真实 LLM（agnes key）驱动完整的执行 → 分析 → 修复 → 重试闭环。
被测 API 用 httpx.MockTransport 模拟（无需真实可执行目标服务）。

场景：用例 path 故意写错（/usre/login），MockTransport 对错误路径返回 404、
对正确路径 /user/login 返回 200。真实 LLM 的 analyze_failure 应识别路径拼写错误，
fix_api_case 应改对路径，重试后执行通过。

运行：pytest -m live tests/ai/test_e2e_agent_closed_loop.py
（需 ~/.insight_eye/llm_config.json 配好真实 key）
"""
from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from insight_aitest.modules.ai.backend.agent.skills import SkillContext, SKILLS
from insight_aitest.modules.testcase.backend.persistence.database import TestCaseDatabase
from insight_aitest.modules.testcase.backend.persistence.models import (
    CaseStatus,
    CaseType,
    TestCase,
    TestType,
)

live = pytest.mark.live

BASE = "https://test.local"


def _handler(request: httpx.Request) -> httpx.Response:
    """模拟被测 API：错误路径 404，正确路径 200。"""
    p = request.url.path
    if request.method == "POST" and p == "/user/login":
        return httpx.Response(200, json={"code": 0, "data": {"token": "abc"}})
    # 错误路径（/usre/login 拼写错误）→ 404
    return httpx.Response(404, json={"err": "not found"})


def _make_transport() -> httpx.MockTransport:
    return httpx.MockTransport(_handler)


def _seed_case(case_db: TestCaseDatabase) -> int:
    """向真实 case_db 插入一条 path 故意写错的 API 用例。"""
    case = TestCase(
        title="登录接口测试",
        type=CaseType.API,
        status=CaseStatus.DRAFT,
        test_design=TestType.POSITIVE,
        content={
            "base_url": BASE,
            "steps": [
                {
                    "method": "POST",
                    "path": "/usre/login",  # 故意拼错（user → usre）
                    "headers": {"Content-Type": "application/json"},
                    "body": {"username": "test", "password": "123456"},
                    "assertions": [
                        {"type": "status_code", "expected": 200},
                    ],
                }
            ],
        },
    )
    return case_db.create_case(case)


@live
def test_e2e_fix_loop_real_llm(tmp_path):
    """真实 LLM 驱动：execute(404) → analyze → fix(改对 path) → re-execute(200)。

    验证完整闭环：真实 LLM 能识别路径拼写错误并修复，重试后通过。
    """
    from insight_aitest.platform.services.llm.client import LLMClient
    from insight_aitest.platform.services.llm.config import load_config

    cfg = load_config()
    if not cfg.api_key_set:
        pytest.skip("LLM API key 未配置")

    # 真实 case_db（fix_api_case 需 update_case 后 get_case 读到新 content）
    case_db = TestCaseDatabase(str(tmp_path / "tc.db"))
    case_id = _seed_case(case_db)
    assert case_id > 0

    # 真实 run_db mock（只需 create_run 返回 id）
    run_db = MagicMock()
    run_db.create_run.side_effect = lambda run: run.id if hasattr(run, "id") else 1

    ctx = SkillContext(
        llm=LLMClient(cfg),
        config=cfg,
        retriever=MagicMock(),
        generator=MagicMock(),
        case_db=case_db,
        project_id=None,
        version_id=None,
        api_run_db=run_db,
        http_transport=_make_transport(),
    )

    # —— 第 1 次执行：path 错误 → 404 → failed ——
    exec_skill = SKILLS["execute_api_case"]
    result1 = exec_skill.execute({"case_id": case_id}, ctx)
    print(f"\n[live] 第1次执行: status={result1['status']}, failures={result1['failures']}")
    assert result1["status"] == "failed"
    assert result1["failures"][0]["status_code"] == 404

    # —— 真实 LLM 分析失败 ——
    analyze_skill = SKILLS["analyze_failure"]
    analysis = analyze_skill.execute(
        {"case_id": case_id, "run_id": result1["run_id"], "failures": result1["failures"]},
        ctx,
    )
    print(f"[live] 分析: root_cause={analysis['root_cause']!r}")
    print(f"[live] 建议: {analysis['suggested_fix']!r}")
    assert analysis["root_cause"]  # 有分析内容
    # 真实 LLM 应识别出路径/404 相关问题
    assert any(kw in (analysis["root_cause"] + analysis["analysis"] + analysis["suggested_fix"]).lower()
               for kw in ["路径", "path", "404", "not found", "拼写", "url", "login", "usre", "user"])

    # —— 真实 LLM 修复 content ——
    fix_skill = SKILLS["fix_api_case"]
    fix_result = fix_skill.execute(
        {"case_id": case_id, "analysis": analysis},
        ctx,
    )
    print(f"[live] 修复: fixed={fix_result['fixed']}")
    assert fix_result["fixed"] is True, f"LLM 修复未生效: {fix_result.get('reason', '')}"

    # 验证修复后的 content path 已改对
    fixed_case = case_db.get_case(case_id)
    fixed_path = fixed_case.content["steps"][0]["path"]
    print(f"[live] 修复后 path: {fixed_path}")
    assert "user" in fixed_path.lower(), f"修复后 path 应含 user: {fixed_path}"

    # —— 第 2 次执行：path 正确 → 200 → passed ——
    result2 = exec_skill.execute({"case_id": case_id}, ctx)
    print(f"[live] 第2次执行: status={result2['status']}, passed_steps={result2['passed_steps']}")
    assert result2["status"] == "passed"
    assert result2["failures"] == []


@live
def test_e2e_fix_loop_unfixable_stops_gracefully(tmp_path):
    """真实 LLM 遇到无法修复的失败（非路径拼写，而是断言逻辑错）时优雅停止。

    场景：断言期望 999 但 API 永远返回 200 → LLM 应尝试修复但无法通过
    （因为 MockTransport 只认 path，改 assertions 不影响响应）。
    验证不会无限循环。
    """
    from insight_aitest.platform.services.llm.client import LLMClient
    from insight_aitest.platform.services.llm.config import load_config

    cfg = load_config()
    if not cfg.api_key_set:
        pytest.skip("LLM API key 未配置")

    case_db = TestCaseDatabase(str(tmp_path / "tc.db"))
    case = TestCase(
        title="断言不可能通过",
        type=CaseType.API,
        status=CaseStatus.DRAFT,
        test_design=TestType.POSITIVE,
        content={
            "base_url": BASE,
            "steps": [
                {
                    "method": "POST",
                    "path": "/user/login",  # 正确路径，能返回 200
                    "headers": {"Content-Type": "application/json"},
                    "body": {"username": "test", "password": "123456"},
                    "assertions": [
                        {"type": "status_code", "expected": 999},  # 不可能通过
                    ],
                }
            ],
        },
    )
    case_id = case_db.create_case(case)

    run_db = MagicMock()
    run_db.create_run.side_effect = lambda run: 1

    ctx = SkillContext(
        llm=LLMClient(cfg),
        config=cfg,
        retriever=MagicMock(),
        generator=MagicMock(),
        case_db=case_db,
        project_id=None,
        version_id=None,
        api_run_db=run_db,
        http_transport=_make_transport(),
    )

    # 用 executor 的 fix loop（max_fixes=1），验证不会无限循环
    from insight_aitest.modules.ai.backend.agent.executor import TaskExecutor
    from insight_aitest.modules.ai.backend.persistence.database import AIDatabase
    from insight_aitest.modules.ai.backend.persistence.models import TaskStatus

    ai_db = AIDatabase(str(tmp_path / "ai.db"))
    task_id = ai_db.create_task("e2e 不可修复测试", uploaded_files=[])

    plan = [{
        "skill": "execute_api_case",
        "desc": "执行不可能通过的用例",
        "params": {"case_id": case_id},
        "loop": {"enabled": True, "max_fixes": 1},
    }]

    ex = TaskExecutor(ctx)
    ex.run(task_id=task_id, plan=plan, task_db=ai_db)

    # 验证 task 终态 + fix_rounds
    final_task = ai_db.get_task(task_id)
    print(f"\n[live] 终态: {final_task.status}")
    steps = final_task.result_json.get("steps", [])
    if steps:
        step0 = steps[0].get("result", {})
        print(f"[live] fix_rounds={step0.get('fix_rounds')}, status={step0.get('status')}")

    # 有 case_id → DONE（即使最终断言未通过）
    assert final_task.status == TaskStatus.DONE
