# -*- coding: utf-8 -*-
"""
iOS 内存使用情况采集器

提供 iOS 设备的内存使用数据采集功能

使用 pymobiledevice3 developer dvt sysmon 获取真实进程内存数据。

要求：
- Developer Mode 已启用
- DeveloperDiskImage 已挂载

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

    def __init__(self, adapter, bundle_id: str):
        """
        初始化内存采集器

        Args:
            adapter: IOSDeviceAdapter 实例
            bundle_id: 应用的 Bundle ID (如 com.example.app)
        """
        self.adapter = adapter
        self.bundle_id = bundle_id
        self._sysmon_helper = None
        self._total_memory_mb = None  # 缓存总内存

    def collect(self) -> Dict[str, float]:
        """
        采集内存使用情况

        通过 pymobiledevice3 developer dvt sysmon 获取真实数据。

        Returns:
            {'used_mb': float, 'total_mb': float, 'percentage': float}
        """
        try:
            from .sysmon_helper import SysmonHelper

            # 延迟初始化 SysmonHelper
            if self._sysmon_helper is None:
                self._sysmon_helper = SysmonHelper()

            if not self._sysmon_helper.is_available():
                logger.warning("Sysmon 服务不可用，使用降级方案")
                return self._collect_fallback()

            # 获取设备总内存
            if self._total_memory_mb is None:
                self._total_memory_mb = self._get_device_total_memory()

            # 通过 Bundle ID 查找进程
            process = self._sysmon_helper.get_process_by_bundle_id(self.bundle_id)

            if process:
                memory_data = self._sysmon_helper.parse_memory_usage(process)
                logger.info(
                    f"===== iOS 内存采集成功 =====\n"
                    f"API: pymobiledevice3 developer dvt sysmon process single\n"
                    f"Bundle ID: {self.bundle_id}\n"
                    f"PID: {process.get('pid')}\n"
                    f"内存使用: {memory_data['used_mb']}MB / {memory_data['total_mb']}MB ({memory_data['percentage']}%)"
                )
                return memory_data
            else:
                logger.warning(f"未找到进程: {self.bundle_id}，使用降级方案")
                return self._collect_fallback()

        except ImportError:
            logger.warning("无法导入 SysmonHelper，使用降级方案")
            return self._collect_fallback()

        except Exception as e:
            logger.debug(f"内存采集失败: {e}")
            return self._collect_fallback()

    def _collect_fallback(self) -> Dict[str, float]:
        """
        降级方案：返回设备总内存（固定值）

        当 Sysmon 服务不可用时使用。

        Returns:
            {'used_mb': float, 'total_mb': float, 'percentage': float}
        """
        # 获取设备总内存
        if self._total_memory_mb is None:
            self._total_memory_mb = self._get_device_total_memory()

        logger.warning(
            "===== iOS 内存采集（降级方案）=====\n"
            "状态: Sysmon 服务不可用\n"
            "说明: 请确保 Developer Mode 已启用且 DeveloperDiskImage 已挂载\n"
            f"返回数据: used_mb=0.0 (无法获取), total_mb={self._total_memory_mb}MB (设备总内存)"
        )

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

            logger.info("===== iOS 设备内存查询 =====")
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
