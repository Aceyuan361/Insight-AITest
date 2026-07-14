# -*- coding: utf-8 -*-
"""
监控器基类
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class BaseMonitor(ABC):
    """设备监控器基类

    所有设备监控器（Android/iOS）都应继承此类并实现抽象方法。

    Attributes:
        device_id: 设备唯一标识符
        _is_monitoring: 是否正在监控
    """

    def __init__(self, device_id: str):
        """初始化监控器

        Args:
            device_id: 设备ID
        """
        self.device_id = device_id
        self._is_monitoring = False

    @abstractmethod
    def connect(self) -> bool:
        """连接设备

        Returns:
            bool: 连接是否成功
        """
        pass

    @abstractmethod
    def disconnect(self):
        """断开设备连接"""
        pass

    @abstractmethod
    def collect_cpu(self, package_name: str) -> Optional[Dict[str, Any]]:
        """采集CPU数据

        Args:
            package_name: 应用包名

        Returns:
            CPU数据字典，如果采集失败返回None
        """
        pass

    @abstractmethod
    def collect_memory(self, package_name: str) -> Optional[Dict[str, Any]]:
        """采集内存数据

        Args:
            package_name: 应用包名

        Returns:
            内存数据字典，如果采集失败返回None
        """
        pass

    @abstractmethod
    def collect_fps(self, package_name: str) -> Optional[Dict[str, Any]]:
        """采集FPS数据

        Args:
            package_name: 应用包名

        Returns:
            FPS数据字典，如果采集失败返回None
        """
        pass

    @abstractmethod
    def collect_network(self, package_name: str) -> Optional[Dict[str, Any]]:
        """采集网络数据

        Args:
            package_name: 应用包名

        Returns:
            网络数据字典，如果采集失败返回None
        """
        pass

    @abstractmethod
    def collect_battery(self) -> Optional[Dict[str, Any]]:
        """采集电池数据

        Returns:
            电池数据字典，如果采集失败返回None
        """
        pass

    def is_connected(self) -> bool:
        """检查是否已连接

        Returns:
            bool: 是否已连接设备
        """
        return self._is_monitoring
