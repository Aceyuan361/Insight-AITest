# -*- coding: utf-8 -*-
"""
iOS 应用进程匹配辅助模块

核心问题：DVT 进程列表中的 ``name`` 字段对应应用的 **CFBundleExecutable**
（可执行文件名，例如 "WeChat"），而不是 Bundle ID（"com.tencent.xin"）或
显示名（"微信"）。早期实现用 Bundle ID 后缀去子串匹配进程名，对绝大多数
应用都会失败（"xin" 无法匹配 "WeChat"）。

本模块通过 InstallationProxyService 一次性查询所有已安装应用，构建
``进程名 -> bundle_id`` 的查找表，从而把 DVT 进程精确映射回 Bundle ID。

兼容 iOS 11-16 (usbmux) 和 iOS 17+ (tunnel)，连接由 IOSConnectionManager 统一管理。
"""

import threading
import time
from typing import Dict, Optional, Tuple

from logzero import logger

from .connection_manager import IOSConnectionManager


class AppLookup:
    """
    已安装应用的可执行文件名 -> Bundle ID 查找表（带缓存）。

    线程安全，可被 SysmonService / 各 Collector / 路由层共享。
    """

    # 每个 UDID 对应一个 (lookup_dict, apps_dict, build_time)
    _cache: Dict[str, Tuple[dict, Optional[dict], float]] = {}
    _cache_lock = threading.Lock()
    _cache_ttl = 30.0  # 30 秒缓存，避免每次查进程都重新拉取应用列表

    @classmethod
    def get_bundle_id_by_executable(
        cls, udid: str, executable_name: str
    ) -> Optional[str]:
        """
        根据进程的可执行文件名（DVT 进程的 ``name`` 字段）查找 Bundle ID。

        Args:
            udid: 设备 UDID
            executable_name: 进程名，例如 "WeChat"、"MobileCal"

        Returns:
            匹配到的 Bundle ID，未找到返回 None
        """
        if not executable_name:
            return None

        lookup = cls._get_lookup(udid)

        # 1) 精确匹配（优先）
        bid = lookup.get(executable_name)
        if bid:
            return bid

        # 2) 大小写不敏感匹配
        bid = lookup.get(executable_name.lower())
        if bid:
            return bid

        return None

    @classmethod
    def build_bundle_to_executable_map(cls, udid: str) -> Dict[str, str]:
        """
        构建 Bundle ID -> 可执行文件名 的映射（用于反向查找）。

        Args:
            udid: 设备 UDID

        Returns:
            {bundle_id: executable_name}
        """
        # 复用缓存的应用列表，避免重复查询
        apps_dict = cls._get_apps_dict(udid)
        result: Dict[str, str] = {}
        for bid, info in (apps_dict or {}).items():
            exe = info.get("CFBundleExecutable")
            if exe:
                result[bid] = exe
        return result

    @classmethod
    def find_executable_for_bundle(cls, udid: str, bundle_id: str) -> Optional[str]:
        """
        根据 Bundle ID 查找其可执行文件名（DVT 进程名）。

        Args:
            udid: 设备 UDID
            bundle_id: 应用 Bundle ID

        Returns:
            可执行文件名，未找到返回 None
        """
        apps_dict = cls._get_apps_dict(udid)
        if not apps_dict or bundle_id not in apps_dict:
            return None
        info = apps_dict[bundle_id]
        # CFBundleExecutable 是 DVT 进程 name 的来源
        exe = info.get("CFBundleExecutable")
        if exe:
            return exe
        # 兜底：某些应用可能没有 CFBundleExecutable，退回到显示名
        return info.get("CFBundleDisplayName") or info.get("CFBundleName")

    @classmethod
    def invalidate(cls, udid: Optional[str] = None) -> None:
        """使缓存失效（应用安装/卸载后调用）。"""
        with cls._cache_lock:
            if udid is None:
                cls._cache.clear()
            else:
                cls._cache.pop(udid, None)

    # ------------------------------------------------------------------
    # 内部实现
    # ------------------------------------------------------------------

    @classmethod
    def _get_lookup(cls, udid: str) -> dict:
        """获取或构建 ``进程名 -> bundle_id`` 查找表（带缓存）。"""
        cached = cls._get_cached(udid)
        if cached is not None:
            return cached[0]

        apps_dict = cls._fetch_installed_apps(udid)
        lookup = cls._build_lookup_from_apps(apps_dict)

        with cls._cache_lock:
            cls._cache[udid] = (lookup, apps_dict, time.time())

        logger.info(f"[AppLookup] 构建进程名查找表: {len(lookup)} 个候选名")
        return lookup

    @classmethod
    def _get_apps_dict(cls, udid: str) -> Optional[dict]:
        """获取已安装应用字典（带缓存，与查找表共享同一缓存）。"""
        cached = cls._get_cached(udid)
        if cached is not None:
            return cached[1]

        # 未缓存时刷新缓存（同时构建查找表和应用字典）
        cls._refresh_cache(udid)
        with cls._cache_lock:
            entry = cls._cache.get(udid)
        return entry[1] if entry else None

    @classmethod
    def _refresh_cache(cls, udid: str) -> bool:
        """强制刷新缓存，返回是否成功。"""
        apps_dict = cls._fetch_installed_apps(udid)
        lookup = cls._build_lookup_from_apps(apps_dict)
        with cls._cache_lock:
            cls._cache[udid] = (lookup, apps_dict, time.time())
        logger.info(f"[AppLookup] 构建进程名查找表: {len(lookup)} 个候选名")
        return True

    @classmethod
    def _get_cached(cls, udid: str):
        """返回未过期的缓存项 ``(lookup, apps_dict, time)``，无缓存返回 None。"""
        with cls._cache_lock:
            cached = cls._cache.get(udid)
            if cached is not None and (time.time() - cached[2]) < cls._cache_ttl:
                return cached
        return None

    @staticmethod
    def _build_lookup_from_apps(apps_dict: Optional[dict]) -> dict:
        """
        从 InstallationProxyService 返回的应用字典构建查找表。

        查找表的键包含：CFBundleExecutable（最重要，DVT 进程名来源）、
        CFBundleDisplayName、CFBundleName、以及 Bundle ID 本身。
        值为对应的 Bundle ID。
        """
        lookup: dict = {}
        if not apps_dict:
            return lookup

        for bundle_id, app_info in apps_dict.items():
            # 收集该应用所有可能的"进程名"
            names = set()
            names.add(bundle_id)

            # CFBundleExecutable —— DVT 进程 name 的真正来源（关键！）
            executable = app_info.get("CFBundleExecutable")
            if executable:
                names.add(executable)

            display_name = app_info.get("CFBundleDisplayName")
            if display_name:
                names.add(display_name)

            bundle_name = app_info.get("CFBundleName")
            if bundle_name:
                names.add(bundle_name)

            # Path —— 某些场景进程的 realAppName 是完整路径
            path = app_info.get("Path")
            if path:
                names.add(path)

            for name in names:
                if name:
                    # setdefault：第一个应用优先（避免被系统应用覆盖）
                    lookup.setdefault(name, bundle_id)
                    lookup.setdefault(name.lower(), bundle_id)

        return lookup

    @staticmethod
    def _fetch_installed_apps(udid: str) -> Optional[dict]:
        """通过 IOSConnectionManager 在事件循环中查询已安装应用。"""
        try:
            from pymobiledevice3.services.installation_proxy import (
                InstallationProxyService,
            )

            mgr = IOSConnectionManager.get_instance(udid)
            if not mgr.is_connected:
                mgr.connect()

            lockdown = mgr.get_async_lockdown()
            service = InstallationProxyService(lockdown)
            return mgr.run_async(service.get_apps(), timeout=15)
        except Exception as e:
            logger.warning(f"[AppLookup] 获取已安装应用列表失败: {e}")
            return None
