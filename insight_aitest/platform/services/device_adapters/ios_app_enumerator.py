# -*- coding: utf-8 -*-
"""
iOS应用枚举器 (pymobiledevice3 v9.x async API)

负责枚举 iOS 设备上安装的应用。
通过 IOSConnectionManager 在事件循环中执行 async InstallationProxyService 和 DVT API。
"""

from typing import List, Optional
from logzero import logger

from .models import AppInfo, AppStatus
from abc import ABC, abstractmethod

from insight_aitest.platform.services.collectors.ios.connection_manager import (
    IOSConnectionManager,
)


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
    通过 pymobiledevice3 v9.x async API 获取 iOS 设备上的应用信息
    """

    def __init__(self, device_id: str):
        """
        初始化iOS应用枚举器

        Args:
            device_id: iOS设备UDID
        """
        super().__init__(device_id)
        logger.info(f"iOS应用枚举器初始化: {self.device_id}")

    def _get_mgr(self) -> IOSConnectionManager:
        """获取或初始化 ConnectionManager"""
        mgr = IOSConnectionManager.get_instance(self.device_id)
        if not mgr.is_connected:
            mgr.connect()
        return mgr

    def enumerate_apps(self, include_system_apps: bool = False) -> List[AppInfo]:
        """
        枚举iOS设备上的所有应用

        通过 IOSConnectionManager 执行 async InstallationProxyService.get_apps()

        Args:
            include_system_apps: 是否包含系统应用

        Returns:
            List[AppInfo]: 应用信息列表
        """
        try:
            from pymobiledevice3.services.installation_proxy import (
                InstallationProxyService,
            )

            mgr = self._get_mgr()
            lockdown = mgr.get_async_lockdown()

            # 在事件循环中执行 async get_apps()
            service = InstallationProxyService(lockdown)
            apps_dict = mgr.run_async(service.get_apps(), timeout=15)

            if not apps_dict:
                logger.warning("未获取到任何应用信息")
                return []

            apps = []
            skipped_system = 0
            for bundle_id, app_info in apps_dict.items():
                # 检查是否为系统应用
                is_system = app_info.get("ApplicationType", "User") != "User"

                # 如果不包含系统应用，跳过系统应用
                if not include_system_apps and is_system:
                    skipped_system += 1
                    continue

                # 获取应用显示名称
                display_name = app_info.get("CFBundleDisplayName", bundle_id)
                if not display_name:
                    display_name = app_info.get("CFBundleName", bundle_id)

                # 获取版本号
                version = app_info.get("CFBundleShortVersionString", None)
                if not version:
                    version = app_info.get("CFBundleVersion", None)

                # 创建 AppInfo 对象
                app_info_obj = AppInfo(
                    package_name=bundle_id,
                    app_name=display_name,
                    pid=None,
                    is_running=False,
                    status=AppStatus.STOPPED,
                    uid=None,
                    version=version,
                )
                apps.append(app_info_obj)

            self._cached_apps = apps
            logger.info(f"枚举iOS应用完成: {len(apps)}个应用 (跳过 {skipped_system} 个系统应用)")
            return apps

        except Exception as e:
            logger.error(f"枚举iOS应用失败: {e}")
            return []

    def _build_app_name_lookup(self) -> dict:
        """
        构建 ``进程名 -> bundle_id`` 查找表（委托给 AppLookup）。

        AppLookup 会缓存应用列表并包含 CFBundleExecutable（DVT 进程 name 的真正来源），
        这是从 DVT 进程名精确反查 Bundle ID 的关键。

        Returns:
            dict: 进程名 -> bundle_id 的映射
        """
        from insight_aitest.platform.services.collectors.ios.app_lookup import AppLookup

        return AppLookup._get_lookup(self.device_id)

    def get_running_apps(self) -> List[AppInfo]:
        """
        获取正在运行的iOS应用

        通过 DvtProvider + DeviceInfo.proclist() (async API) 获取进程列表，
        交叉匹配已安装应用名得到真实 bundle_id。

        Returns:
            List[AppInfo]: 运行中的应用列表
        """
        try:
            logger.info("开始检测iOS运行中应用...")

            # 先构建进程名 -> bundle_id 的查找表
            name_lookup = self._build_app_name_lookup()

            # 通过 ConnectionManager 获取 async 进程列表
            mgr = self._get_mgr()
            processes = mgr.run_async(self._fetch_processes_async(), timeout=15)

            logger.info(f"Sysmon返回 {len(processes) if processes else 0} 个进程")

            running_apps = []
            matched_bundle_ids = set()
            for process in processes or []:
                try:
                    pid = getattr(process, "pid", None)
                    process_name = getattr(process, "name", "")

                    if isinstance(process, dict):
                        pid = process.get("pid")
                        process_name = process.get("name", "")

                    if not process_name:
                        continue

                    # 交叉匹配进程名 -> bundle_id
                    bundle_id = name_lookup.get(process_name)
                    if not bundle_id:
                        bundle_id = name_lookup.get(process_name.lower())

                    if bundle_id and bundle_id not in matched_bundle_ids:
                        matched_bundle_ids.add(bundle_id)
                        running_apps.append(
                            AppInfo(
                                package_name=bundle_id,
                                app_name=process_name,
                                pid=pid,
                                is_running=True,
                                status=AppStatus.RUNNING,
                                uid=None,
                                version=None,
                            )
                        )
                        logger.debug(f"匹配进程 {process_name} (PID:{pid}) -> {bundle_id}")
                except Exception as e:
                    logger.debug(f"处理进程对象失败: {e}")
                    continue

            logger.info(f"检测到 {len(running_apps)} 个运行中的iOS应用")
            return running_apps

        except Exception as e:
            logger.error(f"获取运行中的iOS应用失败: {e}")
            import traceback

            logger.debug(traceback.format_exc())
            return []

    async def _fetch_processes_async(self):
        """异步获取进程列表（通过 DvtProvider + DeviceInfo）"""
        from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
        from pymobiledevice3.services.dvt.instruments.device_info import DeviceInfo

        mgr = IOSConnectionManager.get_instance(self.device_id)
        lockdown = mgr.get_async_lockdown()

        async with DvtProvider(lockdown) as dvt:
            async with DeviceInfo(dvt) as device_info:
                return await device_info.proclist()

    def get_app_info(self, package_name: str) -> Optional[AppInfo]:
        """
        获取iOS应用详细信息

        Args:
            package_name: Bundle ID

        Returns:
            AppInfo: 应用信息
        """
        try:
            from pymobiledevice3.services.installation_proxy import (
                InstallationProxyService,
            )

            mgr = self._get_mgr()
            lockdown = mgr.get_async_lockdown()
            service = InstallationProxyService(lockdown)
            apps_dict = mgr.run_async(service.get_apps(), timeout=15)

            if package_name not in apps_dict:
                logger.warning(f"未找到应用: {package_name}")
                return None

            app_info = apps_dict[package_name]
            display_name = app_info.get("CFBundleDisplayName", package_name)
            version = app_info.get("CFBundleShortVersionString", None)

            return AppInfo(
                package_name=package_name,
                app_name=display_name,
                pid=None,
                is_running=False,
                status=AppStatus.STOPPED,
                uid=None,
                version=version,
            )

        except Exception as e:
            logger.error(f"获取iOS应用详情失败: {e}")
            return None
