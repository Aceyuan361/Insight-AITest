# -*- coding: utf-8 -*-
"""
iOS 电池状态采集器

提供 iOS 设备的电池状态数据采集功能。
通过 IOSConnectionManager 获取 async lockdown，使用 DiagnosticsService.get_battery()。
"""

from typing import Dict, Any
from logzero import logger

from .connection_manager import IOSConnectionManager


class BatteryCollector:
    """iOS 电池状态采集"""

    def __init__(self, adapter):
        """
        初始化电池采集器

        Args:
            adapter: IOSDeviceAdapter 实例
        """
        self.adapter = adapter
        self._diagnostics_service = None

    def collect(self) -> Dict[str, Any]:
        """
        采集电池状态

        Returns:
            {'level': int, 'temperature': float, 'is_charging': bool}
        """
        try:
            return self._collect_via_diagnostics()

        except Exception as e:
            logger.debug(f"电池采集失败: {e}")
            return self._get_default_value()

    def _collect_via_diagnostics(self) -> Dict[str, Any]:
        """
        通过 DiagnosticsService 获取电池信息

        使用 pymobiledevice3 v9.x 的 async DiagnosticsService.get_battery()

        Returns:
            {'level': int, 'temperature': float, 'is_charging': bool}
        """
        try:
            from pymobiledevice3.services.diagnostics import DiagnosticsService

            logger.info("===== iOS 电池采集 =====")
            logger.info("API: pymobiledevice3 DiagnosticsService.get_battery()")

            device_id = getattr(self.adapter, "device_id", None)
            if not device_id:
                logger.warning("无 device_id，返回默认电池值")
                return self._get_default_value()

            mgr = IOSConnectionManager.get_instance(device_id)
            if not mgr.is_connected:
                mgr.connect()

            lockdown = mgr.get_async_lockdown()

            # 在事件循环中执行 async get_battery()
            diagnostics = DiagnosticsService(lockdown)
            battery_info = mgr.run_async(diagnostics.get_battery(), timeout=10)

            logger.info(f"API 返回原始数据: {battery_info}")

            # 解析电池信息
            level = battery_info.get("BatteryCurrentCapacity", 100)
            level = int(level) if level else 100

            # iOS 不暴露温度传感器，返回固定值
            temperature = 25.0

            # 判断充电状态
            is_charging = battery_info.get("BatteryIsCharging", False)
            if isinstance(is_charging, str):
                is_charging = is_charging.lower() in ("true", "1", "yes")

            result = {"level": level, "temperature": temperature, "is_charging": bool(is_charging)}

            logger.info(
                f"解析后数据: level={level}%, temperature={temperature}°C, is_charging={result['is_charging']}"
            )

            return result

        except ImportError as e:
            logger.error(f"无法导入 pymobiledevice3 服务: {e}")
            return self._get_default_value()

        except Exception as e:
            logger.error(f"DiagnosticsService 电池查询失败: {e}", exc_info=True)
            return self._get_default_value()

    def _get_default_value(self) -> Dict[str, Any]:
        """返回默认值"""
        return {"level": 100, "temperature": 25.0, "is_charging": False}
