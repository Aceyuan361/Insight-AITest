# -*- coding: utf-8 -*-
"""executor.execute 的 initial_vars 扩展测试（向后兼容，spec E.1 §3.1）。"""
import httpx
from insight_aitest.modules.api.backend.engine.executor import execute
from insight_aitest.modules.api.backend.persistence.models import RunStatus


def _transport(handler):
    return httpx.MockTransport(handler)


def test_initial_vars_injected_into_step():
    """initial_vars 中的变量能被 step 的 {{var}} 引用。"""
    def h(req):
        assert req.headers["Authorization"] == "Bearer PRESET"
        return httpx.Response(200, json={"ok": True})
    content = {"base_url": "https://x", "steps": [
        {"method": "GET", "path": "/me", "headers": {"Authorization": "Bearer {{token}}"},
         "body": {}, "assertions": [{"type": "status_code", "expected": 200}]}]}
    run = execute(content, transport=_transport(h),
                  initial_vars={"token": "PRESET"})
    assert run.status == RunStatus.PASSED


def test_step_extract_overrides_initial_vars():
    """step 提取的同名变量覆盖 initial_vars。"""
    def h(req):
        if req.url.path == "/login":
            return httpx.Response(200, json={"data": {"token": "FROM_STEP"}})
        return httpx.Response(200, json={"ok": True})
    content = {"base_url": "https://x", "steps": [
        {"method": "POST", "path": "/login", "headers": {}, "body": {},
         "assertions": [{"type": "status_code", "expected": 200}],
         "extract": {"token": "$.data.token"}},
        {"method": "GET", "path": "/me", "headers": {"Authorization": "Bearer {{token}}"},
         "body": {}, "assertions": [{"type": "status_code", "expected": 200}]}]}
    run = execute(content, transport=_transport(h),
                  initial_vars={"token": "PRESET"})
    assert run.status == RunStatus.PASSED
    # 第 2 步用的是 step 提取的 token，不是 initial_vars
    assert run.steps[1].request["headers"]["Authorization"] == "Bearer FROM_STEP"


def test_default_none_backward_compatible():
    """不传 initial_vars（默认 None）= E 首版原行为。"""
    def h(req):
        return httpx.Response(200, json={"ok": True})
    content = {"base_url": "https://x", "steps": [
        {"method": "GET", "path": "/me", "headers": {}, "body": {},
         "assertions": [{"type": "status_code", "expected": 200}]}]}
    run = execute(content, transport=_transport(h))
    assert run.status == RunStatus.PASSED
