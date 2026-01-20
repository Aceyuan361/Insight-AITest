# -*- coding: utf-8 -*-
"""
iOS APM (Application Performance Monitor) 性能监控主类
提供 iOS 应用的性能数据采集功能

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License

Author: Aceyuan361
"""
from logzero import logger

from insight_eyes.public.ios.cpu_collector import CPUCollector
from insight_eyes.public.ios.memory_collector import MemoryCollector
from insight_eyes.public.ios.fps_collector import FPSCollector
from insight_eyes.public.ios.network_collector import NetworkCollector
from insight_eyes.public.ios.battery_collector import BatteryCollector


class IOSAPM:
    """
    iOS 应用性能监控器

    支持采集的指标:
    - CPU 使用率
    - 内存使用
    - FPS 帧率
    - 网络流量
    - 电池状态
    - GPU 使用率（暂不支持）

    与 AndroidAPM 接口保持一致
    """

    def __init__(self, bundleId, udid, frequency=1.0):
        """
        初始化 iOS APM 监控器

        Args:
            bundleId: 应用 Bundle ID (如 com.apple.mobilesafari)
            udid: iOS 设备唯一标识符
            frequency: 采集频率（秒）
        """
        self.bundleId = bundleId
        self.udid = udid
        self.frequency = frequency

        # iOS 不使用 PID
        self.pid = None

        # 网络采集警告标志（避免重复警告）
        self._network_warning_shown = False

        # 初始化各采集器
        self.cpu_collector = CPUCollector(udid)
        self.memory_collector = MemoryCollector(udid)
        self.fps_collector = FPSCollector(udid)
        self.network_collector = NetworkCollector(udid)
        self.battery_collector = BatteryCollector(udid)

        logger.info(f"初始化 iOS APM: BundleID={bundleId}, UDID={udid}, 采集频率={frequency}秒")

    def start(self):
        """启动监控"""
        logger.info(f"iOS 性能监控已启动: BundleID={self.bundleId}")

    def stop(self):
        """停止监控"""
        logger.info(f"iOS 性能监控已停止: BundleID={self.bundleId}")

    def collectCpu(self):
        """
        采集 CPU 使用率

        Returns:
            dict: {'appCpuRate': float, 'sysCpuRate': float} 或 None
        """
        return self.cpu_collector.collect(self.bundleId)

    def collectMemory(self):
        """
        采集内存使用情况

        Returns:
            dict: {
                'totalPass': float,     # 总内存 (MB)
                'nativePass': float,    # Native 内存 (MB)
                'dalvikPass': float,    # Dalvik 内存 (MB，iOS 上为 0)
            } 或 None
        """
        return self.memory_collector.collect(self.bundleId)

    def collectFps(self):
        """
        采集 FPS 帧率数据

        Returns:
            dict: {
                'fps': int,             # 帧率
                'jank': int,            # 普通卡顿次数
                'bigJank': int,         # 严重卡顿次数
                'ftime_avg': float,     # 平均帧时间 (ms)
                'ftime_max': float,     # 最大帧时间 (ms)
                'ftime_min': float,     # 最小帧时间 (ms)
            } 或 None
        """
        return self.fps_collector.collect(self.bundleId)

    def collectFlow(self):
        """
        采集网络流量

        Returns:
            dict: {'upFlow': float, 'downFlow': float} 单位 KB/s 或 None

        注意:
            iOS 网络流量采集受系统限制，tidevice 暂不支持
        """
        # 首次调用时显示警告
        if not self._network_warning_shown:
            logger.warning(f"iOS 网络流量采集暂不支持 (tidevice 限制)")
            logger.warning(f"如需网络监控，建议使用 Android 设备或使用 Instruments 工具")
            self._network_warning_shown = True

        return self.network_collector.collect(self.bundleId)

    def collectBattery(self):
        """
        采集电池状态

        Returns:
            dict: {
                'level': int,           # 电量百分比
                'temperature': float,   # 温度 (°C)
                'current': float,       # 电流 (mA)
                'voltage': float,       # 电压 (V)
                'power': float,         # 功率 (W)
                'status': str,          # 充电状态
            } 或 None
        """
        return self.battery_collector.collect()

    def collectGpu(self):
        """
        采集 GPU 使用率

        Returns:
            dict: {
                'gpu': int,             # GPU 使用率
                'gpu_freq': int,        # GPU 频率 (MHz)
                'gpu_vendor': str,      # GPU 厂商
                'gpu_model': str,       # GPU 型号
            }
        """
        # iOS 暂不支持 GPU 采集，返回默认值
        return {
            'gpu': 0,
            'gpu_freq': 0,
            'gpu_vendor': 'apple',
            'gpu_model': 'Apple GPU'
        }

    def getAllMetrics(self):
        """
        获取所有性能指标

        Returns:
            dict: 包含所有指标的字典
        """
        return {
            'cpu': self.collectCpu(),
            'memory': self.collectMemory(),
            'fps': self.collectFps(),
            'network': self.collectFlow(),
            'battery': self.collectBattery(),
            'gpu': self.collectGpu()
        }
