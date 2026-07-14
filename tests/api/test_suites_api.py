# -*- coding: utf-8 -*-
"""套件 CRUD API 测试（spec E.1 §4）。"""
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _setup_app(tmp_path, monkeypatch):
    import insight_aitest.modules.api.backend.deps as deps
    from insight_aitest.modules.api.backend.persistence.suite_database import (
        SuiteDatabase, SuiteRunDatabase,
    )
    deps._suite_db = SuiteDatabase(str(tmp_path / "api.db"))
    deps._suite_run_db = SuiteRunDatabase(str(tmp_path / "api.db"))
    from insight_aitest.modules.api.backend.routes.suites import router
    app = FastAPI()
    app.include_router(router, prefix="/api/modules/api")
    return TestClient(app)


def test_create_get_list(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    r = c.post("/api/modules/api/suites", json={
        "name": "回归", "case_ids": [1, 2, 3],
        "setup": [], "teardown": []})
    assert r.status_code == 201
    sid = r.json()["id"]
    assert r.json()["case_ids"] == [1, 2, 3]
    assert c.get(f"/api/modules/api/suites/{sid}").json()["name"] == "回归"
    assert len(c.get("/api/modules/api/suites").json()) == 1


def test_update(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    sid = c.post("/api/modules/api/suites", json={"name": "s", "case_ids": [1]}).json()["id"]
    c.put(f"/api/modules/api/suites/{sid}", json={"name": "新", "case_ids": [1, 2]})
    got = c.get(f"/api/modules/api/suites/{sid}").json()
    assert got["name"] == "新"
    assert got["case_ids"] == [1, 2]


def test_delete(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    sid = c.post("/api/modules/api/suites", json={"name": "s", "case_ids": [1]}).json()["id"]
    assert c.delete(f"/api/modules/api/suites/{sid}").status_code == 200
    assert c.get(f"/api/modules/api/suites/{sid}").status_code == 404
