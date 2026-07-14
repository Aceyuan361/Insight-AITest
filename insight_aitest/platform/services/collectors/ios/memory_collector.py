# -*- coding: utf-8 -*-
"""
iOS 内存使用情况采集器

提供 iOS 设备的内存使用数据采集功能

数据采集方式：
- pymobiledevice3 Python API - DVT 协议（流式监听）
- pymobiledevice3 Python API - DVT 协议（按需采集）

注意：
- 需要 Developer Mode 已启用
- 需要 DeveloperDiskImage 已挂载
"""

from typing import Dict, Optional
from logzero import logger


class MemoryCollector:
    """iOS 内存使用采集"""

    # iOS 设备典型内存配置（MB）
    DEVICE_MEMORY_MAP = {
        "iPhone14,": 6 * 1024,  # 6GB
        "iPhone13,": 4 * 1024,  # 4GB
        "iPhone12,": 4 * 1024,  # 4GB
        "iPhone11,": 4 * 1024,  # 4GB
        "default": 4 * 1024,  # 4GB
    }

    def __init__(self, adapter, bundle_id: str, throttle=None):
        """
        初始化内存采集器

        Args:
            adapter: IOSDeviceAdapter 实例
            bundle_id: 应用的 Bundle ID (如 com.example.app)
            throttle: MetricsThrottle 实例（可选，如果提供则使用流式监听）
        """
        self.adapter = adapter
        self.bundle_id = bundle_id
        self._throttle = throttle  # 频率控制层
        self._sysmon_service = None
        self._total_memory_mb = None
        self._last_memory_data = None  # 上次成功采集的内存数据（用于回退）
        self._last_valid_memory: Optional[float] = None  # 上一个有效的内存值

    def collect(self) -> Dict[str, float]:
        """
        采集内存使用情况

        数据采集方式：
        1. MetricsThrottle（流式监听，如果可用）- 首选
        2. pymobiledevice3 Python API - DVT 协议（按需采集）

        Returns:
            {'used_mb': float, 'total_mb': float, 'percentage': float}
        """
        # 获取设备总内存（用于计算百分比）
        if self._total_memory_mb is None:
            self._total_memory_mb = self._get_device_total_memory()

        # 方案 1: 使用 Throttle 层（流式监听，如果可用）
        if self._throttle:
            try:
                metrics = self._throttle.get_metrics(self.bundle_id)

                logger.debug(
                    f"===== iOS 内存采集成功 (流式监听) =====\n"
                    f"Bundle ID: {self.bundle_id}\n"
                    f"内存: {metrics['used_mb']}MB / {metrics['total_mb']}MB"
                )

                memory_data = {
                    "used_mb": metrics["used_mb"],
                    "total_mb": metrics["total_mb"],
                    "percentage": round((metrics["used_mb"] / metrics["total_mb"] * 100), 2),
                }

                self._last_memory_data = memory_data
                return memory_data

            except Exception as e:
                logger.debug(f"流式监听采集失败: {e}，尝试降级方案")

        # 方案 2: 尝试 pymobiledevice3 Python API（按需采集）
        try:
            from .sysmon_service import SysmonService

            if self._sysmon_service is None:
                self._sysmon_service = SysmonService.get_instance(self.adapter.device_id)

            if self._sysmon_service.is_available() or self._sysmon_service.connect():
                logger.debug(
                    f"[MemoryCollector] 调用 get_process_by_bundle_id('{self.bundle_id}')..."
                )
                process = self._sysmon_service.get_process_by_bundle_id(self.bundle_id)

                if process:
                    logger.debug("[MemoryCollector] 找到进程，解析内存数据...")
                    raw_memory_data = self._sysmon_service.parse_memory_usage(process)
                    raw_used_mb = raw_memory_data["used_mb"]

                    # 应用数据过滤算法
                    filtered_used_mb = self._filter_memory_data(raw_used_mb)

                    # 更新 total_mb 为实际设备内存
                    memory_data = {
                        "used_mb": filtered_used_mb,
                        "total_mb": float(self._total_memory_mb),
                        "percentage": round((filtered_used_mb / self._total_memory_mb * 100), 2),
                    }

                    logger.info(
                        f"===== iOS 内存采集成功 (DVT API) =====\n"
                        f"API: pymobiledevice3 Python API (DVT 协议)\n"
                        f"Bundle ID: {self.bundle_id}\n"
                        f"PID: {process.get('pid')}\n"
                        f"原始内存: {raw_used_mb}MB\n"
                        f"过滤后内存: {filtered_used_mb:.2f}MB / {memory_data['total_mb']}MB ({memory_data['percentage']}%)"
                    )
                    # 保存成功采集的数据用于回退
                    self._last_memory_data = memory_data
                    return memory_data
                else:
                    logger.warning(f"[MemoryCollector] 未找到进程 '{self.bundle_id}'")
                    # 尝试使用上次采集的值回退
                    if self._last_memory_data:
                        logger.info(
                            f"[MemoryCollector] 使用上次采集的值回退: {self._last_memory_data['used_mb']}MB"
                        )
                        return self._last_memory_data
                    else:
                        logger.warning("[MemoryCollector] 无历史数据可回退")

        except ImportError:
            logger.debug("SysmonService 不可用，尝试降级方案")
        except Exception as e:
            logger.warning(f"DVT API 内存采集失败: {type(e).__name__}: {e}，尝试降级方案")

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
            "  - pymobiledevice3 Python API: DVT 协议连接失败\n"
            "  - 建议：检查设备连接、Developer Mode 状态\n"
            f"返回数据: used_mb=0.0 (无法获取), total_mb={self._total_memory_mb}MB (设备总内存)"
        )

        return {"used_mb": 0.0, "total_mb": float(self._total_memory_mb), "percentage": 0.0}

    def _get_device_total_memory(self) -> int:
        """
        获取设备总内存（MB）

        尝试通过 mobilegestalt 获取设备型号，然后查表获取内存大小。
        通过 IOSConnectionManager 在事件循环中执行 async mobilegestalt()。

        Returns:
            int: 总内存（MB）
        """
        try:
            from pymobiledevice3.services.diagnostics import DiagnosticsService
            from .connection_manager import IOSConnectionManager

            logger.info("===== iOS 设备内存查询 =====")
            logger.info("API: pymobiledevice3 DiagnosticsService.mobilegestalt()")
            logger.info("参数: ['HardwarePlatform']")

            device_id = getattr(self.adapter, "device_id", None)
            if not device_id:
                logger.warning("无 device_id，使用默认内存值")
                return self.DEVICE_MEMORY_MAP["default"]

            mgr = IOSConnectionManager.get_instance(device_id)
            if not mgr.is_connected:
                mgr.connect()

            lockdown = mgr.get_async_lockdown()
            diagnostics = DiagnosticsService(lockdown)

            # 在事件循环中执行 async mobilegestalt()
            info = mgr.run_async(diagnostics.mobilegestalt(["HardwarePlatform"]), timeout=10)

            logger.info(f"API 返回数据: {info}")

            if info and "HardwarePlatform" in info:
                model = info["HardwarePlatform"]
                logger.info(f"设备型号: {model}")

                # 查表获取内存
                for key, memory in self.DEVICE_MEMORY_MAP.items():
                    if model.startswith(key.rstrip(",")):
                        logger.info(f"匹配到内存配置: {memory}MB (型号: {model})")
                        return memory

            # 未匹配到，使用默认值
            default_memory = self.DEVICE_MEMORY_MAP["default"]
            logger.warning(
                f"未匹配到设备型号，使用默认内存值: {default_memory}MB\n"
                f"请确认设备型号并更新 DEVICE_MEMORY_MAP"
            )
            return default_memory

        except Exception as e:
            logger.error(f"获取设备内存失败: {e}，使用默认值")
            return self.DEVICE_MEMORY_MAP["default"]

    def _filter_memory_data(self, raw_used_mb: float) -> float:
        """
        过滤无效内存数据（最小化方案）

        pymobiledevice3 的 sysmon 已经按自己的频率采样，
        我们只过滤明显无效的数据：
        1. 负值
        2. 超出设备总内存

        不做平滑，直接返回原始值。

        Args:
            raw_used_mb: 原始内存使用量（MB）

        Returns:
            过滤后的内存使用量（MB）
        """
        # 检查是否超出合理范围
        if raw_used_mb < 0:
            logger.debug(f"[内存过滤] 值为负数: {raw_used_mb}MB")
            if self._last_valid_memory is not None:
                return self._last_valid_memory
            else:
                return 0.0

        # 检查是否超过设备总内存
        if self._total_memory_mb and raw_used_mb > self._total_memory_mb:
            logger.debug(f"[内存过滤] 值超过总内存: {raw_used_mb}MB > {self._total_memory_mb}MB")
            if self._last_valid_memory is not None:
                return self._last_valid_memory
            else:
                return self._total_memory_mb

        # 直接返回原始值（不做任何过滤或平滑）
        self._last_valid_memory = raw_used_mb
        return raw_used_mb

    def _get_default_value(self) -> Dict[str, float]:
        """返回默认值（全部失败时）"""
        logger.warning("内存采集完全失败，返回零值")
        return {"used_mb": 0.0, "total_mb": 0.0, "percentage": 0.0}
