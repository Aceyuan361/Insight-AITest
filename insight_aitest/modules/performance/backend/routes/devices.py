# -*- coding: utf-8 -*-
"""
设备管理 API

修复全局变量并发安全问题：
- 使用 DeviceCache 类封装缓存逻辑
- 使用 asyncio.Lock 保护缓存操作
- 使用 FastAPI 的 Depends 实现依赖注入
- 改进单例模式实现，避免 @lru_cache 的限制

优化日志：
- v1.0.2: 添加异步扫描支持，添加设备索引提高查询效率
- v1.0.1: 修复全局变量并发安全问题
- v1.0.0: 初始实现
"""

from fastapi import APIRouter, HTTPException, Depends
from logzero import logger
import time
import asyncio
from typing import List, Optional, Dict

# 修复：使用核心层的 DeviceManager 来调用 scan_devices
# 注意：DeviceManager 是 core.device_manager.DeviceManager，它有 scan_devices 方法
# desktop.core.device_manager.DeviceManager 是 PyQt QObject 类，没有 scan_devices 方法
from insight_aitest.platform.services.device_manager import DeviceManager as CoreDeviceManager
from insight_aitest.platform.services.models.device import Device

router = APIRouter(prefix="/devices", tags=["devices"])


# 单例模式实现（避免 @lru_cache 的限制）
_device_cache_instance: Optional["DeviceCache"] = None
_cache_init_lock = asyncio.Lock()


class DeviceCache:
    """设备缓存管理器（线程安全）

    修复全局变量并发安全问题，使用类封装 + 异步锁保护
    优化：添加设备索引提高查询效率，使用异步扫描避免阻塞
    """

    def __init__(self, ttl: int = 30):
        self._cache: List[Device] = []
        self._cache_index: Dict[str, Device] = {}  # 设备索引：O(1) 查询
        self._cache_time: float = 0
        self._ttl: int = ttl
        self._lock = asyncio.Lock()

    async def get_devices(self, force_refresh: bool = False) -> List[Device]:
        """获取设备列表（带缓存）

        使用线程池执行同步扫描，避免阻塞事件循环
        """
        async with self._lock:
            current_time = time.time()

            if force_refresh or current_time - self._cache_time > self._ttl or not self._cache:
                logger.info("[设备扫描] 开始扫描设备...")
                # 在线程池中执行同步扫描，避免阻塞事件循环
                loop = asyncio.get_running_loop()
                try:
                    self._cache = await loop.run_in_executor(None, CoreDeviceManager.scan_devices)
                    logger.info(f"[设备扫描] scan_devices 返回 {len(self._cache)} 个设备")
                except Exception as e:
                    logger.error(f"[设备扫描] scan_devices 执行失败: {e}", exc_info=True)
                    self._cache = []

                # 构建设备索引，提高查询效率
                self._cache_index = {d.device_id: d for d in self._cache}
                self._cache_time = current_time
                logger.info(f"[设备缓存] 更新缓存: {len(self._cache)} 个设备")
                for dev in self._cache:
                    logger.info(f"[设备列表] - {dev.name} ({dev.device_id})")
            else:
                logger.debug(f"[设备缓存] 使用缓存: {len(self._cache)} 个设备")

            return self._cache.copy()  # 返回副本，避免外部修改

    async def get_device_by_id(self, device_id: str) -> Optional[Device]:
        """根据ID获取设备（使用索引，O(1) 复杂度）"""
        await self.get_devices()  # 确保缓存已更新
        return self._cache_index.get(device_id)

    async def refresh(self) -> List[Device]:
        """强制刷新设备列表"""
        return await self.get_devices(force_refresh=True)


async def get_device_cache() -> DeviceCache:
    """获取设备缓存实例（单例模式）

    使用异步锁确保只创建一个实例

    性能优化：延长 TTL 到 5 分钟（300秒），减少频繁的设备扫描
    - 设备连接状态通常不会频繁变化
    - 用户可手动调用 /api/devices/refresh 强制刷新
    - 大幅降低 API 响应延迟（从约1秒降至<50ms）
    """
    global _device_cache_instance

    if _device_cache_instance is None:
        async with _cache_init_lock:
            if _device_cache_instance is None:
                _device_cache_instance = DeviceCache(ttl=300)  # 5分钟缓存
                logger.debug("创建设备缓存单例 (TTL=300s)")

    return _device_cache_instance


@router.get("")
async def list_devices(cache: DeviceCache = Depends(get_device_cache)) -> List[Device]:
    """扫描并列出可用设备（使用缓存）"""
    return await cache.get_devices()


@router.get("/{device_id}")
async def get_device(device_id: str, cache: DeviceCache = Depends(get_device_cache)) -> Device:
    """获取指定设备信息（使用缓存）"""
    device = await cache.get_device_by_id(device_id)

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    return device


@router.post("/{device_id}/connect")
async def connect_device(device_id: str, cache: DeviceCache = Depends(get_device_cache)):
    """连接指定设备（使用缓存的设备信息）"""
    try:
        from insight_aitest.platform.services.device_adapters.device_adapters import (
            DeviceAdapterFactory,
        )
        from insight_aitest.platform.services.models.device import DeviceType
        from insight_aitest.platform.services.device_common import Platform

        device = await cache.get_device_by_id(device_id)

        if not device:
            raise HTTPException(status_code=404, detail="Device not found")

        platform = Platform.ANDROID if device.type == DeviceType.ANDROID else Platform.IOS

        adapter = DeviceAdapterFactory.create_adapter(device_id, platform)
        if not adapter:
            raise HTTPException(status_code=500, detail="Failed to create device adapter")

        if adapter.connect():
            logger.info(f"设备连接成功: {device_id}")
            return {"device_id": device_id, "status": "connected"}
        else:
            raise HTTPException(status_code=500, detail="Failed to connect to device")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"设备连接失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{device_id}")
async def disconnect_device(device_id: str, cache: DeviceCache = Depends(get_device_cache)):
    """断开设备连接（使用缓存的设备信息）"""
    try:
        from insight_aitest.platform.services.device_adapters.device_adapters import (
            DeviceAdapterFactory,
        )
        from insight_aitest.platform.services.models.device import DeviceType
        from insight_aitest.platform.services.device_common import Platform

        device = await cache.get_device_by_id(device_id)

        if not device:
            raise HTTPException(status_code=404, detail="Device not found")

        platform = Platform.ANDROID if device.type == DeviceType.ANDROID else Platform.IOS

        adapter = DeviceAdapterFactory.create_adapter(device_id, platform)
        if adapter:
            adapter.disconnect()

        logger.info(f"设备已断开: {device_id}")
        return {"device_id": device_id, "status": "disconnected"}

    except Exception as e:
        logger.error(f"设备断开失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh")
async def refresh_devices(cache: DeviceCache = Depends(get_device_cache)) -> List[Device]:
    """刷新设备列表（强制重新扫描）"""
    try:
        devices = await cache.refresh()
        logger.info(f"刷新设备列表: 发现 {len(devices)} 个设备")
        return devices
    except Exception as e:
        logger.error(f"刷新设备列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{device_id}/apps")
async def get_device_apps(
    device_id: str, include_system: bool = False, cache: DeviceCache = Depends(get_device_cache)
):
    """获取设备应用列表（使用缓存的设备信息）"""
    try:
        from insight_aitest.platform.services.device_adapters.app_enumerator import (
            AppEnumeratorFactory,
        )
        from insight_aitest.platform.services.models.device import DeviceType
        from insight_aitest.platform.services.device_common import Platform

        device = await cache.get_device_by_id(device_id)

        if not device:
            raise HTTPException(status_code=404, detail="Device not found")

        platform = Platform.ANDROID if device.type == DeviceType.ANDROID else Platform.IOS

        enumerator = AppEnumeratorFactory.create_enumerator(device_id, platform)
        if not enumerator:
            raise HTTPException(status_code=500, detail="Failed to create app enumerator")

        apps = enumerator.enumerate_apps(include_system_apps=include_system)

        try:
            # 统一使用 enumerator.get_running_apps() 检测运行状态
            # （iOS 通过 DVT proclist + CFBundleExecutable 交叉匹配，
            #   Android 通过 pm/dumpsys，两者返回结构一致）
            running_apps = enumerator.get_running_apps()
            running_map = {app.package_name: app for app in running_apps}

            for app in apps:
                running_app = running_map.get(app.package_name)
                if running_app:
                    app.is_running = True
                    app.pid = running_app.pid
                    app.status = running_app.status

            logger.info(
                f"进程检测完成: {sum(1 for a in apps if a.is_running)}/{len(apps)} 个运行中"
            )
        except Exception as e:
            logger.warning(f"获取运行中的应用失败: {e}")

        apps_data = [
            {
                "package_name": app.package_name,
                "name": app.app_name,
                "is_running": app.is_running,
                "pid": app.pid,
                "status": app.status.value if app.status else None,
            }
            for app in apps
        ]

        logger.info(f"获取设备应用列表: {device_id}, 应用数量: {len(apps_data)}")
        return apps_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取应用列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
