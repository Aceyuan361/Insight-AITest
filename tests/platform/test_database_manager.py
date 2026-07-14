# -*- coding: utf-8 -*-
"""DatabaseManager（platform monitoring）ORM 迁移后的测试（spec P0-1）。

覆盖：会话/指标/告警 CRUD + 单例语义 + 旧库兼容（spec §8.3）。
DatabaseManager 对外返回 Session/MetricsData DTO（保留不变），内部走 ORM。
"""

from __future__ import annotations

import sqlite3
from datetime import datetime

import pytest

from insight_aitest.platform.persistence.database import DatabaseManager
from insight_aitest.platform.services.models.metrics import MetricsData
from insight_aitest.platform.services.models.session import SessionStatus


@pytest.fixture(autouse=True)
def _reset_singleton():
    """每个测试重置单例（DatabaseManager 是进程级单例，跨测试会串）。"""
    DatabaseManager._instance = None
    yield
    DatabaseManager._instance = None


def _db(tmp_path):
    return DatabaseManager(str(tmp_path / "monitoring.db"))


def test_create_and_get_session(tmp_path):
    db = _db(tmp_path)
    s = db.create_session("device1", "com.app", platform="android", sampling_interval=500)
    assert s.id is not None
    assert s.device_id == "device1"
    assert s.app_package == "com.app"
    assert s.platform == "android"
    assert s.status == SessionStatus.RUNNING
    assert s.sampling_interval == 500

    got = db.get_session(s.id)
    assert got is not None
    assert got.device_id == "device1"
    assert got.sampling_interval == 500


def test_invalid_platform_raises(tmp_path):
    db = _db(tmp_path)
    with pytest.raises(ValueError):
        db.create_session("d", "com.app", platform="web")


def test_update_session(tmp_path):
    db = _db(tmp_path)
    s = db.create_session("d", "com.app")
    db.update_session(s.id, status="stopped", end_time=datetime.now().isoformat(), duration=10)
    got = db.get_session(s.id)
    assert got.status == SessionStatus.STOPPED
    assert got.duration == 10


def test_list_and_delete_session(tmp_path):
    db = _db(tmp_path)
    db.create_session("d1", "com.a")
    db.create_session("d2", "com.b")
    assert len(db.list_sessions()) == 2
    assert len(db.list_sessions(device_id="d1")) == 1
    sid = db.list_sessions(device_id="d1")[0].id
    assert db.delete_session(sid) is True
    assert db.get_session(sid) is None
    assert db.delete_session(99999) is False


def test_save_and_get_metrics(tmp_path):
    db = _db(tmp_path)
    s = db.create_session("d", "com.app")
    now = datetime.now()
    db.save_metrics(s.id, MetricsData(timestamp=now, cpu=50.0, memory=200.0, fps=60.0))
    db.save_metrics(s.id, MetricsData(timestamp=now, cpu=80.0, memory=300.0, fps=30.0))
    got = db.get_metrics(s.id)
    assert len(got) == 2
    assert got[0].cpu == 50.0
    assert got[1].fps == 30.0


def test_alerts(tmp_path):
    db = _db(tmp_path)
    s = db.create_session("d", "com.app")
    aid = db.save_alert(
        s.id,
        {
            "alert_type": "fps_low",
            "metric_name": "fps",
            "current_value": 20.0,
            "threshold_value": 50.0,
            "severity": "warning",
            "description": "FPS 过低",
        },
    )
    assert aid is not None
    alerts = db.get_alerts(session_id=s.id)
    assert len(alerts) == 1
    assert alerts[0]["alert_type"] == "fps_low"
    assert alerts[0]["severity"] == "warning"


def test_singleton(tmp_path):
    """DatabaseManager 是单例：同 db_path 返回同一实例。"""
    p = str(tmp_path / "monitoring.db")
    a = DatabaseManager(p)
    b = DatabaseManager(p)
    assert a is b


def test_session_statistics(tmp_path):
    db = _db(tmp_path)
    s = db.create_session("d", "com.app")
    now = datetime.now()
    db.save_metrics(s.id, MetricsData(timestamp=now, cpu=50.0, fps=60.0))
    db.save_metrics(s.id, MetricsData(timestamp=now, cpu=70.0, fps=30.0))
    stats = db.get_session_statistics(s.id)
    assert "cpu_app" in stats
    assert stats["cpu_app"]["max"] == 70.0
    assert stats["cpu_app"]["min"] == 50.0
    assert "fps" in stats


# ===== P0-1 旧库兼容（spec §8.3）=====

_LEGACY_MONITORING_DDL = """
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT, device_id TEXT NOT NULL, app_package TEXT NOT NULL,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP, end_time TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'running', duration INTEGER DEFAULT 0,
    platform TEXT NOT NULL, tags TEXT, sampling_interval INTEGER DEFAULT 1000);
CREATE TABLE metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, cpu REAL, memory REAL, fps REAL,
    network_up REAL, network_down REAL, battery_level REAL);
CREATE TABLE alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, alert_type TEXT NOT NULL, metric_name TEXT,
    current_value REAL, threshold_value REAL, severity TEXT, description TEXT, resolved BOOLEAN DEFAULT 0);
"""


def test_monitoring_legacy_db_compat(tmp_path):
    """旧（裸 sqlite3，无 app_name 列）schema 建库 + 样例 → 新 ORM DatabaseManager 打开读写。

    覆盖：ensure_schema 补 app_name 列 + ORM 读写存量数据。
    """
    legacy = tmp_path / "monitoring.db"
    with sqlite3.connect(legacy) as raw:
        raw.executescript(_LEGACY_MONITORING_DDL)
        raw.execute(
            "INSERT INTO sessions (id, device_id, app_package, platform, status) "
            "VALUES (1, 'legacy_dev', 'com.old', 'android', 'stopped')"
        )
        raw.execute("INSERT INTO metrics (session_id, cpu, fps) VALUES (1, 42.0, 55.0)")
        raw.commit()
        # 确认旧库无 app_name 列
        cols = {r[1] for r in raw.execute("PRAGMA table_info(sessions)")}
        assert "app_name" not in cols

    # 新 ORM 打开（应自动补 app_name 列）
    db = DatabaseManager(str(legacy))

    # app_name 列已补上
    with sqlite3.connect(legacy) as raw:
        cols = {r[1] for r in raw.execute("PRAGMA table_info(sessions)")}
        assert "app_name" in cols

    # 存量会话可读
    s = db.get_session(1)
    assert s is not None
    assert s.device_id == "legacy_dev"
    assert s.status == SessionStatus.STOPPED

    # 存量指标可读
    metrics = db.get_metrics(1)
    assert len(metrics) == 1
    assert metrics[0].cpu == 42.0
    assert metrics[0].fps == 55.0

    # 新增正常
    new_s = db.create_session("new_dev", "com.new")
    assert new_s.id is not None
