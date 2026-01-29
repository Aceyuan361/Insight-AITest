# -*- coding: utf-8 -*-
"""
数据库管理器测试
"""
import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from insight_eyes.core.database import DatabaseManager
from insight_eyes.core.models.session import SessionStatus
from insight_eyes.core.models.metrics import MetricsData


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
def db_manager(temp_db):
    """数据库管理器实例"""
    # 清除单例
    DatabaseManager._instance = None
    return DatabaseManager(temp_db)


def test_create_session(db_manager):
    """测试创建会话"""
    session = db_manager.create_session("test_device", "com.example.app")

    assert session.id is not None
    assert session.device_id == "test_device"
    assert session.app_package == "com.example.app"
    assert session.status == SessionStatus.RUNNING


def test_save_and_get_metrics(db_manager):
    """测试保存和获取指标"""
    session = db_manager.create_session("test_device", "com.example.app")

    metrics = MetricsData(
        timestamp=datetime.now(),
        cpu=50.0,
        memory=512.0,
        fps=60.0,
    )

    db_manager.save_metrics(session.id, metrics)

    retrieved = db_manager.get_session(session.id)
    assert retrieved is not None
    assert retrieved.id == session.id


def test_update_session(db_manager):
    """测试更新会话"""
    session = db_manager.create_session("test_device", "com.example.app")

    db_manager.update_session(
        session.id,
        status="stopped",
        end_time=datetime.now().isoformat(),
        duration=60,
    )

    updated = db_manager.get_session(session.id)
    assert updated.status.value == "stopped"


def test_list_sessions(db_manager):
    """测试列出会话"""
    db_manager.create_session("device1", "app1")
    db_manager.create_session("device2", "app2")

    sessions = db_manager.list_sessions()
    assert len(sessions) >= 2


def test_delete_session(db_manager):
    """测试删除会话"""
    session = db_manager.create_session("test_device", "com.example.app")
    session_id = session.id

    db_manager.delete_session(session_id)

    retrieved = db_manager.get_session(session_id)
    assert retrieved is None


def test_create_session_validation_empty_device_id(db_manager):
    """测试创建会话时空设备ID验证"""
    with pytest.raises(ValueError, match="device_id cannot be empty"):
        db_manager.create_session("", "com.example.app")


def test_create_session_validation_whitespace_device_id(db_manager):
    """测试创建会话时空白设备ID验证"""
    with pytest.raises(ValueError, match="device_id cannot be empty"):
        db_manager.create_session("   ", "com.example.app")


def test_create_session_validation_empty_app_package(db_manager):
    """测试创建会话时空包名验证"""
    with pytest.raises(ValueError, match="app_package cannot be empty"):
        db_manager.create_session("test_device", "")


def test_create_session_validation_invalid_platform(db_manager):
    """测试创建会话时无效平台验证"""
    with pytest.raises(ValueError, match="Invalid platform"):
        db_manager.create_session("test_device", "com.example.app", platform="windows")


def test_create_session_with_ios_platform(db_manager):
    """测试创建iOS平台会话"""
    session = db_manager.create_session("test_device", "com.example.app", platform="ios")

    assert session.platform == "ios"
    assert session.status == SessionStatus.RUNNING
