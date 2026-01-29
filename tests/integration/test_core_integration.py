# -*- coding: utf-8 -*-
"""
核心层集成测试
验证核心层各模块协同工作
"""
import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from insight_eyes.core.device_manager import DeviceManager
from insight_eyes.core.database import DatabaseManager
from insight_eyes.core.models.metrics import MetricsData
from insight_eyes.core.models.session import SessionStatus


@pytest.fixture
def temp_db():
    """临时数据库"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    try:
        Path(db_path).unlink()
    except PermissionError:
        # Windows 上可能无法立即删除文件，忽略此错误
        pass


@pytest.fixture
def clean_db(temp_db):
    """清除数据库单例并初始化"""
    DatabaseManager._instance = None
    DatabaseManager(temp_db)
    yield
    DatabaseManager._instance = None


@pytest.mark.asyncio
async def test_full_monitoring_workflow(clean_db):
    """测试完整监控流程"""
    # 1. 扫描设备
    devices = DeviceManager.scan_devices()
    assert isinstance(devices, list)

    # 2. 开始会话
    session = await DeviceManager.start_session("test_device", "com.example.app")
    assert session.id is not None
    assert session.device_id == "test_device"
    assert session.app_package == "com.example.app"

    # 3. 保存指标数据
    db = DatabaseManager()
    metrics = MetricsData(
        timestamp=datetime.now(),
        cpu=50.0,
        memory=512.0,
        fps=60.0,
    )
    db.save_metrics(session.id, metrics)

    # 4. 验证数据已保存
    retrieved = db.get_session(session.id)
    assert retrieved is not None
    assert retrieved.id == session.id

    # 5. 查询指标数据
    metrics_list = db.get_metrics(session.id)
    assert len(metrics_list) >= 1
    assert metrics_list[0].cpu == 50.0

    # 6. 停止会话
    await DeviceManager.stop_session(session.id)

    # 7. 验证会话已停止
    final_session = db.get_session(session.id)
    assert final_session.status == SessionStatus.STOPPED


@pytest.mark.asyncio
async def test_multiple_sessions_workflow(clean_db):
    """测试多会话监控流程"""
    db = DatabaseManager()

    # 创建多个会话
    session1 = await DeviceManager.start_session("device1", "app1")
    session2 = await DeviceManager.start_session("device2", "app2")

    # 为每个会话保存指标
    metrics1 = MetricsData(timestamp=datetime.now(), cpu=30.0, memory=256.0)
    metrics2 = MetricsData(timestamp=datetime.now(), cpu=70.0, memory=768.0)

    db.save_metrics(session1.id, metrics1)
    db.save_metrics(session2.id, metrics2)

    # 验证会话独立
    assert session1.id != session2.id

    # 列出所有会话
    sessions = db.list_sessions()
    assert len(sessions) >= 2

    # 验证各自的指标数据
    session1_metrics = db.get_metrics(session1.id)
    session2_metrics = db.get_metrics(session2.id)
    assert len(session1_metrics) >= 1
    assert len(session2_metrics) >= 1
    assert session1_metrics[0].cpu == 30.0
    assert session2_metrics[0].cpu == 70.0

    # 清理
    await DeviceManager.stop_session(session1.id)
    await DeviceManager.stop_session(session2.id)


@pytest.mark.asyncio
async def test_session_lifecycle(clean_db):
    """测试会话完整生命周期"""
    db = DatabaseManager()

    # 创建 -> 运行 -> 停止
    session = await DeviceManager.start_session("device", "app")
    assert session.status == SessionStatus.RUNNING

    await DeviceManager.stop_session(session.id)

    stopped = db.get_session(session.id)
    assert stopped.status == SessionStatus.STOPPED
    assert stopped.end_time is not None


def test_database_singleton(clean_db):
    """测试数据库单例模式"""
    db1 = DatabaseManager()
    db2 = DatabaseManager()

    # 应该是同一个实例
    assert db1 is db2

    # 应该使用同一个数据库文件
    assert db1.db_path == db2.db_path
