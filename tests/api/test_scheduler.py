# -*- coding: utf-8 -*-
"""定时调度任务 API + 数据库测试。"""
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _setup_app(tmp_path, monkeypatch):
    import insight_aitest.modules.api.backend.deps as deps
    deps._DB_PATH = str(tmp_path / "api.db")
    from insight_aitest.modules.api.backend.scheduler.routes import _get_sched_db, router
    # Monkeypatch _get_sched_db to use tmp_path
    from insight_aitest.modules.api.backend.scheduler import database as sched_db_mod
    from insight_aitest.modules.api.backend.scheduler import routes as sched_routes
    sched_routes._get_sched_db = lambda: sched_db_mod.ScheduledSuiteDatabase(str(tmp_path / "api.db"))
    # Monkeypatch scheduler manager (avoid starting real BackgroundScheduler)
    class FakeManager:
        def __init__(self): self.jobs = {}
        def add_job(self, sid, cron): self.jobs[sid] = cron; return True
        def remove_job(self, sid): self.jobs.pop(sid, None)
        def trigger_now(self, sid): return True
        def reload(self): pass
    sched_routes.get_scheduler_manager = lambda: FakeManager()

    app = FastAPI()
    app.include_router(router, prefix="/api/modules/api")
    return TestClient(app)


def _setup_db(tmp_path):
    from insight_aitest.modules.api.backend.scheduler.database import ScheduledSuiteDatabase
    return ScheduledSuiteDatabase(str(tmp_path / "api.db"))


class TestSchedulerDB:
    def test_create_get_list(self, tmp_path):
        db = _setup_db(tmp_path)
        sid = db.create(name="每日回归", suite_id=1, cron_expression="0 8 * * *")
        assert sid > 0
        s = db.get(sid)
        assert s.name == "每日回归"
        assert s.cron_expression == "0 8 * * *"
        assert s.enabled is True
        assert len(db.list()) == 1

    def test_update(self, tmp_path):
        db = _setup_db(tmp_path)
        sid = db.create(name="t", suite_id=1, cron_expression="* * * * *")
        db.update(sid, name="updated", cron_expression="0 0 * * *", enabled=False)
        s = db.get(sid)
        assert s.name == "updated"
        assert s.cron_expression == "0 0 * * *"
        assert s.enabled is False

    def test_delete(self, tmp_path):
        db = _setup_db(tmp_path)
        sid = db.create(name="t", suite_id=1, cron_expression="* * * * *")
        assert db.delete(sid) is True
        assert db.get(sid) is None
        assert db.delete(sid) is False

    def test_list_enabled(self, tmp_path):
        db = _setup_db(tmp_path)
        db.create(name="e1", suite_id=1, cron_expression="* * * * *", enabled=True)
        db.create(name="e2", suite_id=2, cron_expression="* * * * *", enabled=False)
        db.create(name="e3", suite_id=3, cron_expression="* * * * *", enabled=True)
        enabled = db.list_enabled()
        assert len(enabled) == 2

    def test_record_run(self, tmp_path):
        db = _setup_db(tmp_path)
        sid = db.create(name="t", suite_id=1, cron_expression="* * * * *")
        db.record_run(sid, "completed", 999)
        s = db.get(sid)
        assert s.last_status == "completed"
        assert s.last_suite_run_id == 999
        assert s.last_run_at is not None


class TestSchedulerAPI:
    def test_create_schedule(self, tmp_path, monkeypatch):
        c = _setup_app(tmp_path, monkeypatch)
        r = c.post("/api/modules/api/schedules", json={
            "name": "每日回归", "suite_id": 1, "cron_expression": "0 8 * * *",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "每日回归"
        assert data["cron_expression"] == "0 8 * * *"
        assert data["enabled"] is True

    def test_invalid_cron_422(self, tmp_path, monkeypatch):
        c = _setup_app(tmp_path, monkeypatch)
        r = c.post("/api/modules/api/schedules", json={
            "name": "bad", "suite_id": 1, "cron_expression": "not a cron",
        })
        assert r.status_code == 422

    def test_list_schedules(self, tmp_path, monkeypatch):
        c = _setup_app(tmp_path, monkeypatch)
        c.post("/api/modules/api/schedules", json={"name": "a", "suite_id": 1})
        c.post("/api/modules/api/schedules", json={"name": "b", "suite_id": 2})
        assert len(c.get("/api/modules/api/schedules").json()) == 2

    def test_update_schedule(self, tmp_path, monkeypatch):
        c = _setup_app(tmp_path, monkeypatch)
        sid = c.post("/api/modules/api/schedules", json={
            "name": "t", "suite_id": 1, "cron_expression": "* * * * *"}).json()["id"]
        r = c.put(f"/api/modules/api/schedules/{sid}", json={
            "name": "updated", "enabled": False})
        assert r.json()["name"] == "updated"
        assert r.json()["enabled"] is False

    def test_delete_schedule(self, tmp_path, monkeypatch):
        c = _setup_app(tmp_path, monkeypatch)
        sid = c.post("/api/modules/api/schedules", json={
            "name": "t", "suite_id": 1}).json()["id"]
        assert c.delete(f"/api/modules/api/schedules/{sid}").status_code == 200
        assert c.get(f"/api/modules/api/schedules/{sid}").status_code == 404

    def test_trigger_now(self, tmp_path, monkeypatch):
        c = _setup_app(tmp_path, monkeypatch)
        sid = c.post("/api/modules/api/schedules", json={
            "name": "t", "suite_id": 1}).json()["id"]
        r = c.post(f"/api/modules/api/schedules/{sid}/run")
        assert r.status_code == 200
        assert r.json()["triggered"] == sid


class TestCronParser:
    def test_parse_valid(self):
        from insight_aitest.modules.api.backend.scheduler.manager import _parse_cron
        result = _parse_cron("0 8 * * *")
        assert result == {"minute": "0", "hour": "8", "day": "*", "month": "*", "day_of_week": "*"}

    def test_parse_complex(self):
        from insight_aitest.modules.api.backend.scheduler.manager import _parse_cron
        result = _parse_cron("*/15 9-17 * * 1-5")
        assert result["minute"] == "*/15"
        assert result["hour"] == "9-17"
        assert result["day_of_week"] == "1-5"

    def test_parse_invalid_too_few(self):
        from insight_aitest.modules.api.backend.scheduler.manager import _parse_cron
        try:
            _parse_cron("0 8 * *")
            assert False, "should raise"
        except ValueError:
            pass
