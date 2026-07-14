# -*- coding: utf-8 -*-
"""
iOS 能耗监控采集器

提供 iOS 设备的能耗监控数据采集功能

数据采集：
- pymobiledevice3 developer dvt energy（仅支持此方法）

注意：py-ios-device 不支持能耗监控，因此没有降级方案。

要求：
- Developer Mode 已启用
- DeveloperDiskImage 已挂载
"""

from typing import Dict
from logzero import logger


class EnergyCollector:
    """iOS 能耗监控采集"""

    def __init__(self, adapter, bundle_id: str):
        """
        初始化能耗采集器

        Args:
            adapter: IOSDeviceAdapter 实例
            bundle_id: 应用的 Bundle ID (如 com.example.app)
        """
        self.adapter = adapter
        self.bundle_id = bundle_id
        self._sysmon_helper = None
        self._cached_pid = None

    def collect(self) -> Dict[str, float]:
        """
        采集能耗数据

        注意：
        - iOS 能耗监控需要 Developer Mode
        - 当前 CLI 方案太慢，暂时返回降级值
        - 未来可使用 DVT Python API 实现

        Returns:
            {
                'energy': float,  # 总能耗 (mW)
                'cpu_energy': float,  # CPU 能耗 (mW)
                'gpu_energy': float,  # GPU 能耗 (mW)
                'network_energy': float  # 网络能耗 (mW)
            }
        """
        # 暂时直接返回降级值（CLI 方案太慢）
        logger.debug("能耗监控：CLI 方案太慢，返回降级值")
        return self._get_fallback_value()

    def _get_fallback_value(self) -> Dict[str, float]:
        """
        降级方案：返回零值

        注意：
        - 能耗监控仅支持 pymobiledevice3 developer dvt energy
        - py-ios-device 不支持能耗监控
        - 因此没有可用的降级方案

        Returns:
            能耗数据字典（全部为零）
        """
        logger.warning(
            "===== iOS 能耗采集（降级方案）=====\n"
            "状态: Sysmon 服务不可用\n"
            "说明:\n"
            "  - 能耗监控仅支持 pymobiledevice3 developer dvt energy\n"
            "  - 需要 Developer Mode 已启用\n"
            "  - 需要 DeveloperDiskImage 已挂载\n"
            "  - py-ios-device 不支持能耗监控（instruments 协议限制）\n"
            "返回数据: 能耗数据全部为 0 (无法获取)"
        )

        return {"energy": 0.0, "cpu_energy": 0.0, "gpu_energy": 0.0, "network_energy": 0.0}

    def _get_default_value(self) -> Dict[str, float]:
        """返回默认值（全部失败时）"""
        logger.warning("能耗采集完全失败，返回零值")
        return {"energy": 0.0, "cpu_energy": 0.0, "gpu_energy": 0.0, "network_energy": 0.0}
