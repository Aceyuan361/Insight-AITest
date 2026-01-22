# -*- coding: utf-8 -*-
"""
iOS CPU 使用率采集器

提供 iOS 设备的 CPU 使用率数据采集功能

使用 pymobiledevice3 developer dvt sysmon 获取真实进程 CPU 数据。

要求：
- Developer Mode 已启用
- DeveloperDiskImage 已挂载

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License
"""

from typing import Dict
from logzero import logger


class CPUCollector:
    """iOS CPU 使用率采集"""

    # iOS 设备典型 CPU 使用率（用于降级方案）
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

    def collect(self) -> Dict[str, float]:
        """
        采集 CPU 使用率

        通过 pymobiledevice3 developer dvt sysmon 获取真实数据。

        Returns:
            {'cpu_app': float, 'cpu_system': float}
        """
        try:
            from .sysmon_helper import SysmonHelper

            # 延迟初始化 SysmonHelper
            if self._sysmon_helper is None:
                self._sysmon_helper = SysmonHelper()

            if not self._sysmon_helper.is_available():
                logger.warning("Sysmon 服务不可用，使用降级方案")
                return self._collect_fallback()

            # 通过 Bundle ID 查找进程
            process = self._sysmon_helper.get_process_by_bundle_id(self.bundle_id)

            if process:
                cpu_usage = self._sysmon_helper.parse_cpu_usage(process)
                logger.info(
                    f"===== iOS CPU 采集成功 =====\n"
                    f"API: pymobiledevice3 developer dvt sysmon process single\n"
                    f"Bundle ID: {self.bundle_id}\n"
                    f"PID: {process.get('pid')}\n"
                    f"CPU 使用率: {cpu_usage}%"
                )
                return {
                    'cpu_app': cpu_usage,
                    'cpu_system': 0.0  # iOS 不区分系统 CPU
                }
            else:
                logger.warning(f"未找到进程: {self.bundle_id}，使用降级方案")
                return self._collect_fallback()

        except ImportError:
            logger.warning("无法导入 SysmonHelper，使用降级方案")
            return self._collect_fallback()

        except Exception as e:
            logger.debug(f"CPU 采集失败: {e}")
            return self._collect_fallback()

    def _collect_fallback(self) -> Dict[str, float]:
        """
        降级方案：返回估算值

        当 Sysmon 服务不可用时使用。

        Returns:
            {'cpu_app': float, 'cpu_system': float}
        """
        logger.warning(
            "===== iOS CPU 采集（降级方案）=====\n"
            "状态: Sysmon 服务不可用\n"
            "说明: 请确保 Developer Mode 已启用且 DeveloperDiskImage 已挂载\n"
            f"返回数据: cpu_app=0.0 (无法获取), cpu_system={self.ESTIMATED_IDLE_CPU}% (估算值)"
        )

        # 返回估算值
        result = {
            'cpu_app': 0.0,  # 应用 CPU 无法获取
            'cpu_system': self.ESTIMATED_IDLE_CPU  # 系统估算值
        }
        logger.info(f"CPU 采集结果: {result}")
        return result

    def _get_default_value(self) -> Dict[str, float]:
        """返回默认值（全部失败时）"""
        logger.warning("CPU 采集完全失败，返回零值")
        return {'cpu_app': 0.0, 'cpu_system': 0.0}
