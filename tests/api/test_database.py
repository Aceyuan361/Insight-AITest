# -*- coding: utf-8 -*-
"""RunDatabase CRUD + 序列化/反序列化 + 过滤测试。"""

from datetime import datetime
from insight_aitest.modules.api.backend.persistence.database import RunDatabase
from insight_aitest.modules.api.backend.persistence.models import (
    RunRecord,
    RunStatus,
    StepResult,
)


def _step(idx=0, passed=True):
    return StepResult(
        step_index=idx,
        request={"method": "GET", "url": "/x", "headers": {}, "body": {}},
        status_code=200,
        response_body={"ok": 1},
        response_headers={"Content-Type": "application/json"},
        elapsed_ms=10,
        assertions=[{"type": "status_code", "expected": 200, "actual": 200, "passed": passed}],
        extracts={},
        error=None,
        passed=passed,
    )


def _run(case_id=1, status=RunStatus.PASSED, title="t"):
    now = datetime.now()
    return RunRecord(
        id=None,
        case_id=case_id,
        case_title=title,
        case_snapshot={"base_url": "http://x", "steps": []},
        status=status,
        total_steps=1,
        passed_steps=1 if status == RunStatus.PASSED else 0,
        started_at=now,
        finished_at=now,
        duration_ms=10,
        steps=[_step()],
        error=None,
    )


def _db(tmp_path):
    return RunDatabase(str(tmp_path / "api.db"))


def test_create_get_roundtrip(tmp_path):
    db = _db(tmp_path)
    rid = db.create_run(_run(case_id=5, title="登录"))
    got = db.get_run(rid)
    assert got.case_id == 5
    assert got.case_title == "登录"
    assert got.status == RunStatus.PASSED
    assert got.total_steps == 1
    assert len(got.steps) == 1
    assert got.steps[0].status_code == 200
    assert got.steps[0].passed is True
    assert got.case_snapshot == {"base_url": "http://x", "steps": []}


def test_list_filter_by_case(tmp_path):
    db = _db(tmp_path)
    db.create_run(_run(case_id=1))
    db.create_run(_run(case_id=2))
    db.create_run(_run(case_id=1))
    assert len(db.list_runs(case_id=1)) == 2
    assert len(db.list_runs(case_id=2)) == 1


def test_list_filter_by_status(tmp_path):
    db = _db(tmp_path)
    db.create_run(_run(status=RunStatus.PASSED))
    db.create_run(_run(status=RunStatus.FAILED))
    db.create_run(_run(status=RunStatus.ERROR))
    assert len(db.list_runs(status=RunStatus.FAILED)) == 1
    assert len(db.list_runs()) == 3


def test_list_summary_excludes_steps(tmp_path):
    db = _db(tmp_path)
    db.create_run(_run())
    rows = db.list_runs()
    assert len(rows) == 1
    # 摘要字段存在，不含 steps
    assert "steps" not in rows[0]
    assert "case_title" in rows[0]
    assert "duration_ms" in rows[0]


def test_delete(tmp_path):
    db = _db(tmp_path)
    rid = db.create_run(_run())
    assert db.delete_run(rid) is True
    assert db.get_run(rid) is None
    assert db.delete_run(rid) is False


def test_run_legacy_db_compat(tmp_path):
    """旧（裸 sqlite3）schema 建库 + 样例数据 → 新 ORM RunDatabase 打开读写（spec §8.3）。"""
    import json
    import sqlite3

    legacy = tmp_path / "api.db"
    with sqlite3.connect(legacy) as raw:
        raw.executescript("""
        CREATE TABLE runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, case_id INTEGER NOT NULL,
            case_title TEXT NOT NULL, case_snapshot TEXT NOT NULL, status TEXT NOT NULL,
            total_steps INTEGER NOT NULL, passed_steps INTEGER NOT NULL,
            started_at TEXT NOT NULL, finished_at TEXT NOT NULL, duration_ms INTEGER NOT NULL,
            results_json TEXT NOT NULL, error TEXT, created_at TEXT NOT NULL);
        CREATE INDEX idx_runs_case ON runs(case_id);
        CREATE INDEX idx_runs_status ON runs(status);
        """)
        raw.execute(
            "INSERT INTO runs (case_id, case_title, case_snapshot, status, total_steps, "
            "passed_steps, started_at, finished_at, duration_ms, results_json, error, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                1,
                "存量",
                json.dumps({"base_url": "http://x"}),
                "passed",
                1,
                1,
                "2026-06-01T10:00:00",
                "2026-06-01T10:00:01",
                1000,
                json.dumps([_step().__dict__]),
                None,
                "2026-06-01T10:00:00",
            ),
        )
        raw.commit()

    db = _db(tmp_path)
    got = db.get_run(1)
    assert got is not None
    assert got.case_title == "存量"
    assert got.status == RunStatus.PASSED
    assert got.case_snapshot == {"base_url": "http://x"}
    assert len(got.steps) == 1
    # 新增正常
    nid = db.create_run(_run(case_id=2, title="新"))
    assert db.get_run(nid).case_title == "新"
    assert len(db.list_runs()) == 2
