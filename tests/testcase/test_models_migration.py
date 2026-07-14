# tests/testcase/test_models_migration.py
# -*- coding: utf-8 -*-
"""TestCase task_id/batch_id 列幂等迁移测试。"""
import sqlite3

from insight_aitest.modules.testcase.backend.persistence.database import TestCaseDatabase, _ensure_task_columns


def test_ensure_task_columns_adds_to_old_db(tmp_path):
    """旧 testcases 表（无 task_id/batch_id）迁移后应补齐两列。"""
    db_path = str(tmp_path / "tc.db")
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE testcases (id INTEGER PRIMARY KEY, title TEXT, type TEXT, "
            "description TEXT, priority TEXT, status TEXT, test_design TEXT, "
            "preconditions TEXT, content_json TEXT, tags TEXT, source TEXT, "
            "project_id INTEGER, version_id INTEGER, last_run_at TEXT, "
            "last_result TEXT, created_at TEXT, updated_at TEXT)"
        )
        conn.commit()
    _ensure_task_columns(db_path)
    with sqlite3.connect(db_path) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(testcases)")}
    assert "task_id" in cols
    assert "batch_id" in cols


def test_ensure_task_columns_idempotent(tmp_path):
    """重复调用幂等，不报错。"""
    db_path = str(tmp_path / "tc.db")
    TestCaseDatabase(db_path)
    TestCaseDatabase(db_path)
    _ensure_task_columns(db_path)
