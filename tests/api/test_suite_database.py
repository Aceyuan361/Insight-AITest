# -*- coding: utf-8 -*-
"""SuiteDatabase + SuiteRunDatabase CRUD + 快照 + 僵尸回收测试。"""

from datetime import datetime
from insight_aitest.modules.api.backend.persistence.suite_database import (
    SuiteDatabase,
    SuiteRunDatabase,
)
from insight_aitest.modules.api.backend.persistence.suite_models import (
    Suite,
    SuiteRunRecord,
    SuiteRunStatus,
)


def _suite(name="回归套件", case_ids=None):
    return Suite(
        id=None, name=name, description="d", case_ids=case_ids or [1, 2, 3], setup=[], teardown=[]
    )


def _suite_run(suite_id=1, status=SuiteRunStatus.RUNNING, total=3):
    return SuiteRunRecord(
        id=None,
        suite_id=suite_id,
        suite_name="回归套件",
        suite_snapshot={"case_ids": [1, 2, 3], "setup": [], "teardown": []},
        environment_id=None,
        environment_name=None,
        status=status,
        total=total,
        done=0,
        case_run_ids=[],
        setup_status=None,
        started_at=datetime.now(),
        finished_at=None,
        error=None,
    )


def test_suite_crud(tmp_path):
    db = SuiteDatabase(str(tmp_path / "api.db"))
    sid = db.create(_suite(case_ids=[3, 1, 2]))
    s = db.get(sid)
    assert s.name == "回归套件"
    assert s.case_ids == [3, 1, 2]
    db.update(sid, name="新名称")
    assert db.get(sid).name == "新名称"
    assert len(db.list()) == 1
    assert db.delete(sid) is True
    assert db.get(sid) is None


def test_suite_run_create_get(tmp_path):
    db = SuiteRunDatabase(str(tmp_path / "api.db"))
    rid = db.create(_suite_run())
    sr = db.get(rid)
    assert sr.status == SuiteRunStatus.RUNNING
    assert sr.total == 3
    assert sr.done == 0
    assert sr.case_run_ids == []
    assert sr.finished_at is None


def test_suite_run_update_progress(tmp_path):
    """跑完一条 case 后更新 done + 追加 run_id。"""
    db = SuiteRunDatabase(str(tmp_path / "api.db"))
    rid = db.create(_suite_run())
    db.update_progress(rid, done=1, case_run_id=10)
    sr = db.get(rid)
    assert sr.done == 1
    assert sr.case_run_ids == [10]
    db.update_progress(rid, done=2, case_run_id=11)
    assert db.get(rid).case_run_ids == [10, 11]


def test_suite_run_finish(tmp_path):
    db = SuiteRunDatabase(str(tmp_path / "api.db"))
    rid = db.create(_suite_run())
    db.finish(rid, status=SuiteRunStatus.COMPLETED)
    sr = db.get(rid)
    assert sr.status == SuiteRunStatus.COMPLETED
    assert sr.finished_at is not None


def test_suite_run_list_filter(tmp_path):
    db = SuiteRunDatabase(str(tmp_path / "api.db"))
    db.create(_suite_run(suite_id=1, status=SuiteRunStatus.COMPLETED))
    db.create(_suite_run(suite_id=2, status=SuiteRunStatus.FAILED))
    db.create(_suite_run(suite_id=1, status=SuiteRunStatus.COMPLETED))
    assert len(db.list()) == 3
    assert len(db.list(suite_id=1)) == 2
    assert len(db.list(status=SuiteRunStatus.FAILED)) == 1


def test_zombie_recovery_on_init(tmp_path):
    """新建实例时，遗留 running 应被回收为 interrupted。"""
    path = str(tmp_path / "api.db")
    db1 = SuiteRunDatabase(path)
    rid = db1.create(_suite_run(status=SuiteRunStatus.RUNNING))
    assert db1.get(rid).status == SuiteRunStatus.RUNNING
    # 模拟进程重启：新实例（同一文件）
    db2 = SuiteRunDatabase(path)
    assert db2.get(rid).status == SuiteRunStatus.INTERRUPTED
    assert db2.get(rid).finished_at is not None


def test_suite_legacy_db_compat(tmp_path):
    """旧（裸 sqlite3，_json 后缀列名）schema 建库 + 样例 → 新 ORM 打开读写（spec §8.3）。

    关键：旧库列名是 case_ids_json/setup_json/suite_snapshot_json/case_run_ids_json，
    ORM 模型必须映射到这些列名（不能丢 _json 后缀），否则旧库读不动。
    """
    import json
    import sqlite3

    legacy = tmp_path / "api.db"
    with sqlite3.connect(legacy) as raw:
        raw.executescript("""
        CREATE TABLE suites (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, description TEXT DEFAULT '',
            case_ids_json TEXT NOT NULL, setup_json TEXT DEFAULT '[]', teardown_json TEXT DEFAULT '[]',
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE suite_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, suite_id INTEGER NOT NULL, suite_name TEXT NOT NULL,
            suite_snapshot_json TEXT NOT NULL, environment_id INTEGER, environment_name TEXT,
            status TEXT NOT NULL, total INTEGER NOT NULL, done INTEGER NOT NULL,
            case_run_ids_json TEXT NOT NULL, setup_status TEXT, started_at TEXT NOT NULL,
            finished_at TEXT, error TEXT, created_at TEXT NOT NULL);
        CREATE INDEX idx_suite_runs_suite ON suite_runs(suite_id);
        CREATE INDEX idx_suite_runs_status ON suite_runs(status);
        """)
        raw.execute(
            "INSERT INTO suites (name, description, case_ids_json, setup_json, teardown_json, "
            "created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
            (
                "存量套件",
                "",
                json.dumps([1, 2]),
                "[]",
                "[]",
                "2026-06-01T10:00:00",
                "2026-06-01T10:00:00",
            ),
        )
        raw.execute(
            "INSERT INTO suite_runs (suite_id, suite_name, suite_snapshot_json, status, total, done, "
            "case_run_ids_json, started_at, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                1,
                "存量套件",
                json.dumps({"case_ids": [1, 2]}),
                "completed",
                2,
                2,
                json.dumps([10, 11]),
                "2026-06-01T10:00:00",
                "2026-06-01T10:00:00",
            ),
        )
        raw.commit()

    sdb = SuiteDatabase(str(legacy))
    suite = sdb.get(1)
    assert suite is not None
    assert suite.name == "存量套件"
    assert suite.case_ids == [1, 2]  # 从 case_ids_json 列读回

    rdb = SuiteRunDatabase(str(legacy))
    run = rdb.get(1)
    assert run is not None
    assert run.suite_name == "存量套件"
    assert run.case_run_ids == [10, 11]  # 从 case_run_ids_json 列读回
    assert run.suite_snapshot == {"case_ids": [1, 2]}  # 从 suite_snapshot_json 列读回

    # 新增正常
    nid = sdb.create(Suite(name="新套件", case_ids=[3]))
    assert sdb.get(nid).case_ids == [3]
