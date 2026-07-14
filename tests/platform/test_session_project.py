# -*- coding: utf-8 -*-
"""SessionRow（performance）应支持 project_id（阶段 1 数据贯通 Task 5）。

监控会话归属项目，便于按"项目 A 的 App"聚合 + 删除项目引用计数。
"""
from insight_aitest.platform.persistence.database import DatabaseManager


def test_create_session_with_project(tmp_path):
    DatabaseManager._instance = None
    db = DatabaseManager(str(tmp_path / "monitoring.db"))
    s = db.create_session("dev1", "com.app", project_id=5)
    assert s.project_id == 5
    got = db.get_session(s.id)
    assert got.project_id == 5


def test_create_session_without_project_defaults_null(tmp_path):
    DatabaseManager._instance = None
    db = DatabaseManager(str(tmp_path / "monitoring.db"))
    s = db.create_session("dev1", "com.app")
    assert s.project_id is None


def test_list_sessions_filter_by_project(tmp_path):
    DatabaseManager._instance = None
    db = DatabaseManager(str(tmp_path / "monitoring.db"))
    db.create_session("d1", "com.a", project_id=1)
    db.create_session("d2", "com.b", project_id=2)
    db.create_session("d3", "com.c")  # 无项目

    sessions = db.list_sessions(project_id=1)
    assert len(sessions) == 1
    assert sessions[0].device_id == "d1"
    assert sessions[0].project_id == 1

    # 无过滤返回全部
    all_sessions = db.list_sessions()
    assert len(all_sessions) == 3
