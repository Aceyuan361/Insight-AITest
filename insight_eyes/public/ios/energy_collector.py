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

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License
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

        通过 pymobiledevice3 developer dvt energy 获取真实数据。

        注意：此功能需要 Developer Mode，且无降级方案。

        Returns:
            {
                'energy': float,  # 总能耗 (mW)
                'cpu_energy': float,  # CPU 能耗 (mW)
                'gpu_energy': float,  # GPU 能耗 (mW)
                'network_energy': float  # 网络能耗 (mW)
            }
        """
        try:
            from .sysmon_helper import SysmonHelper

            # 延迟初始化 SysmonHelper
            if self._sysmon_helper is None:
                self._sysmon_helper = SysmonHelper()

            if not self._sysmon_helper.is_available():
                logger.warning("Sysmon 服务不可用，能耗监控需要 Developer Mode")
                return self._get_fallback_value()

            # 先获取进程信息（以得到 PID）
            process = self._sysmon_helper.get_process_by_bundle_id(self.bundle_id)

            if not process:
                logger.warning(f"未找到进程: {self.bundle_id}，无法获取能耗数据")
                return self._get_fallback_value()

            pid = process.get('pid')
            self._cached_pid = pid

            # 获取能耗统计
            energy_stats = self._sysmon_helper.get_energy_stats(pid)

            if energy_stats:
                # 解析能耗数据
                result = {
                    'energy': energy_stats.get('energy.cost', 0.0),
                    'cpu_energy': energy_stats.get('energy.cpu.cost', 0.0),
                    'gpu_energy': energy_stats.get('energy.gpu.cost', 0.0),
                    'network_energy': energy_stats.get('energy.networking.cost', 0.0)
                }

                logger.info(
                    f"===== iOS 能耗采集成功 =====\n"
                    f"API: pymobiledevice3 developer dvt energy {pid}\n"
                    f"Bundle ID: {self.bundle_id}\n"
                    f"PID: {pid}\n"
                    f"总能耗: {result['energy']:.2f} mW\n"
                    f"  - CPU: {result['cpu_energy']:.2f} mW\n"
                    f"  - GPU: {result['gpu_energy']:.2f} mW\n"
                    f"  - 网络: {result['network_energy']:.2f} mW"
                )
                return result
            else:
                logger.warning(f"无法获取能耗数据: PID {pid}")
                return self._get_fallback_value()

        except ImportError:
            logger.warning("无法导入 SysmonHelper，能耗监控需要 Developer Mode")
            return self._get_fallback_value()

        except Exception as e:
            logger.debug(f"能耗采集失败: {e}")
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

        return {
            'energy': 0.0,
            'cpu_energy': 0.0,
            'gpu_energy': 0.0,
            'network_energy': 0.0
        }

    def _get_default_value(self) -> Dict[str, float]:
        """返回默认值（全部失败时）"""
        logger.warning("能耗采集完全失败，返回零值")
        return {
            'energy': 0.0,
            'cpu_energy': 0.0,
            'gpu_energy': 0.0,
            'network_energy': 0.0
        }
