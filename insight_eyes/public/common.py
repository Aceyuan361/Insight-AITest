# -*- coding: utf-8 -*-
"""
设备检测模块
提供 Android/iOS 设备检测和平台识别功能

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License

Author: Aceyuan361
"""
import subprocess
import json
import shutil
from logzero import logger
from enum import Enum


class Platform(Enum):
    """平台枚举"""
    Android = "Android"
    iOS = "iOS"


class Devices:
    """设备检测工具类"""

    def __init__(self):
        self._tidevice_available = None

    @property
    def tidevice_available(self):
        """检查 tidevice 是否可用（缓存结果）"""
        if self._tidevice_available is None:
            self._tidevice_available = shutil.which('tidevice') is not None
            if self._tidevice_available:
                logger.info("tidevice 可用")
            else:
                logger.warning("tidevice 未安装，iOS 设备检测不可用")
        return self._tidevice_available

    def getDevices(self):
        """
        获取所有连接的设备列表

        Returns:
            list: 设备信息字符串列表，如 ["Android emulator-5554", "iOS iPhone"]
        """
        devices = []

        # 获取 Android 设备
        android_devices = self._get_android_devices()
        for device_id in android_devices:
            devices.append(f"Android {device_id}")

        # 获取 iOS 设备
        if self.tidevice_available:
            ios_devices = self._get_ios_devices()
            for device in ios_devices:
                devices.append(f"iOS {device['name']} ({device['udid']})")

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

    def _get_ios_devices(self):
        """获取 iOS 设备列表"""
        try:
            result = subprocess.run(
                ['tidevice', 'list', '--json'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                logger.error(f"获取 iOS 设备列表失败: {result.stderr}")
                return []

            return json.loads(result.stdout)

        except json.JSONDecodeError as e:
            logger.error(f"解析 iOS 设备列表失败: {e}")
            return []
        except Exception as e:
            logger.error(f"获取 iOS 设备失败: {e}")
            return []

    def getIdbyDevice(self, device_info_str, platform):
        """
        从设备信息字符串中提取设备 ID

        Args:
            device_info_str: 设备信息字符串，如 "Android emulator-5554"
            platform: 平台类型 (Platform.Android 或 Platform.iOS)

        Returns:
            str: 设备 ID
        """
        if platform == Platform.Android:
            # Android: "Android emulator-5554" -> "emulator-5554"
            if device_info_str.startswith("Android "):
                return device_info_str[8:].strip()
            return device_info_str
        elif platform == Platform.iOS:
            # iOS: "iOS iPhone (udid)" -> "udid"
            if '(' in device_info_str and ')' in device_info_str:
                return device_info_str.split('(')[1].split(')')[0].strip()
            return device_info_str
        return device_info_str

    def getPkgnameByiOS(self, udid):
        """
        获取 iOS 设备上的应用包名列表

        Args:
            udid: iOS 设备 UDID

        Returns:
            list: 应用包名列表
        """
        try:
            result = subprocess.run(
                ['tidevice', '--udid', udid, 'app', 'list'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                logger.error(f"获取 iOS 应用列表失败: {result.stderr}")
                return []

            packages = []
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line and not line.startswith('Total:'):
                    # 格式: com.apple.mobilesafari (Mobile Safari)
                    if ' ' in line:
                        bundle_id = line.split(' ')[0]
                        packages.append(bundle_id)
                    else:
                        packages.append(line)

            return packages

        except Exception as e:
            logger.error(f"获取 iOS 应用列表失败: {e}")
            return []
