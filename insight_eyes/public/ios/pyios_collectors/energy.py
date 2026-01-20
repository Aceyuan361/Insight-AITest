# -*- coding: utf-8 -*-
"""
Energy 数据采集器
基于 Apple Instruments Energy 服务的 Battery 数据采集

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License

Author: Aceyuan361
"""
from typing import Optional, Dict, Any
from logzero import logger

from .base import PyIOSCollectorBase


class EnergyCollector(PyIOSCollectorBase):
    """
    Energy 采集器

    Apple Instruments Energy 服务提供：
    - 电池电量
    - 电池温度
    - 电流和电压
    - 电池状态（充电/放电）

    支持版本：iOS 17-26
    """

    def __init__(self, rpc_connection, bundle_id: str):
        """
        初始化 Energy 采集器

        Args:
            rpc_connection: InstrumentServer RPC 连接
            bundle_id: 目标应用的 Bundle ID
        """
        super().__init__(rpc_connection)
        self.bundle_id = bundle_id
        self._service_name = "com.apple.instruments.server.services.energy"

        # 配置参数
        self._sampling_interval = 1.0  # 采样间隔（秒）

    def configure(self) -> bool:
        """
        配置 Energy 服务

        Returns:
            bool: 配置是否成功
        """
        try:
            # Energy 服务通常使用默认配置
            logger.debug(f"[Energy] ✓ 使用默认配置")
            return True

        except Exception as e:
            logger.error(f"[Energy] ✗ 配置失败: {e}")
            return False

    def start(self) -> bool:
        """
        启动 Energy 服务

        Returns:
            bool: 启动是否成功
        """
        try:
            self._rpc.call(self._service_name, "start")
            logger.info(f"[Energy] ✓ 服务已启动: {self.bundle_id}")
            return True

        except Exception as e:
            logger.error(f"[Energy] ✗ 启动失败: {e}")
            return False

    def stop(self) -> bool:
        """
        停止 Energy 服务

        Returns:
            bool: 停止是否成功
        """
        try:
            self._rpc.call(self._service_name, "stop")
            logger.info(f"[Energy] ✓ 服务已停止")
            return True

        except Exception as e:
            logger.error(f"[Energy] ✗ 停止失败: {e}")
            return False

    def parse_message(self, message: Any) -> Optional[Dict[str, Any]]:
        """
        解析 Energy 消息

        Energy 消息格式可能包含：
        {
            'level': 85,           # 电量百分比
            'temperature': 28.5,   # 温度（摄氏度）
            'current': 100,        # 电流（mA）
            'voltage': 3.8,        # 电压（V）
            'power': 0.38,         # 功率（W）
            'status': 'discharging' # 状态
        }

        Args:
            message: 原始 DTX 消息

        Returns:
            dict: {
                'battery': {...}
            }
        """
        try:
            if not message:
                return None

            # 提取电池数据
            result = {
                'battery': self._extract_battery_data(message)
            }

            return result

        except Exception as e:
            logger.error(f"[Energy] 解析消息失败: {e}")
            return None

    def _extract_battery_data(self, message: Dict) -> Dict[str, Any]:
        """
        提取 Battery 数据

        Args:
            message: Energy 消息

        Returns:
            dict: {
                'level': int,          # 电量百分比
                'temperature': float,  # 温度（℃）
                'current': int,        # 电流（mA）
                'voltage': float,      # 电压（V）
                'power': float,        # 功率（W）
                'status': str          # 状态
            }
        """
        try:
            # 初始化默认值
            level = 100
            temperature = 25.0
            current = 0
            voltage = 0.0
            power = 0.0
            status = 'unknown'

            if isinstance(message, dict):
                # 尝试多种可能的字段名
                if 'level' in message:
                    level = int(message['level'])
                elif 'batteryLevel' in message:
                    level = int(message['batteryLevel'])

                if 'temperature' in message:
                    temperature = float(message['temperature'])

                if 'current' in message:
                    current = int(message['current'])

                if 'voltage' in message:
                    voltage = float(message['voltage'])
                    # 计算功率 P = U * I
                    if current != 0:
                        power = round(voltage * current / 1000, 3)  # V * mA / 1000 = W

                if 'power' in message:
                    power = float(message['power'])

                if 'status' in message:
                    status = str(message['status'])
                elif 'batteryState' in message:
                    status = str(message['batteryState'])

            return {
                'level': level,
                'temperature': round(temperature, 1),
                'current': current,
                'voltage': round(voltage, 2),
                'power': round(power, 3),
                'status': status
            }

        except (KeyError, AttributeError, TypeError) as e:
            logger.warning(f"[Energy] Battery 数据格式错误: {type(e).__name__}: {e}")
            # 返回默认值
            return {
                'level': 100,
                'temperature': 25.0,
                'current': 0,
                'voltage': 0.0,
                'power': 0.0,
                'status': 'unknown'
            }
        except (ValueError, ArithmeticError) as e:
            logger.warning(f"[Energy] Battery 数值转换失败: {e}")
            return {
                'level': 100,
                'temperature': 25.0,
                'current': 0,
                'voltage': 0.0,
                'power': 0.0,
                'status': 'unknown'
            }

    def collect_battery(self) -> Optional[Dict[str, Any]]:
        """
        单次 Battery 采集（便捷方法）

        Returns:
            dict: Battery 数据
        """
        message = self.receive_message()
        if message:
            battery_data = self._extract_battery_data(message)
            return battery_data
        return None
