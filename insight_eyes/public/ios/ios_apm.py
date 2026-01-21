# -*- coding: utf-8 -*-
"""
iOS APM (Application Performance Monitor) 性能监控主类
提供 iOS 应用的性能数据采集功能

架构说明：
- 使用 py-ios-device 架构（PyIOSConnection + SysMontapCollector + GraphicsCollector + EnergyCollector）
- 弃用 tidevice 采集器（标记为 @deprecated）
- 使用 IOSDataNormalizer 统一数据格式

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License

Author: Aceyuan361
"""
from logzero import logger
from typing import Optional, Dict, Any


class IOSAPM:
    """
    iOS 应用性能监控器

    支持采集的指标:
    - CPU 使用率
    - 内存使用
    - FPS 帧率
    - 网络流量
    - 电池状态
    - GPU 使用率（通过 py-ios-device）

    架构：
    - 使用 py-ios-device 架构（PyIOSConnection + 专用采集器）
    - 弃用 tidevice 采集器

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

        # py-ios-device 连接和采集器（延迟初始化）
        self._connection = None
        self._sysmontap_collector = None  # CPU/Memory/Network 采集器
        self._graphics_collector = None   # FPS/GPU 采集器
        self._energy_collector = None     # Battery 采集器

        # 网络采集警告标志（避免重复警告）
        self._network_warning_shown = False

        logger.info(f"初始化 iOS APM (py-ios-device 架构): BundleID={bundleId}, UDID={udid}, 采集频率={frequency}秒")

    def _ensure_connection(self) -> bool:
        """
        确保连接已建立

        Returns:
            bool: 连接是否可用
        """
        if self._connection is None:
            try:
                from insight_eyes.public.ios.pyios_connect import PyIOSConnection
                self._connection = PyIOSConnection(self.udid)
                if not self._connection.connect():
                    logger.error("[IOSAPM] 连接失败")
                    return False
            except Exception as e:
                logger.error(f"[IOSAPM] 连接异常: {e}")
                return False

        return self._connection.is_connected()

    def _get_sysmontap_collector(self):
        """获取或创建 SysMontap 采集器"""
        if not self._ensure_connection():
            return None

        if self._sysmontap_collector is None:
            try:
                from insight_eyes.public.ios.pyios_collectors.sysmontap import SysMontapCollector
                self._sysmontap_collector = SysMontapCollector(
                    self._connection.rpc,
                    self.bundleId
                )
                self._sysmontap_collector.configure()
                self._sysmontap_collector.start()
                logger.debug("[IOSAPM] SysMontap 采集器已启动")
            except Exception as e:
                logger.error(f"[IOSAPM] 创建 SysMontap 采集器失败: {e}")
                return None

        return self._sysmontap_collector

    def _get_graphics_collector(self):
        """获取或创建 Graphics 采集器"""
        if not self._ensure_connection():
            return None

        if self._graphics_collector is None:
            try:
                from insight_eyes.public.ios.pyios_collectors.graphics import GraphicsCollector
                self._graphics_collector = GraphicsCollector(
                    self._connection.rpc,
                    self.bundleId
                )
                self._graphics_collector.configure()
                self._graphics_collector.start()
                logger.debug("[IOSAPM] Graphics 采集器已启动")
            except Exception as e:
                logger.error(f"[IOSAPM] 创建 Graphics 采集器失败: {e}")
                return None

        return self._graphics_collector

    def _get_energy_collector(self):
        """获取或创建 Energy 采集器"""
        if not self._ensure_connection():
            return None

        if self._energy_collector is None:
            try:
                from insight_eyes.public.ios.pyios_collectors.energy import EnergyCollector
                self._energy_collector = EnergyCollector(
                    self._connection.rpc,
                    self.bundleId
                )
                self._energy_collector.configure()
                self._energy_collector.start()
                logger.debug("[IOSAPM] Energy 采集器已启动")
            except Exception as e:
                logger.error(f"[IOSAPM] 创建 Energy 采集器失败: {e}")
                return None

        return self._energy_collector

    def start(self):
        """启动监控"""
        if not self._ensure_connection():
            logger.warning("[IOSAPM] 启动失败：连接不可用")
            return
        logger.info(f"iOS 性能监控已启动: BundleID={self.bundleId}")

    def stop(self):
        """停止监控"""
        # 停止所有采集器
        if self._sysmontap_collector:
            try:
                self._sysmontap_collector.stop()
            except Exception as e:
                logger.warning(f"[IOSAPM] 停止 SysMontap 采集器失败: {e}")

        if self._graphics_collector:
            try:
                self._graphics_collector.stop()
            except Exception as e:
                logger.warning(f"[IOSAPM] 停止 Graphics 采集器失败: {e}")

        if self._energy_collector:
            try:
                self._energy_collector.stop()
            except Exception as e:
                logger.warning(f"[IOSAPM] 停止 Energy 采集器失败: {e}")

        # 断开连接
        if self._connection:
            try:
                self._connection.disconnect()
            except Exception as e:
                logger.warning(f"[IOSAPM] 断开连接失败: {e}")

        logger.info(f"iOS 性能监控已停止: BundleID={self.bundleId}")

    def collectCpu(self):
        """
        采集 CPU 使用率

        Returns:
            dict: {'appCpuRate': float, 'sysCpuRate': float} 或 None
        """
        try:
            collector = self._get_sysmontap_collector()
            if not collector:
                return None

            raw_data = collector.collect_cpu()

            # 使用 IOSDataNormalizer 规范化数据
            from insight_eyes.public.ios.data_normalizer import IOSDataNormalizer
            return IOSDataNormalizer.normalize_cpu(raw_data)

        except Exception as e:
            logger.warning(f"[IOSAPM] py-ios-device CPU 采集失败: {e}，尝试降级到 tidevice")
            return self._collect_cpu_tidevice()

    def _collect_cpu_tidevice(self):
        """
        使用 tidevice 采集 CPU（降级方案）

        Returns:
            dict: {'appCpuRate': float, 'sysCpuRate': float} 或 None
        """
        try:
            from insight_eyes.public.ios.cpu_collector import CPUCollector
            collector = CPUCollector(self.udid)
            return collector.collect()
        except Exception as e:
            logger.error(f"[IOSAPM] tidevice CPU 采集失败: {e}")
            return None

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
        try:
            collector = self._get_sysmontap_collector()
            if not collector:
                return None

            raw_data = collector.collect_memory()

            # 使用 IOSDataNormalizer 规范化数据
            from insight_eyes.public.ios.data_normalizer import IOSDataNormalizer
            return IOSDataNormalizer.normalize_memory(raw_data)

        except Exception as e:
            logger.warning(f"[IOSAPM] py-ios-device Memory 采集失败: {e}，尝试降级到 tidevice")
            return self._collect_memory_tidevice()

    def _collect_memory_tidevice(self):
        """使用 tidevice 采集 Memory（降级方案）"""
        try:
            from insight_eyes.public.ios.memory_collector import MemoryCollector
            collector = MemoryCollector(self.udid, self.bundleId)
            return collector.collect()
        except Exception as e:
            logger.error(f"[IOSAPM] tidevice Memory 采集失败: {e}")
            return None

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
        try:
            collector = self._get_graphics_collector()
            if not collector:
                return None

            raw_data = collector.collect_fps()

            # 使用 IOSDataNormalizer 规范化数据
            from insight_eyes.public.ios.data_normalizer import IOSDataNormalizer
            return IOSDataNormalizer.normalize_fps(raw_data)

        except Exception as e:
            logger.warning(f"[IOSAPM] py-ios-device FPS 采集失败: {e}，尝试降级到 tidevice")
            return self._collect_fps_tidevice()

    def _collect_fps_tidevice(self):
        """使用 tidevice 采集 FPS（降级方案）"""
        try:
            from insight_eyes.public.ios.fps_collector import FPSCollector
            collector = FPSCollector(self.udid, self.bundleId)
            return collector.collect()
        except Exception as e:
            logger.error(f"[IOSAPM] tidevice FPS 采集失败: {e}")
            return None

    def collectFlow(self):
        """
        采集网络流量

        Returns:
            dict: {'upFlow': float, 'downFlow': float} 单位 KB/s 或 None

        注意:
            py-ios-device 支持网络流量采集
        """
        try:
            collector = self._get_sysmontap_collector()
            if not collector:
                return None

            raw_data = collector.collect_network()

            # 使用 IOSDataNormalizer 规范化数据
            from insight_eyes.public.ios.data_normalizer import IOSDataNormalizer
            normalized = IOSDataNormalizer.normalize_network(raw_data)

            # 首次成功采集时提示
            if not self._network_warning_shown and normalized:
                logger.info(f"[IOSAPM] ✓ 网络流量采集支持 (py-ios-device)")
                self._network_warning_shown = True

            return normalized

        except Exception as e:
            logger.error(f"[IOSAPM] Network 采集失败: {e}")
            return None

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
        try:
            collector = self._get_energy_collector()
            if not collector:
                return None

            raw_data = collector.collect_battery()

            # 使用 IOSDataNormalizer 规范化数据
            from insight_eyes.public.ios.data_normalizer import IOSDataNormalizer
            return IOSDataNormalizer.normalize_battery(raw_data)

        except Exception as e:
            logger.warning(f"[IOSAPM] py-ios-device Battery 采集失败: {e}，尝试降级到 tidevice")
            return self._collect_battery_tidevice()

    def _collect_battery_tidevice(self):
        """使用 tidevice 采集 Battery（降级方案）"""
        try:
            from insight_eyes.public.ios.battery_collector import BatteryCollector
            collector = BatteryCollector(self.udid)
            return collector.collect()
        except Exception as e:
            logger.error(f"[IOSAPM] tidevice Battery 采集失败: {e}")
            return None

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
        try:
            collector = self._get_graphics_collector()
            if not collector:
                # 返回默认值
                return {
                    'gpu': 0,
                    'gpu_freq': 0,
                    'gpu_vendor': 'apple',
                    'gpu_model': 'Apple GPU'
                }

            raw_data = collector.collect_gpu()

            # 使用 IOSDataNormalizer 规范化数据
            from insight_eyes.public.ios.data_normalizer import IOSDataNormalizer
            normalized = IOSDataNormalizer.normalize_gpu(raw_data)
            return normalized if normalized else {
                'gpu': 0,
                'gpu_freq': 0,
                'gpu_vendor': 'apple',
                'gpu_model': 'Apple GPU'
            }

        except Exception as e:
            logger.error(f"[IOSAPM] GPU 采集失败: {e}")
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
