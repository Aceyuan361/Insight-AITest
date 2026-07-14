# -*- coding: utf-8 -*-
from fastapi import FastAPI
from fastapi.testclient import TestClient

from insight_aitest.platform.api.platform import (
    build_platform_router,
    set_dashboard_provider,
    set_registry_view,
)


def _make_app(modules_view=None, dashboard_provider=None):
    if modules_view is not None:
        set_registry_view(modules_view)
    if dashboard_provider is not None:
        set_dashboard_provider(dashboard_provider)
    app = FastAPI()
    app.include_router(build_platform_router(), prefix="/api/platform")
    return app


def test_modules_endpoint_returns_list():
    app = _make_app(modules_view=lambda: [])
    client = TestClient(app)
    r = client.get("/api/platform/modules")
    assert r.status_code == 200
    assert r.json() == []


def test_modules_endpoint_returns_registry_view():
    sample = [{"id": "performance", "name": {"zh": "性能"}, "order": 1}]
    app = _make_app(modules_view=lambda: sample)
    client = TestClient(app)
    r = client.get("/api/platform/modules")
    assert r.status_code == 200
    assert r.json() == sample


def test_health_endpoint():
    app = _make_app()
    client = TestClient(app)
    r = client.get("/api/platform/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_dashboard_summary_returns_provider_data():
    """注入 provider 后 /dashboard/summary 返回其数据。"""
    data = {
        "executions": [{"id": 1, "module": "api", "status": "passed"}],
        "stats": {"api": {"total": 1, "passed": 1, "pass_rate": 1.0}},
        "testcases": {"total": 5, "by_result": {"passed": 3}},
        "monitoring": {"total_sessions": 2, "active_sessions": 1},
    }
    app = _make_app(dashboard_provider=lambda: data)
    client = TestClient(app)
    r = client.get("/api/platform/dashboard/summary")
    assert r.status_code == 200
    assert r.json() == data


def test_dashboard_summary_degrades_on_provider_error():
    """provider 抛异常时安全降级为空结构（不 500）。"""
    app = _make_app(dashboard_provider=_raise)
    client = TestClient(app)
    r = client.get("/api/platform/dashboard/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["executions"] == []
    assert body["stats"] == {}
    assert "testcases" in body


def _raise():
    raise RuntimeError("provider boom")
