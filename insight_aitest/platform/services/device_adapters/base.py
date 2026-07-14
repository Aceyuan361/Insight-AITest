# -*- coding: utf-8 -*-
"""
设备适配器基类

BaseDeviceAdapter 定义所有设备适配器必须实现的统一接口。
抽取到独立文件以打破 device_adapters.py 与 ios_device_adapter.py 之间的循环导入。
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from .models import DeviceInfo  # noqa: F401
from .models import Platform, DeviceStatus  # noqa: F401


class BaseDeviceAdapter(ABC):
    """
    设备适配器基类
    定义所有设备适配器必须实现的接口
    """

    def __init__(self, device_id: str):
        """
        初始化设备适配器

        Args:
            device_id: 设备ID
        """
        self.device_id = device_id
        self._device_info: Optional[DeviceInfo] = None

    @abstractmethod
    def connect(self) -> bool:
        """
        连接设备

        Returns:
            bool: 是否连接成功
        """
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """
        断开设备连接

        Returns:
            bool: 是否断开成功
        """
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """
        检查设备是否连接

        Returns:
            bool: 是否已连接
        """
        pass

    @abstractmethod
    def get_device_info(self) -> Optional[DeviceInfo]:
        """
        获取设备信息

        Returns:
            DeviceInfo: 设备信息，获取失败返回None
        """
        pass

    @abstractmethod
    def execute_command(self, command: str, timeout: int = 30) -> str:
        """
        在设备上执行命令

        Args:
            command: 要执行的命令
            timeout: 超时时间（秒）

        Returns:
            str: 命令输出
        """
        pass

    @abstractmethod
    def install_app(self, app_path: str) -> bool:
        """
        安装应用

        Args:
            app_path: 应用文件路径

        Returns:
            bool: 是否安装成功
        """
        pass

    @abstractmethod
    def uninstall_app(self, package_name: str) -> bool:
        """
        卸载应用

        Args:
            package_name: 包名

        Returns:
            bool: 是否卸载成功
        """
        pass

    @abstractmethod
    def start_app(self, package_name: str, activity: str = None) -> bool:
        """
        启动应用

        Args:
            package_name: 包名
            activity: Activity名称（Android）

        Returns:
            bool: 是否启动成功
        """
        pass

    @abstractmethod
    def stop_app(self, package_name: str) -> bool:
        """
        停止应用

        Args:
            package_name: 包名

        Returns:
            bool: 是否停止成功
        """
        pass

    def get_battery_level(self) -> int:
        """
        获取电池电量

        Returns:
            int: 电池电量百分比
        """
        return 100

    def get_device_temperature(self) -> float:
        """
        获取设备温度

        Returns:
            float: 温度（摄氏度）
        """
        return 0.0

    def get_network_type(self) -> str:
        """
        获取网络类型

        Returns:
            str: 网络类型（4G/5G/Wi-Fi/Unknown）
        """
        return "Unknown"

    # ========== 性能指标采集接口 ==========

    def collect_fps(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        采集FPS数据

        Args:
            package_name: 应用包名

        Returns:
            dict: FPS数据，包含fps, jank, big_jank, ftime_avg等字段
        """
        return None

    def collect_memory(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        采集内存数据

        Args:
            package_name: 应用包名

        Returns:
            dict: 内存数据，包含totalPass, nativePass, dalvikPass等字段（单位KB）
        """
        return None

    def collect_cpu(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        采集CPU数据

        Args:
            package_name: 应用包名

        Returns:
            dict: CPU数据，包含appCpuRate, sysCpuRate等字段（百分比）
        """
        return None

    def collect_network(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        采集网络数据

        Args:
            package_name: 应用包名

        Returns:
            dict: 网络数据，包含upFlow, downFlow等字段（KB/s）
        """
        return None

    def collect_battery(self) -> Optional[Dict[str, Any]]:
        """
        采集电池数据

        Returns:
            dict: 电池数据，包含level, temperature等字段
        """
        return None
