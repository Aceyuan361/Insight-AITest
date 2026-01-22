# -*- coding: utf-8 -*-
"""
iOS 内存使用情况采集器

提供 iOS 设备的内存使用数据采集功能

数据采集优先级：
1. pymobiledevice3 developer dvt sysmon（首选，Developer Mode）
2. py-ios-device instruments（降级方案，instruments 协议）

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License
"""

from typing import Dict
from logzero import logger


class MemoryCollector:
    """iOS 内存使用采集"""

    # iOS 设备典型内存配置（MB）
    DEVICE_MEMORY_MAP = {
        'iPhone14,': 6 * 1024,  # 6GB
        'iPhone13,': 4 * 1024,  # 4GB
        'iPhone12,': 4 * 1024,  # 4GB
        'iPhone11,': 4 * 1024,  # 4GB
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
        self._py_ios_device_helper = None
        self._total_memory_mb = None

    def collect(self) -> Dict[str, float]:
        """
        采集内存使用情况

        数据采集优先级：
        1. pymobiledevice3 developer dvt sysmon（首选）
        2. py-ios-device instruments（降级方案）
        3. 默认值（最终降级）

        Returns:
            {'used_mb': float, 'total_mb': float, 'percentage': float}
        """
        # 获取设备总内存（用于计算百分比）
        if self._total_memory_mb is None:
            self._total_memory_mb = self._get_device_total_memory()

        # 方案 1: 尝试 pymobiledevice3 sysmon
        try:
            from .sysmon_helper import SysmonHelper

            if self._sysmon_helper is None:
                self._sysmon_helper = SysmonHelper()

            if self._sysmon_helper.is_available():
                process = self._sysmon_helper.get_process_by_bundle_id(self.bundle_id)

                if process:
                    memory_data = self._sysmon_helper.parse_memory_usage(process)
                    # 更新 total_mb 为实际设备内存
                    memory_data['total_mb'] = float(self._total_memory_mb)
                    memory_data['percentage'] = round((memory_data['used_mb'] / self._total_memory_mb * 100), 2)

                    logger.info(
                        f"===== iOS 内存采集成功 (sysmon) =====\n"
                        f"API: pymobiledevice3 developer dvt sysmon process single\n"
                        f"Bundle ID: {self.bundle_id}\n"
                        f"PID: {process.get('pid')}\n"
                        f"内存使用: {memory_data['used_mb']}MB / {memory_data['total_mb']}MB ({memory_data['percentage']}%)"
                    )
                    return memory_data

        except ImportError:
            logger.debug("SysmonHelper 不可用，尝试降级方案")
        except Exception as e:
            logger.debug(f"Sysmon 采集失败: {e}，尝试降级方案")

        # 方案 2: 尝试 py-ios-device
        try:
            from .py_ios_device_helper import PyiOSDeviceHelper

            if self._py_ios_device_helper is None:
                self._py_ios_device_helper = PyiOSDeviceHelper()

            if self._py_ios_device_helper.is_available():
                process_data = self._py_ios_device_helper.get_process_cpu_memory(self.bundle_id)

                if process_data:
                    memory_data = self._py_ios_device_helper.parse_memory_usage(process_data)
                    # 更新 total_mb 为实际设备内存
                    memory_data['total_mb'] = float(self._total_memory_mb)
                    memory_data['percentage'] = round((memory_data['used_mb'] / self._total_memory_mb * 100), 2)

                    logger.info(
                        f"===== iOS 内存采集成功 (py-ios-device) =====\n"
                        f"API: py-ios-device instruments sysmontap\n"
                        f"Bundle ID: {self.bundle_id}\n"
                        f"PID: {process_data.get('pid')}\n"
                        f"内存使用: {memory_data['used_mb']}MB / {memory_data['total_mb']}MB ({memory_data['percentage']}%)"
                    )
                    return memory_data

        except ImportError:
            logger.debug("py-ios-device 未安装，使用最终降级方案")
        except Exception as e:
            logger.debug(f"py-ios-device 采集失败: {e}，使用最终降级方案")

        # 方案 3: 最终降级方案
        return self._collect_final_fallback()

    def _collect_final_fallback(self) -> Dict[str, float]:
        """
        最终降级方案：返回设备总内存

        当所有采集方案都不可用时使用。

        Returns:
            {'used_mb': float, 'total_mb': float, 'percentage': float}
        """
        logger.warning(
            "===== iOS 内存采集（最终降级方案）=====\n"
            "状态: 所有真实数据源均不可用\n"
            "说明:\n"
            "  - pymobiledevice3 sysmon: 需要 Developer Mode\n"
            "  - py-ios-device: 请运行 pip install py-ios-device\n"
            f"返回数据: used_mb=0.0 (无法获取), total_mb={self._total_memory_mb}MB (设备总内存)"
        )

        return {
            'used_mb': 0.0,
            'total_mb': float(self._total_memory_mb),
            'percentage': 0.0
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
