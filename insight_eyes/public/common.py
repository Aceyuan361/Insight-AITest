# -*- coding: utf-8 -*-
"""
设备检测模块
提供 Android 设备检测和平台识别功能
"""
import subprocess
from logzero import logger
from enum import Enum


class Platform(Enum):
    """平台枚举"""
    ANDROID = "Android"
    # 向后兼容别名（保持旧代码正常运行）
    Android = ANDROID
    IOS = "iOS"
    UNKNOWN = "Unknown"


class Devices:
    """设备检测工具类（仅支持 Android 设备）"""

    def getDevices(self):
        """
        获取所有连接的设备列表

        Returns:
            list: 设备信息字符串列表，如 ["Android emulator-5554"]
        """
        devices = []

        # 获取 Android 设备
        android_devices = self._get_android_devices()
        for device_id in android_devices:
            devices.append(f"Android {device_id}")

        return devices

    def _get_android_devices(self):
        """获取 Android 设备列表"""
        try:
            from insight_eyes.public.adb import ADBHelper

            # 使用ADBHelper获取设备列表，防止命令注入
            adb_helper = ADBHelper()
            devices = adb_helper.devices()

            if not devices:
                logger.debug("未检测到 Android 设备（请检查USB连接和ADB调试）")

            return devices

        except FileNotFoundError:
            logger.error("ADB 未找到，请确保已安装 Android SDK Platform-Tools")
            return []
        except subprocess.TimeoutExpired:
            logger.error("ADB 命令超时")
            return []
        except Exception as e:
            logger.error(f"获取 Android 设备失败: {e}")
            return []

    def getIdbyDevice(self, device_info_str, platform):
        """
        从设备信息字符串中提取设备 ID

        Args:
            device_info_str: 设备信息字符串，如 "Android emulator-5554"
            platform: 平台类型 (Platform.Android)

        Returns:
            str: 设备 ID
        """
        if platform == Platform.Android:
            # Android: "Android emulator-5554" -> "emulator-5554"
            if device_info_str.startswith("Android "):
                return device_info_str[8:].strip()
            return device_info_str
        return device_info_str
