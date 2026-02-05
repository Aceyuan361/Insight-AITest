# -*- coding: utf-8 -*-
"""
设备连接与App枚举筛选模块
提供设备管理、应用枚举、设备监控等功能
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
    IOSDeviceAdapter,
    DeviceAdapterFactory,
)

from .app_enumerator import (
    BaseAppEnumerator,
    AndroidAppEnumerator,
    AppEnumeratorFactory,
)

# iOS 应用枚举器在单独的文件中
try:
    from .ios_app_enumerator import IOSAppEnumerator
    _IOS_ENUMERATOR_AVAILABLE = True
except ImportError:
    _IOS_ENUMERATOR_AVAILABLE = False
    IOSAppEnumerator = None  # type: ignore

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
    'IOSDeviceAdapter',
    'DeviceAdapterFactory',

    # 应用枚举器
    'BaseAppEnumerator',
    'AndroidAppEnumerator',
    'IOSAppEnumerator',
    'AppEnumeratorFactory',

    # 设备管理器
    'DeviceScannerThread',
    'DeviceMonitorThread',
    'DeviceManager',
]

# 模块版本
__version__ = '1.0.0'

# 模块信息
__license__ = 'MIT'
__description__ = '设备连接与App枚举筛选模块'
