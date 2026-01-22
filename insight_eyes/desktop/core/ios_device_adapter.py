# -*- coding: utf-8 -*-
"""
iOS设备适配器

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License

Author: Aceyuan361
"""

from typing import Optional, Dict, Any
from logzero import logger

from .models import DeviceInfo, Platform, DeviceStatus, AppInfo
from abc import ABC, abstractmethod


# 复制定义基类以避免循环导入
# TODO: 考虑将 BaseDeviceAdapter 移到单独的 base.py 文件中
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

    def connect(self) -> bool:
        """
        连接iOS设备

        Returns:
            bool: 是否连接成功
        """
        try:
            # 尝试导入 pymobiledevice3
            try:
                from pymobiledevice3.lockdown import LockdownClient
            except ImportError:
                logger.error("pymobiledevice3 未安装，无法连接 iOS 设备")
                logger.error("请运行: pip install pymobiledevice3")
                return False

            # 创建 LockdownClient 连接
            self._lockdown_client = LockdownClient(self.device_id)

            if self._lockdown_client:
                self._connected = True
                logger.info(f"iOS设备连接成功: {self.device_id}")
                return True
            else:
                logger.error(f"iOS设备连接失败: {self.device_id}")
                return False

        except Exception as e:
            logger.error(f"iOS设备连接异常: {e}")
            self._connected = False
            return False

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
            if not self._connected or not self._lockdown_client:
                return False

            # 尝试查询设备信息来验证连接
            self._lockdown_client.get_value()
            return True

        except Exception as e:
            logger.debug(f"检查iOS设备连接状态失败: {e}")
            self._connected = False
            return False

    def get_device_info(self) -> Optional[DeviceInfo]:
        """
        获取iOS设备详细信息

        Returns:
            DeviceInfo: 设备信息
        """
        try:
            if not self._lockdown_client:
                return None

            # 获取设备信息
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
        采集内存数据（需要未来实现）

        Args:
            package_name: Bundle ID

        Returns:
            dict: 内存数据
        """
        logger.warning("iOS 内存采集功能尚未实现")
        return None

    def collect_cpu(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        采集CPU数据（需要未来实现）

        Args:
            package_name: Bundle ID

        Returns:
            dict: CPU数据
        """
        logger.warning("iOS CPU 采集功能尚未实现")
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

    def cleanup(self):
        """
        清理设备适配器资源
        """
        logger.info(f"开始清理iOS设备适配器: {self.device_id}")

        try:
            self.disconnect()
            logger.info(f"iOS设备适配器已清理: {self.device_id}")

        except Exception as e:
            logger.error(f"清理iOS设备适配器时出错: {e}")
