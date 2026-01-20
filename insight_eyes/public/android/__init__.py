# -*- coding: utf-8 -*-
"""
Android 性能采集模块

导出 Android 平台的所有性能采集器类

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License

Author: Aceyuan361
"""

from insight_eyes.public.android.cpu_collector import CPUCollector
from insight_eyes.public.android.memory_collector import MemoryCollector
from insight_eyes.public.android.fps_collector import FPSMonitor, SurfaceStatsCollector
from insight_eyes.public.android.network_collector import NetworkCollector
from insight_eyes.public.android.battery_collector import BatteryCollector
from insight_eyes.public.android.android_apm import AndroidAPM

__all__ = [
    'AndroidAPM',
    'CPUCollector',
    'MemoryCollector',
    'FPSMonitor',
    'SurfaceStatsCollector',
    'NetworkCollector',
    'BatteryCollector',
]
