# -*- coding: utf-8 -*-
"""
设备管理器 - 核心层
提供桌面版和 Web 版共享的设备管理功能

注意：此模块为初始实现，设备扫描和数据采集功能将在后续任务中
从桌面层移植到核心层。当前版本仅提供基本框架和数据库集成。
"""
from typing import List, AsyncIterator
from datetime import datetime
from logzero import logger

from insight_eyes.core.models.device import Device, DeviceType, DeviceStatus
from insight_eyes.core.models.session import Session, SessionStatus
from insight_eyes.core.models.metrics import MetricsData
from insight_eyes.core.database import DatabaseManager


class DeviceManager:
    """设备管理器

    负责设备扫描、会话管理和数据流推送。

    注意：当前版本为简化实现，完整的设备管理功能将在后续任务中实现。
    """

    @staticmethod
    def scan_devices() -> List[Device]:
        """扫描可用设备

        扫描 Android 设备（通过 ADB）和 iOS 设备（通过 pymobiledevice3）。

        Returns:
            设备列表
        """
        logger.info("扫描设备...")
        devices = []

        # 扫描 Android 设备
        android_devices = DeviceManager._scan_android_devices()
        devices.extend(android_devices)

        # 扫描 iOS 设备
        ios_devices = DeviceManager._scan_ios_devices()
        devices.extend(ios_devices)

        logger.info(f"扫描完成，共发现 {len(devices)} 个设备")
        return devices

    @staticmethod
    def _scan_android_devices() -> List[Device]:
        """扫描 Android 设备

        Returns:
            Android 设备列表
        """
        devices = []
        try:
            from insight_eyes.public.adb import ADBHelper

            adb_helper = ADBHelper()
            device_ids = adb_helper.devices()

            for device_id in device_ids:
                try:
                    # 获取设备属性
                    model = adb_helper.get_device_property("ro.product.model", device_id) or device_id
                    sdk_version = adb_helper.get_device_property("ro.build.version.sdk", device_id)
                    device_name = adb_helper.get_device_property("ro.product.manufacturer", device_id) or model

                    # 获取设备状态
                    # 这里简化处理，如果能获取到属性说明设备在线
                    status = DeviceStatus.ONLINE

                    device = Device(
                        device_id=device_id,
                        name=f"{device_name} ({model})",
                        type=DeviceType.ANDROID,
                        status=status,
                        sdk_version=sdk_version,
                        model=model,
                    )
                    devices.append(device)
                    logger.info(f"发现 Android 设备: {device.name} ({device_id})")

                except Exception as e:
                    logger.warning(f"获取 Android 设备信息失败 [{device_id}]: {e}")
                    # 即使获取详细信息失败，也添加设备到列表
                    devices.append(Device(
                        device_id=device_id,
                        name=f"Android Device ({device_id[:8]}...)",
                        type=DeviceType.ANDROID,
                        status=DeviceStatus.ONLINE,
                    ))

        except FileNotFoundError:
            logger.debug("ADB 未找到，跳过 Android 设备扫描")
        except Exception as e:
            logger.error(f"扫描 Android 设备失败: {e}")

        return devices

    @staticmethod
    def _scan_ios_devices() -> List[Device]:
        """扫描 iOS 设备

        Returns:
            iOS 设备列表
        """
        devices = []

        try:
            # 尝试导入 pymobiledevice3
            try:
                from pymobiledevice3.usbmux import list_devices
            except ImportError:
                logger.debug("pymobiledevice3 未安装，跳过 iOS 设备扫描")
                return devices

            # 扫描 iOS 设备
            ios_device_list = list_devices()

            for device in ios_device_list:
                try:
                    device_id = str(device.serial)

                    # 获取设备信息
                    device_type = device.connection_type
                    model = getattr(device, 'device_class', 'iOS Device')

                    device = Device(
                        device_id=device_id,
                        name=f"iOS Device ({device_id[:8]}...)",
                        type=DeviceType.IOS,
                        status=DeviceStatus.ONLINE,
                        model=model,
                    )
                    devices.append(device)
                    logger.info(f"发现 iOS 设备: {device.name} ({device_id})")

                except Exception as e:
                    logger.warning(f"处理 iOS 设备信息失败: {e}")

        except Exception as e:
            logger.debug(f"扫描 iOS 设备失败: {e}")

        return devices

    @staticmethod
    async def start_session(device_id: str, app_package: str, platform: str = "android") -> Session:
        """开始监控会话

        Args:
            device_id: 设备ID
            app_package: 应用包名
            platform: 平台类型 ('android' 或 'ios')

        Returns:
            创建的会话对象
        """
        import os
        db_path = os.path.join(os.path.expanduser("~"), ".insight_eye", "monitoring.db")
        db = DatabaseManager(db_path)
        session = db.create_session(device_id, app_package, platform=platform)

        logger.info(f"开始监控会话: {session.id}")
        return session

    @staticmethod
    async def stop_session(session_id: int) -> None:
        """停止监控会话

        Args:
            session_id: 会话ID
        """
        import os
        db_path = os.path.join(os.path.expanduser("~"), ".insight_eye", "monitoring.db")
        db = DatabaseManager(db_path)
        db.update_session(
            session_id,
            status="stopped",
            end_time=datetime.now().isoformat(),
        )

        logger.info(f"停止监控会话: {session_id}")

    @staticmethod
    async def stream_metrics(session_id: int) -> AsyncIterator[MetricsData]:
        """流式推送监控数据

        TODO: 从桌面层移植实际的数据采集逻辑
        - 创建后台采集线程
        - 通过设备适配器采集数据
        - 实时推送到 WebSocket

        Args:
            session_id: 会话ID

        Yields:
            监控指标数据（当前返回模拟数据）
        """
        import asyncio

        # TODO: 实现实际的数据采集逻辑
        # 这里先返回模拟数据，待后续从 desktop 移植实现
        while True:
            await asyncio.sleep(1)
            yield MetricsData(
                timestamp=datetime.now(),
                cpu=50.0,
                memory=512.0,
                fps=60.0,
            )
