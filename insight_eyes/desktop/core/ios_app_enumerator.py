# -*- coding: utf-8 -*-
"""
iOS应用枚举器（骨架实现）
负责枚举 iOS 设备上安装的应用

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License

Author: Aceyuan361
"""

from typing import List, Optional
from logzero import logger

from .models import AppInfo, AppStatus
from abc import ABC, abstractmethod


# 复制定义基类以避免循环导入
# TODO: 考虑将 BaseAppEnumerator 移到单独的 base.py 文件中
class BaseAppEnumerator(ABC):
    """应用枚举器基类"""

    def __init__(self, device_id: str):
        self.device_id = device_id
        self._cached_apps: List[AppInfo] = []

    @abstractmethod
    def enumerate_apps(self, include_system_apps: bool = False) -> List[AppInfo]:
        pass

    @abstractmethod
    def get_running_apps(self) -> List[AppInfo]:
        pass

    @abstractmethod
    def get_app_info(self, package_name: str) -> Optional[AppInfo]:
        pass


class IOSAppEnumerator(BaseAppEnumerator):
    """
    iOS应用枚举器（骨架实现）
    注意：当前为骨架实现，所有方法返回空值或默认值
    TODO: 实现通过 libimobiledevice 或其他方式获取iOS应用信息
    """

    def __init__(self, device_id: str):
        """
        初始化iOS应用枚举器

        Args:
            device_id: iOS设备UDID
        """
        super().__init__(device_id)
        logger.info(f"iOS应用枚举器初始化（骨架）: {self.device_id}")

    def enumerate_apps(self, include_system_apps: bool = False) -> List[AppInfo]:
        """
        枚举iOS设备上的所有应用（骨架实现）

        Args:
            include_system_apps: 是否包含系统应用

        Returns:
            List[AppInfo]: 应用信息列表（骨架：返回空列表）
        """
        logger.warning("enumerate_apps: 骨架实现，返回空列表")
        return []

    def get_running_apps(self) -> List[AppInfo]:
        """
        获取正在运行的iOS应用（骨架实现）

        Returns:
            List[AppInfo]: 运行中的应用列表（骨架：返回空列表）
        """
        logger.warning("get_running_apps: 骨架实现，返回空列表")
        return []

    def get_app_info(self, package_name: str) -> Optional[AppInfo]:
        """
        获取iOS应用详细信息（骨架实现）

        Args:
            package_name: Bundle ID

        Returns:
            AppInfo: 应用信息（骨架：返回None）
        """
        logger.warning(f"get_app_info: 骨架实现，返回None: {package_name}")
        return None
