# -*- coding: utf-8 -*-
"""套件执行引擎测试（spec E.1 §3）。

不真起 BackgroundTasks，直接同步调 execute_suite 验证结果。
用 mock 的 case 提供 + MockTransport。
"""
import httpx
from insight_aitest.modules.api.backend.engine.suite_executor import execute_suite
from insight_aitest.modules.api.backend.persistence.suite_models import SuiteRunStatus


def _handler(req: httpx.Request) -> httpx.Response:
    p = req.url.path
    if req.method == "POST" and p == "/login":
        return httpx.Response(200, json={"data": {"token": "TKN"}})
    if req.method == "GET" and p == "/me":
        return httpx.Response(200, json={"data": {"user": "x"}})
    if req.method == "GET" and p == "/boom":
        return httpx.Response(500, text="err")
    return httpx.Response(200, json={"ok": True})


def _cases():
    """模拟从 D 读 case：{case_id: {title, content}}。"""
    return {
        1: {"title": "登录", "content": {"base_url": "https://x", "steps": [
            {"method": "POST", "path": "/login", "headers": {}, "body": {},
             "assertions": [{"type": "status_code", "expected": 200}],
             "extract": {"token": "$.data.token"}}]}},
        2: {"title": "查我", "content": {"base_url": "https://x", "steps": [
            {"method": "GET", "path": "/me", "headers": {}, "body": {},
             "assertions": [{"type": "status_code", "expected": 200}]}]}},
        3: {"title": "失败", "content": {"base_url": "https://x", "steps": [
            {"method": "GET", "path": "/boom", "headers": {}, "body": {},
             "assertions": [{"type": "status_code", "expected": 200}]}]}},
    }


def _suite_def(case_ids, setup=None, teardown=None):
    return {"id": 1, "name": "s", "case_ids": case_ids,
            "setup": setup or [], "teardown": teardown or []}


def test_all_pass():
    """两条 case 都过 → completed。"""
    transport = httpx.MockTransport(_handler)
    result = execute_suite(
        suite=_suite_def([1, 2]),
        cases_provider=lambda cid: _cases().get(cid),
        run_saver=lambda run: 100,  # mock：返回 run_id
        transport=transport,
        environment=None,
    )
    assert result["status"] == SuiteRunStatus.COMPLETED
    assert result["done"] == 2
    assert len(result["case_run_ids"]) == 2


def test_one_fail_marks_failed():
    """有 case 失败 → failed（但不中断，全部跑完）。"""
    transport = httpx.MockTransport(_handler)
    result = execute_suite(
        suite=_suite_def([2, 3]),
        cases_provider=lambda cid: _cases().get(cid),
        run_saver=lambda run: 200,
        transport=transport,
        environment=None,
    )
    assert result["status"] == SuiteRunStatus.FAILED
    assert result["done"] == 2  # 失败也跑了


def test_setup_provides_vars_to_cases():
    """setup 提取的变量注入所有 case。"""
    transport = httpx.MockTransport(_handler)
    # setup 登录拿 token，case 2 用 {{token}}
    setup = [{"method": "POST", "path": "/login", "headers": {}, "body": {},
              "assertions": [{"type": "status_code", "expected": 200}],
              "extract": {"token": "$.data.token"}}]
    case2 = {"title": "查我", "content": {"base_url": "https://x", "steps": [
        {"method": "GET", "path": "/me",
         "headers": {"Authorization": "Bearer {{token}}"}, "body": {},
         "assertions": [{"type": "status_code", "expected": 200}]}]}}
    cases = {2: case2}
    result = execute_suite(
        suite=_suite_def([2], setup=setup),
        cases_provider=lambda cid: cases.get(cid),
        run_saver=lambda run: 300,
        transport=transport,
        environment=None,
    )
    assert result["status"] == SuiteRunStatus.COMPLETED
    assert result["setup_status"] == "passed"


def test_setup_fail_skips_cases():
    """setup 失败 → 套件 failed，case 不跑。"""
    def boom_transport_handler(req):
        raise httpx.ConnectError("setup network down")
    transport = httpx.MockTransport(boom_transport_handler)
    result = execute_suite(
        suite=_suite_def([1, 2], setup=[
            {"method": "POST", "path": "/login", "headers": {}, "body": {},
             "assertions": [{"type": "status_code", "expected": 200}]}]),
        cases_provider=lambda cid: _cases().get(cid),
        run_saver=lambda run: 400,
        transport=transport,
        environment=None,
    )
    assert result["status"] == SuiteRunStatus.FAILED
    assert result["setup_status"] in ("error", "failed")
    assert result["done"] == 0  # case 没跑


def test_environment_overrides_base_url_and_vars():
    """环境覆盖 case base_url + 注入环境变量。"""
    transport = httpx.MockTransport(_handler)
    # case 用环境变量 {{env_user}}（来自环境）+ 环境的 base_url
    case1 = {"title": "查我", "content": {"base_url": "https://original", "steps": [
        {"method": "GET", "path": "/me", "headers": {"X-User": "{{env_user}}"}, "body": {},
         "assertions": [{"type": "status_code", "expected": 200}]}]}}
    env = type("E", (), {"base_url": "https://x", "variables": {"env_user": "alice"}})()
    result = execute_suite(
        suite=_suite_def([1]),
        cases_provider=lambda cid: case1 if cid == 1 else None,
        run_saver=lambda run: 500,
        transport=transport,
        environment=env,
    )
    assert result["status"] == SuiteRunStatus.COMPLETED


def test_missing_case_skipped():
    """case_ids 含不存在的 case → 跳过，记录错误。"""
    transport = httpx.MockTransport(_handler)
    result = execute_suite(
        suite=_suite_def([2, 999]),  # 999 不存在
        cases_provider=lambda cid: _cases().get(cid),
        run_saver=lambda run: 600,
        transport=transport,
        environment=None,
    )
    assert result["done"] == 1  # 只跑了存在的 1 条
