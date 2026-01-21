# -*- coding: utf-8 -*-
"""
设备连接与App枚举筛选模块
提供设备管理、应用枚举、设备监控等功能

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License

Author: Aceyuan361
"""

from .models import (
    # 平台和状态枚举
    Platform,
    DeviceStatus,
    AppStatus,
    DeviceChangeType,

    # 数据模型
    AppInfo,
    DeviceInfo,
    DeviceFilter,
    AppFilter,
    MonitoringConfig,
    DeviceChangeEvent,
)

from .device_adapters import (
    BaseDeviceAdapter,
    AndroidDeviceAdapter,
    DeviceAdapterFactory,
)

from .app_enumerator import (
    BaseAppEnumerator,
    AndroidAppEnumerator,
    AppEnumeratorFactory,
)

from .device_manager import (
    DeviceScannerThread,
    DeviceMonitorThread,
    DeviceManager,
)

__all__ = [
    # 模型类
    'Platform',
    'DeviceStatus',
    'AppStatus',
    'DeviceChangeType',
    'AppInfo',
    'DeviceInfo',
    'DeviceFilter',
    'AppFilter',
    'MonitoringConfig',
    'DeviceChangeEvent',

    # 设备适配器
    'BaseDeviceAdapter',
    'AndroidDeviceAdapter',
    'DeviceAdapterFactory',

    # 应用枚举器
    'BaseAppEnumerator',
    'AndroidAppEnumerator',
    'AppEnumeratorFactory',

    # 设备管理器
    'DeviceScannerThread',
    'DeviceMonitorThread',
    'DeviceManager',
]

# 模块版本
__version__ = '1.0.0'

# 模块信息
__author__ = 'Aceyuan361'
__license__ = 'MIT'
__description__ = '设备连接与App枚举筛选模块'
