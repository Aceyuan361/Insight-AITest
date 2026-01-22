# -*- coding: utf-8 -*-
"""
iOS 内存使用情况采集器

提供 iOS 设备的内存使用数据采集功能

注意：pymobiledevice3 7.2.1 没有 sysmon 服务，因此无法获取
真实的进程内存使用。此实现使用降级方案。

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License
"""

from typing import Dict
from logzero import logger


class MemoryCollector:
    """iOS 内存使用采集"""

    # iOS 设备典型内存配置（MB）
    # 不同设备的物理内存不同，这里使用常见值
    DEVICE_MEMORY_MAP = {
        # iPhone 系列
        'iPhone14,': 6 * 1024,  # 6GB
        'iPhone13,': 4 * 1024,  # 4GB
        'iPhone12,': 4 * 1024,  # 4GB
        'iPhone11,': 4 * 1024,  # 4GB
        # 默认值（适用于大多数现代 iOS 设备）
        'default': 4 * 1024,  # 4GB
    }

    def __init__(self, adapter):
        """
        初始化内存采集器

        Args:
            adapter: IOSDeviceAdapter 实例
        """
        self.adapter = adapter
        self._total_memory_mb = None  # 缓存总内存

    def collect(self) -> Dict[str, float]:
        """
        采集内存使用情况

        由于 pymobiledevice3 7.2.1 没有 sysmon 服务，
        目前返回设备总内存作为参考值。

        Returns:
            {'used_mb': float, 'total_mb': float, 'percentage': float}
        """
        try:
            # 尝试主方案（目前未实现，直接跳到降级方案）
            return self._collect_fallback()

        except Exception as e:
            logger.debug(f"内存采集失败: {e}")
            return self._get_default_value()

    def _collect_fallback(self) -> Dict[str, float]:
        """
        降级方案：返回设备总内存（固定值）

        注意：pymobiledevice3 7.2.1 没有 sysmon 服务，
        无法获取真实的内存使用数据。

        可能的改进方向：
        1. 使用 IORegistry 获取硬件内存信息
        2. 使用 mobilegestalt 获取设备型号，推算内存大小
        3. 使用 instruments 命令行工具（需要 macOS）

        Returns:
            {'used_mb': float, 'total_mb': float, 'percentage': float}
        """
        logger.info(
            "iOS 内存采集使用设备总内存（pymobiledevice3 7.2.1 没有 sysmon 服务）"
        )

        # 获取设备总内存
        if self._total_memory_mb is None:
            self._total_memory_mb = self._get_device_total_memory()

        # 返回总内存作为参考（无法获取真实使用量）
        return {
            'used_mb': 0.0,  # 使用量无法获取
            'total_mb': float(self._total_memory_mb),
            'percentage': 0.0  # 使用率无法计算
        }

    def _get_device_total_memory(self) -> int:
        """
        获取设备总内存（MB）

        尝试通过 mobilegestalt 获取设备型号，然后查表获取内存大小

        Returns:
            int: 总内存（MB）
        """
        try:
            from pymobiledevice3.lockdown import create_using_usbmux
            from pymobiledevice3.services.diagnostics import DiagnosticsService

            logger.info("===== iOS 内存采集 =====")
            logger.info("API: pymobiledevice3 DiagnosticsService.mobilegestalt()")
            logger.info("参数: ['HardwarePlatform']")

            lockdown = create_using_usbmux()
            diagnostics = DiagnosticsService(lockdown)

            # 获取设备信息
            info = diagnostics.mobilegestalt(['HardwarePlatform'])

            logger.info(f"API 返回数据: {info}")

            if info and 'HardwarePlatform' in info:
                model = info['HardwarePlatform']
                logger.info(f"设备型号: {model}")

                # 查表获取内存
                for key, memory in self.DEVICE_MEMORY_MAP.items():
                    if model.startswith(key.rstrip(',')):
                        logger.info(f"匹配到内存配置: {memory}MB (型号: {model})")
                        return memory

            # 未匹配到，使用默认值
            default_memory = self.DEVICE_MEMORY_MAP['default']
            logger.warning(
                f"未匹配到设备型号，使用默认内存值: {default_memory}MB\n"
                f"请确认设备型号并更新 DEVICE_MEMORY_MAP"
            )
            return default_memory

        except Exception as e:
            logger.error(f"获取设备内存失败: {e}，使用默认值")
            return self.DEVICE_MEMORY_MAP['default']

    def _get_default_value(self) -> Dict[str, float]:
        """返回默认值（全部失败时）"""
        logger.warning("内存采集完全失败，返回零值")
        return {
            'used_mb': 0.0,
            'total_mb': 0.0,
            'percentage': 0.0
        }
