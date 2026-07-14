# -*- coding: utf-8 -*-
"""E 执行/历史 API 集成测试（TestClient + mock D 回填，spec E §5）。"""
import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/login":
        return httpx.Response(200, json={"data": {"token": "abc"}})
    return httpx.Response(200, json={"ok": True})


def _setup_app(tmp_path, monkeypatch):
    import insight_aitest.modules.api.backend.deps as api_deps
    from insight_aitest.modules.api.backend.persistence.database import RunDatabase
    api_deps._run_db = RunDatabase(str(tmp_path / "api.db"))

    # mock D：execute 拉 D 用例 + 回填 D 结果。用 monkeypatch 拦截 httpx 调用
    monkeypatch.setattr(
        "insight_aitest.modules.api.backend.routes.runs._fetch_case_from_d",
        lambda case_id: {
            "id": case_id, "title": "登录用例", "type": "api", "status": "ready",
            "content": {"base_url": "https://test.local", "steps": [
                {"method": "POST", "path": "/login", "headers": {}, "body": {},
                 "assertions": [{"type": "status_code", "expected": 200}],
                 "extract": {"token": "$.data.token"}}]}},
    )
    monkeypatch.setattr(
        "insight_aitest.modules.api.backend.routes.runs._patch_result_to_d",
        lambda case_id, result, run_at: True,
    )
    # executor 用 MockTransport（monkeypatch 注入 transport 工厂）
    monkeypatch.setattr(
        "insight_aitest.modules.api.backend.routes.runs._make_transport",
        lambda: httpx.MockTransport(_handler),
    )

    from insight_aitest.modules.api.backend.routes import router as api_router
    app = FastAPI()
    app.include_router(api_router, prefix="/api/modules/api")
    return TestClient(app)


def test_execute_returns_run(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    r = c.post("/api/modules/api/runs/execute", json={"case_id": 1})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "passed"
    assert body["total_steps"] == 1
    assert body["case_title"] == "登录用例"
    assert len(body["steps"]) == 1
    assert body["steps"][0]["status_code"] == 200


def test_list_and_detail(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    c.post("/api/modules/api/runs/execute", json={"case_id": 1})
    c.post("/api/modules/api/runs/execute", json={"case_id": 2})

    lst = c.get("/api/modules/api/runs").json()
    assert len(lst) == 2
    assert "steps" not in lst[0]

    rid = lst[0]["id"]
    detail = c.get(f"/api/modules/api/runs/{rid}").json()
    assert "steps" in detail
    assert detail["id"] == rid


def test_list_filter(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    c.post("/api/modules/api/runs/execute", json={"case_id": 1})
    c.post("/api/modules/api/runs/execute", json={"case_id": 2})
    assert len(c.get("/api/modules/api/runs?case_id=1").json()) == 1


def test_delete(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    rid = c.post("/api/modules/api/runs/execute", json={"case_id": 1}).json()["id"]
    assert c.delete(f"/api/modules/api/runs/{rid}").status_code == 200
    assert c.get(f"/api/modules/api/runs/{rid}").status_code == 404


def test_execute_case_not_found(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "insight_aitest.modules.api.backend.routes.runs._fetch_case_from_d",
        lambda case_id: None,
    )
    r = c.post("/api/modules/api/runs/execute", json={"case_id": 999})
    assert r.status_code == 404


def test_execute_invalid_content(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "insight_aitest.modules.api.backend.routes.runs._fetch_case_from_d",
        lambda case_id: {"id": case_id, "title": "x", "type": "api",
                         "content": {"no_base_url": True, "steps": []}},
    )
    r = c.post("/api/modules/api/runs/execute", json={"case_id": 1})
    assert r.status_code == 422


def test_backfill_failure_does_not_block(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "insight_aitest.modules.api.backend.routes.runs._patch_result_to_d",
        lambda case_id, result, run_at: (_ for _ in ()).throw(RuntimeError("D down")),
    )
    r = c.post("/api/modules/api/runs/execute", json={"case_id": 1})
    assert r.status_code == 200  # 回填失败不阻断
    assert r.json()["status"] == "passed"
