# -*- coding: utf-8 -*-
"""测试看板 stats API 增强（趋势 + 失败 TOP + 平均耗时）。"""
from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _setup_app(tmp_path, monkeypatch):
    import insight_aitest.modules.api.backend.deps as deps
    from insight_aitest.modules.api.backend.persistence.database import RunDatabase
    deps._run_db = RunDatabase(str(tmp_path / "api.db"))
    from insight_aitest.modules.api.backend.routes.runs import router
    app = FastAPI()
    app.include_router(router, prefix="/api/modules/api")
    return TestClient(app)


def _make_run(status: str = "passed", duration: int = 100, case_id: int = 1, title: str = "test"):
    from insight_aitest.modules.api.backend.persistence.models import RunRecord, RunStatus
    return RunRecord(
        id=None, case_id=case_id, case_title=title, case_snapshot={},
        status=RunStatus(status), total_steps=1, passed_steps=1 if status == "passed" else 0,
        started_at=datetime.now(), finished_at=datetime.now(),
        duration_ms=duration, steps=[],
    )


def test_stats_basic(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    import insight_aitest.modules.api.backend.deps as deps
    db = deps.get_run_db()
    db.create_run(_make_run("passed", 100, 1, "登录"))
    db.create_run(_make_run("passed", 200, 2, "查询"))
    db.create_run(_make_run("failed", 300, 3, "删除"))

    r = c.get("/api/modules/api/runs/stats")
    data = r.json()
    assert data["total"] == 3
    assert data["passed"] == 2
    assert data["failed"] == 1
    assert data["avg_duration_ms"] == 200  # (100+200+300)/3
    assert data["pass_rate"] == 66.7


def test_stats_trend(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    import insight_aitest.modules.api.backend.deps as deps
    db = deps.get_run_db()
    db.create_run(_make_run("passed", 100, 1))
    db.create_run(_make_run("failed", 100, 1))

    data = c.get("/api/modules/api/runs/stats").json()
    assert "trend" in data
    assert len(data["trend"]) == 30  # 30 天
    # 今天应该有数据
    today = data["trend"][-1]
    assert today["total"] == 2
    assert today["passed"] == 1
    assert today["failed"] == 1
    assert today["pass_rate"] == 50.0


def test_stats_top_failures(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    import insight_aitest.modules.api.backend.deps as deps
    db = deps.get_run_db()
    # case 1: 3 次 failed
    for _ in range(3):
        db.create_run(_make_run("failed", 100, 1, "常失败用例"))
    # case 2: 1 次 error
    db.create_run(_make_run("error", 100, 2, "偶发错误"))
    # case 3: 全 pass
    db.create_run(_make_run("passed", 100, 3, "正常用例"))

    data = c.get("/api/modules/api/runs/stats").json()
    assert "top_failures" in data
    tf = data["top_failures"]
    assert len(tf) >= 1
    assert tf[0]["case_title"] == "常失败用例"
    assert tf[0]["failed"] == 3


def test_stats_empty(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    data = c.get("/api/modules/api/runs/stats").json()
    assert data["total"] == 0
    assert data["pass_rate"] == 0
    assert data["avg_duration_ms"] == 0
    assert len(data["trend"]) == 30
    assert data["top_failures"] == []
