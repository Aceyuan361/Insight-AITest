# -*- coding: utf-8 -*-
"""
iOS CPU 使用率采集器

提供 iOS 设备的 CPU 使用率数据采集功能

注意：pymobiledevice3 7.2.1 没有 sysmon 服务，因此无法获取
真实的进程 CPU 使用率。此实现使用降级方案。

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License
"""

from typing import Dict
from logzero import logger


class CPUCollector:
    """iOS CPU 使用率采集"""

    # iOS 设备典型 CPU 使用率（用于估算）
    ESTIMATED_IDLE_CPU = 5.0  # 系统空闲时 CPU 使用率
    ESTIMATED_ACTIVE_CPU = 15.0  # 系统活跃时 CPU 使用率

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

        由于 pymobiledevice3 7.2.1 没有 sysmon 服务，
        目前返回估算值。

        Returns:
            {'cpu_app': float, 'cpu_system': float}
        """
        try:
            # 尝试主方案（目前未实现，直接跳到降级方案）
            return self._collect_fallback()

        except Exception as e:
            logger.debug(f"CPU 采集失败: {e}")
            return self._get_default_value()

    def _collect_fallback(self) -> Dict[str, float]:
        """
        降级方案：返回估算值

        注意：pymobiledevice3 7.2.1 没有 sysmon 服务，
        无法获取真实的 CPU 使用率数据。

        可能的改进方向：
        1. 升级到有 sysmon 支持的 pymobiledevice3 版本（如果存在）
        2. 使用 instruments 命令行工具（需要 macOS）
        3. 使用 debugserver + shell 命令（需要越狱设备）

        Returns:
            {'cpu_app': float, 'cpu_system': float}
        """
        logger.warning(
            "===== iOS CPU 采集 =====\n"
            "API: pymobiledevice3 (无 sysmon 服务)\n"
            "状态: 使用降级方案（估算值）\n"
            "说明: pymobiledevice3 7.2.1 不提供 sysmon 服务，无法获取真实 CPU 数据\n"
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
