# -*- coding: utf-8 -*-
"""
iOS CPU 使用率采集器

提供 iOS 设备的 CPU 使用率数据采集功能

数据采集优先级：
1. pymobiledevice3 developer dvt sysmon（首选，Developer Mode）
2. py-ios-device instruments（降级方案，instruments 协议）

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License
"""

from typing import Dict
from logzero import logger


class CPUCollector:
    """iOS CPU 使用率采集"""

    # iOS 设备典型 CPU 使用率（用于最终降级）
    ESTIMATED_IDLE_CPU = 5.0  # 系统空闲时 CPU 使用率
    ESTIMATED_ACTIVE_CPU = 15.0  # 系统活跃时 CPU 使用率

    def __init__(self, adapter, bundle_id: str):
        """
        初始化 CPU 采集器

        Args:
            adapter: IOSDeviceAdapter 实例
            bundle_id: 应用的 Bundle ID (如 com.example.app)
        """
        self.adapter = adapter
        self.bundle_id = bundle_id
        self._sysmon_helper = None
        self._py_ios_device_helper = None

    def collect(self) -> Dict[str, float]:
        """
        采集 CPU 使用率

        数据采集优先级：
        1. pymobiledevice3 developer dvt sysmon（首选）
        2. py-ios-device instruments（降级方案）
        3. 估算值（最终降级）

        Returns:
            {'cpu_app': float, 'cpu_system': float}
        """
        # 方案 1: 尝试 pymobiledevice3 sysmon
        try:
            from .sysmon_helper import SysmonHelper

            if self._sysmon_helper is None:
                self._sysmon_helper = SysmonHelper()

            if self._sysmon_helper.is_available():
                process = self._sysmon_helper.get_process_by_bundle_id(self.bundle_id)

                if process:
                    cpu_usage = self._sysmon_helper.parse_cpu_usage(process)
                    logger.info(
                        f"===== iOS CPU 采集成功 (sysmon) =====\n"
                        f"API: pymobiledevice3 developer dvt sysmon process single\n"
                        f"Bundle ID: {self.bundle_id}\n"
                        f"PID: {process.get('pid')}\n"
                        f"CPU 使用率: {cpu_usage}%"
                    )
                    return {
                        'cpu_app': cpu_usage,
                        'cpu_system': 0.0  # iOS 不区分系统 CPU
                    }

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
                    cpu_usage = self._py_ios_device_helper.parse_cpu_usage(process_data)
                    logger.info(
                        f"===== iOS CPU 采集成功 (py-ios-device) =====\n"
                        f"API: py-ios-device instruments sysmontap\n"
                        f"Bundle ID: {self.bundle_id}\n"
                        f"PID: {process_data.get('pid')}\n"
                        f"CPU 使用率: {cpu_usage}%"
                    )
                    return {
                        'cpu_app': cpu_usage,
                        'cpu_system': 0.0
                    }

        except ImportError:
            logger.debug("py-ios-device 未安装，使用最终降级方案")
        except Exception as e:
            logger.debug(f"py-ios-device 采集失败: {e}，使用最终降级方案")

        # 方案 3: 最终降级方案（估算值）
        return self._collect_final_fallback()

    def _collect_final_fallback(self) -> Dict[str, float]:
        """
        最终降级方案：返回估算值

        当所有采集方案都不可用时使用。

        Returns:
            {'cpu_app': float, 'cpu_system': float}
        """
        logger.warning(
            "===== iOS CPU 采集（最终降级方案）=====\n"
            "状态: 所有真实数据源均不可用\n"
            "说明:\n"
            "  - pymobiledevice3 sysmon: 需要 Developer Mode\n"
            "  - py-ios-device: 请运行 pip install py-ios-device\n"
            f"返回数据: cpu_app=0.0 (无法获取), cpu_system={self.ESTIMATED_IDLE_CPU}% (估算值)"
        )

        result = {
            'cpu_app': 0.0,
            'cpu_system': self.ESTIMATED_IDLE_CPU
        }
        logger.info(f"CPU 采集结果: {result}")
        return result

    def _get_default_value(self) -> Dict[str, float]:
        """返回默认值（全部失败时）"""
        logger.warning("CPU 采集完全失败，返回零值")
        return {'cpu_app': 0.0, 'cpu_system': 0.0}
