# -*- coding: utf-8 -*-
"""
iOS CPU 使用率采集器

提供 iOS 设备的 CPU 使用率数据采集功能

数据采集方式：
- pymobiledevice3 Python API - DVT 协议（流式监听）
- pymobiledevice3 Python API - DVT 协议（按需采集）

注意：
- 需要 Developer Mode 已启用
- 需要 DeveloperDiskImage 已挂载
"""

from typing import Dict, Optional
from logzero import logger


class CPUCollector:
    """iOS CPU 使用率采集"""

    # iOS 设备典型 CPU 使用率（用于最终降级）
    ESTIMATED_IDLE_CPU = 5.0  # 系统空闲时 CPU 使用率
    ESTIMATED_ACTIVE_CPU = 15.0  # 系统活跃时 CPU 使用率

    def __init__(self, adapter, bundle_id: str, throttle=None):
        """
        初始化 CPU 采集器

        Args:
            adapter: IOSDeviceAdapter 实例
            bundle_id: 应用的 Bundle ID (如 com.example.app)
            throttle: MetricsThrottle 实例（可选，如果提供则使用流式监听）
        """
        self.adapter = adapter
        self.bundle_id = bundle_id
        self._throttle = throttle  # 频率控制层
        self._sysmon_service = None
        self._last_cpu_data = None  # 上次成功采集的 CPU 数据（用于回退）
        self._last_valid_cpu: Optional[float] = None  # 上一个有效的 CPU 值

    def collect(self) -> Dict[str, float]:
        """
        采集 CPU 使用率

        数据采集方式：
        1. MetricsThrottle（流式监听，如果可用）- 首选
        2. pymobiledevice3 Python API - DVT 协议（按需采集）

        Returns:
            {'cpu_app': float, 'cpu_system': float}
        """
        # 方案 1: 使用 Throttle 层（流式监听，如果可用）
        if self._throttle:
            try:
                metrics = self._throttle.get_metrics(self.bundle_id)

                logger.debug(
                    f"===== iOS CPU 采集成功 (流式监听) =====\n"
                    f"Bundle ID: {self.bundle_id}\n"
                    f"CPU: {metrics['cpu_app']}%"
                )

                cpu_data = {"cpu_app": metrics["cpu_app"], "cpu_system": metrics["cpu_system"]}
                self._last_cpu_data = cpu_data
                return cpu_data

            except Exception as e:
                logger.debug(f"流式监听采集失败: {e}，尝试按需采集")

        # 方案 2: 尝试 pymobiledevice3 Python API（按需采集）
        try:
            from .sysmon_service import SysmonService

            if self._sysmon_service is None:
                self._sysmon_service = SysmonService.get_instance(self.adapter.device_id)

            if self._sysmon_service.is_available() or self._sysmon_service.connect():
                process = self._sysmon_service.get_process_by_bundle_id(self.bundle_id)

                if process:
                    raw_cpu = self._sysmon_service.parse_cpu_usage(process)

                    # 应用数据过滤算法
                    filtered_cpu = self._filter_cpu_data(raw_cpu)

                    logger.info(
                        f"===== iOS CPU 采集成功 (DVT API) =====\n"
                        f"API: pymobiledevice3 Python API (DVT 协议)\n"
                        f"Bundle ID: {self.bundle_id}\n"
                        f"PID: {process.get('pid')}\n"
                        f"原始 CPU: {raw_cpu}%\n"
                        f"过滤后 CPU: {filtered_cpu}%"
                    )
                    cpu_data = {"cpu_app": filtered_cpu, "cpu_system": 0.0}  # iOS 不区分系统 CPU
                    # 保存成功采集的数据用于回退
                    self._last_cpu_data = cpu_data
                    return cpu_data

        except ImportError:
            logger.debug("SysmonService 不可用，尝试降级方案")
        except Exception as e:
            logger.debug(f"DVT API 采集失败: {e}，尝试降级方案")

        # 方案 3: 最终降级方案（估算值）
        return self._collect_final_fallback()

    def _filter_cpu_data(self, raw_cpu: float) -> float:
        """
        过滤无效 CPU 数据（最小化方案）

        pymobiledevice3 的 sysmon 已经按自己的频率采样，
        我们只过滤明显无效的数据：
        1. None 值（采集失败）
        2. 超出物理范围（< 0 或 > 100）

        不做平滑，不过滤 0 值（因为应用可能真的空闲）

        Args:
            raw_cpu: 原始 CPU 使用率

        Returns:
            过滤后的 CPU 使用率
        """
        # 检查是否超出物理范围
        if raw_cpu < 0.0 or raw_cpu > 100.0:
            logger.debug(f"[CPU 过滤] 值超出物理范围: {raw_cpu}%")
            if self._last_valid_cpu is not None:
                return self._last_valid_cpu
            else:
                return 0.0

        # 直接返回原始值（不做任何过滤或平滑）
        self._last_valid_cpu = raw_cpu
        return raw_cpu

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
            "  - pymobiledevice3 Python API: DVT 协议连接失败\n"
            "  - 建议：检查设备连接、Developer Mode 状态\n"
            f"返回数据: cpu_app=0.0 (无法获取), cpu_system={self.ESTIMATED_IDLE_CPU}% (估算值)"
        )

        result = {"cpu_app": 0.0, "cpu_system": self.ESTIMATED_IDLE_CPU}
        logger.info(f"CPU 采集结果: {result}")
        return result

    def _get_default_value(self) -> Dict[str, float]:
        """返回默认值（全部失败时）"""
        logger.warning("CPU 采集完全失败，返回零值")
        return {"cpu_app": 0.0, "cpu_system": 0.0}
