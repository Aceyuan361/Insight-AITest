# -*- coding: utf-8 -*-
"""
iOS应用枚举器
负责枚举 iOS 设备上安装的应用
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
    iOS应用枚举器
    通过 pymobiledevice3 获取 iOS 设备上的应用信息
    """

    def __init__(self, device_id: str):
        """
        初始化iOS应用枚举器

        Args:
            device_id: iOS设备UDID
        """
        super().__init__(device_id)
        self._lockdown_client = None
        self._installation_proxy = None
        logger.info(f"iOS应用枚举器初始化: {self.device_id}")

        # 尝试初始化连接
        try:
            self._init_connection()
        except Exception as e:
            logger.warning(f"iOS应用枚举器初始化失败（将在首次使用时重试）: {e}")

    def _init_connection(self):
        """初始化 pymobiledevice3 连接"""
        try:
            from pymobiledevice3.lockdown import create_using_usbmux
            from pymobiledevice3.services.installation_proxy import InstallationProxyService

            # 使用 pymobiledevice3 7.x 的正确 API
            # create_using_usbmux() 会自动查找并连接设备
            lockdown = create_using_usbmux()

            # 验证连接的设备是否匹配
            connected_udid = lockdown.udid
            if connected_udid != self.device_id:
                logger.warning(f"连接的设备 ({connected_udid}) 与请求的设备 ({self.device_id}) 不匹配")
                # 如果只有一个设备，也可以继续使用
                logger.info(f"使用已连接的设备: {connected_udid}")

            # 创建 InstallationProxy 服务
            self._installation_proxy = InstallationProxyService(lockdown)
            logger.info(f"iOS应用枚举器连接成功: {self.device_id}")

        except Exception as e:
            logger.warning(f"初始化 iOS 连接失败: {e}")
            self._installation_proxy = None

    def enumerate_apps(self, include_system_apps: bool = False) -> List[AppInfo]:
        """
        枚举iOS设备上的所有应用

        Args:
            include_system_apps: 是否包含系统应用

        Returns:
            List[AppInfo]: 应用信息列表
        """
        try:
            # 如果连接未初始化，尝试初始化
            if self._installation_proxy is None:
                self._init_connection()

            if self._installation_proxy is None:
                logger.warning("无法连接到 iOS 设备，返回空列表")
                return []

            # 使用 pymobiledevice3 获取应用列表
            apps_dict = self._installation_proxy.get_apps()

            if not apps_dict:
                logger.warning("未获取到任何应用信息")
                return []

            apps = []
            skipped_system = 0
            for bundle_id, app_info in apps_dict.items():
                # 检查是否为系统应用
                is_system = app_info.get('ApplicationType', 'User') != 'User'

                # 如果不包含系统应用，跳过系统应用
                if not include_system_apps and is_system:
                    skipped_system += 1
                    continue

                # 获取应用显示名称
                display_name = app_info.get('CFBundleDisplayName', bundle_id)
                if not display_name:
                    display_name = app_info.get('CFBundleName', bundle_id)

                # 获取版本号
                version = app_info.get('CFBundleShortVersionString', None)
                if not version:
                    version = app_info.get('CFBundleVersion', None)

                # 创建 AppInfo 对象
                app_info_obj = AppInfo(
                    package_name=bundle_id,  # iOS 使用 Bundle ID
                    app_name=display_name,
                    pid=None,
                    is_running=False,
                    status=AppStatus.STOPPED,
                    uid=None,
                    version=version
                )
                apps.append(app_info_obj)

            self._cached_apps = apps
            logger.info(f"枚举iOS应用完成: {len(apps)}个应用 (跳过 {skipped_system} 个系统应用)")
            return apps

        except Exception as e:
            logger.error(f"枚举iOS应用失败: {e}")
            # 返回空列表而不是抛出异常（降级策略）
            return []

    def get_running_apps(self) -> List[AppInfo]:
        """
        获取正在运行的iOS应用

        Returns:
            List[AppInfo]: 运行中的应用列表
        """
        try:
            # iOS 进程监控比较复杂，需要使用 sysmon 服务
            # 这里先返回一个空列表，未来可以扩展
            logger.warning("iOS 运行中应用检测功能尚未实现")
            return []

        except Exception as e:
            logger.error(f"获取运行中的iOS应用失败: {e}")
            return []

    def get_app_info(self, package_name: str) -> Optional[AppInfo]:
        """
        获取iOS应用详细信息

        Args:
            package_name: Bundle ID

        Returns:
            AppInfo: 应用信息
        """
        try:
            # 如果连接未初始化，尝试初始化
            if self._installation_proxy is None:
                self._init_connection()

            if self._installation_proxy is None:
                return None

            # 获取特定应用的详细信息
            # 注意：get_apps() 可以接受应用类型参数，但获取单个应用需要不同方式
            apps_dict = self._installation_proxy.get_apps()

            if package_name not in apps_dict:
                logger.warning(f"未找到应用: {package_name}")
                return None

            app_info = apps_dict[package_name]
            display_name = app_info.get('CFBundleDisplayName', package_name)
            version = app_info.get('CFBundleShortVersionString', None)

            return AppInfo(
                package_name=package_name,
                app_name=display_name,
                pid=None,
                is_running=False,
                status=AppStatus.STOPPED,
                uid=None,
                version=version
            )

        except Exception as e:
            logger.error(f"获取iOS应用详情失败: {e}")
            return None
