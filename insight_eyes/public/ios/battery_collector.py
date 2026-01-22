# -*- coding: utf-8 -*-
"""
iOS 电池状态采集器

提供 iOS 设备的电池状态数据采集功能

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License
"""

from typing import Dict, Any
from logzero import logger


class BatteryCollector:
    """iOS 电池状态采集"""

    def __init__(self, adapter):
        """
        初始化电池采集器

        Args:
            adapter: IOSDeviceAdapter 实例
        """
        self.adapter = adapter

    def collect(self) -> Dict[str, Any]:
        """
        采集电池状态

        Returns:
            {'level': int, 'temperature': float}
        """
        try:
            return self._collect_via_lockdown()

        except Exception as e:
            logger.debug(f"电池采集失败: {e}")
            return self._get_default_value()

    def _collect_via_lockdown(self) -> Dict[str, Any]:
        """
        通过 Lockdown 连接获取电池信息

        iOS 设备电池信息可以通过 pymobiledevice3 的 LockdownClient 获取

        Returns:
            {'level': int, 'temperature': float}
        """
        try:
            if not self.adapter or not self.adapter._connection:
                logger.warning("设备未连接，返回默认电池值")
                return self._get_default_value()

            # 尝试获取电池信息
            # 注意：iOS 电池信息需要通过特定的 lockdown 查询
            # 这是占位实现
            logger.info("iOS 电池采集使用估算值（尚未实现完整功能）")

            return {
                'level': 100,
                'temperature': 25.0
            }

        except Exception as e:
            logger.debug(f"Lockdown 电池查询失败: {e}")
            return self._get_default_value()

    def _get_default_value(self) -> Dict[str, Any]:
        """返回默认值"""
        return {'level': 100, 'temperature': 25.0}
