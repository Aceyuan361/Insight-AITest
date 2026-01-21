# -*- coding: utf-8 -*-
"""
iOS APM (Application Performance Monitor) 性能监控主类
提供 iOS 应用的性能数据采集功能

架构说明：
- 使用 IOSPyDeviceCollector 实现持久连接架构
- 数据持续推送到回调缓存，查询时返回缓存中的最新数据
- 与 AndroidAPM 接口保持一致

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
    - GPU 使用率

    架构：
    - 使用 IOSPyDeviceCollector 实现持久连接
    - 数据持续推送，collect 方法返回缓存中的最新数据
    - 与 AndroidAPM 接口保持一致
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

        # IOSPyDeviceCollector 采集器（延迟初始化）
        self._collector = None

        logger.info(f"初始化 iOS APM (PyiOSDevice架构): BundleID={bundleId}, UDID={udid}, 采集频率={frequency}秒")

    def _ensure_collector(self):
        """
        确保 IOSPyDeviceCollector 采集器已初始化

        Returns:
            IOSPyDeviceCollector: 采集器实例
        """
        if self._collector is None:
            from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector
            self._collector = IOSPyDeviceCollector(self.udid, self.bundleId)
            logger.debug(f"[IOSAPM] 采集器已初始化: UDID={self.udid}, BundleID={self.bundleId}")

        return self._collector

    def start(self):
        """
        启动监控

        建立持久连接并启动 Instruments 服务监控
        """
        try:
            collector = self._ensure_collector()

            if not collector.start():
                logger.warning(f"[IOSAPM] 启动失败: BundleID={self.bundleId}")
                return

            logger.info(f"[IOSAPM] ✓ 监控已启动: BundleID={self.bundleId}, UDID={self.udid}")

        except Exception as e:
            logger.error(f"[IOSAPM] 启动异常: {e}")
            import traceback
            logger.debug(traceback.format_exc())

    def stop(self):
        """
        停止监控

        停止 Instruments 服务并关闭持久连接
        """
        try:
            if self._collector:
                self._collector.stop()
                logger.info(f"[IOSAPM] ✓ 监控已停止: BundleID={self.bundleId}")

        except Exception as e:
            logger.warning(f"[IOSAPM] 停止监控失败: {e}")

    def collectCpu(self):
        """
        采集 CPU 使用率

        Returns:
            dict: {'appCpuRate': float, 'sysCpuRate': float} 或 None
        """
        try:
            collector = self._ensure_collector()
            return collector.collect_cpu()
        except Exception as e:
            logger.error(f"[IOSAPM] CPU 采集失败: {e}")
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
            collector = self._ensure_collector()
            return collector.collect_memory()
        except Exception as e:
            logger.error(f"[IOSAPM] Memory 采集失败: {e}")
            return None

    def collectFps(self):
        """
        采集 FPS 帧率数据

        Returns:
            dict: {
                'fps': int,             # 帧率
                'jank': int,            # 普通卡顿次数 (iOS 暂不支持)
                'bigJank': int,         # 严重卡顿次数 (iOS 暂不支持)
                'ftime_avg': float,     # 平均帧时间 (ms，iOS 暂不支持)
                'ftime_max': float,     # 最大帧时间 (ms，iOS 暂不支持)
                'ftime_min': float,     # 最小帧时间 (ms，iOS 暂不支持)
            } 或 None
        """
        try:
            collector = self._ensure_collector()
            fps_data = collector.collect_fps()

            if fps_data:
                # 补充 iOS 暂不支持的字段
                fps_data.setdefault('jank', 0)
                fps_data.setdefault('bigJank', 0)
                fps_data.setdefault('ftime_avg', 0.0)
                fps_data.setdefault('ftime_max', 0.0)
                fps_data.setdefault('ftime_min', 0.0)

            return fps_data

        except Exception as e:
            logger.error(f"[IOSAPM] FPS 采集失败: {e}")
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
            collector = self._ensure_collector()
            return collector.collect_network()
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
                'voltage': float,       # 电压 (V，iOS 暂不支持)
                'power': float,         # 功率 (W，iOS 暂不支持)
                'status': str,          # 充电状态 (iOS 暂不支持)
            } 或 None
        """
        try:
            collector = self._ensure_collector()
            battery_data = collector.collect_battery()

            if battery_data:
                # 补充 iOS 暂不支持的字段
                battery_data.setdefault('voltage', 0.0)
                battery_data.setdefault('power', 0.0)
                battery_data.setdefault('status', 'unknown')

            return battery_data

        except Exception as e:
            logger.error(f"[IOSAPM] Battery 采集失败: {e}")
            return None

    def collectGpu(self):
        """
        采集 GPU 使用率

        Returns:
            dict: {
                'gpu': int,             # GPU 使用率 (iOS 暂不支持)
                'gpu_freq': int,        # GPU 频率 (MHz，iOS 暂不支持)
                'gpu_vendor': str,      # GPU 厂商
                'gpu_model': str,       # GPU 型号
            }
        """
        # iOS GPU 监控暂未实现
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
