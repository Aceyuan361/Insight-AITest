# -*- coding: utf-8 -*-
"""套件执行/历史 API 测试（spec E.1 §4）。

用同步方式测 BackgroundTasks：FastAPI TestClient 会等 BackgroundTasks 完成。
"""
import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _handler(req: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"ok": True})


def _setup_app(tmp_path, monkeypatch):
    import insight_aitest.modules.api.backend.deps as deps
    from insight_aitest.modules.api.backend.persistence.database import RunDatabase
    from insight_aitest.modules.api.backend.persistence.suite_database import (
        SuiteDatabase, SuiteRunDatabase,
    )
    deps._run_db = RunDatabase(str(tmp_path / "api.db"))
    deps._suite_db = SuiteDatabase(str(tmp_path / "api.db"))
    deps._suite_run_db = SuiteRunDatabase(str(tmp_path / "api.db"))

    # mock D 的 case 提供 + 回填（patch suites 模块引用的导入名，确保 task 内用到）
    monkeypatch.setattr(
        "insight_aitest.modules.api.backend.routes.suites._fetch_case_from_d",
        lambda cid: {"id": cid, "title": f"case{cid}", "type": "api",
                     "content": {"base_url": "https://x", "steps": [
                         {"method": "GET", "path": "/ok", "headers": {}, "body": {},
                          "assertions": [{"type": "status_code", "expected": 200}]}]}},
    )
    monkeypatch.setattr(
        "insight_aitest.modules.api.backend.routes.suites._patch_result_to_d",
        lambda cid, result, run_at: True,
    )
    monkeypatch.setattr(
        "insight_aitest.modules.api.backend.routes.suites._make_transport",
        lambda: httpx.MockTransport(_handler),
    )

    from insight_aitest.modules.api.backend.routes import router as api_router
    app = FastAPI()
    app.include_router(api_router, prefix="/api/modules/api")
    return TestClient(app)


def test_execute_suite(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    sid = c.post("/api/modules/api/suites", json={"name": "s", "case_ids": [1, 2]}).json()["id"]
    r = c.post(f"/api/modules/api/suites/{sid}/execute")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in ("completed", "running")
    srid = body["suite_run_id"]

    # 查详情
    detail = c.get(f"/api/modules/api/suites/runs/{srid}").json()
    assert detail["total"] == 2
    assert len(detail["case_run_ids"]) == 2


def test_list_suite_runs(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    sid = c.post("/api/modules/api/suites", json={"name": "s", "case_ids": [1]}).json()["id"]
    c.post(f"/api/modules/api/suites/{sid}/execute")
    c.post(f"/api/modules/api/suites/{sid}/execute")
    runs = c.get(f"/api/modules/api/suites/runs?suite_id={sid}").json()
    assert len(runs) == 2


def test_delete_suite_run(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    sid = c.post("/api/modules/api/suites", json={"name": "s", "case_ids": [1]}).json()["id"]
    srid = c.post(f"/api/modules/api/suites/{sid}/execute").json()["suite_run_id"]
    assert c.delete(f"/api/modules/api/suites/runs/{srid}").status_code == 200
    assert c.get(f"/api/modules/api/suites/runs/{srid}").status_code == 404


def test_execute_suite_not_found(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    assert c.post("/api/modules/api/suites/999/execute").status_code == 404
