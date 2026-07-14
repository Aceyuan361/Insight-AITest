# -*- coding: utf-8 -*-
"""Agent 执行闭环 skill 测试：execute_api_case / analyze_failure / fix_api_case。

用 httpx.MockTransport 顶替真实网络，FakeLLM 顶替真实 LLM，不依赖 API key。
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import httpx

from insight_aitest.modules.ai.backend.agent.skills import (
    SKILLS,
    SkillContext,
    _execute_api_case,
    _analyze_failure,
    _fix_api_case,
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
        return httpx.Response(200, json={"data": {"id": 1}})
    if request.method == "GET" and p == "/notfound":
        return httpx.Response(404, json={"err": "no"})
    return httpx.Response(500, text="??")


def _transport():
    return httpx.MockTransport(_handler)


class FakeLLM:
    """假 LLM：chat 返回可控 JSON。"""

    def __init__(self, response: str = ""):
        self._response = response
        self.calls = []

    def chat(self, messages, **kwargs):
        self.calls.append(messages)
        return self._response


def _make_ctx(tmp_path, case: TestCase, llm_response: str = "") -> tuple[SkillContext, MagicMock]:
    """构造带 Mock run_db + Mock case_db 的 SkillContext。"""
    # case_db：只 mock 我们用到的方法
    case_db = MagicMock()
    case_db.get_case.return_value = case
    case_db.update_result = MagicMock()
    case_db.update_case = MagicMock()

    # run_db：mock create_run 返回固定 id
    run_db = MagicMock()
    run_db.create_run.return_value = 42

    ctx = SkillContext(
        llm=FakeLLM(llm_response),
        config=MagicMock(chat_model="fake-model"),
        retriever=MagicMock(),
        generator=MagicMock(),
        case_db=case_db,
        project_id=None,
        version_id=None,
        api_run_db=run_db,
        http_transport=_transport(),
    )
    return ctx, case_db


# ===== execute_api_case =====


def test_execute_api_case_pass(tmp_path):
    """断言通过 → status=passed，无 failures。"""
    case = TestCase(
        title="查列表",
        type=CaseType.API,
        status=CaseStatus.DRAFT,
        test_design=TestType.POSITIVE,
        content={
            "base_url": BASE,
            "steps": [
                {"method": "GET", "path": "/ok", "headers": {}, "body": {},
                 "assertions": [{"type": "status_code", "expected": 200}]},
            ],
        },
    )
    ctx, case_db = _make_ctx(tmp_path, case)

    result = _execute_api_case({"case_id": 1}, ctx)

    assert result["status"] == "passed"
    assert result["passed_steps"] == 1
    assert result["total_steps"] == 1
    assert result["case_id"] == 1
    assert result["run_id"] == 42
    assert result["failures"] == []
    # 回填被调用
    case_db.update_result.assert_called_once()


def test_execute_api_case_fail(tmp_path):
    """断言失败 → status=failed（不抛异常），failures 非空。"""
    case = TestCase(
        title="查不存在",
        type=CaseType.API,
        status=CaseStatus.DRAFT,
        test_design=TestType.NEGATIVE,
        content={
            "base_url": BASE,
            "steps": [
                {"method": "GET", "path": "/notfound", "headers": {}, "body": {},
                 "assertions": [{"type": "status_code", "expected": 200}]},
            ],
        },
    )
    ctx, case_db = _make_ctx(tmp_path, case)

    result = _execute_api_case({"case_id": 2}, ctx)

    assert result["status"] == "failed"
    assert result["passed_steps"] == 0
    assert len(result["failures"]) == 1
    assert result["failures"][0]["status_code"] == 404


def test_execute_api_case_missing_case(tmp_path):
    """用例不存在 → 抛 ValueError（记为 step_error）。"""
    ctx, case_db = _make_ctx(tmp_path, TestCase(title="x", type=CaseType.API, content={}))
    case_db.get_case.return_value = None

    try:
        _execute_api_case({"case_id": 999}, ctx)
        assert False, "应抛 ValueError"
    except ValueError:
        pass


def test_execute_api_case_no_run_db(tmp_path):
    """api_run_db 未注入 → 抛 RuntimeError。"""
    case = TestCase(
        title="x", type=CaseType.API, content={"base_url": BASE, "steps": []}
    )
    ctx, _ = _make_ctx(tmp_path, case)
    ctx.api_run_db = None
    try:
        _execute_api_case({"case_id": 1}, ctx)
        assert False, "应抛 RuntimeError"
    except RuntimeError:
        pass


# ===== analyze_failure =====


def test_analyze_failure_parses_llm_json(tmp_path):
    """LLM 返回合法 JSON → 提取 root_cause / analysis / suggested_fix。"""
    case = TestCase(title="登录", type=CaseType.API, content={"base_url": BASE, "steps": []})
    llm_resp = json.dumps({
        "root_cause": "路径拼写错误",
        "analysis": "期望200但返回404",
        "suggested_fix": "把 /usre 改为 /user",
    })
    ctx, _ = _make_ctx(tmp_path, case, llm_resp)

    result = _analyze_failure(
        {"case_id": 1, "run_id": 42, "failures": [{"step_index": 0, "status_code": 404}]},
        ctx,
    )

    assert result["root_cause"] == "路径拼写错误"
    assert result["analysis"] == "期望200但返回404"
    assert result["suggested_fix"] == "把 /usre 改为 /user"
    assert result["case_id"] == 1


def test_analyze_failure_fallback_on_bad_llm(tmp_path):
    """LLM 返回非 JSON → 降级机械摘要。"""
    case = TestCase(title="x", type=CaseType.API, content={})
    ctx, _ = _make_ctx(tmp_path, case, "我无法理解")

    result = _analyze_failure(
        {"case_id": 1, "failures": [{"step_index": 0}, {"step_index": 1}]},
        ctx,
    )

    assert result["root_cause"]  # 有降级值
    assert "2" in result["analysis"]  # 提到失败步数


# ===== fix_api_case =====


def test_fix_api_case_success(tmp_path):
    """LLM 返回合法 content → 校验通过 → 落库。"""
    case = TestCase(title="x", type=CaseType.API, content={"base_url": BASE, "steps": [
        {"method": "GET", "path": "/wrong", "assertions": [{"type": "status_code", "expected": 200}]}
    ]})
    fixed_content = {
        "base_url": BASE,
        "steps": [
            {"method": "GET", "path": "/ok",
             "assertions": [{"type": "status_code", "expected": 200}]}
        ],
    }
    ctx, case_db = _make_ctx(tmp_path, case, json.dumps(fixed_content))

    result = _fix_api_case(
        {"case_id": 1, "analysis": {"root_cause": "路径错", "analysis": "...", "suggested_fix": "改路径"}},
        ctx,
    )

    assert result["fixed"] is True
    case_db.update_case.assert_called_once()
    _, kwargs = case_db.update_case.call_args
    assert kwargs["content"]["steps"][0]["path"] == "/ok"


def test_fix_api_case_rejects_invalid_content(tmp_path):
    """LLM 返回不合法 content → fixed=False，不落库。"""
    case = TestCase(title="x", type=CaseType.API, content={})
    ctx, case_db = _make_ctx(tmp_path, case, json.dumps({"no_base_url": True}))

    result = _fix_api_case({"case_id": 1, "analysis": {}}, ctx)

    assert result["fixed"] is False
    case_db.update_case.assert_not_called()


def test_fix_api_case_fallback_on_bad_llm(tmp_path):
    """LLM 返回非 JSON → fixed=False。"""
    case = TestCase(title="x", type=CaseType.API, content={})
    ctx, case_db = _make_ctx(tmp_path, case, "无内容")

    result = _fix_api_case({"case_id": 1, "analysis": {}}, ctx)

    assert result["fixed"] is False
    case_db.update_case.assert_not_called()


# ===== 注册表 =====


def test_closed_loop_skills_registered():
    """3 个执行闭环 skill 注册进 SKILLS，进 catalog。"""
    assert "execute_api_case" in SKILLS
    assert "analyze_failure" in SKILLS
    assert "fix_api_case" in SKILLS

    from insight_aitest.modules.ai.backend.agent.skills import get_skill_catalog
    catalog = get_skill_catalog()
    assert "execute_api_case" in catalog
    assert "analyze_failure" in catalog
    assert "fix_api_case" in catalog
