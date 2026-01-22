# -*- coding: utf-8 -*-
"""
iOS CPU 使用率采集器

提供 iOS 设备的 CPU 使用率数据采集功能

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License
"""

from typing import Dict
from logzero import logger


class CPUCollector:
    """iOS CPU 使用率采集"""

    def __init__(self, adapter):
        """
        初始化 CPU 采集器

        Args:
            adapter: IOSDeviceAdapter 实例
        """
        self.adapter = adapter

    def collect(self) -> Dict[str, float]:
        """
        采集 CPU 使用率

        Returns:
            {'cpu_app': float, 'cpu_system': float}
        """
        try:
            # 方法 1：尝试通过 pymobiledevice3 获取进程信息
            return self._collect_via_process_info()

        except Exception as e:
            logger.debug(f"进程信息方法失败: {e}")

            # 方法 2：返回默认值
            return self._get_default_value()

    def _collect_via_process_info(self) -> Dict[str, float]:
        """
        通过进程信息获取 CPU 使用率

        iOS 设备需要通过 pymobiledevice3 获取进程列表和 CPU 使用率
        这是占位实现，实际需要调用原生 API

        Returns:
            {'cpu_app': float, 'cpu_system': float}
        """
        # TODO: 实现 iOS CPU 采集
        # 需要使用 pymobiledevice3 的进程管理功能
        # 目前返回估算值
        logger.info("iOS CPU 采集使用估算值（尚未实现完整功能）")
        return {'cpu_app': 0.0, 'cpu_system': 10.0}

    def _get_default_value(self) -> Dict[str, float]:
        """返回默认值"""
        logger.warning("CPU 采集失败，返回默认值")
        return {'cpu_app': 0.0, 'cpu_system': 0.0}
