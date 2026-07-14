# -*- coding: utf-8 -*-
"""环境管理增强测试：variables_meta / clone / export / import / default auto-use。"""
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


class TestVariablesMeta:
    def test_create_with_meta(self, tmp_path, monkeypatch):
        c = _setup_app(tmp_path, monkeypatch)
        r = c.post("/api/modules/api/environments", json={
            "name": "dev", "base_url": "https://dev",
            "variables": {"token": "abc", "count": "5"},
            "variables_meta": {"token": "secret", "count": "text"},
        })
        assert r.status_code == 201
        data = r.json()
        assert data["variables_meta"]["token"] == "secret"

    def test_update_meta(self, tmp_path, monkeypatch):
        c = _setup_app(tmp_path, monkeypatch)
        eid = c.post("/api/modules/api/environments", json={
            "name": "dev", "base_url": "https://dev"}).json()["id"]
        c.put(f"/api/modules/api/environments/{eid}", json={
            "variables": {"key": "val"},
            "variables_meta": {"key": "json"},
        })
        data = c.get(f"/api/modules/api/environments/{eid}").json()
        assert data["variables_meta"]["key"] == "json"

    def test_old_db_compat_no_meta(self, tmp_path, monkeypatch):
        """旧库无 variables_meta_json 列时 migrate 后默认为 {}。"""
        c = _setup_app(tmp_path, monkeypatch)
        eid = c.post("/api/modules/api/environments", json={
            "name": "old", "base_url": "https://old"}).json()["id"]
        data = c.get(f"/api/modules/api/environments/{eid}").json()
        assert data["variables_meta"] == {}


class TestClone:
    def test_clone_basic(self, tmp_path, monkeypatch):
        c = _setup_app(tmp_path, monkeypatch)
        eid = c.post("/api/modules/api/environments", json={
            "name": "dev", "base_url": "https://dev",
            "variables": {"token": "abc"}, "variables_meta": {"token": "secret"},
        }).json()["id"]
        r = c.post(f"/api/modules/api/environments/{eid}/clone", json={"new_name": "dev-copy"})
        assert r.status_code == 201
        clone = r.json()
        assert clone["name"] == "dev-copy"
        assert clone["base_url"] == "https://dev"
        assert clone["variables"] == {"token": "abc"}
        assert clone["variables_meta"]["token"] == "secret"
        assert clone["is_default"] is False

    def test_clone_name_conflict_409(self, tmp_path, monkeypatch):
        c = _setup_app(tmp_path, monkeypatch)
        c.post("/api/modules/api/environments", json={"name": "dev", "base_url": "https://dev"})
        eid = c.post("/api/modules/api/environments", json={"name": "prod", "base_url": "https://p"}).json()["id"]
        r = c.post(f"/api/modules/api/environments/{eid}/clone", json={"new_name": "dev"})
        assert r.status_code == 409

    def test_clone_source_not_found_404(self, tmp_path, monkeypatch):
        c = _setup_app(tmp_path, monkeypatch)
        r = c.post("/api/modules/api/environments/9999/clone", json={"new_name": "x"})
        assert r.status_code == 404


class TestExportImport:
    def test_export_import_roundtrip(self, tmp_path, monkeypatch):
        c = _setup_app(tmp_path, monkeypatch)
        c.post("/api/modules/api/environments", json={
            "name": "dev", "base_url": "https://dev",
            "variables": {"t": "x"}, "variables_meta": {"t": "secret"},
        })
        c.post("/api/modules/api/environments", json={"name": "prod", "base_url": "https://prod"})

        # Export
        r = c.get("/api/modules/api/environments/export")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 2

        # Import to a fresh DB
        import insight_aitest.modules.api.backend.deps as deps
        from insight_aitest.modules.api.backend.persistence.environment_database import EnvironmentDatabase
        c2 = _setup_app(tmp_path / "fresh", monkeypatch)

        r2 = c2.post("/api/modules/api/environments/import", json=data)
        assert r2.status_code == 200
        assert r2.json()["imported"] == 2
        assert r2.json()["skipped"] == 0

        # Verify
        envs = c2.get("/api/modules/api/environments").json()
        assert len(envs) == 2

    def test_import_skip_existing(self, tmp_path, monkeypatch):
        c = _setup_app(tmp_path, monkeypatch)
        c.post("/api/modules/api/environments", json={"name": "dev", "base_url": "https://dev"})
        r = c.post("/api/modules/api/environments/import", json=[
            {"name": "dev", "base_url": "https://other"},
            {"name": "prod", "base_url": "https://prod"},
        ])
        assert r.json()["imported"] == 1
        assert r.json()["skipped"] == 1


class TestDefaultAutoUse:
    def test_get_default(self, tmp_path, monkeypatch):
        import insight_aitest.modules.api.backend.deps as deps
        from insight_aitest.modules.api.backend.persistence.environment_database import EnvironmentDatabase
        db = EnvironmentDatabase(str(tmp_path / "api.db"))
        db.create(name="dev", base_url="https://dev", is_default=True)
        db.create(name="prod", base_url="https://prod")
        default = db.get_default()
        assert default is not None
        assert default.name == "dev"
