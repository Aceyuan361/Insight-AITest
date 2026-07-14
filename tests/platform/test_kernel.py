# -*- coding: utf-8 -*-
from fastapi.testclient import TestClient

from insight_aitest.platform.kernel import build_app


def test_build_app_has_platform_endpoints():
    app = build_app()
    client = TestClient(app)
    assert client.get("/api/platform/health").status_code == 200
    r = client.get("/api/platform/modules")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_build_app_root_returns_version():
    app = build_app()
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["version"] == "2.0.0"
