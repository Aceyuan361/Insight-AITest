# -*- coding: utf-8 -*-
"""
设备管理器
负责设备检测、连接、App枚举、状态监控

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License

Author: Aceyuan361
"""

import time
from typing import List, Optional, Dict, Callable, Set, Any
from datetime import datetime
from threading import RLock
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread, QMutex
from logzero import logger

from .models import (
    DeviceInfo, Platform, DeviceStatus, AppInfo,
    DeviceFilter, AppFilter, DeviceChangeEvent, DeviceChangeType, MonitoringConfig,
    ReconnectConfig, ReconnectState
)
from .device_adapters import DeviceAdapterFactory, BaseDeviceAdapter
from .app_enumerator import AppEnumeratorFactory, BaseAppEnumerator


class DeviceScannerThread(QThread):
    """
    设备扫描线程
    定期扫描新设备并检测设备断开
    """

    # 信号定义
    device_discovered = pyqtSignal(DeviceInfo)  # 发现新设备
    device_lost = pyqtSignal(str)  # 设备断开（设备ID）

    def __init__(self, scan_interval: int = 5):
        """
        初始化设备扫描线程

        Args:
            scan_interval: 扫描间隔（秒）
        """
        super().__init__()
        self._scan_interval = scan_interval
        self._running = False
        self._known_devices: Set[str] = set()
        self._mutex = QMutex()

    def start_scan(self):
        """开始扫描"""
        self._running = True
        self._known_devices.clear()
        self.start()

    def stop_scan(self):
        """
        停止扫描 - 修复版（崩溃修复）

        修复内容：
        - 使用 wait(5000) 超时，避免无限等待
        - 如果线程仍在运行，记录警告但不阻塞
        """
        self._running = False

        # 等待线程结束，最多 5 秒
        if not self.wait(5000):
            logger.warning("设备扫描线程未能在 5 秒内停止")
        else:
            logger.debug("设备扫描线程已停止")

    def run(self):
        """
        扫描线程主循环
        定期检测设备变化

        修复内容（崩溃修复）：
        - 使用短 sleep (100ms) 循环，可快速响应停止信号
        - 避免使用 time.sleep() 阻塞
        """
        from insight_eyes.public.common import Devices

        while self._running:
            try:
                # 获取当前连接的设备
                devices_detector = Devices()
                device_list = devices_detector.getDevices()

                current_devices = set()

                # 处理每个设备
                for device_str in device_list:
                    # 解析设备信息
                    if device_str.startswith("Android "):
                        device_id = device_str[8:].strip()
                        platform = Platform.ANDROID
                    elif device_str.startswith("iOS "):
                        # iOS: "iOS iPhone (udid)"
                        if '(' in device_str and ')' in device_str:
                            device_id = device_str.split('(')[1].split(')')[0].strip()
                        else:
                            device_id = device_str[4:].strip()
                        platform = Platform.IOS
                    else:
                        continue

                    current_devices.add(device_id)

                    # 检查是否是新设备
                    if device_id not in self._known_devices:
                        # 创建设备信息
                        device_info = self._create_device_info(device_id, platform, device_str)
                        if device_info:
                            self.device_discovered.emit(device_info)
                            self._known_devices.add(device_id)
                            logger.info(f"发现新设备: {device_info.name} ({device_info.platform.value})")

                # 检查是否有设备断开
                lost_devices = self._known_devices - current_devices
                for device_id in lost_devices:
                    self.device_lost.emit(device_id)
                    self._known_devices.discard(device_id)
                    logger.info(f"设备断开: {device_id}")

            except Exception as e:
                logger.error(f"设备扫描异常: {e}")

            # 可中断的等待：使用 100ms 的短 sleep，循环直到达到扫描间隔
            # 这样可以在 100ms 内响应停止信号
            elapsed = 0
            while elapsed < self._scan_interval * 1000 and self._running:
                self.msleep(100)  # PyQt6 的可中断 sleep
                elapsed += 100

    def _create_device_info(self, device_id: str, platform: Platform, device_str: str) -> Optional[DeviceInfo]:
        """
        创建设备信息

        Args:
            device_id: 设备ID
            platform: 平台类型
            device_str: 设备字符串

        Returns:
            DeviceInfo: 设备信息
        """
        try:
            logger.debug(f"正在创建设备信息: {device_id} ({platform.value})")

            # 创建适配器
            adapter = DeviceAdapterFactory.create_adapter(device_id, platform)
            if not adapter:
                logger.warning(f"无法为设备 {device_id} 创建适配器")
                return None

            # 连接设备
            if not adapter.connect():
                logger.warning(f"无法连接到设备 {device_id}，请检查设备状态")
                return None

            # 获取设备信息
            device_info = adapter.get_device_info()
            if device_info:
                device_info.status = DeviceStatus.CONNECTED
                logger.info(f"成功获取设备信息: {device_info.name} ({device_id})")
            else:
                logger.warning(f"无法获取设备信息: {device_id}")
            return device_info

        except Exception as e:
            logger.error(f"创建设备信息失败 [{device_id}]: {e}", exc_info=True)
            return None


class DeviceMonitorThread(QThread):
    """
    设备监控线程
    监控指定设备的状态变化（电池、温度、网络等）
    """

    # 信号定义
    device_updated = pyqtSignal(DeviceInfo)  # 设备信息更新
    app_list_updated = pyqtSignal(str, list)  # 应用列表更新（设备ID, 应用列表）
    monitoring_error = pyqtSignal(str, str)  # 监控错误（设备ID, 错误信息）

    def __init__(self, device_id: str, platform: Platform, monitor_interval: int = 10):
        """
        初始化设备监控线程

        Args:
            device_id: 设备ID
            platform: 平台类型
            monitor_interval: 监控间隔（秒）
        """
        super().__init__()
        self.device_id = device_id
        self.platform = platform
        self._monitor_interval = monitor_interval
        self._running = False

        # 创建适配器和枚举器
        self._adapter = DeviceAdapterFactory.create_adapter(device_id, platform)
        self._enumerator = AppEnumeratorFactory.create_enumerator(device_id, platform)

    def start_monitor(self):
        """开始监控"""
        self._running = True
        self.start()

    def stop_monitor(self):
        """
        停止监控 - 修复版（崩溃修复）
        """
        self._running = False
        # 等待线程结束，最多 5 秒
        if not self.wait(5000):
            logger.warning(f"设备监控线程 {self.device_id} 未能在 5 秒内停止")
        else:
            logger.debug(f"设备监控线程 {self.device_id} 已停止")

    def run(self):
        """
        监控线程主循环
        定期更新设备状态

        修复内容（崩溃修复）：
        - 使用短 sleep (100ms) 循环，可快速响应停止信号
        - 避免使用 time.sleep() 阻塞
        """
        while self._running:
            try:
                # 检查设备是否还在连接
                if not self._adapter or not self._adapter.is_connected():
                    self.monitoring_error.emit(self.device_id, "设备已断开连接")
                    break

                # 更新设备信息
                device_info = self._adapter.get_device_info()
                if device_info:
                    self.device_updated.emit(device_info)

                # 更新应用列表（每隔几次循环更新一次，减少开销）
                # 这里简化为每次都更新，实际可以优化

            except Exception as e:
                logger.error(f"设备监控异常: {self.device_id}, {e}")
                self.monitoring_error.emit(self.device_id, str(e))

            # 可中断的等待：使用 100ms 的短 sleep，循环直到达到监控间隔
            elapsed = 0
            while elapsed < self._monitor_interval * 1000 and self._running:
                self.msleep(100)
                elapsed += 100

    def refresh_apps(self) -> List[AppInfo]:
        """
        刷新应用列表

        Returns:
            List[AppInfo]: 应用列表
        """
        try:
            if not self._enumerator:
                return []

            # 获取所有应用列表
            apps = self._enumerator.enumerate_apps(include_system_apps=False)

            # 获取运行中的应用，并更新运行状态
            try:
                running_apps = self._enumerator.get_running_apps()
                running_packages = {app.package_name for app in running_apps}

                # 更新应用的运行状态
                for app in apps:
                    if app.package_name in running_packages:
                        # 找到对应的运行中的应用，复制其运行信息
                        running_app = next((a for a in running_apps if a.package_name == app.package_name), None)
                        if running_app:
                            app.is_running = True
                            app.pid = running_app.pid
                            app.status = running_app.status
            except Exception as e:
                logger.warning(f"获取运行中的应用失败: {e}")

            self.app_list_updated.emit(self.device_id, apps)
            return apps

        except Exception as e:
            logger.error(f"刷新应用列表失败: {e}")
            return []

    def get_running_apps(self) -> List[AppInfo]:
        """
        获取运行中的应用

        Returns:
            List[AppInfo]: 运行中的应用列表
        """
        try:
            if not self._enumerator:
                return []

            return self._enumerator.get_running_apps()

        except Exception as e:
            logger.error(f"获取运行中的应用失败: {e}")
            return []


class DeviceHeartbeatThread(QThread):
    """
    设备心跳检测线程
    定期检查设备连接状态，检测设备意外断开
    """

    # 信号定义
    heartbeat_lost = pyqtSignal(str)  # 设备心跳丢失（设备ID）
    heartbeat_restored = pyqtSignal(str)  # 设备心跳恢复（设备ID）

    def __init__(self, device_id: str, adapter: BaseDeviceAdapter,
                 heartbeat_interval: int = 5, heartbeat_timeout: int = 15):
        """
        初始化设备心跳检测线程

        Args:
            device_id: 设备ID
            adapter: 设备适配器
            heartbeat_interval: 心跳检测间隔（秒）
            heartbeat_timeout: 心跳超时时间（秒）
        """
        super().__init__()
        self.device_id = device_id
        self._adapter = adapter
        self._heartbeat_interval = heartbeat_interval
        self._heartbeat_timeout = heartbeat_timeout
        self._running = False
        self._last_heartbeat_time = None

    def start_heartbeat(self):
        """开始心跳检测"""
        self._running = True
        self._last_heartbeat_time = time.time()
        self.start()

    def stop_heartbeat(self):
        """
        停止心跳检测 - 修复版（崩溃修复）
        """
        self._running = False
        # 等待线程结束，最多 5 秒
        if not self.wait(5000):
            logger.warning(f"设备心跳线程 {self.device_id} 未能在 5 秒内停止")
        else:
            logger.debug(f"设备心跳线程 {self.device_id} 已停止")

    def update_heartbeat(self):
        """更新心跳时间"""
        self._last_heartbeat_time = time.time()

    def run(self):
        """
        心跳检测线程主循环
        定期检查设备连接状态

        修复内容（崩溃修复）：
        - 使用短 sleep (100ms) 循环，可快速响应停止信号
        - 避免使用 time.sleep() 阻塞
        """
        was_connected = True

        while self._running:
            try:
                # 检查设备连接状态
                if self._adapter and self._adapter.is_connected():
                    # 连接正常，更新心跳
                    self.update_heartbeat()

                    if not was_connected:
                        # 心跳恢复
                        self.heartbeat_restored.emit(self.device_id)
                        logger.info(f"设备心跳恢复: {self.device_id}")
                        was_connected = True
                else:
                    # 连接断开
                    current_time = time.time()

                    # 检查是否超时
                    if self._last_heartbeat_time and (current_time - self._last_heartbeat_time) > self._heartbeat_timeout:
                        if was_connected:
                            # 心跳丢失
                            self.heartbeat_lost.emit(self.device_id)
                            logger.warning(f"设备心跳丢失: {self.device_id}")
                            was_connected = False

            except Exception as e:
                logger.error(f"设备心跳检测异常: {self.device_id}, {e}")
                self.heartbeat_lost.emit(self.device_id)

            # 可中断的等待：使用 100ms 的短 sleep，循环直到达到心跳间隔
            elapsed = 0
            while elapsed < self._heartbeat_interval * 1000 and self._running:
                self.msleep(100)
                elapsed += 100


class DeviceReconnectThread(QThread):
    """
    设备重连线程
    使用指数退避策略自动重连设备
    """

    # 信号定义
    reconnect_started = pyqtSignal(str)  # 开始重连（设备ID）
    reconnect_success = pyqtSignal(str, int)  # 重连成功（设备ID，重试次数）
    reconnect_failed = pyqtSignal(str, str, int)  # 重连失败（设备ID，错误信息，重试次数）
    reconnect_cancelled = pyqtSignal(str)  # 重连取消（设备ID）
    reconnect_progress = pyqtSignal(str, int, int)  # 重连进度（设备ID，当前重试次数，最大重试次数）

    def __init__(self, device_id: str, platform: Platform,
                 reconnect_config: ReconnectConfig = None):
        """
        初始化设备重连线程

        Args:
            device_id: 设备ID
            platform: 平台类型
            reconnect_config: 重连配置
        """
        super().__init__()
        self.device_id = device_id
        self.platform = platform
        self._config = reconnect_config or ReconnectConfig()
        self._state = ReconnectState(device_id=device_id)
        self._running = False
        self._mutex = QMutex()

    def start_reconnect(self):
        """开始重连"""
        self._running = True
        self._state.reset()
        self._state.current_interval = self._config.initial_retry_interval
        self.start()

    def stop_reconnect(self):
        """停止重连 - 修复版（崩溃修复 P0-4）"""
        self._mutex.lock()
        self._state.cancelled = True
        self._running = False
        self._mutex.unlock()
        # 添加超时避免无限阻塞（最多等待 5 秒）
        if not self.wait(5000):
            logger.warning(f"设备重连线程 {self.device_id} 未能在 5 秒内停止")
        self.reconnect_cancelled.emit(self.device_id)
        logger.info(f"设备重连已取消: {self.device_id}")

    def is_reconnecting(self) -> bool:
        """是否正在重连"""
        return self._running and not self._state.cancelled

    def get_retry_count(self) -> int:
        """获取当前重试次数"""
        return self._state.retry_count

    def get_state(self) -> ReconnectState:
        """获取重连状态"""
        return self._state

    def run(self):
        """
        重连线程主循环
        使用指数退避策略进行重连
        """
        self.reconnect_started.emit(self.device_id)
        logger.info(f"开始重连设备: {self.device_id}")

        while self._running:
            # 检查是否已取消
            self._mutex.lock()
            if self._state.cancelled:
                self._mutex.unlock()
                break

            # 检查是否超过最大重试次数
            if self._config.max_retry_count > 0 and self._state.retry_count >= self._config.max_retry_count:
                self._mutex.unlock()
                error_msg = f"达到最大重试次数 ({self._config.max_retry_count})"
                self.reconnect_failed.emit(self.device_id, error_msg, self._state.retry_count)
                logger.error(f"设备重连失败: {self.device_id}, {error_msg}")
                self._running = False
                break

            self._mutex.unlock()

            # 发送进度信号
            self.reconnect_progress.emit(
                self.device_id,
                self._state.retry_count + 1,
                self._config.max_retry_count if self._config.max_retry_count > 0 else 999
            )

            # 尝试重连
            try:
                # 创建适配器
                adapter = DeviceAdapterFactory.create_adapter(self.device_id, self.platform)
                if not adapter:
                    raise Exception("无法创建设备适配器")

                # 尝试连接
                if adapter.connect():
                    # 连接成功
                    self.reconnect_success.emit(self.device_id, self._state.retry_count + 1)
                    logger.info(f"设备重连成功: {self.device_id}, 重试次数: {self._state.retry_count + 1}")
                    self._running = False
                    break
                else:
                    raise Exception("连接失败")

            except Exception as e:
                # 连接失败，继续重试
                error_msg = str(e)
                logger.warning(f"设备重连尝试失败: {self.device_id}, 错误: {error_msg}, 重试次数: {self._state.retry_count + 1}")

                # 更新重试状态（指数退避）
                self._mutex.lock()
                self._state.increment_retry(
                    self._config.max_retry_interval,
                    self._config.retry_multiplier
                )
                self._mutex.unlock()

            # 等待下一次重试（使用当前间隔）
            wait_time = self._state.current_interval
            logger.info(f"等待 {wait_time} 秒后进行下一次重连: {self.device_id}")

            # 可中断的等待：使用 100ms 的短 sleep，循环直到达到重试间隔
            # 这样可以在 100ms 内响应停止信号（修复 P0-4）
            elapsed_ms = 0
            wait_time_ms = int(wait_time * 1000)  # 转换为毫秒
            while elapsed_ms < wait_time_ms and self._running:
                # 每次最多 sleep 100ms，确保能快速响应停止信号
                sleep_duration = min(100, wait_time_ms - elapsed_ms)
                self.msleep(int(sleep_duration))
                elapsed_ms += sleep_duration

                # 检查是否已取消
                self._mutex.lock()
                if self._state.cancelled:
                    self._mutex.unlock()
                    break
                self._mutex.unlock()


class DeviceManager(QObject):
    """
    设备管理器
    负责设备的连接、断开、监控和应用枚举
    """

    # 信号定义
    device_discovered = pyqtSignal(DeviceInfo)  # 发现新设备
    device_lost = pyqtSignal(str)  # 设备断开（设备ID）
    device_updated = pyqtSignal(DeviceInfo)  # 设备信息更新
    app_list_updated = pyqtSignal(str, list)  # 应用列表更新（设备ID, 应用列表）
    monitoring_started = pyqtSignal(str)  # 监控开始（设备ID）
    monitoring_stopped = pyqtSignal(str)  # 监控停止（设备ID）
    error_occurred = pyqtSignal(str, str)  # 错误发生（设备ID, 错误信息）

    # 重连相关信号
    reconnect_started = pyqtSignal(str)  # 开始重连（设备ID）
    reconnect_success = pyqtSignal(str, int)  # 重连成功（设备ID，重试次数）
    reconnect_failed = pyqtSignal(str, str, int)  # 重连失败（设备ID，错误信息，重试次数）
    reconnect_cancelled = pyqtSignal(str)  # 重连取消（设备ID）
    reconnect_progress = pyqtSignal(str, int, int)  # 重连进度（设备ID，当前次数，最大次数）
    device_disconnected = pyqtSignal(str)  # 设备意外断开（设备ID）

    def __init__(self, reconnect_config: ReconnectConfig = None):
        """
        初始化设备管理器

        Args:
            reconnect_config: 重连配置
        """
        super().__init__()

        # 设备存储
        self._devices: Dict[str, DeviceInfo] = {}
        self._device_monitors: Dict[str, DeviceMonitorThread] = {}
        self._device_heartbeats: Dict[str, DeviceHeartbeatThread] = {}
        self._device_reconnects: Dict[str, DeviceReconnectThread] = {}
        self._device_mutex = RLock()

        # 重连配置
        self._reconnect_config = reconnect_config or ReconnectConfig()

        # 设备扫描线程
        self._scanner_thread: Optional[DeviceScannerThread] = None

        # 连接扫描器信号
        self._init_scanner()

    def _init_scanner(self):
        """初始化设备扫描器"""
        self._scanner_thread = DeviceScannerThread(scan_interval=5)
        self._scanner_thread.device_discovered.connect(self._on_device_discovered)
        self._scanner_thread.device_lost.connect(self._on_device_lost)

    def start_scan(self):
        """开始扫描设备"""
        if self._scanner_thread and not self._scanner_thread.isRunning():
            self._scanner_thread.start_scan()
            logger.info("设备扫描已启动")

    def stop_scan(self):
        """停止扫描设备"""
        if self._scanner_thread and self._scanner_thread.isRunning():
            self._scanner_thread.stop_scan()
            logger.info("设备扫描已停止")

    def _on_device_discovered(self, device_info: DeviceInfo):
        """
        处理发现新设备事件

        Args:
            device_info: 设备信息
        """
        with self._device_mutex:
            self._devices[device_info.device_id] = device_info
            self.device_discovered.emit(device_info)

    def _on_device_lost(self, device_id: str):
        """
        处理设备断开事件

        Args:
            device_id: 设备ID
        """
        with self._device_mutex:
            # 停止监控
            if device_id in self._device_monitors:
                self.stop_monitoring(device_id)

            # 移除设备
            if device_id in self._devices:
                del self._devices[device_id]

            self.device_lost.emit(device_id)

    def get_devices(self, device_filter: Optional[DeviceFilter] = None) -> List[DeviceInfo]:
        """
        获取所有设备

        Args:
            device_filter: 设备过滤器（可选）

        Returns:
            List[DeviceInfo]: 设备列表
        """
        with self._device_mutex:
            devices = list(self._devices.values())

        # 应用过滤器
        if device_filter:
            devices = [d for d in devices if device_filter.matches(d)]

        return devices

    def get_device(self, device_id: str) -> Optional[DeviceInfo]:
        """
        获取指定设备信息

        Args:
            device_id: 设备ID

        Returns:
            DeviceInfo: 设备信息，未找到返回None
        """
        with self._device_mutex:
            return self._devices.get(device_id)

    def get_device_apps(self, device_id: str,
                       app_filter: Optional[AppFilter] = None,
                       force_refresh: bool = False) -> List[AppInfo]:
        """
        获取设备上的应用列表

        Args:
            device_id: 设备ID
            app_filter: 应用过滤器（可选）
            force_refresh: 是否强制刷新

        Returns:
            List[AppInfo]: 应用列表
        """
        device = self.get_device(device_id)
        if not device:
            return []

        # 如果需要刷新或者应用列表为空
        if force_refresh or not device.apps:
            self._refresh_device_apps(device_id)

        with self._device_mutex:
            apps = device.apps.copy()

        # 应用过滤器
        if app_filter:
            apps = [a for a in apps if app_filter.matches(a)]

        return apps

    def _refresh_device_apps(self, device_id: str) -> bool:
        """
        刷新设备应用列表

        Args:
            device_id: 设备ID

        Returns:
            bool: 是否成功
        """
        try:
            # 获取监控线程
            monitor = self._device_monitors.get(device_id)
            if not monitor:
                # 如果没有监控线程，创建一个临时的
                device = self.get_device(device_id)
                if not device:
                    return False

                enumerator = AppEnumeratorFactory.create_enumerator(device_id, device.platform)
                if not enumerator:
                    return False

                # 获取所有应用列表
                apps = enumerator.enumerate_apps(include_system_apps=False)

                # 获取运行中的应用，并更新运行状态
                try:
                    running_apps = enumerator.get_running_apps()
                    running_packages = {app.package_name for app in running_apps}

                    # 更新应用的运行状态
                    for app in apps:
                        if app.package_name in running_packages:
                            # 找到对应的运行中的应用，复制其运行信息
                            running_app = next((a for a in running_apps if a.package_name == app.package_name), None)
                            if running_app:
                                app.is_running = True
                                app.pid = running_app.pid
                                app.status = running_app.status
                except Exception as e:
                    logger.warning(f"获取运行中的应用失败: {e}")

                device.apps = apps
                return True

            # 使用监控线程刷新
            apps = monitor.refresh_apps()
            device = self.get_device(device_id)
            if device:
                device.apps = apps

            return True

        except Exception as e:
            logger.error(f"刷新设备应用列表失败: {e}")
            return False

    def monitor_device(self, device_id: str, auto_refresh_apps: bool = True) -> bool:
        """
        开始监控设备

        Args:
            device_id: 设备ID
            auto_refresh_apps: 是否自动刷新应用列表

        Returns:
            bool: 是否成功开始监控
        """
        with self._device_mutex:
            # 检查是否已经在监控
            if device_id in self._device_monitors:
                logger.warning(f"设备已在监控中: {device_id}")
                return True

            # 获取设备信息
            device = self._devices.get(device_id)
            if not device:
                logger.error(f"设备不存在: {device_id}")
                return False

            # 创建监控线程
            monitor = DeviceMonitorThread(device_id, device.platform, monitor_interval=10)
            monitor.device_updated.connect(self._on_device_updated)
            monitor.app_list_updated.connect(self._on_app_list_updated)
            monitor.monitoring_error.connect(self._on_monitoring_error)

            # 启动监控
            monitor.start_monitor()
            self._device_monitors[device_id] = monitor

            # 标记设备正在监控
            device.is_monitoring = True

            # 启动心跳检测
            if self._reconnect_config.enable_heartbeat:
                self._start_heartbeat(device_id)

            self.monitoring_started.emit(device_id)
            logger.info(f"开始监控设备: {device_id}")
            return True

    def stop_monitoring(self, device_id: str) -> bool:
        """
        停止监控设备

        Args:
            device_id: 设备ID

        Returns:
            bool: 是否成功停止监控
        """
        with self._device_mutex:
            monitor = self._device_monitors.get(device_id)
            if not monitor:
                logger.warning(f"设备未在监控中: {device_id}")
                return False

            # 停止监控线程
            monitor.stop_monitor()
            del self._device_monitors[device_id]

            # 停止心跳检测
            if device_id in self._device_heartbeats:
                self._stop_heartbeat(device_id)

            # 更新设备状态
            device = self._devices.get(device_id)
            if device:
                device.is_monitoring = False

            self.monitoring_stopped.emit(device_id)
            logger.info(f"停止监控设备: {device_id}")
            return True

    def is_monitoring(self, device_id: str) -> bool:
        """
        检查设备是否正在监控

        Args:
            device_id: 设备ID

        Returns:
            bool: 是否正在监控
        """
        with self._device_mutex:
            return device_id in self._device_monitors

    def _on_device_updated(self, device_info: DeviceInfo):
        """
        处理设备信息更新事件

        Args:
            device_info: 更新后的设备信息
        """
        with self._device_mutex:
            # 更新设备信息
            if device_info.device_id in self._devices:
                # 保留原有的应用列表
                old_apps = self._devices[device_info.device_id].apps
                device_info.apps = old_apps
                self._devices[device_info.device_id] = device_info

        self.device_updated.emit(device_info)

    def _on_app_list_updated(self, device_id: str, apps: List[AppInfo]):
        """
        处理应用列表更新事件

        Args:
            device_id: 设备ID
            apps: 应用列表
        """
        with self._device_mutex:
            if device_id in self._devices:
                self._devices[device_id].apps = apps

        self.app_list_updated.emit(device_id, apps)

    def _on_monitoring_error(self, device_id: str, error_msg: str):
        """
        处理监控错误事件

        Args:
            device_id: 设备ID
            error_msg: 错误信息
        """
        self.error_occurred.emit(device_id, error_msg)

    def search_devices(self, keyword: str) -> List[DeviceInfo]:
        """
        搜索设备

        Args:
            keyword: 搜索关键字（匹配设备名称或型号）

        Returns:
            List[DeviceInfo]: 匹配的设备列表
        """
        device_filter = DeviceFilter(search_text=keyword)
        return self.get_devices(device_filter)

    def search_apps(self, device_id: str, keyword: str,
                    running_only: bool = False) -> List[AppInfo]:
        """
        搜索设备上的应用

        Args:
            device_id: 设备ID
            keyword: 搜索关键字（匹配应用名称或包名）
            running_only: 是否只显示运行中的应用

        Returns:
            List[AppInfo]: 匹配的应用列表
        """
        app_filter = AppFilter(search_text=keyword, running_only=running_only)
        return self.get_device_apps(device_id, app_filter)

    def disconnect_device(self, device_id: str) -> bool:
        """
        断开设备连接

        Args:
            device_id: 设备ID

        Returns:
            bool: 是否成功断开
        """
        # 停止监控
        self.stop_monitoring(device_id)

        # 获取设备
        device = self.get_device(device_id)
        if not device:
            return False

        # 创建适配器并断开连接
        adapter = DeviceAdapterFactory.create_adapter(device_id, device.platform)
        if adapter:
            adapter.disconnect()

        # 从设备列表中移除
        with self._device_mutex:
            if device_id in self._devices:
                del self._devices[device_id]

        logger.info(f"设备已断开: {device_id}")
        return True

    def cleanup(self):
        """清理资源 - 修复版（方案3：优化清理顺序）"""
        logger.info("开始清理设备管理器资源")

        # ============ 方案3：正确的清理顺序 ============
        # 步骤 1：停止所有重连（最先停止，避免启动新线程）
        with self._device_mutex:
            for device_id in list(self._device_reconnects.keys()):
                logger.debug(f"停止重连: {device_id}")
                self.cancel_reconnect(device_id)

        # 步骤 2：停止所有心跳
        with self._device_mutex:
            for device_id in list(self._device_heartbeats.keys()):
                logger.debug(f"停止心跳: {device_id}")
                self._stop_heartbeat(device_id)

        # 步骤 3：停止所有监控
        with self._device_mutex:
            for device_id in list(self._device_monitors.keys()):
                logger.debug(f"停止监控: {device_id}")
                self.stop_monitoring(device_id)

        # 步骤 4：停止扫描（最后停止）
        self.stop_scan()

        # 步骤 5：断开扫描器信号连接
        if self._scanner_thread:
            try:
                self._scanner_thread.device_discovered.disconnect()
                self._scanner_thread.device_lost.disconnect()
            except Exception as e:
                logger.debug(f"断开扫描器信号时出错: {e}")

        # 步骤 6：清空设备列表
        with self._device_mutex:
            self._devices.clear()

        logger.info("设备管理器资源已清理")

    def get_monitoring_config(self, device_id: str) -> Optional[MonitoringConfig]:
        """
        获取监控配置

        Args:
            device_id: 设备ID

        Returns:
            MonitoringConfig: 监控配置
        """
        # 返回默认配置
        # 实际应用中可以从配置文件加载或让用户自定义
        return MonitoringConfig()

    def update_monitoring_config(self, device_id: str, config: MonitoringConfig) -> bool:
        """
        更新监控配置

        Args:
            device_id: 设备ID
            config: 新的监控配置

        Returns:
            bool: 是否成功更新
        """
        # 更新监控配置
        # 实际应用中需要保存到配置文件并应用到监控线程
        logger.info(f"更新监控配置: {device_id}")
        return True

    # ========== 重连相关方法 ==========

    def _start_heartbeat(self, device_id: str):
        """
        启动设备心跳检测

        Args:
            device_id: 设备ID
        """
        try:
            # 获取设备信息
            device = self._devices.get(device_id)
            if not device:
                return

            # 获取适配器
            adapter = DeviceAdapterFactory.create_adapter(device_id, device.platform)
            if not adapter:
                return

            # 创建心跳检测线程
            heartbeat = DeviceHeartbeatThread(
                device_id=device_id,
                adapter=adapter,
                heartbeat_interval=self._reconnect_config.heartbeat_interval,
                heartbeat_timeout=self._reconnect_config.heartbeat_timeout
            )

            # 连接信号
            heartbeat.heartbeat_lost.connect(self._on_heartbeat_lost)
            heartbeat.heartbeat_restored.connect(self._on_heartbeat_restored)

            # 启动心跳检测
            heartbeat.start_heartbeat()
            self._device_heartbeats[device_id] = heartbeat

            logger.info(f"启动设备心跳检测: {device_id}")

        except Exception as e:
            logger.error(f"启动心跳检测失败: {device_id}, {e}")

    def _stop_heartbeat(self, device_id: str):
        """
        停止设备心跳检测

        Args:
            device_id: 设备ID
        """
        if device_id in self._device_heartbeats:
            heartbeat = self._device_heartbeats[device_id]
            heartbeat.stop_heartbeat()
            del self._device_heartbeats[device_id]
            logger.info(f"停止设备心跳检测: {device_id}")

    def _on_heartbeat_lost(self, device_id: str):
        """
        处理心跳丢失事件

        Args:
            device_id: 设备ID
        """
        logger.warning(f"检测到设备心跳丢失: {device_id}")

        # 更新设备状态
        with self._device_mutex:
            device = self._devices.get(device_id)
            if device:
                device.status = DeviceStatus.RECONNECTING
                self.device_updated.emit(device)

        # 发送设备断开信号
        self.device_disconnected.emit(device_id)

        # 启动自动重连
        if self._reconnect_config.enable_auto_reconnect:
            self.start_reconnect(device_id)

    def _on_heartbeat_restored(self, device_id: str):
        """
        处理心跳恢复事件

        Args:
            device_id: 设备ID
        """
        logger.info(f"设备心跳已恢复: {device_id}")

        # 更新设备状态
        with self._device_mutex:
            device = self._devices.get(device_id)
            if device:
                device.status = DeviceStatus.CONNECTED
                self.device_updated.emit(device)

    def start_reconnect(self, device_id: str) -> bool:
        """
        开始重连设备

        Args:
            device_id: 设备ID

        Returns:
            bool: 是否成功开始重连
        """
        try:
            # 检查设备是否在重连中
            if device_id in self._device_reconnects and self._device_reconnects[device_id].is_reconnecting():
                logger.warning(f"设备已在重连中: {device_id}")
                return True

            # 获取设备信息
            device = self._devices.get(device_id)
            if not device:
                logger.error(f"设备不存在: {device_id}")
                return False

            # 创建重连线程
            reconnect_thread = DeviceReconnectThread(
                device_id=device_id,
                platform=device.platform,
                reconnect_config=self._reconnect_config
            )

            # 连接信号
            reconnect_thread.reconnect_started.connect(self._on_reconnect_started)
            reconnect_thread.reconnect_success.connect(self._on_reconnect_success)
            reconnect_thread.reconnect_failed.connect(self._on_reconnect_failed)
            reconnect_thread.reconnect_cancelled.connect(self._on_reconnect_cancelled)
            reconnect_thread.reconnect_progress.connect(self._on_reconnect_progress)

            # 启动重连
            reconnect_thread.start_reconnect()
            self._device_reconnects[device_id] = reconnect_thread

            logger.info(f"开始设备重连: {device_id}")
            return True

        except Exception as e:
            logger.error(f"启动设备重连失败: {device_id}, {e}")
            return False

    def cancel_reconnect(self, device_id: str) -> bool:
        """
        取消设备重连

        Args:
            device_id: 设备ID

        Returns:
            bool: 是否成功取消
        """
        if device_id in self._device_reconnects:
            reconnect_thread = self._device_reconnects[device_id]
            if reconnect_thread.is_reconnecting():
                reconnect_thread.stop_reconnect()
                logger.info(f"取消设备重连: {device_id}")
                return True
        return False

    def is_reconnecting(self, device_id: str) -> bool:
        """
        检查设备是否正在重连

        Args:
            device_id: 设备ID

        Returns:
            bool: 是否正在重连
        """
        if device_id in self._device_reconnects:
            return self._device_reconnects[device_id].is_reconnecting()
        return False

    def get_reconnect_state(self, device_id: str) -> Optional[ReconnectState]:
        """
        获取设备重连状态

        Args:
            device_id: 设备ID

        Returns:
            ReconnectState: 重连状态
        """
        if device_id in self._device_reconnects:
            return self._device_reconnects[device_id].get_state()
        return None

    def _on_reconnect_started(self, device_id: str):
        """
        处理重连开始事件

        Args:
            device_id: 设备ID
        """
        logger.info(f"设备重连已启动: {device_id}")

        # 更新设备状态
        with self._device_mutex:
            device = self._devices.get(device_id)
            if device:
                device.status = DeviceStatus.RECONNECTING
                self.device_updated.emit(device)

        # 转发信号
        self.reconnect_started.emit(device_id)

    def _on_reconnect_success(self, device_id: str, retry_count: int):
        """
        处理重连成功事件

        Args:
            device_id: 设备ID
            retry_count: 重试次数
        """
        logger.info(f"设备重连成功: {device_id}, 重试次数: {retry_count}")

        # 更新设备状态
        with self._device_mutex:
            device = self._devices.get(device_id)
            if device:
                device.status = DeviceStatus.CONNECTED
                self.device_updated.emit(device)

        # 重新启动心跳检测
        if device_id in self._device_monitors:
            self._start_heartbeat(device_id)

        # 清理重连线程
        if device_id in self._device_reconnects:
            del self._device_reconnects[device_id]

        # 转发信号
        self.reconnect_success.emit(device_id, retry_count)

    def _on_reconnect_failed(self, device_id: str, error_msg: str, retry_count: int):
        """
        处理重连失败事件

        Args:
            device_id: 设备ID
            error_msg: 错误信息
            retry_count: 重试次数
        """
        logger.error(f"设备重连失败: {device_id}, 错误: {error_msg}, 重试次数: {retry_count}")

        # 更新设备状态
        with self._device_mutex:
            device = self._devices.get(device_id)
            if device:
                device.status = DeviceStatus.OFFLINE
                self.device_updated.emit(device)

        # 清理重连线程
        if device_id in self._device_reconnects:
            del self._device_reconnects[device_id]

        # 转发信号
        self.reconnect_failed.emit(device_id, error_msg, retry_count)

    def _on_reconnect_cancelled(self, device_id: str):
        """
        处理重连取消事件

        Args:
            device_id: 设备ID
        """
        logger.info(f"设备重连已取消: {device_id}")

        # 更新设备状态
        with self._device_mutex:
            device = self._devices.get(device_id)
            if device:
                device.status = DeviceStatus.OFFLINE
                self.device_updated.emit(device)

        # 清理重连线程
        if device_id in self._device_reconnects:
            del self._device_reconnects[device_id]

        # 转发信号
        self.reconnect_cancelled.emit(device_id)

    def _on_reconnect_progress(self, device_id: str, current: int, max_count: int):
        """
        处理重连进度事件

        Args:
            device_id: 设备ID
            current: 当前重试次数
            max_count: 最大重试次数
        """
        logger.debug(f"设备重连进度: {device_id}, {current}/{max_count}")

        # 转发信号
        self.reconnect_progress.emit(device_id, current, max_count)

    def set_reconnect_config(self, config: ReconnectConfig):
        """
        设置重连配置

        Args:
            config: 重连配置
        """
        self._reconnect_config = config
        logger.info(f"更新重连配置: {config.to_dict()}")

    def get_reconnect_config(self) -> ReconnectConfig:
        """
        获取重连配置

        Returns:
            ReconnectConfig: 重连配置
        """
        return self._reconnect_config

    # ========== 统一数据采集接口 ==========

    def collect_metrics(self, device_id: str, package_name: str) -> Optional[Dict[str, Any]]:
        """
        统一数据采集接口
        采集指定设备和应用的性能指标

        Args:
            device_id: 设备ID
            package_name: 应用包名/Bundle ID

        Returns:
            dict: 包含所有性能指标的字典
            {
                'fps': {...},  # FPS数据
                'memory': {...},  # 内存数据
                'cpu': {...},  # CPU数据
                'network': {...},  # 网络数据
                'battery': {...}  # 电池数据
            }
            如果采集失败返回None
        """
        try:
            # 获取设备信息
            device = self.get_device(device_id)
            if not device:
                logger.error(f"设备不存在: {device_id}")
                return None

            # 创建设备适配器
            adapter = DeviceAdapterFactory.create_adapter(device_id, device.platform)
            if not adapter:
                logger.error(f"无法创建设备适配器: {device_id}")
                return None

            # 检查设备连接
            if not adapter.is_connected():
                logger.warning(f"设备未连接: {device_id}")
                # 尝试重新连接
                if not adapter.connect():
                    logger.error(f"设备连接失败: {device_id}")
                    return None

            # 采集所有指标
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'device_id': device_id,
                'package_name': package_name,
                'platform': device.platform.value,
                'fps': {},
                'memory': {},
                'cpu': {},
                'network': {},
                'battery': {}
            }

            # 采集FPS数据
            try:
                fps_data = adapter.collect_fps(package_name)
                if fps_data:
                    metrics['fps'] = fps_data
            except Exception as e:
                logger.warning(f"FPS采集失败: {e}")

            # 采集内存数据
            try:
                memory_data = adapter.collect_memory(package_name)
                if memory_data:
                    metrics['memory'] = memory_data
            except Exception as e:
                logger.warning(f"内存采集失败: {e}")

            # 采集CPU数据
            try:
                cpu_data = adapter.collect_cpu(package_name)
                if cpu_data:
                    metrics['cpu'] = cpu_data
            except Exception as e:
                logger.warning(f"CPU采集失败: {e}")

            # 采集网络数据
            try:
                network_data = adapter.collect_network(package_name)
                if network_data:
                    metrics['network'] = network_data
            except Exception as e:
                logger.warning(f"网络采集失败: {e}")

            # 采集电池数据
            try:
                battery_data = adapter.collect_battery()
                if battery_data:
                    metrics['battery'] = battery_data
            except Exception as e:
                logger.warning(f"电池采集失败: {e}")

            # 检查是否至少有一个指标采集成功
            has_data = any([
                metrics['fps'],
                metrics['memory'],
                metrics['cpu'],
                metrics['network'],
                metrics['battery']
            ])

            if has_data:
                logger.debug(f"数据采集成功: {device_id}/{package_name}")
                return metrics
            else:
                logger.warning(f"所有指标采集均失败: {device_id}/{package_name}")
                return None

        except Exception as e:
            logger.error(f"采集指标数据异常: {e}", exc_info=True)
            return None

    def collect_metrics_batch(self, device_id: str, package_names: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        批量采集多个应用的性能指标

        Args:
            device_id: 设备ID
            package_names: 应用包名列表

        Returns:
            dict: {package_name: metrics_dict}
        """
        results = {}
        for package_name in package_names:
            results[package_name] = self.collect_metrics(device_id, package_name)
        return results
