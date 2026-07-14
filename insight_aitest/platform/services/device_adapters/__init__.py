# -*- coding: utf-8 -*-
"""
设备适配器层 - 平台级设备抽象。

包装底层采集器（platform.services.collectors），对外暴露统一的
DeviceAdapter / AppEnumerator 接口。供设备管理器和各业务模块复用。
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

__all__ = [
    # 模型类
    "Platform",
    "DeviceStatus",
    "AppStatus",
    "DeviceChangeType",
    "AppInfo",
    "DeviceInfo",
    "DeviceFilter",
    "AppFilter",
    "MonitoringConfig",
    "DeviceChangeEvent",
    # 设备适配器
    "BaseDeviceAdapter",
    "AndroidDeviceAdapter",
    "IOSDeviceAdapter",
    "DeviceAdapterFactory",
    # 应用枚举器
    "BaseAppEnumerator",
    "AndroidAppEnumerator",
    "IOSAppEnumerator",
    "AppEnumeratorFactory",
]

__version__ = "1.0.0"
