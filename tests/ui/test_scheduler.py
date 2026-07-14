# -*- coding: utf-8 -*-
"""UI 定时调度测试。"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from insight_aitest.modules.ui.backend.scheduler.manager import _parse_cron


def test_parse_cron_valid():
    result = _parse_cron("0 9 * * 1-5")
    assert result == {"minute": "0", "hour": "9", "day": "*", "month": "*", "day_of_week": "1-5"}


def test_parse_cron_too_few_parts():
    with pytest.raises(ValueError, match="5 段"):
        _parse_cron("0 9 *")


def test_parse_cron_too_many_parts():
    with pytest.raises(ValueError, match="5 段"):
        _parse_cron("0 9 * * 1-5 extra")


def _setup_app(tmp_path):
    import insight_aitest.modules.ui.backend.deps as ui_deps
    from insight_aitest.modules.ui.backend.scheduler.database import ScheduledUIBatchDatabase
    ui_deps._DB_PATH = str(tmp_path / "ui.db")
    from insight_aitest.modules.ui.backend.scheduler import database as sched_db_mod
    # 确保 DB 路径用 tmp
    app = FastAPI()
    from insight_aitest.modules.ui.backend.scheduler.routes import router
    app.include_router(router, prefix="/api/modules/ui")
    # patch _get_sched_db 用 tmp 路径
    import insight_aitest.modules.ui.backend.scheduler.routes as routes_mod
    routes_mod._get_sched_db = lambda: ScheduledUIBatchDatabase(str(tmp_path / "ui.db"))
    # patch scheduler manager to avoid starting real threads
    import insight_aitest.modules.ui.backend.scheduler.routes as rm
    from unittest.mock import MagicMock
    mock_mgr = MagicMock()
    mock_mgr.add_job.return_value = True
    mock_mgr.remove_job.return_value = None
    mock_mgr.trigger_now.return_value = True
    rm.get_ui_scheduler_manager = lambda: mock_mgr
    return TestClient(app)


def test_create_schedule(tmp_path):
    c = _setup_app(tmp_path)
    r = c.post("/api/modules/ui/schedules", json={
        "name": "每日冒烟", "cron_expression": "0 9 * * 1-5", "case_ids": [1, 2],
    })
    assert r.status_code == 201
    assert r.json()["name"] == "每日冒烟"
    assert r.json()["case_ids"] == [1, 2]
    assert r.json()["enabled"] is True


def test_create_schedule_invalid_cron(tmp_path):
    c = _setup_app(tmp_path)
    r = c.post("/api/modules/ui/schedules", json={
        "name": "bad", "cron_expression": "not cron", "case_ids": [1],
    })
    assert r.status_code == 422


def test_create_schedule_empty_cases(tmp_path):
    c = _setup_app(tmp_path)
    r = c.post("/api/modules/ui/schedules", json={
        "name": "empty", "cron_expression": "0 9 * * *", "case_ids": [],
    })
    assert r.status_code == 422


def test_list_schedules(tmp_path):
    c = _setup_app(tmp_path)
    c.post("/api/modules/ui/schedules", json={"name": "s1", "cron_expression": "0 9 * * *", "case_ids": [1]})
    c.post("/api/modules/ui/schedules", json={"name": "s2", "cron_expression": "0 10 * * *", "case_ids": [2]})
    r = c.get("/api/modules/ui/schedules")
    assert len(r.json()) == 2


def test_update_schedule(tmp_path):
    c = _setup_app(tmp_path)
    sid = c.post("/api/modules/ui/schedules", json={"name": "s1", "cron_expression": "0 9 * * *", "case_ids": [1]}).json()["id"]
    r = c.put(f"/api/modules/ui/schedules/{sid}", json={"name": "updated", "enabled": False})
    assert r.status_code == 200
    assert r.json()["name"] == "updated"
    assert r.json()["enabled"] is False


def test_delete_schedule(tmp_path):
    c = _setup_app(tmp_path)
    sid = c.post("/api/modules/ui/schedules", json={"name": "s1", "cron_expression": "0 9 * * *", "case_ids": [1]}).json()["id"]
    assert c.delete(f"/api/modules/ui/schedules/{sid}").status_code == 200
    assert c.get(f"/api/modules/ui/schedules/{sid}").status_code == 404


def test_trigger_schedule(tmp_path):
    c = _setup_app(tmp_path)
    sid = c.post("/api/modules/ui/schedules", json={"name": "s1", "cron_expression": "0 9 * * *", "case_ids": [1]}).json()["id"]
    r = c.post(f"/api/modules/ui/schedules/{sid}/run")
    assert r.status_code == 200
    assert r.json()["triggered"] == sid
