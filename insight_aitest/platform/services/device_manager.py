# -*- coding: utf-8 -*-
"""
设备管理器 - 核心层
提供桌面版和 Web 版共享的设备管理功能。

实现设备扫描（Android + iOS）、监控会话生命周期、并行指标采集
（FPS/内存/CPU/网络/电池，asyncio.gather + 线程池桥接）、
阈值告警检测（含 30s 冷却）与持久化。
iOS 设备连接依赖 pymobiledevice3（详见 device_adapters）。
"""

import time
from typing import List, AsyncIterator
from datetime import datetime
from logzero import logger
import asyncio

from insight_aitest.platform.services.models.device import Device, DeviceType, DeviceStatus
from insight_aitest.platform.services.models.session import Session, SessionStatus
from insight_aitest.platform.services.models.metrics import MetricsData
from insight_aitest.platform.persistence.database import DatabaseManager


class DeviceManager:
    """设备管理器（全静态方法 + 类级共享状态）。

    负责设备扫描、监控会话生命周期、并行指标采集与阈值告警检测。
    类级字段（_cancel_tokens / _adapter_cache / _alert_*）用于跨方法共享，
    单元测试需通过 _reset_device_manager_state 夹具重置。
    """

    # 类级别的取消令牌管理，用于停止正在运行的数据采集任务
    _cancel_tokens: dict[int, asyncio.Event] = {}

    # 设备适配器缓存（复用适配器实例，避免重复初始化APM）
    _adapter_cache: dict[str, object] = {}

    # 告警阈值配置（默认值）
    _alert_thresholds = {
        "fps_threshold": 50.0,  # FPS阈值（降低以便更容易触发）
        "memory_threshold_mb": 100.0,  # 内存阈值(MB)（降低以便更容易触发）
        "cpu_threshold_percent": 50.0,  # CPU阈值(%（降低以便更容易触发）)
        "battery_threshold_temp": 35.0,  # 电池温度阈值(°C)（降低以便更容易触发）
    }

    # 告警冷却期记录（避免重复告警）{alert_key: last_trigger_time}
    _alert_cooldown: dict[str, float] = {}  # 存储上次触发时间戳
    _alert_cooldown_seconds: int = 30  # 冷却期30秒 {}

    # 每个会话的告警阈值配置 {session_id: {threshold_key: value}}
    _session_alert_thresholds: dict[int, dict[str, float]] = {}

    @staticmethod
    def scan_devices() -> List[Device]:
        """扫描可用设备

        扫描并返回所有已连接的 Android 和 iOS 设备。
        使用桌面层的设备适配器进行设备连接和信息获取。

        在无设备环境（如 CI/E2E 测试）中返回空列表。

        Returns:
            设备列表
        """
        logger.info("[设备扫描] scan_devices 开始执行...")
        logger.info("[设备扫描] 导入桌面层模块...")
        try:
            from insight_aitest.platform.services.device_common import Devices, Platform
            from insight_aitest.platform.services.device_adapters.device_adapters import (
                DeviceAdapterFactory,
            )

            logger.info("[设备扫描] 桌面层模块导入成功")
        except ImportError as e:
            logger.warning(f"[设备扫描] 桌面层模块不可用: {e}，返回空设备列表")
            return []

        logger.info("[设备扫描] 开始扫描设备...")
        devices = []

        try:
            # 获取当前连接的设备
            logger.info("[设备扫描] 创建 Devices 实例...")
            devices_detector = Devices()
            logger.info("[设备扫描] 调用 getDevices()...")
            device_list = devices_detector.getDevices()

            logger.info(f"[设备扫描] 检测到 {len(device_list)} 个设备字符串: {device_list}")

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
                                model=device_info.model,
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
    async def start_session(
        device_id: str,
        app_package: str,
        platform: str = "android",
        sampling_interval: int = 1000,
        alert_thresholds: dict = None,
        project_id: int = None,
    ) -> Session:
        """开始监控会话

        Args:
            device_id: 设备ID
            app_package: 应用包名
            platform: 平台类型 ('android' 或 'ios')
            sampling_interval: 采样间隔（毫秒），默认1000ms
            alert_thresholds: 告警阈值配置，格式：{fps: float, memory: float, cpu: float, temperature: float}

        Returns:
            创建的会话对象
        """
        db = DatabaseManager.default()
        session = db.create_session(
            device_id,
            app_package,
            platform=platform,
            sampling_interval=sampling_interval,
            project_id=project_id,
        )

        # 存储会话的告警阈值配置
        if alert_thresholds:
            DeviceManager._session_alert_thresholds[session.id] = {
                "fps_threshold": alert_thresholds.get("fps", 50.0),
                "memory_threshold_mb": alert_thresholds.get("memory", 500.0),
                "cpu_threshold_percent": alert_thresholds.get("cpu", 80.0),
                "battery_threshold_temp": alert_thresholds.get("temperature", 45.0),
            }
            logger.info(
                f"会话 {session.id} 使用自定义告警阈值: {DeviceManager._session_alert_thresholds[session.id]}"
            )
        else:
            # 使用默认阈值
            DeviceManager._session_alert_thresholds[session.id] = {
                "fps_threshold": 50.0,
                "memory_threshold_mb": 100.0,
                "cpu_threshold_percent": 50.0,
                "battery_threshold_temp": 35.0,
            }
            logger.info(
                f"会话 {session.id} 使用默认告警阈值: {DeviceManager._session_alert_thresholds[session.id]}"
            )

        # 创建取消令牌
        DeviceManager._cancel_tokens[session.id] = asyncio.Event()

        logger.info(f"开始监控会话: {session.id}, 采样间隔: {sampling_interval}ms")
        return session

    @staticmethod
    async def stop_session(session_id: int) -> None:
        """停止监控会话

        Args:
            session_id: 会话ID
        """
        db = DatabaseManager.default()
        db.update_session(
            session_id,
            status="stopped",
            end_time=datetime.now().isoformat(),
        )

        # 设置取消令牌，停止数据采集
        if session_id in DeviceManager._cancel_tokens:
            DeviceManager._cancel_tokens[session_id].set()
            del DeviceManager._cancel_tokens[session_id]
            logger.info(f"已设置取消令牌: session={session_id}")

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
        from insight_aitest.platform.services.device_common import Platform

        # 获取会话信息
        db = DatabaseManager.default()
        session = db.get_session(session_id)

        if not session:
            logger.error(f"会话不存在: {session_id}")
            return

        logger.info(
            f"开始流式推送监控数据: session={session_id}, device={session.device_id}, app={session.app_package}, sampling_interval={session.sampling_interval}ms"
        )

        # 导入核心层的设备适配器，直接使用采集方法
        from insight_aitest.platform.services.device_adapters.device_adapters import (
            DeviceAdapterFactory,
        )

        # 生成适配器缓存键
        adapter_key = f"{session.device_id}_{session.platform}"

        try:
            # 检查适配器缓存，复用已有实例
            adapter = DeviceManager._adapter_cache.get(adapter_key)

            if adapter is None:
                # 创建新的设备适配器
                platform = Platform.ANDROID if session.platform == "android" else Platform.IOS
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

                # 缓存适配器实例（供后续复用）
                DeviceManager._adapter_cache[adapter_key] = adapter
                logger.info(f"设备适配器已创建并缓存: {adapter_key}")
            else:
                logger.info(f"复用缓存的设备适配器: {adapter_key}")

            logger.info("设备适配器已就绪，开始数据采集")

            # 获取取消令牌
            cancel_event = DeviceManager._cancel_tokens.get(session_id)

            try:
                while True:
                    # 检查取消令牌，如果已设置则停止数据采集
                    if cancel_event and cancel_event.is_set():
                        logger.info(f"检测到停止信号，结束数据采集: session={session_id}")
                        break

                    # 检查会话状态，如果已停止则结束数据采集
                    current_session = db.get_session(session_id)
                    if current_session and current_session.status == SessionStatus.STOPPED:
                        logger.info(f"会话已停止，结束数据采集: session={session_id}")
                        break

                    try:
                        # 计时开始：测量单次采集总耗时
                        collection_start = time.time()

                        # 并行采集所有指标（优化性能，避免串行等待）
                        # 使用 asyncio.gather 并行执行独立的采集任务
                        async def collect_all_metrics():
                            """并行采集所有性能指标"""
                            metrics_data = MetricsData(timestamp=datetime.now())

                            # 定义各个采集任务
                            async def collect_fps_task():
                                try:
                                    fps_start = time.time()
                                    # 在线程池中执行阻塞的采集操作
                                    loop = asyncio.get_running_loop()
                                    fps_data = await loop.run_in_executor(
                                        None, adapter.collect_fps, session.app_package
                                    )
                                    if fps_data:
                                        metrics_data.fps = float(fps_data.get("fps", 0))
                                    fps_elapsed = (time.time() - fps_start) * 1000
                                    logger.debug(f"[性能] FPS采集耗时: {fps_elapsed:.0f}ms")
                                except Exception as e:
                                    logger.debug(f"FPS采集失败: {e}")

                            async def collect_memory_task():
                                try:
                                    mem_start = time.time()
                                    loop = asyncio.get_running_loop()
                                    memory_data = await loop.run_in_executor(
                                        None, adapter.collect_memory, session.app_package
                                    )
                                    if memory_data:
                                        if session.platform == "ios":
                                            metrics_data.memory = float(
                                                memory_data.get("used_mb", 0)
                                            )
                                        else:
                                            metrics_data.memory = float(
                                                memory_data.get("totalPass", 0)
                                            )
                                    mem_elapsed = (time.time() - mem_start) * 1000
                                    logger.debug(f"[性能] 内存采集耗时: {mem_elapsed:.0f}ms")
                                except Exception as e:
                                    logger.debug(f"内存采集失败: {e}")

                            async def collect_cpu_task():
                                try:
                                    cpu_start = time.time()
                                    loop = asyncio.get_running_loop()
                                    cpu_data = await loop.run_in_executor(
                                        None, adapter.collect_cpu, session.app_package
                                    )
                                    if cpu_data:
                                        if session.platform == "ios":
                                            metrics_data.cpu = float(cpu_data.get("cpu_app", 0.0))
                                        else:
                                            metrics_data.cpu = float(
                                                cpu_data.get("appCpuRate", 0.0)
                                            )
                                    cpu_elapsed = (time.time() - cpu_start) * 1000
                                    logger.debug(f"[性能] CPU采集耗时: {cpu_elapsed:.0f}ms")
                                except Exception as e:
                                    logger.debug(f"CPU采集失败: {e}")

                            async def collect_network_task():
                                try:
                                    net_start = time.time()
                                    loop = asyncio.get_running_loop()
                                    network_data = await loop.run_in_executor(
                                        None, adapter.collect_network, session.app_package
                                    )
                                    if network_data:
                                        metrics_data.network_up = float(
                                            network_data.get("upFlow", 0.0)
                                        )
                                        metrics_data.network_down = float(
                                            network_data.get("downFlow", 0.0)
                                        )
                                    net_elapsed = (time.time() - net_start) * 1000
                                    logger.debug(f"[性能] 网络采集耗时: {net_elapsed:.0f}ms")
                                except Exception as e:
                                    logger.debug(f"网络采集失败: {e}")

                            async def collect_battery_task():
                                try:
                                    bat_start = time.time()
                                    loop = asyncio.get_running_loop()
                                    battery_data = await loop.run_in_executor(
                                        None, adapter.collect_battery
                                    )
                                    if battery_data:
                                        metrics_data.battery = float(battery_data.get("level", 0))
                                        metrics_data.temperature = float(
                                            battery_data.get("temperature", 0.0)
                                        )
                                    bat_elapsed = (time.time() - bat_start) * 1000
                                    logger.debug(f"[性能] 电池采集耗时: {bat_elapsed:.0f}ms")
                                except Exception as e:
                                    logger.debug(f"电池采集失败: {e}")

                            # 并行执行所有采集任务
                            await asyncio.gather(
                                collect_fps_task(),
                                collect_memory_task(),
                                collect_cpu_task(),
                                collect_network_task(),
                                collect_battery_task(),
                                return_exceptions=True,
                            )

                            return metrics_data

                        # 执行并行采集
                        metrics_data = await collect_all_metrics()

                        # 计算总采集耗时
                        total_elapsed = (time.time() - collection_start) * 1000
                        logger.info(
                            f"[性能] 并行采集总耗时: {total_elapsed:.0f}ms (目标: {session.sampling_interval}ms)"
                        )

                        # 检查是否至少有一个指标采集成功
                        has_data = any(
                            [
                                metrics_data.fps is not None,
                                metrics_data.memory is not None,
                                metrics_data.cpu is not None,
                                metrics_data.network_up is not None,
                                metrics_data.network_down is not None,
                                metrics_data.battery is not None,
                            ]
                        )

                        if has_data:
                            logger.debug(
                                f"数据采集成功: CPU={metrics_data.cpu:.1f}%, "
                                f"Memory={metrics_data.memory:.1f}MB, "
                                f"FPS={metrics_data.fps:.0f}"
                            )

                            # 保存到数据库（修复测试报告无数据问题）
                            try:
                                db.save_metrics(session_id, metrics_data)
                            except Exception as e:
                                logger.error(f"保存指标数据失败: {e}")

                            # 执行告警检测
                            triggered_alerts = []
                            try:
                                triggered_alerts = DeviceManager._check_and_save_alerts(
                                    db,
                                    session_id,
                                    session.device_id,
                                    session.app_package,
                                    metrics_data,
                                )
                            except Exception as e:
                                logger.error(f"告警检测失败: {e}")

                            # 先推送告警数据（如果有）
                            if triggered_alerts:
                                # 为每个告警创建一个特殊的MetricsData对象
                                # 使用is_alert标志和alert_data字段
                                for alert in triggered_alerts:
                                    # 创建告警数据对象
                                    alert_metrics = MetricsData(
                                        timestamp=metrics_data.timestamp,
                                        fps=metrics_data.fps,
                                        cpu=metrics_data.cpu,
                                        memory=metrics_data.memory,
                                        network_up=metrics_data.network_up,
                                        network_down=metrics_data.network_down,
                                        battery=metrics_data.battery,
                                        temperature=metrics_data.temperature,
                                        # 添加告警相关字段
                                        is_alert=True,
                                        alert_data=alert,
                                    )
                                    yield alert_metrics
                                    logger.info(f"推送告警到前端: {alert['content']}")

                            # 然后推送正常的指标数据
                            yield metrics_data
                        else:
                            logger.warning(
                                f"所有指标采集均失败: {session.device_id}/{session.app_package}"
                            )

                    except Exception as e:
                        logger.error(f"数据采集异常: {e}", exc_info=True)

                    # 使用会话配置的采样间隔（毫秒转换为秒）
                    sleep_seconds = session.sampling_interval / 1000
                    logger.debug(
                        f"使用采样间隔: {session.sampling_interval}ms, sleep: {sleep_seconds}s"
                    )
                    await asyncio.sleep(sleep_seconds)

            except asyncio.CancelledError:
                logger.info(f"流式推送已取消: session={session_id}")
            finally:
                # 清理适配器资源
                if adapter:
                    adapter.cleanup()
                # 从缓存中移除适配器
                if adapter_key in DeviceManager._adapter_cache:
                    del DeviceManager._adapter_cache[adapter_key]
                    logger.info(f"已从缓存移除设备适配器: {adapter_key}")
                logger.info(f"设备适配器资源已清理: session={session_id}")

        except Exception as e:
            logger.error(f"流式推送异常: {e}", exc_info=True)
            raise

    @staticmethod
    def _check_and_save_alerts(
        db: DatabaseManager, session_id: int, device_id: str, app_package: str, metrics: MetricsData
    ) -> list:
        """检查并保存告警

        根据阈值配置检测性能异常，并保存告警到数据库。
        使用会话级别的告警阈值配置，而不是全局默认值。

        Args:
            db: 数据库管理器
            session_id: 会话ID
            device_id: 设备ID
            app_package: 应用包名
            metrics: 指标数据

        Returns:
            触发的告警列表，每个告警包含：id, time, level, content
        """
        current_time = time.time()
        cooldown_seconds = DeviceManager._alert_cooldown_seconds

        # 获取会话级别的告警阈值（优先使用自定义阈值，否则使用默认值）
        thresholds = DeviceManager._session_alert_thresholds.get(
            session_id, DeviceManager._alert_thresholds
        )

        # 调试日志：记录当前指标值和阈值
        logger.debug(
            f"[告警检测] Session {session_id}: FPS={metrics.fps}, Memory={metrics.memory}MB, CPU={metrics.cpu}%, Temp={metrics.temperature}°C"
        )
        logger.debug(
            f"[告警检测] 阈值: FPS<{thresholds['fps_threshold']}, Memory>{thresholds['memory_threshold_mb']}MB, CPU>{thresholds['cpu_threshold_percent']}%, Temp>{thresholds['battery_threshold_temp']}°C"
        )

        alerts_to_save = []

        # 检测 FPS 低
        if metrics.fps is not None and metrics.fps < thresholds["fps_threshold"]:
            alert_key = f"low_fps_{session_id}"
            last_trigger = DeviceManager._alert_cooldown.get(alert_key, 0)

            if current_time - last_trigger >= cooldown_seconds:
                alerts_to_save.append(
                    {
                        "alert_type": "low_fps",
                        "metric_name": "FPS",
                        "current_value": metrics.fps,
                        "threshold_value": thresholds["fps_threshold"],
                        "severity": "warning" if metrics.fps >= 20 else "critical",
                        "description": f'FPS过低: {metrics.fps:.1f} < {thresholds["fps_threshold"]}',
                    }
                )
                DeviceManager._alert_cooldown[alert_key] = current_time
                logger.info(f"触发告警: FPS过低 {metrics.fps:.1f}")

        # 检测内存高
        if metrics.memory is not None and metrics.memory > thresholds["memory_threshold_mb"]:
            alert_key = f"high_memory_{session_id}"
            last_trigger = DeviceManager._alert_cooldown.get(alert_key, 0)

            if current_time - last_trigger >= cooldown_seconds:
                alerts_to_save.append(
                    {
                        "alert_type": "high_memory",
                        "metric_name": "Memory",
                        "current_value": metrics.memory,
                        "threshold_value": thresholds["memory_threshold_mb"],
                        "severity": "warning",
                        "description": f'内存过高: {metrics.memory:.1f}MB > {thresholds["memory_threshold_mb"]}MB',
                    }
                )
                DeviceManager._alert_cooldown[alert_key] = current_time
                logger.info(f"触发告警: 内存过高 {metrics.memory:.1f}MB")

        # 检测CPU高
        if metrics.cpu is not None and metrics.cpu > thresholds["cpu_threshold_percent"]:
            alert_key = f"high_cpu_{session_id}"
            last_trigger = DeviceManager._alert_cooldown.get(alert_key, 0)

            if current_time - last_trigger >= cooldown_seconds:
                alerts_to_save.append(
                    {
                        "alert_type": "high_cpu",
                        "metric_name": "CPU",
                        "current_value": metrics.cpu,
                        "threshold_value": thresholds["cpu_threshold_percent"],
                        "severity": "warning" if metrics.cpu < 90 else "critical",
                        "description": f'CPU过高: {metrics.cpu:.1f}% > {thresholds["cpu_threshold_percent"]}%',
                    }
                )
                DeviceManager._alert_cooldown[alert_key] = current_time
                logger.info(f"触发告警: CPU过高 {metrics.cpu:.1f}%")

        # 检测电池温度高
        if (
            metrics.temperature is not None
            and metrics.temperature > thresholds["battery_threshold_temp"]
        ):
            alert_key = f"high_temp_{session_id}"
            last_trigger = DeviceManager._alert_cooldown.get(alert_key, 0)

            if current_time - last_trigger >= cooldown_seconds:
                alerts_to_save.append(
                    {
                        "alert_type": "high_temperature",
                        "metric_name": "Temperature",
                        "current_value": metrics.temperature,
                        "threshold_value": thresholds["battery_threshold_temp"],
                        "severity": "warning",
                        "description": f'电池温度过高: {metrics.temperature:.1f}°C > {thresholds["battery_threshold_temp"]}°C',
                    }
                )
                DeviceManager._alert_cooldown[alert_key] = current_time
                logger.info(f"触发告警: 电池温度过高 {metrics.temperature:.1f}°C")

        # 保存所有触发的告警
        logger.debug(f"[告警检测] 本次检测到 {len(alerts_to_save)} 个告警需要保存")

        # 构建返回给前端的告警列表
        triggered_alerts = []

        for alert in alerts_to_save:
            try:
                alert_id = db.save_alert(session_id, alert)
                logger.info(f"[告警保存] 成功保存告警 ID={alert_id}: {alert['description']}")

                # 添加到返回列表，格式化为前端需要的格式
                level = "严重" if alert["severity"] == "critical" else "警告"
                triggered_alerts.append(
                    {
                        "id": alert_id,
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "level": level,
                        "content": alert["description"],
                    }
                )
            except Exception as e:
                logger.error(f"[告警保存] 失败: {e}, 告警内容: {alert}")

        if len(alerts_to_save) == 0:
            logger.debug("[告警检测] 未触发任何告警")

        return triggered_alerts
