# -*- coding: utf-8 -*-
"""
iOS设备适配器
"""

import threading
import time
from typing import Optional, Dict, Any
from logzero import logger

from .models import DeviceInfo, Platform, DeviceStatus, AppInfo
from abc import ABC, abstractmethod
from insight_eyes.public.ios.exceptions import (
    DeviceNotTrustedError,
    DeviceConnectionError,
    PMD3NotInstalledError,
    DeviceNotFoundError,
    DeveloperModeNotEnabledError
)


# 复制定义基类以避免循环导入
# TODO: 考虑将 BaseDeviceAdapter 移到单独的 base.py 文件中

# ========== 自动重连配置 ==========
RECONNECT_MAX_RETRIES = 3  # 最大重试次数
RECONNECT_INITIAL_DELAY = 1.0  # 初始重试延迟（秒）
RECONNECT_MAX_DELAY = 16.0  # 最大重试延迟（秒）
RECONNECT_BACKOFF_MULTIPLIER = 2.0  # 退避倍数

# 不应重试的异常类型（用户需手动干预）
NO_RETRY_EXCEPTIONS = (
    DeviceNotTrustedError,
    PMD3NotInstalledError,
    DeveloperModeNotEnabledError,
)
class BaseDeviceAdapter(ABC):
    """设备适配器基类"""

    def __init__(self, device_id: str):
        self.device_id = device_id
        self._device_info: Optional[DeviceInfo] = None

    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        pass

    @abstractmethod
    def get_device_info(self) -> Optional[DeviceInfo]:
        pass

    @abstractmethod
    def execute_command(self, command: str, timeout: int = 30) -> str:
        pass

    @abstractmethod
    def install_app(self, app_path: str) -> bool:
        pass

    @abstractmethod
    def uninstall_app(self, package_name: str) -> bool:
        pass

    @abstractmethod
    def start_app(self, package_name: str, activity: str = None) -> bool:
        pass

    @abstractmethod
    def stop_app(self, package_name: str) -> bool:
        pass

    def collect_fps(self, package_name: str) -> Optional[Dict[str, Any]]:
        return None

    def collect_memory(self, package_name: str) -> Optional[Dict[str, Any]]:
        return None

    def collect_cpu(self, package_name: str) -> Optional[Dict[str, Any]]:
        return None

    def collect_network(self, package_name: str) -> Optional[Dict[str, Any]]:
        return None

    def collect_battery(self) -> Optional[Dict[str, Any]]:
        return None


class IOSDeviceAdapter(BaseDeviceAdapter):
    """
    iOS设备适配器
    通过 pymobiledevice3 与 iOS 设备通信
    """

    def __init__(self, device_id: str):
        """
        初始化iOS设备适配器

        Args:
            device_id: iOS设备UDID
        """
        super().__init__(device_id)
        self._lockdown_client = None
        self._connected = False
        self._apm = None  # IOSAPM 实例缓存
        self._apm_lock = threading.Lock()  # APM 实例锁
        self.platform = Platform.IOS  # 平台标识

        # 重连机制相关
        self._retry_count = 0  # 当前重试次数
        self._last_error = None  # 最后一次错误
        self._connecting = False  # 是否正在连接中（防止重连并发）
        self._connect_lock = threading.Lock()  # 连接锁

    def connect(self) -> bool:
        """
        连接iOS设备（带自动重试机制）

        Returns:
            bool: 是否连接成功

        Raises:
            PMD3NotInstalledError: pymobiledevice3 未安装
            DeviceNotTrustedError: 设备未信任
            DeviceConnectionError: 连接失败（重试次数用尽后）
        """
        # 使用锁防止并发连接
        with self._connect_lock:
            # 如果正在连接，等待连接完成
            if self._connecting:
                logger.debug(f"iOS设备正在连接中，等待: {self.device_id}")
                # 简单等待：最多等待连接完成（可优化为使用条件变量）
                return self._connected

            self._connecting = True

        try:
            # 首先检查 pymobiledevice3 版本
            if not self._check_pymobiledevice3_version():
                logger.error("pymobiledevice3 版本检查失败")
                return False

            # 尝试连接，带重试机制
            return self._connect_with_retry()
        finally:
            with self._connect_lock:
                self._connecting = False

    def _check_pymobiledevice3_version(self) -> bool:
        """
        检查 pymobiledevice3 版本是否满足要求

        Returns:
            bool: 版本是否满足要求
        """
        try:
            import pkg_resources
            required_version = "4.0.0"
            current_version = pkg_resources.get_distribution("pymobiledevice3").version

            from packaging import version
            if version.parse(current_version) < version.parse(required_version):
                logger.error(
                    f"pymobiledevice3 版本过低: {current_version} < {required_version}，"
                    f"请运行: pip install -U pymobiledevice3"
                )
                return False

            logger.info(f"pymobiledevice3 版本检查通过: {current_version}")
            return True

        except Exception as e:
            logger.warning(f"pymobiledevice3 版本检查失败（将继续尝试）: {e}")
            return True  # 检查失败不阻止连接

    def _connect_with_retry(self) -> bool:
        """
        带重试机制的连接实现（指数退避策略）

        Returns:
            bool: 是否连接成功
        """
        delay = RECONNECT_INITIAL_DELAY

        for attempt in range(RECONNECT_MAX_RETRIES + 1):
            self._retry_count = attempt

            try:
                success = self._attempt_connect()
                if success:
                    if attempt > 0:
                        logger.info(f"iOS设备重连成功: {self.device_id} (第 {attempt} 次重试)")
                    return True

            except NO_RETRY_EXCEPTIONS as e:
                # 不应重试的异常，直接抛出
                logger.error(f"iOS设备连接失败（需手动干预）: {type(e).__name__}: {e}")
                self._last_error = e
                raise

            except Exception as e:
                self._last_error = e
                logger.warning(
                    f"iOS设备连接失败 (尝试 {attempt + 1}/{RECONNECT_MAX_RETRIES + 1}): {e}"
                )

                # 如果还有重试机会，等待后重试
                if attempt < RECONNECT_MAX_RETRIES:
                    logger.info(f"等待 {delay:.1f} 秒后重试...")
                    time.sleep(delay)
                    delay = min(delay * RECONNECT_BACKOFF_MULTIPLIER, RECONNECT_MAX_DELAY)
                else:
                    logger.error(f"iOS设备连接失败（已达最大重试次数）: {self.device_id}")
                    error = DeviceConnectionError(self.device_id, f"已重试 {RECONNECT_MAX_RETRIES} 次均失败")
                    raise error

        return False

    def _attempt_connect(self) -> bool:
        """
        单次连接尝试

        Returns:
            bool: 是否连接成功

        Raises:
            PMD3NotInstalledError: pymobiledevice3 未安装
            DeviceNotFoundError: 设备未找到
            DeviceNotTrustedError: 设备未信任
            Exception: 其他连接错误
        """
        # 检查 pymobiledevice3 是否安装
        try:
            from pymobiledevice3 import usbmux
        except ImportError:
            error = PMD3NotInstalledError()
            logger.error(str(error))
            logger.error(error.get_install_command())
            raise error

        # 验证设备存在
        devices = usbmux.list_devices()
        device_udids = [d.serial for d in devices]

        if self.device_id not in device_udids:
            error = DeviceNotFoundError(self.device_id)
            logger.error(str(error))
            raise error

        # 临时方案：暂时不创建实际的 Lockdown 连接
        # TODO: 实现 pymobiledevice3 的正确连接方式
        # 当前 pymobiledevice3 版本的 API 较复杂，需要 LockdownServiceProvider
        self._connected = True
        logger.info(f"iOS设备连接成功（临时方案）: {self.device_id}")
        return True

    def disconnect(self) -> bool:
        """
        断开iOS设备连接

        Returns:
            bool: 是否断开成功
        """
        try:
            if self._lockdown_client:
                # pymobiledevice3 的 LockdownClient 通常会自动管理连接
                # 这里我们只需标记为未连接
                self._lockdown_client = None

            self._connected = False
            logger.info(f"iOS设备已断开: {self.device_id}")
            return True

        except Exception as e:
            logger.error(f"断开iOS设备连接异常: {e}")
            return False

    def is_connected(self) -> bool:
        """
        检查iOS设备是否连接

        Returns:
            bool: 是否已连接
        """
        try:
            if not self._connected:
                return False

            # 如果有 lockdown_client，尝试验证连接
            if self._lockdown_client:
                self._lockdown_client.get_value()

            return True

        except Exception as e:
            logger.debug(f"检查iOS设备连接状态失败: {e}")
            self._connected = False
            return False

    def is_healthy(self) -> bool:
        """
        检查连接是否健康（增强版连接检查）

        Returns:
            bool: 连接是否健康
        """
        try:
            # 基本连接状态
            if not self.is_connected():
                return False

            # 尝试获取设备信息来验证连接可用性
            device_info = self.get_device_info()
            return device_info is not None

        except Exception as e:
            logger.debug(f"iOS设备健康检查失败: {e}")
            return False

    def get_device_info(self) -> Optional[DeviceInfo]:
        """
        获取iOS设备详细信息

        Returns:
            DeviceInfo: 设备信息
        """
        try:
            # 临时方案：如果没有 LockdownClient，返回基本信息
            if not self._lockdown_client:
                device_name = f'🍎 iOS Device ({self.device_id[:8]})'
                device_info = DeviceInfo(
                    device_id=self.device_id,
                    name=device_name,
                    platform=Platform.IOS,
                    model='iPhone',
                    os_version='iOS',
                    serial_number=self.device_id,
                    manufacturer='Apple',
                    status=DeviceStatus.CONNECTED
                )
                logger.info(f"获取 iOS 设备信息（临时方案）: {device_name}")
                return device_info

            # 完整方案：通过 LockdownClient 获取详细信息
            device_info_dict = self._lockdown_client.get_value()

            # 解析设备信息
            model = device_info_dict.get('ProductType', 'Unknown')
            manufacturer = "Apple"  # iOS 设备都是 Apple
            serial = device_info_dict.get('SerialNumber', self.device_id)
            os_version = device_info_dict.get('ProductVersion', 'Unknown')
            device_name = device_info_dict.get('DeviceName', f'iOS Device {self.device_id[:8]}')

            # 构建设备信息
            device_info = DeviceInfo(
                device_id=self.device_id,
                name=device_name,
                platform=Platform.IOS,
                model=model,
                os_version=f"iOS {os_version}",
                serial_number=serial,
                manufacturer=manufacturer,
                status=DeviceStatus.CONNECTED
            )

            # 获取电池电量
            battery_level = self.get_battery_level()
            if battery_level is not None:
                device_info.battery_level = battery_level

            # 获取网络类型
            device_info.network_type = self.get_network_type()

            # 获取温度
            device_info.temperature = self.get_device_temperature()

            self._device_info = device_info
            return device_info

        except Exception as e:
            logger.error(f"获取iOS设备信息失败: {e}")
            return None

    def check_device_ready(self) -> bool:
        """
        检查设备是否准备好进行监控

        Returns:
            bool: 设备是否准备好
        """
        try:
            if not self.is_connected():
                return False

            # 检查设备是否被信任
            if self._lockdown_client:
                # 尝试获取设备信息
                self._lockdown_client.get_value()
                return True

            return False

        except Exception as e:
            logger.warning(f"检查iOS设备准备状态失败: {e}")
            return False

    def execute_command(self, command: str, timeout: int = 30) -> str:
        """
        在iOS设备上执行命令（iOS 限制较多，此方法功能有限）

        Args:
            command: 命令
            timeout: 超时时间（秒）

        Returns:
            str: 命令输出
        """
        logger.warning("iOS 设备不支持直接执行命令")
        return ""

    def install_app(self, app_path: str) -> bool:
        """
        安装应用（需要未来实现）

        Args:
            app_path: 应用文件路径（.ipa 文件）

        Returns:
            bool: 是否安装成功
        """
        logger.warning("iOS 应用安装功能尚未实现")
        return False

    def uninstall_app(self, package_name: str) -> bool:
        """
        卸载应用（需要未来实现）

        Args:
            package_name: Bundle ID

        Returns:
            bool: 是否卸载成功
        """
        logger.warning("iOS 应用卸载功能尚未实现")
        return False

    def start_app(self, package_name: str, activity: str = None) -> bool:
        """
        启动应用（需要未来实现）

        Args:
            package_name: Bundle ID
            activity: 忽略（iOS 不需要 Activity）

        Returns:
            bool: 是否启动成功
        """
        logger.warning("iOS 应用启动功能尚未实现")
        return False

    def stop_app(self, package_name: str) -> bool:
        """
        停止应用（需要未来实现）

        Args:
            package_name: Bundle ID

        Returns:
            bool: 是否停止成功
        """
        logger.warning("iOS 应用停止功能尚未实现")
        return False

    def get_battery_level(self) -> int:
        """
        获取电池电量（需要未来实现）

        Returns:
            int: 电池电量百分比
        """
        # TODO: 使用 pymobiledevice3 获取电池信息
        return 100

    def get_device_temperature(self) -> float:
        """
        获取设备温度（iOS 限制访问）

        Returns:
            float: 温度（摄氏度）
        """
        # iOS 不允许第三方应用访问温度传感器
        return 0.0

    def get_network_type(self) -> str:
        """
        获取网络类型（需要未来实现）

        Returns:
            str: 网络类型（4G/5G/Wi-Fi/Unknown）
        """
        # TODO: 使用 pymobiledevice3 获取网络信息
        return "Unknown"

    # ========== 性能指标采集接口（需要未来实现）==========

    def collect_fps(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        采集FPS数据（需要未来实现）

        Args:
            package_name: Bundle ID

        Returns:
            dict: FPS数据
        """
        logger.warning("iOS FPS 采集功能尚未实现")
        return None

    def collect_memory(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        采集内存数据

        Args:
            package_name: Bundle ID

        Returns:
            dict: 内存数据

        Raises:
            ProcessNotFoundError: 如果应用进程不存在
        """
        # 通过 APM 采集数据
        # 注意：_get_apm() 会抛出 ProcessNotFoundError 如果进程不存在
        apm = self._get_apm(package_name)
        if apm:
            return apm.collectMemory()
        return None

    def collect_cpu(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        采集CPU数据

        Args:
            package_name: Bundle ID

        Returns:
            dict: CPU数据

        Raises:
            ProcessNotFoundError: 如果应用进程不存在
        """
        # 通过 APM 采集数据
        # 注意：_get_apm() 会抛出 ProcessNotFoundError 如果进程不存在
        apm = self._get_apm(package_name)
        if apm:
            return apm.collectCpu()
        return None

    def collect_network(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        采集网络数据（需要未来实现）

        Args:
            package_name: Bundle ID

        Returns:
            dict: 网络数据
        """
        logger.warning("iOS 网络采集功能尚未实现")
        return None

    def collect_battery(self) -> Optional[Dict[str, Any]]:
        """
        采集电池数据（需要未来实现）

        Returns:
            dict: 电池数据
        """
        logger.warning("iOS 电池采集功能尚未实现")
        return None

    # ========== APM 管理方法 ==========

    def _get_apm(self, bundle_name: str):
        """
        获取或初始化 IOSAPM 实例 - 线程安全版本

        使用双重检查锁定模式（Double-Checked Locking）：
        1. 快速检查（无锁）：如果已有匹配的 APM 实例，直接返回
        2. 锁保护检查：在锁内再次检查，防止竞态条件
        3. 创建新实例：仅在需要时创建，避免重复初始化

        Args:
            bundle_name: 应用 Bundle ID（使用 "__battery__" 表示电池采集）

        Returns:
            IOSAPM: APM 实例
        """
        # 特殊处理：电池采集不需要包名，使用现有的 APM 实例（如果有）
        if bundle_name == "__battery__":
            with self._apm_lock:
                # 如果已有 APM 实例，直接复用（不需要包名）
                if self._apm:
                    return self._apm
                # 如果没有 APM 实例，创建一个不带包名的实例用于电池采集
                from insight_eyes.public.ios.ios_apm import IOSAPM
                logger.debug(f"[APM管理] 创建电池专用 APM 实例: device={self.device_id}")
                self._apm = IOSAPM("", self.device_id)
                return self._apm

        # 快速路径：如果已有匹配的 APM 实例，直接返回（无锁，利用 Python GIL）
        if self._apm is not None and self._apm.bundle_name == bundle_name:
            return self._apm

        # 慢速路径：需要创建或更换 APM，使用锁保护
        with self._apm_lock:
            # 双重检查：可能在等待锁时已被其他线程创建
            if self._apm is not None and self._apm.bundle_name == bundle_name:
                return self._apm

            from insight_eyes.public.ios.ios_apm import IOSAPM

            # 如果之前的 APM 存在且包名不同，先停止旧实例
            if self._apm is not None:
                try:
                    logger.debug(f"[APM管理] 停止旧 APM 实例: {self._apm.bundle_name}")
                    self._apm.stop()
                except Exception as e:
                    logger.warning(f"[APM管理] 停止旧 APM 失败: {e}")

            # 创建新的 APM 实例
            logger.debug(f"[APM管理] 创建新 APM 实例: bundle={bundle_name}, device={self.device_id}")
            self._apm = IOSAPM(bundle_name, self.device_id)
            # 启动 APM（添加异常处理）
            try:
                self._apm.start()
                logger.debug(f"[APM管理] APM 启动成功: {bundle_name}")
            except Exception as start_error:
                logger.error(f"[APM管理] APM 启动失败: {type(start_error).__name__}: {start_error}")
                # 清理失败的 APM 实例
                self._apm = None
                raise

        return self._apm

    def cleanup(self):
        """
        清理设备适配器资源（增强版，确保资源正确释放）
        """
        logger.info(f"开始清理iOS设备适配器: {self.device_id}")

        # 使用锁确保清理过程线程安全
        with self._connect_lock:
            try:
                # 1. 停止 APM 实例
                if self._apm:
                    try:
                        logger.debug(f"停止 IOSAPM: {self._apm.bundle_name}")
                        self._apm.stop()
                        self._apm = None
                    except Exception as e:
                        logger.warning(f"停止 IOSAPM 失败（继续清理）: {e}")

                # 2. 断开设备连接
                try:
                    self.disconnect()
                except Exception as e:
                    logger.warning(f"断开设备连接失败（继续清理）: {e}")

                # 3. 重置所有状态（即使出错也确保重置）
                self._connected = False
                self._lockdown_client = None
                self._retry_count = 0
                self._last_error = None
                self._connecting = False

                logger.info(f"iOS设备适配器已清理: {self.device_id}")

            except Exception as e:
                logger.error(f"清理iOS设备适配器时出错: {e}")
                # 即使出错也要确保基本状态被重置
                self._connected = False
                self._lockdown_client = None
