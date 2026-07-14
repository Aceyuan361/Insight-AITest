# -*- coding: utf-8 -*-
"""UIRunDatabase CRUD + 序列化/反序列化 + 过滤测试（对标 tests/api/test_database.py）。"""

from datetime import datetime

from insight_aitest.modules.ui.backend.persistence.database import UIRunDatabase
from insight_aitest.modules.ui.backend.persistence.models import (
    RunRecord,
    RunStatus,
    UIStepResult,
)


def _step(idx=0, passed=True, kind="action"):
    return UIStepResult(
        step_index=idx,
        kind=kind,
        prompt="点击登录按钮",
        screenshot=None,
        action_log="clicked",
        assert_passed=None,
        extracts={},
        elapsed_ms=100,
        error=None,
        passed=passed,
    )


def _run(case_id=1, status=RunStatus.PASSED, title="登录测试"):
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
        duration_ms=100,
        steps=[_step()],
        base_url_used="http://x",
        error=None,
    )


def _db(tmp_path):
    return UIRunDatabase(str(tmp_path / "ui.db"))


def test_create_get_roundtrip(tmp_path):
    db = _db(tmp_path)
    rid = db.create_run(_run(case_id=5, title="登录"))
    got = db.get_run(rid)
    assert got.case_id == 5
    assert got.case_title == "登录"
    assert got.status == RunStatus.PASSED
    assert got.total_steps == 1
    assert len(got.steps) == 1
    assert got.steps[0].kind == "action"
    assert got.steps[0].passed is True
    assert got.case_snapshot == {"base_url": "http://x", "steps": []}
    assert got.base_url_used == "http://x"


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
    assert "base_url_used" in rows[0]


def test_delete(tmp_path):
    db = _db(tmp_path)
    rid = db.create_run(_run())
    assert db.delete_run(rid) is True
    assert db.get_run(rid) is None
    assert db.delete_run(rid) is False


def test_assert_step_roundtrip(tmp_path):
    """assert 步的 assert_passed 字段序列化往返。"""
    db = _db(tmp_path)
    run = _run()
    run.steps = [_step(idx=0, kind="assert", passed=True)]
    run.steps[0].assert_passed = True
    rid = db.create_run(run)
    got = db.get_run(rid)
    assert got.steps[0].kind == "assert"
    assert got.steps[0].assert_passed is True
