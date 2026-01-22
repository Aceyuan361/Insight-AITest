# -*- coding: utf-8 -*-
"""
iOS 内存使用情况采集器

提供 iOS 设备的内存使用数据采集功能

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License
"""

from typing import Dict
from logzero import logger


class MemoryCollector:
    """iOS 内存使用采集"""

    def __init__(self, adapter):
        """
        初始化内存采集器

        Args:
            adapter: IOSDeviceAdapter 实例
        """
        self.adapter = adapter

    def collect(self) -> Dict[str, float]:
        """
        采集内存使用情况

        Returns:
            {'used_mb': float, 'total_mb': float}
        """
        try:
            return self._collect_via_device_info()

        except Exception as e:
            logger.debug(f"内存采集失败: {e}")
            return self._get_default_value()

    def _collect_via_device_info(self) -> Dict[str, float]:
        """
        通过设备信息获取内存使用情况

        iOS 设备内存信息需要通过 pymobiledevice3 获取
        这是占位实现，实际需要调用原生 API

        Returns:
            {'used_mb': float, 'total_mb': float}
        """
        # TODO: 实现 iOS 内存采集
        # 需要使用 pymobiledevice3 获取设备内存信息
        # 目前返回估算值
        logger.info("iOS 内存采集使用估算值（尚未实现完整功能）")
        return {'used_mb': 0.0, 'total_mb': 0.0}

    def _get_default_value(self) -> Dict[str, float]:
        """返回默认值"""
        return {'used_mb': 0.0, 'total_mb': 0.0}
