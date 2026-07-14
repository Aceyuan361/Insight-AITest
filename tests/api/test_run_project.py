# -*- coding: utf-8 -*-
"""RunRecord（api/ui）应支持 project_id（冗余自 case + list 过滤）。

阶段 1 数据贯通 Task 4：执行记录是不可变快照，从 case 冗余 project_id
便于查询 + 删除项目引用计数。
"""
from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from insight_aitest.modules.api.backend.persistence.models import RunRecord, RunStatus


def _setup_api_app(tmp_path, monkeypatch):
    monkeypatch.setenv("INSIGHT_EYE_AI_LLM_API_KEY", "sk-test")
    monkeypatch.setenv("INSIGHT_EYE_AI_EMBED_DIM", "4")
    import insight_aitest.modules.api.backend.deps as api_deps
    api_deps._run_db = None
    from insight_aitest.modules.api.backend.persistence.database import RunDatabase
    api_deps._run_db = RunDatabase(str(tmp_path / "api.db"))
    from insight_aitest.modules.api.backend.routes import router as api_router
    app = FastAPI()
    app.include_router(api_router, prefix="/api/modules/api")
    return TestClient(app), api_deps._run_db


def test_list_runs_filter_by_project(tmp_path, monkeypatch):
    c, db = _setup_api_app(tmp_path, monkeypatch)
    now = datetime.now()
    for pid in (1, 2):
        r = RunRecord(
            case_id=10, case_title="t", case_snapshot={},
            status=RunStatus.PASSED, total_steps=1, passed_steps=1,
            started_at=now, finished_at=now, duration_ms=10, steps=[],
            project_id=pid,
        )
        db.create_run(r)

    r = c.get("/api/modules/api/runs?project_id=1")
    assert r.status_code == 200
    runs = r.json()
    assert len(runs) == 1
    assert runs[0]["project_id"] == 1


def test_list_runs_all_when_no_project_filter(tmp_path, monkeypatch):
    c, db = _setup_api_app(tmp_path, monkeypatch)
    now = datetime.now()
    for pid in (1, None):
        r = RunRecord(
            case_id=10, case_title="t", case_snapshot={},
            status=RunStatus.PASSED, total_steps=1, passed_steps=1,
            started_at=now, finished_at=now, duration_ms=10, steps=[],
            project_id=pid,
        )
        db.create_run(r)

    r = c.get("/api/modules/api/runs")
    assert r.status_code == 200
    assert len(r.json()) == 2
