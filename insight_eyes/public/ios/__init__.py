# -*- coding: utf-8 -*-
"""
iOS 性能采集模块

导出 iOS 平台的所有性能采集器类

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License

Author: Aceyuan361
"""

from insight_eyes.public.ios.cpu_collector import CPUCollector
from insight_eyes.public.ios.memory_collector import MemoryCollector
from insight_eyes.public.ios.fps_collector import FPSCollector
from insight_eyes.public.ios.network_collector import NetworkCollector
from insight_eyes.public.ios.battery_collector import BatteryCollector
from insight_eyes.public.ios.ios_apm import IOSAPM

__all__ = [
    'IOSAPM',
    'CPUCollector',
    'MemoryCollector',
    'FPSCollector',
    'NetworkCollector',
    'BatteryCollector',
]
