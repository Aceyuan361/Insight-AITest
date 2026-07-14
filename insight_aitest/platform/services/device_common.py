# -*- coding: utf-8 -*-
"""
设备检测模块
提供 Android 和 iOS 设备检测和平台识别功能
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
    """设备检测工具类（支持 Android 和 iOS 设备）"""

    def getDevices(self):
        """
        获取所有连接的设备列表

        Returns:
            list: 设备信息字符串列表，如 ["Android emulator-5554", "iOS <device-serial>"]
        """
        devices = []

        # 获取 Android 设备
        android_devices = self._get_android_devices()
        for device_id in android_devices:
            devices.append(f"Android {device_id}")

        # 获取 iOS 设备
        ios_devices = self._get_ios_devices()
        devices.extend(ios_devices)

        return devices

    def _get_android_devices(self):
        """获取 Android 设备列表"""
        logger.info("[ADB检测] 开始检测 Android 设备...")
        try:
            from insight_aitest.platform.services.collectors.adb import ADBHelper

            # 使用ADBHelper获取设备列表，防止命令注入
            logger.info("[ADB检测] 创建 ADBHelper 实例...")
            adb_helper = ADBHelper()
            logger.info(f"[ADB检测] ADB 路径: {adb_helper.adb_path}")
            logger.info("[ADB检测] 执行 adb devices 命令...")
            devices = adb_helper.devices()
            logger.info(f"[ADB检测] 检测到 {len(devices)} 个 Android 设备: {devices}")

            if not devices:
                logger.warning("[ADB检测] 未检测到 Android 设备（请检查USB连接和ADB调试）")

            return devices

        except FileNotFoundError:
            logger.error("[ADB检测] ADB 未找到，请确保已安装 Android SDK Platform-Tools")
            return []
        except subprocess.TimeoutExpired:
            logger.error("[ADB检测] ADB 命令超时")
            return []
        except Exception as e:
            logger.error(f"[ADB检测] 获取 Android 设备失败: {e}", exc_info=True)
            return []

    def _get_ios_devices(self):
        """获取 iOS 设备列表

        pymobiledevice3 >=9.x 中 list_devices() 是协程，需要 asyncio.run() 执行。
        """
        try:
            import asyncio

            from pymobiledevice3.usbmux import list_devices

            devices = []

            # pymobiledevice3 >=9.x: list_devices() 返回协程
            if asyncio.iscoroutinefunction(list_devices):
                ios_device_list = asyncio.run(list_devices())
            else:
                ios_device_list = list_devices()

            for device in ios_device_list:
                device_id = str(device.serial)
                devices.append(f"iOS {device_id}")
                logger.debug(f"检测到 iOS 设备: {device_id}")

            return devices

        except ImportError:
            logger.debug("pymobiledevice3 未安装，跳过 iOS 设备扫描")
            return []
        except Exception as e:
            logger.error(f"获取 iOS 设备失败: {e}")
            return []

    def getIdbyDevice(self, device_info_str, platform):
        """
        从设备信息字符串中提取设备 ID

        Args:
            device_info_str: 设备信息字符串，如 "Android emulator-5554" 或 "iOS <device-serial>"
            platform: 平台类型 (Platform.Android 或 Platform.IOS)

        Returns:
            str: 设备 ID
        """
        if platform == Platform.Android:
            # Android: "Android emulator-5554" -> "emulator-5554"
            if device_info_str.startswith("Android "):
                return device_info_str[8:].strip()
            return device_info_str
        elif platform == Platform.IOS:
            # iOS: "iOS <device-serial>" -> "<device-serial>"
            if device_info_str.startswith("iOS "):
                return device_info_str[4:].strip()
            return device_info_str
        return device_info_str
