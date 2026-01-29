# -*- coding: utf-8 -*-
"""
桌面版与核心层集成模块

此模块演示如何从核心层导入共享功能。
桌面版可以选择性地使用核心层的实现。
"""

# 从核心层导入数据模型（可以用于类型注解和数据交换）
from insight_eyes.core.models.session import Session, SessionStatus
from insight_eyes.core.models.device import Device, DeviceType, DeviceStatus
from insight_eyes.core.models.metrics import MetricsData, MetricType

# 从核心层导入数据库管理器（如果需要使用核心层的简化版本）
# from insight_eyes.core.database import DatabaseManager

# 从核心层导入设备管理器（如果需要使用核心层的会话管理功能）
# from insight_eyes.core.device_manager import DeviceManager

__all__ = [
    "Session",
    "SessionStatus",
    "Device",
    "DeviceType",
    "DeviceStatus",
    "MetricsData",
    "MetricType",
    # "DatabaseManager",
    # "DeviceManager",
]


def convert_desktop_session_to_core(desktop_session_dict: dict) -> Session:
    """将桌面版的会话字典转换为核心层的 Session 对象

    Args:
        desktop_session_dict: 桌面版的会话字典

    Returns:
        核心层的 Session 对象
    """
    from datetime import datetime

    return Session(
        id=desktop_session_dict.get('id'),
        device_id=desktop_session_dict.get('device_id'),
        app_package=desktop_session_dict.get('package_name'),
        platform=desktop_session_dict.get('platform', 'android'),
        start_time=datetime.fromisoformat(desktop_session_dict['start_time']) if isinstance(desktop_session_dict.get('start_time'), str) else desktop_session_dict.get('start_time'),
        end_time=datetime.fromisoformat(desktop_session_dict['end_time']) if desktop_session_dict.get('end_time') and isinstance(desktop_session_dict['end_time'], str) else desktop_session_dict.get('end_time'),
        status=SessionStatus(desktop_session_dict.get('status', 'running')),
        duration=desktop_session_dict.get('duration', 0)
    )
