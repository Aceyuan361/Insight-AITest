# -*- coding: utf-8 -*-
"""
Android 性能采集模块

导出 Android 平台的所有性能采集器类
"""

from insight_aitest.platform.services.collectors.android.cpu_collector import CPUCollector
from insight_aitest.platform.services.collectors.android.memory_collector import MemoryCollector
from insight_aitest.platform.services.collectors.android.fps_collector import (
    FPSMonitor,
    SurfaceStatsCollector,
)
from insight_aitest.platform.services.collectors.android.network_collector import NetworkCollector
from insight_aitest.platform.services.collectors.android.battery_collector import BatteryCollector
from insight_aitest.platform.services.collectors.android.android_apm import AndroidAPM

__all__ = [
    "AndroidAPM",
    "CPUCollector",
    "MemoryCollector",
    "FPSMonitor",
    "SurfaceStatsCollector",
    "NetworkCollector",
    "BatteryCollector",
]
