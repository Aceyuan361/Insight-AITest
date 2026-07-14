# -*- coding: utf-8 -*-
"""
iOS APM (Application Performance Monitoring) 主类

提供统一的 iOS 性能监控接口，类似 AndroidAPM
"""

import re
from typing import Dict, Any
from logzero import logger

# Bundle ID 验证正则表达式（iOS 应用标识符格式）
# iOS Bundle ID 格式: 如 com.example.app，至少两级
_BUNDLE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)+$")


def _validate_bundle_id(bundle_id: str) -> bool:
    """
    验证 iOS Bundle ID 格式是否有效

    Args:
        bundle_id: 应用 Bundle ID

    Returns:
        bool: Bundle ID 是否有效

    Examples:
        有效: com.example.app, com.company.myapp
        无效: example, com..app, -com.example
    """
    if not bundle_id or not isinstance(bundle_id, str):
        return False

    # 检查长度限制
    if len(bundle_id) > 200:
        logger.warning(f"Bundle ID 过长: {len(bundle_id)} > 200 字符")
        return False

    # 使用正则表达式验证格式
    if not _BUNDLE_ID_PATTERN.match(bundle_id):
        logger.warning(f"Bundle ID 格式无效: {bundle_id}")
        return False

    return True


class IOSAPM:
    """
    iOS 性能监控主类

    提供统一的性能数据采集接口

    支持采集的指标:
    - CPU 使用率
    - 内存使用
    - FPS 帧率
    - 网络流量
    - 电池状态
    - 能耗监控
    """

    def __init__(self, bundle_name: str, device_id: str, frequency: float = 1.0, **kwargs):
        """
        初始化 iOS APM

        Args:
            bundle_name: 应用 Bundle ID (如 com.example.app)
            device_id: iOS 设备 UDID
            frequency: 采集频率（秒），范围 0.1-60
            **kwargs: 其他参数

        Raises:
            ValueError: 当 Bundle ID 格式无效或频率超出范围时
        """
        # 输入验证
        if not _validate_bundle_id(bundle_name):
            raise ValueError(
                f"无效的 Bundle ID 格式: {bundle_name}。"
                f"Bundle ID 应遵循 iOS 命名规范，如 com.example.app"
            )

        if not isinstance(frequency, (int, float)) or frequency <= 0 or frequency > 60:
            raise ValueError(f"无效的采集频率: {frequency}。频率应在 0.1-60 秒之间")

        if not device_id or not isinstance(device_id, str):
            raise ValueError(f"无效的设备 ID: {device_id}")

        self.bundle_name = bundle_name
        self.device_id = device_id
        self.frequency = frequency
        self.kwargs = kwargs

        # 设备适配器（延迟初始化）
        self.adapter = None

        # 采集器（延迟初始化）
        self.cpu_collector = None
        self.memory_collector = None
        self.fps_monitor = None
        self.network_collector = None
        self.battery_collector = None
        self.energy_collector = None

        logger.info(
            f"初始化 iOS APM: bundle={bundle_name}, device={device_id}, 采集频率={frequency}秒"
        )

    def start(self):
        """启动性能监控"""
        logger.info(f"启动 iOS APM: {self.bundle_name} @ {self.device_id}")

        # 导入并创建设备适配器
        from insight_aitest.platform.services.collectors.ios.ios_device_adapter import (
            IOSDeviceAdapter,
        )
        from insight_aitest.platform.services.collectors.ios.sysmon_service import SysmonService
        from insight_aitest.platform.services.collectors.ios.exceptions import ProcessNotFoundError

        # 连接设备
        self.adapter = IOSDeviceAdapter(self.device_id)

        try:
            self.adapter.connect()
        except Exception as e:
            from insight_aitest.platform.services.collectors.ios.exceptions import IOSMonitorError

            if isinstance(e, IOSMonitorError):
                # 重新抛出 iOS 专用异常
                raise
            else:
                # 包装为通用连接错误
                raise ConnectionError(f"无法连接 iOS 设备: {self.device_id}, 原因: {e}")

        # ===== 启动前验证进程存在性 =====
        logger.info("正在检查目标进程...")
        sysmon_service = SysmonService.get_instance(self.device_id)

        if not sysmon_service.connect():
            raise ConnectionError(f"无法连接到设备: {self.device_id}")

        target_process = sysmon_service.get_process_by_bundle_id(self.bundle_name)

        if not target_process:
            raise ProcessNotFoundError(bundle_id=self.bundle_name, device_id=self.device_id)

        logger.info(
            f"✓ 找到目标进程: PID={target_process.get('pid')}, Name={target_process.get('name')}"
        )

        # ===== 启动流式监听服务 =====
        from insight_aitest.platform.services.collectors.ios.sysmon_stream_service import (
            SysmonStreamService,
        )
        from insight_aitest.platform.services.collectors.ios.metrics_throttle import MetricsThrottle

        # 创建频率控制层
        self._throttle = MetricsThrottle(target_frequency=self.frequency)

        # 创建并启动监听服务
        self._stream_service = SysmonStreamService.get_instance(self.device_id)

        # 设置频率控制层
        self._stream_service.set_throttle(self._throttle)

        # 启动监听
        self._stream_service.start_monitoring()

        logger.info("✓ 流式监听服务已启动")

        # 预热等待：让第一批包含 CPU 的数据到达
        # iOS sysmontap 第一批数据通常没有 CPU 值（cpuUsage=None）
        # 需要等待第二批数据才有有效的 CPU 数据
        logger.debug("等待流式监听预热（让第一批 CPU 数据到达）...")
        import time

        time.sleep(1.5)  # 等待 1.5 秒，确保至少有一批包含 CPU 的数据
        logger.debug("流式监听预热完成")

        # 初始化各采集器（添加异常处理）
        try:
            from insight_aitest.platform.services.collectors.ios.cpu_collector import CPUCollector
            from insight_aitest.platform.services.collectors.ios.memory_collector import (
                MemoryCollector,
            )
            from insight_aitest.platform.services.collectors.ios.battery_collector import (
                BatteryCollector,
            )
            from insight_aitest.platform.services.collectors.ios.energy_collector import (
                EnergyCollector,
            )
            from insight_aitest.platform.services.collectors.ios.network_collector import (
                NetworkCollector,
            )

            # 传递 Throttle 给 CPU 和 Memory 采集器
            self.cpu_collector = CPUCollector(
                self.adapter, self.bundle_name, throttle=self._throttle
            )
            self.memory_collector = MemoryCollector(
                self.adapter, self.bundle_name, throttle=self._throttle
            )
            self.battery_collector = BatteryCollector(self.adapter)
            self.energy_collector = EnergyCollector(self.adapter, self.bundle_name)
            self.network_collector = NetworkCollector(self.adapter, self.bundle_name)

            # 启动网络采集器
            self.network_collector.start()

            logger.info("iOS APM 启动成功")
        except Exception as e:
            logger.error(f"初始化采集器失败: {type(e).__name__}: {e}")
            # 确保在失败时清理资源
            self.cpu_collector = None
            self.memory_collector = None
            self.battery_collector = None
            self.energy_collector = None
            raise

    def stop(self):
        """停止性能监控"""
        # 停止网络采集器
        if self.network_collector:
            self.network_collector.stop()
            logger.info("网络采集器已停止")

        # 停止流式监听服务
        if hasattr(self, "_stream_service") and self._stream_service:
            self._stream_service.stop_monitoring()
            logger.info("流式监听服务已停止")

        if self.adapter:
            self.adapter.disconnect()
            self.adapter = None

        # 清理采集器
        self.cpu_collector = None
        self.memory_collector = None
        self.fps_monitor = None
        self.network_collector = None
        self.battery_collector = None
        self.energy_collector = None

        logger.info("iOS APM 已停止")

    def collectCpu(self) -> Dict[str, Any]:
        """
        采集 CPU 使用率

        Returns:
            {'cpu_app': float, 'cpu_system': float}
        """
        if self.cpu_collector:
            return self.cpu_collector.collect()

        logger.warning("iOS CPU 采集器未初始化，返回默认值")
        return {"cpu_app": 0.0, "cpu_system": 0.0}

    def collectMemory(self) -> Dict[str, Any]:
        """
        采集内存使用情况

        Returns:
            {'used_mb': float, 'total_mb': float}
        """
        if self.memory_collector:
            return self.memory_collector.collect()

        logger.warning("iOS 内存采集器未初始化，返回默认值")
        return {"used_mb": 0.0, "total_mb": 0.0}

    def collectFps(self) -> Dict[str, Any]:
        """
        采集帧率信息

        Returns:
            {'fps': int, 'jank': int}

        注意：iOS 不向第三方暴露真实应用 FPS（私有 API，越狱外不可用），
        此处返回占位值 60，不代表真实帧率。前端/文档据此标注，勿当真实数据。
        """
        logger.debug("iOS FPS 返回占位值 60（iOS 不暴露真实应用 FPS）")
        return {"fps": 60, "jank": 0}

    def collectFlow(self) -> Dict[str, Any]:
        """
        采集网络流量

        基于 pcapd 服务实现系统级网络流量监控。

        Returns:
            {'upFlow': float, 'downFlow': float} 单位 KB/s
        """
        logger.debug(f"[iOS APM] collectFlow() 调用, network_collector={self.network_collector}")
        if self.network_collector:
            result = self.network_collector.collect()
            logger.debug(f"[iOS APM] collectFlow() 返回: {result}")
            return result

        logger.debug("iOS 网络采集器未初始化，返回默认值")
        return {"upFlow": 0.0, "downFlow": 0.0}

    def collectBattery(self) -> Dict[str, Any]:
        """
        采集电池状态

        Returns:
            {'level': int, 'temperature': float}
        """
        if self.battery_collector:
            return self.battery_collector.collect()

        logger.warning("iOS 电池采集器未初始化，返回默认值")
        return {"level": 100, "temperature": 25.0}

    def collectEnergy(self) -> Dict[str, Any]:
        """
        采集能耗数据

        Returns:
            {
                'energy': float,  # 总能耗 (mW)
                'cpu_energy': float,  # CPU 能耗 (mW)
                'gpu_energy': float,  # GPU 能耗 (mW)
                'network_energy': float  # 网络能耗 (mW)
            }
        """
        if self.energy_collector:
            return self.energy_collector.collect()

        logger.warning("iOS 能耗采集器未初始化，返回默认值")
        return {"energy": 0.0, "cpu_energy": 0.0, "gpu_energy": 0.0, "network_energy": 0.0}

    def getAllMetrics(self) -> Dict[str, Any]:
        """
        获取所有性能指标

        Returns:
            dict: 包含所有指标的字典
        """
        return {
            "cpu": self.collectCpu(),
            "memory": self.collectMemory(),
            "fps": self.collectFps(),
            "network": self.collectFlow(),
            "battery": self.collectBattery(),
            "energy": self.collectEnergy(),
        }
