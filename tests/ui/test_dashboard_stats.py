# -*- coding: utf-8 -*-
"""UI 看板 stats 端点测试。"""
from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _setup_app(tmp_path):
    import insight_aitest.modules.ui.backend.deps as ui_deps
    from insight_aitest.modules.ui.backend.persistence.database import UIRunDatabase
    db_path = str(tmp_path / "ui.db")
    ui_deps._run_db = UIRunDatabase(db_path)

    app = FastAPI()
    from insight_aitest.modules.ui.backend.routes.runs import router
    app.include_router(router, prefix="/api/modules/ui")
    return TestClient(app), ui_deps._run_db


def _create_run(db, status="passed", case_title="test", case_id=1, duration_ms=100):
    from insight_aitest.modules.ui.backend.persistence.models import RunRecord, RunStatus
    sr = RunRecord(
        id=None, case_id=case_id, case_title=case_title, case_snapshot={},
        status=RunStatus(status), total_steps=1, passed_steps=1 if status == "passed" else 0,
        started_at=datetime.now(), finished_at=datetime.now(),
        duration_ms=duration_ms, steps=[], base_url_used="http://test.local",
    )
    return db.create_run(sr)


def test_stats_empty(tmp_path):
    c, db = _setup_app(tmp_path)
    r = c.get("/api/modules/ui/runs/stats")
    data = r.json()
    assert data["total"] == 0
    assert data["pass_rate"] == 0
    assert data["avg_duration_ms"] == 0
    assert isinstance(data["trend"], list)
    assert len(data["trend"]) == 30  # 补全 30 天
    assert isinstance(data["top_failures"], list)


def test_stats_with_runs(tmp_path):
    c, db = _setup_app(tmp_path)
    _create_run(db, status="passed", case_title="case1", case_id=1, duration_ms=200)
    _create_run(db, status="passed", case_title="case1", case_id=1, duration_ms=400)
    _create_run(db, status="failed", case_title="case2", case_id=2, duration_ms=100)
    r = c.get("/api/modules/ui/runs/stats")
    data = r.json()
    assert data["total"] == 3
    assert data["passed"] == 2
    assert data["failed"] == 1
    assert data["pass_rate"] == round(2 / 3 * 100, 1)
    assert data["avg_duration_ms"] == round((200 + 400 + 100) / 3)


def test_stats_trend_has_today(tmp_path):
    c, db = _setup_app(tmp_path)
    _create_run(db, status="passed")
    data = c.get("/api/modules/ui/runs/stats").json()
    today = data["trend"][-1]  # 最后一天是今天
    assert today["total"] >= 1
    assert today["passed"] >= 1


def test_stats_top_failures(tmp_path):
    c, db = _setup_app(tmp_path)
    _create_run(db, status="failed", case_title="fail-case", case_id=10)
    _create_run(db, status="error", case_title="fail-case", case_id=10)
    _create_run(db, status="passed", case_title="ok-case", case_id=11)
    data = c.get("/api/modules/ui/runs/stats").json()
    assert len(data["top_failures"]) > 0
    assert data["top_failures"][0]["case_title"] == "fail-case"
    assert data["top_failures"][0]["failed"] + data["top_failures"][0]["error"] == 2
