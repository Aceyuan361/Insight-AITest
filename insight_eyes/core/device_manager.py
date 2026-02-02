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
    async def start_session(device_id: str, app_package: str, platform: str = "android", sampling_interval: int = 1000) -> Session:
        """开始监控会话

        Args:
            device_id: 设备ID
            app_package: 应用包名
            platform: 平台类型 ('android' 或 'ios')
            sampling_interval: 采样间隔（毫秒），默认1000ms

        Returns:
            创建的会话对象
        """
        import os
        db_path = os.path.join(os.path.expanduser("~"), ".insight_eye", "monitoring.db")
        db = DatabaseManager(db_path)
        session = db.create_session(device_id, app_package, platform=platform, sampling_interval=sampling_interval)

        logger.info(f"开始监控会话: {session.id}, 采样间隔: {sampling_interval}ms")
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

        从桌面层移植实际的数据采集逻辑，确保与桌面版算法一致：
        - 直接使用桌面层的设备适配器进行数据采集
        - 保持与桌面版相同的计算精度
        - 每秒采集一次数据

        采集频率：1秒
        数据来源：桌面层 AndroidAPM / IOSAPM

        Args:
            session_id: 会话ID

        Yields:
            监控指标数据（实时采集的真实数据）
        """
        import asyncio
        import os
        from insight_eyes.public.common import Platform

        # 获取会话信息
        db_path = os.path.join(os.path.expanduser("~"), ".insight_eye", "monitoring.db")
        db = DatabaseManager(db_path)
        session = db.get_session(session_id)

        if not session:
            logger.error(f"会话不存在: {session_id}")
            return

        logger.info(f"开始流式推送监控数据: session={session_id}, device={session.device_id}, app={session.app_package}")

        # 导入桌面层的设备适配器，直接使用采集方法
        from insight_eyes.desktop.core.device_adapters import DeviceAdapterFactory

        try:
            # 创建设备适配器
            platform = Platform.ANDROID if session.platform == 'android' else Platform.IOS
            adapter = DeviceAdapterFactory.create_adapter(session.device_id, platform)

            if not adapter:
                logger.error(f"无法创建设备适配器: {session.device_id}")
                return

            # 确保设备已连接
            if not adapter.is_connected():
                logger.info(f"连接设备: {session.device_id}")
                if not adapter.connect():
                    logger.error(f"设备连接失败: {session.device_id}")
                    return

            logger.info(f"设备适配器已就绪，开始数据采集")

            try:
                while True:
                    try:
                        # 直接使用适配器采集各项指标数据
                        metrics_data = MetricsData(timestamp=datetime.now())

                        # 采集 FPS
                        try:
                            fps_data = adapter.collect_fps(session.app_package)
                            if fps_data:
                                metrics_data.fps = float(fps_data.get('fps', 0))
                        except Exception as e:
                            logger.debug(f"FPS采集失败: {e}")

                        # 采集内存
                        try:
                            memory_data = adapter.collect_memory(session.app_package)
                            if memory_data:
                                # iOS使用used_mb，Android使用totalPass
                                if session.platform == 'ios':
                                    metrics_data.memory = float(memory_data.get('used_mb', 0))
                                else:
                                    metrics_data.memory = float(memory_data.get('totalPass', 0))
                        except Exception as e:
                            logger.debug(f"内存采集失败: {e}")

                        # 采集 CPU
                        try:
                            cpu_data = adapter.collect_cpu(session.app_package)
                            if cpu_data:
                                # iOS使用cpu_app，Android使用appCpuRate
                                if session.platform == 'ios':
                                    metrics_data.cpu = float(cpu_data.get('cpu_app', 0.0))
                                else:
                                    metrics_data.cpu = float(cpu_data.get('appCpuRate', 0.0))
                        except Exception as e:
                            logger.debug(f"CPU采集失败: {e}")

                        # 采集网络
                        try:
                            network_data = adapter.collect_network(session.app_package)
                            if network_data:
                                metrics_data.network_up = float(network_data.get('upFlow', 0.0))
                                metrics_data.network_down = float(network_data.get('downFlow', 0.0))
                        except Exception as e:
                            logger.debug(f"网络采集失败: {e}")

                        # 采集电池
                        try:
                            battery_data = adapter.collect_battery()
                            if battery_data:
                                metrics_data.battery = float(battery_data.get('level', 0))
                                metrics_data.temperature = float(battery_data.get('temperature', 0.0))
                        except Exception as e:
                            logger.debug(f"电池采集失败: {e}")

                        # 检查是否至少有一个指标采集成功
                        has_data = any([
                            metrics_data.fps is not None,
                            metrics_data.memory is not None,
                            metrics_data.cpu is not None,
                            metrics_data.network_up is not None,
                            metrics_data.network_down is not None,
                            metrics_data.battery is not None
                        ])

                        if has_data:
                            logger.debug(f"数据采集成功: CPU={metrics_data.cpu:.1f}%, "
                                         f"Memory={metrics_data.memory:.1f}MB, "
                                         f"FPS={metrics_data.fps:.0f}")
                            yield metrics_data
                        else:
                            logger.warning(f"所有指标采集均失败: {session.device_id}/{session.app_package}")

                    except Exception as e:
                        logger.error(f"数据采集异常: {e}", exc_info=True)

                    # 使用会话配置的采样间隔（毫秒转换为秒）
                    sleep_seconds = session.sampling_interval / 1000
                    await asyncio.sleep(sleep_seconds)

            except asyncio.CancelledError:
                logger.info(f"流式推送已取消: session={session_id}")
            finally:
                # 清理适配器资源
                if adapter:
                    adapter.cleanup()
                logger.info(f"设备适配器资源已清理: session={session_id}")

        except Exception as e:
            logger.error(f"流式推送异常: {e}", exc_info=True)
            raise
