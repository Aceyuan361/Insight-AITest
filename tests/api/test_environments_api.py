# -*- coding: utf-8 -*-
"""环境 CRUD API 测试（spec E.1 §4）。"""
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _setup_app(tmp_path, monkeypatch):
    import insight_aitest.modules.api.backend.deps as deps
    from insight_aitest.modules.api.backend.persistence.environment_database import EnvironmentDatabase
    deps._env_db = EnvironmentDatabase(str(tmp_path / "api.db"))
    from insight_aitest.modules.api.backend.routes.environments import router
    app = FastAPI()
    app.include_router(router, prefix="/api/modules/api")
    return TestClient(app)


def test_create_get_list(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    r = c.post("/api/modules/api/environments", json={
        "name": "dev", "base_url": "https://dev.example.com",
        "variables": {"token": "x"}, "is_default": True})
    assert r.status_code == 201
    eid = r.json()["id"]
    assert r.json()["is_default"] is True

    assert c.get(f"/api/modules/api/environments/{eid}").json()["name"] == "dev"
    assert len(c.get("/api/modules/api/environments").json()) == 1


def test_name_unique_409(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    c.post("/api/modules/api/environments", json={"name": "dev", "base_url": "https://a"})
    r = c.post("/api/modules/api/environments", json={"name": "dev", "base_url": "https://b"})
    assert r.status_code == 409


def test_put_sets_default_clears_others(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    e1 = c.post("/api/modules/api/environments",
                json={"name": "dev", "base_url": "https://a", "is_default": True}).json()["id"]
    e2 = c.post("/api/modules/api/environments",
                json={"name": "prod", "base_url": "https://b"}).json()["id"]
    c.put(f"/api/modules/api/environments/{e2}", json={
        "name": "prod", "base_url": "https://b", "is_default": True})
    assert c.get(f"/api/modules/api/environments/{e1}").json()["is_default"] is False
    assert c.get(f"/api/modules/api/environments/{e2}").json()["is_default"] is True


def test_delete(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    eid = c.post("/api/modules/api/environments",
                 json={"name": "dev", "base_url": "https://a"}).json()["id"]
    assert c.delete(f"/api/modules/api/environments/{eid}").status_code == 200
    assert c.get(f"/api/modules/api/environments/{eid}").status_code == 404
