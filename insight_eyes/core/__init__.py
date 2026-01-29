# -*- coding: utf-8 -*-
"""
Insight-Eye 核心层
提供桌面版和 Web 版共享的业务逻辑
"""

__version__ = "1.0.3"

from insight_eyes.core.models.session import Session, SessionStatus
from insight_eyes.core.models.device import Device, DeviceType, DeviceStatus
from insight_eyes.core.models.metrics import MetricsData, MetricType

from insight_eyes.core.device_manager import DeviceManager
from insight_eyes.core.database import DatabaseManager
# TODO: 后续任务中实现
# from insight_eyes.core.report_generator import ReportGenerator

__all__ = [
    "__version__",
    "Session",
    "SessionStatus",
    "Device",
    "DeviceType",
    "DeviceStatus",
    "MetricsData",
    "MetricType",
    "DeviceManager",
    "DatabaseManager",
    # "ReportGenerator",
]
