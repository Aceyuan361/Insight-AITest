# -*- coding: utf-8 -*-
"""
核心层数据模型

此包提供 Insight-AITest 的核心数据模型定义，包括：
- Session: 监控会话模型
- Device: 设备信息模型
- MetricsData: 性能指标数据模型

所有模型都支持 to_dict() 和 from_dict() 方法进行序列化和反序列化。
"""

from insight_aitest.platform.services.models.session import Session, SessionStatus
from insight_aitest.platform.services.models.device import Device, DeviceType, DeviceStatus
from insight_aitest.platform.services.models.metrics import MetricsData, MetricType

__all__ = [
    "Session",
    "SessionStatus",
    "Device",
    "DeviceType",
    "DeviceStatus",
    "MetricsData",
    "MetricType",
]
