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

        扫描并返回所有已连接的 Android 和 iOS 设备。
        使用桌面层的设备适配器进行设备连接和信息获取。

        Returns:
            设备列表
        """
        from insight_eyes.public.common import Devices, Platform
        from insight_eyes.desktop.core.device_adapters import DeviceAdapterFactory

        logger.info("扫描设备...")
        devices = []

        try:
            # 获取当前连接的设备
            devices_detector = Devices()
            device_list = devices_detector.getDevices()

            logger.debug(f"检测到 {len(device_list)} 个设备字符串: {device_list}")

            # 处理每个设备
            for device_str in device_list:
                try:
                    # 解析设备类型和ID
                    if device_str.startswith("Android "):
                        device_id = device_str[8:].strip()
                        device_type = DeviceType.ANDROID
                        platform = Platform.ANDROID
                    elif device_str.startswith("iOS "):
                        device_id = device_str[4:].strip()
                        device_type = DeviceType.IOS
                        platform = Platform.IOS
                    else:
                        logger.debug(f"跳过未知设备格式: {device_str}")
                        continue

                    logger.debug(f"处理设备: {device_id} ({device_type.value})")

                    # 创建设备适配器并获取设备信息
                    adapter = DeviceAdapterFactory.create_adapter(device_id, platform)
                    if not adapter:
                        logger.warning(f"无法为设备 {device_id} 创建适配器")
                        continue

                    # 连接设备并获取信息
                    if adapter.connect():
                        device_info = adapter.get_device_info()
                        if device_info:
                            # 转换桌面层 DeviceInfo 为核心层 Device 模型
                            device = Device(
                                device_id=device_info.device_id,
                                name=device_info.name,
                                type=device_type,
                                status=DeviceStatus.ONLINE,
                                sdk_version=device_info.os_version,
                                model=device_info.model
                            )
                            devices.append(device)
                            logger.info(f"发现设备: {device.name} ({device.type.value})")
                        else:
                            logger.warning(f"无法获取设备信息: {device_id}")
                    else:
                        logger.warning(f"无法连接到设备 {device_id}")

                except Exception as e:
                    logger.error(f"处理设备失败 [{device_str}]: {e}", exc_info=True)
                    continue

        except Exception as e:
            logger.error(f"设备扫描异常: {e}", exc_info=True)

        logger.info(f"扫描完成，共发现 {len(devices)} 个设备")
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
