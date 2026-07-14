# -*- coding: utf-8 -*-
"""DeviceManager 单元测试（platform services）。

覆盖 scan_devices 降级 / start/stop_session / _check_and_save_alerts / stream_metrics。
全部用 mock，不依赖真实设备，可 CI 全量运行。

复用 tests/conftest.py 的 dispose_all autouse（持久层隔离）。
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from insight_aitest.platform.persistence.database import DatabaseManager
from insight_aitest.platform.services.device_manager import DeviceManager
from insight_aitest.platform.services.models.metrics import MetricsData
from insight_aitest.platform.services.models.session import SessionStatus


@pytest.fixture(autouse=True)
def _reset_device_manager_state():
    """重置 DeviceManager 类级共享状态（跨测试隔离）。"""
    DeviceManager._cancel_tokens.clear()
    DeviceManager._adapter_cache.clear()
    DeviceManager._alert_cooldown.clear()
    DeviceManager._session_alert_thresholds.clear()
    yield
    DeviceManager._cancel_tokens.clear()
    DeviceManager._adapter_cache.clear()
    DeviceManager._alert_cooldown.clear()
    DeviceManager._session_alert_thresholds.clear()


@pytest.fixture(autouse=True)
def _reset_db_singleton():
    """DatabaseManager 单例隔离（同 test_database_manager.py 模式）。"""
    DatabaseManager._instance = None
    yield
    DatabaseManager._instance = None


def _db(tmp_path):
    return DatabaseManager(str(tmp_path / "monitoring.db"))


# ===== scan_devices 降级路径 =====


def test_scan_devices_returns_empty_when_import_fails(monkeypatch):
    """桌面层模块不可用时（CI/无设备环境）返回空列表，不抛异常。"""
    import builtins

    real_import = builtins.__import__

    def _fail_import(name, *args, **kwargs):
        if name.startswith("insight_aitest.platform.services.device_common"):
            raise ImportError("simulated unavailable")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fail_import)
    result = DeviceManager.scan_devices()
    assert result == []


# ===== start/stop_session =====


async def test_start_session_creates_cancel_token_and_thresholds(tmp_path):
    """start_session 应创建 DB 会话、写入会话级阈值、创建取消令牌。"""
    db = _db(tmp_path)
    with patch.object(DatabaseManager, "default", return_value=db):
        s = await DeviceManager.start_session(
            "dev1",
            "com.app",
            platform="android",
            sampling_interval=500,
            alert_thresholds={
                "fps": 30.0,
                "memory": 400.0,
                "cpu": 70.0,
                "temperature": 40.0,
            },
        )
    assert s.id is not None
    assert s.sampling_interval == 500
    # 取消令牌已创建
    assert s.id in DeviceManager._cancel_tokens
    assert isinstance(DeviceManager._cancel_tokens[s.id], asyncio.Event)
    # 自定义阈值已存
    assert DeviceManager._session_alert_thresholds[s.id]["fps_threshold"] == 30.0
    assert DeviceManager._session_alert_thresholds[s.id]["memory_threshold_mb"] == 400.0


async def test_start_session_default_thresholds_when_none(tmp_path):
    """未传 alert_thresholds 时使用默认阈值。"""
    db = _db(tmp_path)
    with patch.object(DatabaseManager, "default", return_value=db):
        s = await DeviceManager.start_session("dev1", "com.app")
    t = DeviceManager._session_alert_thresholds[s.id]
    assert t["fps_threshold"] == 50.0
    assert t["cpu_threshold_percent"] == 50.0


async def test_stop_session_sets_cancel_token_and_db_status(tmp_path):
    """stop_session 应 set 取消令牌、删除令牌、更新 DB 状态为 stopped。"""
    db = _db(tmp_path)
    with patch.object(DatabaseManager, "default", return_value=db):
        s = await DeviceManager.start_session("dev1", "com.app")
        await DeviceManager.stop_session(s.id)
    # 令牌已清理
    assert s.id not in DeviceManager._cancel_tokens
    # DB 状态已更新
    got = db.get_session(s.id)
    assert got.status == SessionStatus.STOPPED


# ===== _check_and_save_alerts =====


def _metrics(**kw) -> MetricsData:
    """构造一个指标对象，默认所有字段 None。"""
    return MetricsData(timestamp=datetime.now(), **kw)


def _make_session_with_thresholds(db) -> int:
    """在 DB 创建真实会话（满足 alerts FK 约束）并写入标准阈值，返回 session id。"""
    s = db.create_session("dev1", "com.app", platform="android")
    DeviceManager._session_alert_thresholds[s.id] = {
        "fps_threshold": 50.0,
        "memory_threshold_mb": 100.0,
        "cpu_threshold_percent": 50.0,
        "battery_threshold_temp": 35.0,
    }
    return s.id


def test_alert_low_fps_warning(tmp_path):
    """FPS 低于阈值（≥20）→ warning，触发后冷却期内不再触发。"""
    db = _db(tmp_path)
    sid = _make_session_with_thresholds(db)
    m = _metrics(fps=25.0)  # 25 < 50, ≥20 → warning
    alerts = DeviceManager._check_and_save_alerts(db, sid, "dev1", "com.app", m)
    assert len(alerts) == 1
    assert alerts[0]["level"] == "警告"  # warning → 警告
    assert "FPS过低" in alerts[0]["content"]
    # DB 已存
    assert len(db.get_alerts(session_id=sid)) == 1


def test_alert_low_fps_critical(tmp_path):
    """FPS 严重低（<20）→ critical。"""
    db = _db(tmp_path)
    sid = _make_session_with_thresholds(db)
    m = _metrics(fps=10.0)  # <20 → critical
    alerts = DeviceManager._check_and_save_alerts(db, sid, "dev1", "com.app", m)
    assert len(alerts) == 1
    assert alerts[0]["level"] == "严重"  # critical → 严重


def test_alert_cooldown_suppresses_within_window(tmp_path):
    """冷却期内（默认 30s）同 session 同类型告警被抑制。"""
    db = _db(tmp_path)
    sid = _make_session_with_thresholds(db)
    m = _metrics(fps=25.0)
    first = DeviceManager._check_and_save_alerts(db, sid, "dev1", "com.app", m)
    second = DeviceManager._check_and_save_alerts(db, sid, "dev1", "com.app", m)
    assert len(first) == 1
    assert len(second) == 0  # 冷却期，抑制


def test_alert_high_memory_cpu_temp(tmp_path):
    """内存高/CPU 高/温度高三类同时触发。"""
    db = _db(tmp_path)
    sid = _make_session_with_thresholds(db)
    m = _metrics(memory=200.0, cpu=60.0, temperature=40.0)
    alerts = DeviceManager._check_and_save_alerts(db, sid, "dev1", "com.app", m)
    # 三类（FPS 正常不触发）
    types = {a["content"].split(":")[0] for a in alerts}
    assert "内存过高" in types
    assert "CPU过高" in types
    assert "电池温度过高" in types


def test_alert_cpu_critical_when_ge_90(tmp_path):
    """CPU ≥90 → critical（严重）。"""
    db = _db(tmp_path)
    sid = _make_session_with_thresholds(db)
    m = _metrics(cpu=95.0)
    alerts = DeviceManager._check_and_save_alerts(db, sid, "dev1", "com.app", m)
    assert len(alerts) == 1
    assert alerts[0]["level"] == "严重"


def test_alert_none_when_all_normal(tmp_path):
    """所有指标正常时不触发任何告警。"""
    db = _db(tmp_path)
    sid = _make_session_with_thresholds(db)
    m = _metrics(fps=60.0, memory=50.0, cpu=20.0, temperature=30.0)
    alerts = DeviceManager._check_and_save_alerts(db, sid, "dev1", "com.app", m)
    assert len(alerts) == 0


def test_alert_none_when_metrics_all_none(tmp_path):
    """所有指标 None 时（采集全失败）不触发告警，不抛异常。"""
    db = _db(tmp_path)
    sid = _make_session_with_thresholds(db)
    m = _metrics()
    alerts = DeviceManager._check_and_save_alerts(db, sid, "dev1", "com.app", m)
    assert len(alerts) == 0


# ===== stream_metrics =====


async def test_stream_metrics_yields_data_and_saves(tmp_path):
    """stream_metrics 正常采集 → yield MetricsData + 存库，取消令牌停止，适配器清理。"""
    db = _db(tmp_path)
    with patch.object(DatabaseManager, "default", return_value=db):
        s = await DeviceManager.start_session("dev1", "com.app", sampling_interval=10)

    # mock 适配器：collect_* 返回固定数据（全部在阈值内，不触发告警）
    fake_adapter = MagicMock()
    fake_adapter.is_connected.return_value = True
    fake_adapter.collect_fps.return_value = {"fps": 60}
    fake_adapter.collect_memory.return_value = {"totalPass": 50.0}
    fake_adapter.collect_cpu.return_value = {"appCpuRate": 20.0}
    fake_adapter.collect_network.return_value = {"upFlow": 1.0, "downFlow": 2.0}
    fake_adapter.collect_battery.return_value = {"level": 90, "temperature": 30.0}

    with patch(
        "insight_aitest.platform.services.device_adapters.device_adapters.DeviceAdapterFactory.create_adapter",
        return_value=fake_adapter,
    ):
        results = []
        async for data in DeviceManager.stream_metrics(s.id):
            results.append(data)
            # 第一轮后停止
            DeviceManager._cancel_tokens[s.id].set()

    assert len(results) >= 1
    # 第一条应是正常指标（fps=60，所有指标在阈值内不触发告警）
    first = results[0]
    assert first.fps == 60.0
    assert first.memory == 50.0
    # 已存库
    assert len(db.get_metrics(s.id)) >= 1
    # 适配器资源已清理
    fake_adapter.cleanup.assert_called_once()


async def test_stream_metrics_no_session_returns_empty(tmp_path):
    """会话不存在时直接返回（不 yield）。"""
    results = []
    async for _ in DeviceManager.stream_metrics(999999):
        results.append(_)
    assert results == []


async def test_stream_metrics_ios_field_shape(tmp_path):
    """iOS 适配器返回的字段（used_mb/cpu_app）能正确流经 DeviceManager 管道。"""
    db = _db(tmp_path)
    with patch.object(DatabaseManager, "default", return_value=db):
        s = await DeviceManager.start_session(
            "ios-dev1", "com.example.app", platform="ios", sampling_interval=10
        )

    # mock iOS 形状的适配器返回值（字段名与 Android 不同）
    fake_adapter = MagicMock()
    fake_adapter.is_connected.return_value = True
    fake_adapter.collect_fps.return_value = {"fps": 60, "jank": 0}  # iOS 占位
    fake_adapter.collect_memory.return_value = {"used_mb": 128.5, "total_mb": 4096.0}
    fake_adapter.collect_cpu.return_value = {"cpu_app": 15.3, "cpu_system": 30.0}
    fake_adapter.collect_network.return_value = {"upFlow": 2.0, "downFlow": 5.0}
    fake_adapter.collect_battery.return_value = {"level": 85, "temperature": 25.0}

    with patch(
        "insight_aitest.platform.services.device_adapters.device_adapters.DeviceAdapterFactory.create_adapter",
        return_value=fake_adapter,
    ):
        results = []
        async for data in DeviceManager.stream_metrics(s.id):
            results.append(data)
            DeviceManager._cancel_tokens[s.id].set()

    assert len(results) >= 1
    first = results[0]
    # iOS 字段映射：used_mb → memory, cpu_app → cpu
    assert first.memory == 128.5
    assert first.cpu == 15.3
    # 网络/电池字段两种平台一致
    assert first.network_up == 2.0
    assert first.network_down == 5.0
    fake_adapter.cleanup.assert_called_once()
