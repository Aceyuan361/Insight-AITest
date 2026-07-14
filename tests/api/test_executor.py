# -*- coding: utf-8 -*-
"""执行引擎测试（httpx.MockTransport，无真实网络，spec E §4/§8）。"""
import httpx
from insight_aitest.modules.api.backend.engine.executor import execute
from insight_aitest.modules.api.backend.persistence.models import RunStatus


def _handler(request: httpx.Request) -> httpx.Response:
    """按 path/method 返回预设响应。"""
    p = request.url.path
    if request.method == "POST" and p == "/login":
        return httpx.Response(200, json={"data": {"token": "abc"}})
    if request.method == "GET" and p == "/me":
        return httpx.Response(200, json={"data": {"user": "x"}})
    if request.method == "GET" and p == "/notfound":
        return httpx.Response(404, json={"err": "no"})
    if request.method == "GET" and p == "/big":
        return httpx.Response(200, json={"data": "z" * 100_000})
    return httpx.Response(500, text="??")


def _transport():
    return httpx.MockTransport(_handler)


BASE = "https://test.local"
LOGIN_CASE = {
    "base_url": BASE,
    "steps": [
        {"method": "POST", "path": "/login", "headers": {}, "body": {},
         "assertions": [{"type": "status_code", "expected": 200}],
         "extract": {"token": "$.data.token"}},
        {"method": "GET", "path": "/me",
         "headers": {"Authorization": "Bearer {{token}}"}, "body": {},
         "assertions": [{"type": "status_code", "expected": 200},
                        {"type": "jsonpath", "path": "$.data.user", "expected": "x"}]},
    ],
}


def test_pass_chain():
    run = execute(LOGIN_CASE, transport=_transport())
    assert run.status == RunStatus.PASSED
    assert run.total_steps == 2
    assert run.passed_steps == 2
    # 变量提取串联：第 2 步 header 注入了 token
    assert run.steps[1].request["headers"]["Authorization"] == "Bearer abc"
    assert run.steps[1].extracts == {}  # 第 2 步无 extract


def test_assertion_fail_marks_failed():
    case = {"base_url": BASE, "steps": [
        {"method": "GET", "path": "/notfound", "headers": {}, "body": {},
         "assertions": [{"type": "status_code", "expected": 200}]}]}
    run = execute(case, transport=_transport())
    assert run.status == RunStatus.FAILED
    assert run.passed_steps == 0
    assert run.steps[0].passed is False


def test_error_does_not_short_circuit():
    # 第 1 步变量未定义 → error；后续步仍执行
    case = {"base_url": BASE, "steps": [
        {"method": "GET", "path": "/me", "headers": {"X": "{{nope}}"}, "body": {},
         "assertions": [{"type": "status_code", "expected": 200}]},
        {"method": "GET", "path": "/me", "headers": {}, "body": {},
         "assertions": [{"type": "status_code", "expected": 200}]}]}
    run = execute(case, transport=_transport())
    assert run.status == RunStatus.ERROR  # 任一步 error → error
    assert run.steps[0].error is not None
    assert run.steps[1].passed is True    # 后续步照跑


def test_network_error_marks_error():
    def boom(request):
        raise httpx.ConnectError("conn refused")
    case = {"base_url": BASE, "steps": [
        {"method": "GET", "path": "/me", "headers": {}, "body": {},
         "assertions": [{"type": "status_code", "expected": 200}]}]}
    run = execute(case, transport=httpx.MockTransport(boom))
    assert run.status == RunStatus.ERROR
    assert run.steps[0].status_code is None
    assert run.steps[0].error is not None


def test_extract_failure_marks_error():
    case = {"base_url": BASE, "steps": [
        {"method": "POST", "path": "/login", "headers": {}, "body": {},
         "assertions": [{"type": "status_code", "expected": 200}],
         "extract": {"nope": "$.data.does_not_exist"}}]}
    run = execute(case, transport=_transport())
    assert run.status == RunStatus.ERROR
    assert run.steps[0].error is not None


def test_response_body_truncated():
    case = {"base_url": BASE, "steps": [
        {"method": "GET", "path": "/big", "headers": {}, "body": {},
         "assertions": [{"type": "status_code", "expected": 200}]}]}
    run = execute(case, transport=_transport())
    body = run.steps[0].response_body
    assert isinstance(body, str)
    assert "[truncated]" in body
    assert len(body) < 100_000


def test_invalid_schema_raises():
    import pytest
    with pytest.raises(ValueError):
        execute({"no_base_url": True, "steps": []}, transport=_transport())
    with pytest.raises(ValueError):
        execute({"base_url": BASE, "steps": "not-a-list"}, transport=_transport())
