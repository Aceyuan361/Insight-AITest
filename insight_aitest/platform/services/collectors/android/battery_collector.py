# -*- coding: utf-8 -*-
"""
Android 电池采集器
使用 ADB 实现 Android 设备的电池数据采集

改进：
- 集成设备配置系统（DeviceProfile）
"""

import re
from typing import Optional, Dict, Any
from logzero import logger
from insight_aitest.platform.services.collectors.adb import adb


class BatteryCollector:
    """
    Android 电池状态采集器 - 集成设备配置系统

    使用 ADB shell dumpsys battery 命令获取设备的电池信息
    """

    def __init__(self, device_id: str, device_profile=None):
        """
        初始化电池采集器

        Args:
            device_id: Android 设备 ID
            device_profile: 设备配置档案（可选）
        """
        self.device_id = device_id
        self.device_profile = device_profile
        self.strategy = device_profile.get_strategy() if device_profile else None

        if self.strategy:
            logger.debug(
                f"[电池采集器] 使用策略: {self.strategy.battery_method}, "
                f"温度单位: {self.strategy.battery_temperature_unit}"
            )

    def _parse_battery_from_dumpsys(self) -> Optional[Dict[str, Any]]:
        """
        使用 dumpsys battery 解析电池状态

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
            result = adb.shell("dumpsys battery", self.device_id)

            if not result:
                return None

            lines = result.strip().split("\n")

            battery_data = {
                "level": 0,
                "temperature": 0,
                "current": 0,
                "voltage": 0,
                "power": 0,
                "status": "unknown",
            }

            for line in lines:
                # 解析电量百分比
                if "level" in line.lower():
                    match = re.search(r"level:\s*(\d+)", line, re.IGNORECASE)
                    if match:
                        battery_data["level"] = int(match.group(1))

                # 解析温度 (单位: 0.1°C)
                elif "temperature" in line.lower():
                    match = re.search(r"temperature:\s*(\d+\.?\d*)", line, re.IGNORECASE)
                    if match:
                        temp_value = float(match.group(1))
                        # 温度可能以 0.1°C 为单位
                        if temp_value > 100:
                            battery_data["temperature"] = round(temp_value / 10, 1)
                        else:
                            battery_data["temperature"] = round(temp_value, 1)

                # 解析电流 (单位: mA 或 μA)
                elif "current" in line.lower() and "not" not in line.lower():
                    # 尝试多种格式
                    match = re.search(
                        r"current.*?:\s*(-?\d+\.?\d*)\s*(mA|uA|µA)?", line, re.IGNORECASE
                    )
                    if match:
                        current_value = float(match.group(1))
                        unit = match.group(2)

                        # 转换为 mA
                        if unit and ("uA" in unit or "µA" in unit):
                            battery_data["current"] = round(current_value / 1000, 2)
                        else:
                            battery_data["current"] = round(current_value, 2)

                # 解析电压 (单位: mV)
                elif "voltage" in line.lower() and "not" not in line.lower():
                    match = re.search(r"voltage.*?:\s*(\d+\.?\d*)\s*(mV|V)?", line, re.IGNORECASE)
                    if match:
                        voltage_value = float(match.group(1))
                        unit = match.group(2)

                        # 转换为 V
                        if unit and "mV" in unit:
                            battery_data["voltage"] = round(voltage_value / 1000, 2)
                        else:
                            battery_data["voltage"] = round(voltage_value, 2)

                # 解析充电状态
                elif "status" in line.lower():
                    match = re.search(r"status:\s*(\d+|[a-zA-Z]+)", line, re.IGNORECASE)
                    if match:
                        status_value = match.group(1)

                        # 数字状态码转文字
                        status_map = {
                            "1": "charging",
                            "2": "discharging",
                            "3": "not charging",
                            "4": "full",
                            "5": "unknown",
                        }

                        if status_value in status_map:
                            battery_data["status"] = status_map[status_value]
                        elif status_value.lower() in [
                            "charging",
                            "discharging",
                            "full",
                            "not charging",
                        ]:
                            battery_data["status"] = status_value.lower()

            # 计算功率 (W = V * A)
            if battery_data["voltage"] > 0 and battery_data["current"] != 0:
                battery_data["power"] = round(
                    abs(battery_data["voltage"] * battery_data["current"] / 1000), 3
                )

            return battery_data

        except Exception as e:
            logger.error(f"使用 dumpsys 获取电池信息失败: {e}")
            return None

    def _parse_battery_from_health(self) -> Optional[Dict[str, Any]]:
        """
        备选方法: 从 /sys/class/power_supply/ 获取电池信息

        Returns:
            dict: 电池数据或 None
        """
        try:
            battery_data = {
                "level": 0,
                "temperature": 0,
                "current": 0,
                "voltage": 0,
                "power": 0,
                "status": "unknown",
            }

            # 尝试读取电量
            capacity = adb.shell(
                "cat /sys/class/power_supply/battery/capacity 2>/dev/null", self.device_id
            )
            if capacity:
                battery_data["level"] = int(capacity.strip())

            # 尝试读取电压
            voltage = adb.shell(
                "cat /sys/class/power_supply/battery/voltage_now 2>/dev/null", self.device_id
            )
            if voltage:
                voltage_uv = int(voltage.strip())
                battery_data["voltage"] = round(voltage_uv / 1000000, 2)  # μV -> V

            # 尝试读取电流
            current = adb.shell(
                "cat /sys/class/power_supply/battery/current_now 2>/dev/null", self.device_id
            )
            if current:
                current_ua = int(current.strip())
                battery_data["current"] = round(current_ua / 1000, 2)  # μA -> mA

            # 尝试读取温度
            temp = adb.shell("cat /sys/class/power_supply/battery/temp 2>/dev/null", self.device_id)
            if temp:
                temp_tenth = int(temp.strip())
                battery_data["temperature"] = round(temp_tenth / 10, 1)  # 0.1°C -> °C

            # 尝试读取状态
            status = adb.shell(
                "cat /sys/class/power_supply/battery/status 2>/dev/null", self.device_id
            )
            if status:
                battery_data["status"] = status.strip().lower()

            # 计算功率
            if battery_data["voltage"] > 0 and battery_data["current"] != 0:
                battery_data["power"] = round(
                    abs(battery_data["voltage"] * battery_data["current"] / 1000), 3
                )

            return battery_data

        except Exception as e:
            logger.debug(f"从 sysfs 获取电池信息失败: {e}")
            return None

    def collect(self) -> Optional[Dict[str, Any]]:
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

        注意：
            - level: 电量百分比 (0-100)
            - temperature: 电池温度（摄氏度）
            - current: 电流，正数表示充电，负数表示放电（mA）
            - voltage: 电池电压（V）
            - power: 功率（W），绝对值
            - status: 充电状态 (charging/discharging/full/not charging/unknown)
        """
        try:
            # 方法1: 使用 dumpsys battery
            result = self._parse_battery_from_dumpsys()
            logger.debug(
                f"[电池采集器] dumpsys 结果: level={result.get('level') if result else None}, temp={result.get('temperature') if result else None}"
            )
            if result and result["level"] > 0:
                logger.debug(f"[电池采集器] 使用 dumpsys 结果: level={result['level']}%")
                return result

            # 方法2: 使用 sysfs 接口
            result = self._parse_battery_from_health()
            logger.debug(
                f"[电池采集器] sysfs 结果: level={result.get('level') if result else None}, temp={result.get('temperature') if result else None}"
            )
            if result and result["level"] > 0:
                logger.debug(f"[电池采集器] 使用 sysfs 结果: level={result['level']}%")
                return result

            # 如果都失败，返回默认值
            logger.debug("[电池采集器] 两种方法都未获取到有效电池数据（level=0），返回默认值")
            return {
                "level": 0,
                "temperature": 0,
                "current": 0,
                "voltage": 0,
                "power": 0,
                "status": "unknown",
            }

        except Exception as e:
            logger.error(f"Android 电池采集失败: {e}")
            return None
