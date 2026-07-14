# -*- coding: utf-8 -*-
"""Agent run_api_suite skill 测试：套件执行 + 回归判定。

用 httpx.MockTransport 顶替真实网络，不依赖外部服务。
"""
from __future__ import annotations

from unittest.mock import MagicMock

import httpx

from insight_aitest.modules.ai.backend.agent.skills import (
    SKILLS,
    SkillContext,
    _run_api_suite,
)
from insight_aitest.modules.testcase.backend.persistence.models import (
    CaseStatus,
    CaseType,
    TestCase,
    TestType,
)


# ===== 公共夹具 =====

BASE = "https://test.local"


def _handler(request: httpx.Request) -> httpx.Response:
    p = request.url.path
    if request.method == "GET" and p == "/ok":
        return httpx.Response(200, json={"ok": True})
    if request.method == "GET" and p == "/fail":
        return httpx.Response(500, json={"err": "boom"})
    return httpx.Response(404, text="?")


def _transport():
    return httpx.MockTransport(_handler)


def _make_case(case_id: int, path: str, last_result: str | None = None) -> TestCase:
    """构造一个 API 用例。path 决定执行结果（/ok 通过，/fail 失败）。"""
    case = TestCase(
        title=f"用例{case_id}",
        type=CaseType.API,
        status=CaseStatus.READY,
        test_design=TestType.POSITIVE,
        content={
            "base_url": BASE,
            "steps": [
                {"method": "GET", "path": path, "headers": {}, "body": {},
                 "assertions": [{"type": "status_code", "expected": 200}]},
            ],
        },
    )
    case.id = case_id
    case.last_result = last_result
    return case


def _make_ctx(cases: dict[int, TestCase], tmp_path) -> tuple[SkillContext, MagicMock]:
    """构造带 Mock case_db / run_db / suite_run_db 的 SkillContext。"""
    case_db = MagicMock()
    case_db.get_case.side_effect = lambda cid: cases.get(cid)
    # update_result 模拟回填：更新内存 case 的 last_result
    def _update_result(cid, result, run_at=None):
        if cid in cases:
            cases[cid].last_result = result
    case_db.update_result.side_effect = _update_result

    run_db = MagicMock()
    run_db.create_run.side_effect = lambda run: id(run)  # 用对象 id 作假 run_id

    suite_db = MagicMock()
    suite_run_db = MagicMock()
    suite_run_db.create.return_value = 100  # suite_run_id
    suite_run_db.finish = MagicMock()
    suite_run_db.update_setup_status = MagicMock()

    ctx = SkillContext(
        llm=MagicMock(),
        config=MagicMock(chat_model="fake"),
        retriever=MagicMock(),
        generator=MagicMock(),
        case_db=case_db,
        project_id=None,
        version_id=None,
        api_run_db=run_db,
        http_transport=_transport(),
        suite_db=suite_db,
        suite_run_db=suite_run_db,
    )
    return ctx, suite_run_db


# ===== 测试 =====


def test_run_api_suite_all_pass(tmp_path):
    """两条用例都通过 → status=completed，无回归。"""
    cases = {
        1: _make_case(1, "/ok"),
        2: _make_case(2, "/ok"),
    }
    ctx, suite_run_db = _make_ctx(cases, tmp_path)

    result = _run_api_suite({"case_ids": [1, 2]}, ctx)

    assert result["status"] == "completed"
    assert result["done"] == 2
    assert result["total"] == 2
    assert result["regression_count"] == 0
    assert result["regressions"] == []
    assert len(result["case_results"]) == 2
    suite_run_db.finish.assert_called_once()


def test_run_api_suite_regression_detection(tmp_path):
    """回归：case1 之前 passed 现在 failed → 检测到回归；case2 一直 passed → 无回归。"""
    cases = {
        1: _make_case(1, "/fail", last_result="passed"),  # 之前通过，现在失败
        2: _make_case(2, "/ok", last_result="passed"),    # 一直通过
    }
    ctx, suite_run_db = _make_ctx(cases, tmp_path)

    result = _run_api_suite({"case_ids": [1, 2]}, ctx)

    assert result["status"] == "failed"  # 有 case 失败
    assert result["regression_count"] == 1
    assert 1 in result["regressions"]
    assert 2 not in result["regressions"]
    # case_results 有回归标记
    cr1 = next(c for c in result["case_results"] if c["case_id"] == 1)
    assert cr1["regression"] is True
    assert cr1["baseline"] == "passed"
    assert cr1["current"] == "failed"


def test_run_api_suite_no_regression_on_newly_failing(tmp_path):
    """非回归：case 之前没跑过（last_result=None）现在失败 → 不算回归。"""
    cases = {1: _make_case(1, "/fail", last_result=None)}
    ctx, _ = _make_ctx(cases, tmp_path)

    result = _run_api_suite({"case_ids": [1]}, ctx)

    assert result["status"] == "failed"
    assert result["regression_count"] == 0  # 没基线，不算回归


def test_run_api_suite_missing_suite_db(tmp_path):
    """suite_run_db 未注入 → 抛 RuntimeError。"""
    cases = {}
    ctx, _ = _make_ctx(cases, tmp_path)
    ctx.suite_run_db = None
    try:
        _run_api_suite({"case_ids": [1]}, ctx)
        assert False, "应抛 RuntimeError"
    except RuntimeError:
        pass


def test_run_api_suite_needs_case_ids_or_suite_id(tmp_path):
    """缺 case_ids 和 suite_id → 抛 ValueError。"""
    ctx, _ = _make_ctx({}, tmp_path)
    try:
        _run_api_suite({}, ctx)
        assert False, "应抛 ValueError"
    except ValueError:
        pass


def test_run_api_suite_registered():
    """run_api_suite 注册进 SKILLS，进 catalog。"""
    assert "run_api_suite" in SKILLS
    from insight_aitest.modules.ai.backend.agent.skills import get_skill_catalog
    assert "run_api_suite" in get_skill_catalog()
