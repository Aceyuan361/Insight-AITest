# -*- coding: utf-8 -*-
"""
SysMontap 数据采集器
基于 Apple Instruments SysMontap 服务的 CPU 和 Memory 数据采集

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License

Author: Aceyuan361
"""
import time
from typing import Optional, Dict, Any, List
from logzero import logger

from .base import PyIOSCollectorBase


class SysMontapCollector(PyIOSCollectorBase):
    """
    SysMontap 采集器

    Apple Instruments SysMontap 服务提供：
    - CPU 使用率（应用和系统）
    - 内存使用情况（物理内存、虚拟内存）
    - 网络流量（上行、下行）
    - 线程数等系统信息

    支持版本：iOS 17-26
    """

    def __init__(self, rpc_connection, bundle_id: str):
        """
        初始化 SysMontap 采集器

        Args:
            rpc_connection: InstrumentServer RPC 连接
            bundle_id: 目标应用的 Bundle ID
        """
        super().__init__(rpc_connection)
        self.bundle_id = bundle_id
        self._service_name = "com.apple.instruments.server.services.sysmontap"

        # 配置参数
        self._update_rate = 1000  # 数据更新频率（毫秒）
        self._proc_attrs = ['cpuUsage', 'memVirtualSize', 'memResidentSize', 'threadCount']
        self._sys_attrs = ['cpuTotal', 'networkIn', 'networkOut', 'memFree']

        # 网络速率计算缓存（用于计算 KB/s）
        self._last_network_data = {
            'down_bytes': 0,
            'up_bytes': 0,
            'last_time': time.time()
        }

    def configure(self) -> bool:
        """
        配置 SysMontap 服务

        Returns:
            bool: 配置是否成功
        """
        try:
            config = {
                'ur': self._update_rate,
                'procAttrs': self._proc_attrs,
                'sysAttrs': self._sys_attrs
            }

            self._rpc.call(self._service_name, "setConfig:", config)
            logger.debug(f"[SysMontap] ✓ 配置成功: {config}")
            return True

        except Exception as e:
            logger.error(f"[SysMontap] ✗ 配置失败: {e}")
            return False

    def start(self) -> bool:
        """
        启动 SysMontap 服务

        Returns:
            bool: 启动是否成功
        """
        try:
            self._rpc.call(self._service_name, "start")
            logger.info(f"[SysMontap] ✓ 服务已启动: {self.bundle_id}")
            return True

        except Exception as e:
            logger.error(f"[SysMontap] ✗ 启动失败: {e}")
            return False

    def stop(self) -> bool:
        """
        停止 SysMontap 服务

        Returns:
            bool: 停止是否成功
        """
        try:
            self._rpc.call(self._service_name, "stop")
            logger.info(f"[SysMontap] ✓ 服务已停止")
            return True

        except Exception as e:
            logger.error(f"[SysMontap] ✗ 停止失败: {e}")
            return False

    def parse_message(self, message: Any) -> Optional[Dict[str, Any]]:
        """
        解析 SysMontap 消息

        SysMontap 消息格式：
        {
            'processes': [
                {
                    'pid': 123,
                    'name': 'App Name',
                    'bundleId': 'com.example.app',
                    'cpuUsage': 15.2,
                    'memVirtualSize': 150000000,
                    'memResidentSize': 120000000,
                    'threadCount': 5
                },
                ...
            ],
            'system': {
                'cpuTotal': 35.8,
                'memFree': 2000000000,
                'networkIn': 1024000,
                'networkOut': 512000
            }
        }

        Args:
            message: 原始 DTX 消息

        Returns:
            dict: {
                'cpu': {'appCpuRate': float, 'sysCpuRate': float},
                'memory': {'totalPass': float, 'nativePass': float, 'dalvikPass': float},
                'network': {'upFlow': float, 'downFlow': float}
            }
        """
        try:
            if not message:
                return None

            # 提取所有数据
            result = {
                'cpu': self._extract_cpu_data(message),
                'memory': self._extract_memory_data(message),
                'network': self._extract_network_data(message)
            }

            return result

        except Exception as e:
            logger.error(f"[SysMontap] 解析消息失败: {e}")
            return None

    def _extract_cpu_data(self, message: Dict) -> Dict[str, float]:
        """
        提取 CPU 数据

        Args:
            message: SysMontap 消息

        Returns:
            dict: {'appCpuRate': float, 'sysCpuRate': float}
        """
        try:
            # 初始化默认值
            app_cpu = 0.0
            sys_cpu = 0.0

            # 从系统信息获取总 CPU 使用率
            if 'system' in message:
                sys_cpu = float(message['system'].get('cpuTotal', 0))

            # 从进程列表查找目标应用
            if 'processes' in message:
                for proc in message['processes']:
                    if proc.get('bundleId') == self.bundle_id:
                        app_cpu = float(proc.get('cpuUsage', 0))
                        break

            return {
                'appCpuRate': round(app_cpu, 2),
                'sysCpuRate': round(sys_cpu, 2)
            }

        except (KeyError, AttributeError, TypeError) as e:
            logger.warning(f"[SysMontap] CPU 数据格式错误: {type(e).__name__}: {e}")
            return {'appCpuRate': 0.0, 'sysCpuRate': 0.0}
        except (ValueError, ArithmeticError) as e:
            logger.warning(f"[SysMontap] CPU 数值转换失败: {e}")
            return {'appCpuRate': 0.0, 'sysCpuRate': 0.0}

    def _extract_memory_data(self, message: Dict) -> Dict[str, float]:
        """
        提取 Memory 数据

        Args:
            message: SysMontap 消息

        Returns:
            dict: {'totalPass': float, 'nativePass': float, 'dalvikPass': float}
        """
        try:
            # 初始化默认值
            total_mb = 0.0
            native_mb = 0.0

            # 从进程列表查找目标应用
            if 'processes' in message:
                for proc in message['processes']:
                    if proc.get('bundleId') == self.bundle_id:
                        # 优先使用物理内存（memResidentSize）
                        resident = proc.get('memResidentSize', 0)
                        virtual = proc.get('memVirtualSize', resident)

                        # 转换为 MB（字节 -> MB）
                        total_mb = round(resident / (1024 * 1024), 2)
                        native_mb = round(virtual / (1024 * 1024), 2)
                        break

            return {
                'totalPass': total_mb,
                'nativePass': native_mb,
                'dalvikPass': 0.0  # iOS 没有 Dalvik
            }

        except (KeyError, AttributeError, TypeError) as e:
            logger.warning(f"[SysMontap] Memory 数据格式错误: {type(e).__name__}: {e}")
            return {'totalPass': 0, 'nativePass': 0, 'dalvikPass': 0}
        except (ValueError, ArithmeticError) as e:
            logger.warning(f"[SysMontap] Memory 数值转换失败: {e}")
            return {'totalPass': 0, 'nativePass': 0, 'dalvikPass': 0}

    def _extract_network_data(self, message: Dict) -> Dict[str, float]:
        """
        提取 Network 数据（计算速率而非累计值）

        Args:
            message: SysMontap 消息

        Returns:
            dict: {'upFlow': float, 'downFlow': float} (KB/s)
        """
        try:
            current_time = time.time()

            # 从系统信息获取网络流量（累计值，字节）
            if 'system' in message:
                system = message['system']
                down_bytes = system.get('networkIn', 0)
                up_bytes = system.get('networkOut', 0)

                # 计算时间差（秒）
                time_delta = current_time - self._last_network_data['last_time']

                # 避免除零和首次采样
                if time_delta < 0.1:  # 时间间隔太短，返回上次值
                    return {
                        'upFlow': self._last_network_data.get('up_rate', 0),
                        'downFlow': self._last_network_data.get('down_rate', 0)
                    }

                # 计算速率（字节/秒 → KB/s）
                if self._last_network_data['last_time'] > 0:
                    down_delta = down_bytes - self._last_network_data['down_bytes']
                    up_delta = up_bytes - self._last_network_data['up_bytes']

                    # 处理计数器回绕（设备重启等情况）
                    if down_delta < 0:
                        down_delta = down_bytes
                    if up_delta < 0:
                        up_delta = up_bytes

                    down_rate = round(down_delta / time_delta / 1024, 2)  # KB/s
                    up_rate = round(up_delta / time_delta / 1024, 2)    # KB/s
                else:
                    down_rate = 0
                    up_rate = 0

                # 更新缓存
                self._last_network_data = {
                    'down_bytes': down_bytes,
                    'up_bytes': up_bytes,
                    'down_rate': down_rate,
                    'up_rate': up_rate,
                    'last_time': current_time
                }

                return {'upFlow': up_rate, 'downFlow': down_rate}

            return {'upFlow': 0, 'downFlow': 0}

        except (KeyError, AttributeError, TypeError) as e:
            logger.warning(f"[SysMontap] Network 数据格式错误: {type(e).__name__}: {e}")
            return {'upFlow': 0, 'downFlow': 0}
        except (ValueError, ArithmeticError) as e:
            logger.warning(f"[SysMontap] Network 数值转换失败: {e}")
            return {'upFlow': 0, 'downFlow': 0}

    def collect_cpu(self) -> Optional[Dict[str, float]]:
        """
        单次 CPU 采集（便捷方法）

        Returns:
            dict: {'appCpuRate': float, 'sysCpuRate': float}
        """
        message = self.receive_message()
        if message:
            cpu_data = self._extract_cpu_data(message)
            return cpu_data
        return None

    def collect_memory(self) -> Optional[Dict[str, float]]:
        """
        单次 Memory 采集（便捷方法）

        Returns:
            dict: {'totalPass': float, 'nativePass': float, 'dalvikPass': float}
        """
        message = self.receive_message()
        if message:
            mem_data = self._extract_memory_data(message)
            return mem_data
        return None

    def collect_network(self) -> Optional[Dict[str, float]]:
        """
        单次 Network 采集（便捷方法）

        Returns:
            dict: {'upFlow': float, 'downFlow': float}
        """
        message = self.receive_message()
        if message:
            net_data = self._extract_network_data(message)
            return net_data
        return None
