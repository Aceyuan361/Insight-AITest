# -*- coding: utf-8 -*-
"""
设备管理 API
"""
from fastapi import APIRouter, HTTPException
from logzero import logger
import time

from insight_eyes.core.device_manager import DeviceManager
from insight_eyes.core.models.device import Device


router = APIRouter(prefix="/api/devices", tags=["devices"])

# 设备缓存：避免频繁扫描设备
_device_cache: list[Device] = []
_cache_time: float = 0
_CACHE_TTL: int = 30  # 缓存30秒


@router.get("")
async def list_devices():
    """扫描并列出可用设备（使用缓存）"""
    global _device_cache, _cache_time

    # 检查缓存是否有效
    current_time = time.time()
    if current_time - _cache_time > _CACHE_TTL or not _device_cache:
        # 缓存过期或为空，刷新设备列表
        _device_cache = DeviceManager.scan_devices()
        _cache_time = current_time
        logger.info(f"扫描到 {len(_device_cache)} 个设备")
    else:
        logger.debug(f"使用设备缓存: {len(_device_cache)} 个设备")

    return _device_cache


@router.get("/{device_id}")
async def get_device(device_id: str):
    """获取指定设备信息（使用缓存，避免频繁扫描）"""
    global _device_cache, _cache_time

    # 检查缓存是否有效
    current_time = time.time()
    if current_time - _cache_time > _CACHE_TTL or not _device_cache:
        # 缓存过期或为空，刷新设备列表
        _device_cache = DeviceManager.scan_devices()
        _cache_time = current_time
        logger.debug(f"刷新设备缓存: {len(_device_cache)} 个设备")

    # 从缓存中查找设备
    for device in _device_cache:
        if device.device_id == device_id:
            return device

    raise HTTPException(status_code=404, detail="Device not found")


@router.post("/{device_id}/connect")
async def connect_device(device_id: str):
    """连接指定设备（使用缓存的设备信息）"""
    try:
        from insight_eyes.desktop.core.device_adapters import DeviceAdapterFactory
        from insight_eyes.desktop.core.models import DeviceType
        from insight_eyes.public.common import Platform

        # 使用缓存的设备列表
        device = next((d for d in _device_cache if d.device_id == device_id), None)

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
async def disconnect_device(device_id: str):
    """断开设备连接（使用缓存的设备信息）"""
    try:
        from insight_eyes.desktop.core.device_adapters import DeviceAdapterFactory
        from insight_eyes.desktop.core.models import DeviceType
        from insight_eyes.public.common import Platform

        # 使用缓存的设备列表
        device = next((d for d in _device_cache if d.device_id == device_id), None)

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
async def refresh_devices():
    """刷新设备列表（强制重新扫描）"""
    global _device_cache, _cache_time

    try:
        # 强制刷新设备列表并更新缓存
        _device_cache = DeviceManager.scan_devices()
        _cache_time = time.time()
        logger.info(f"刷新设备列表: 发现 {len(_device_cache)} 个设备")
        return _device_cache
    except Exception as e:
        logger.error(f"刷新设备列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{device_id}/apps")
async def get_device_apps(device_id: str, include_system: bool = False):
    """获取设备应用列表（使用缓存的设备信息）"""
    try:
        from insight_eyes.desktop.core.app_enumerator import AppEnumeratorFactory
        from insight_eyes.core.models.device import DeviceType
        from insight_eyes.public.common import Platform

        # 使用缓存的设备列表
        device = next((d for d in _device_cache if d.device_id == device_id), None)

        if not device:
            raise HTTPException(status_code=404, detail="Device not found")

        platform = Platform.ANDROID if device.type == DeviceType.ANDROID else Platform.IOS

        enumerator = AppEnumeratorFactory.create_enumerator(device_id, platform)
        if not enumerator:
            raise HTTPException(status_code=500, detail="Failed to create app enumerator")

        apps = enumerator.enumerate_apps(include_system_apps=include_system)

        try:
            # iOS 平台使用 SysmonService 检查进程（需要开发者模式）
            if platform == Platform.IOS:
                try:
                    from insight_eyes.public.ios.sysmon_service import SysmonService
                    sysmon_service = SysmonService.get_instance(device_id)

                    if sysmon_service.connect():
                        for app in apps:
                            process = sysmon_service.get_process_by_bundle_id(app.package_name)
                            if process:
                                app.is_running = True
                                app.pid = process.get('pid')
                        logger.info(f"iOS 进程检测完成: {sum(1 for a in apps if a.is_running)}/{len(apps)} 个运行中")
                    else:
                        logger.warning("iOS DVT 连接失败（可能需要开发者模式），跳过进程检测")
                except Exception as ios_error:
                    logger.warning(f"iOS 进程检测失败: {ios_error}，跳过检测")
            else:
                # Android 平台使用标准方法
                running_apps = enumerator.get_running_apps()
                running_packages = {app.package_name for app in running_apps}

                for app in apps:
                    if app.package_name in running_packages:
                        running_app = next((a for a in running_apps if a.package_name == app.package_name), None)
                        if running_app:
                            app.is_running = True
                            app.pid = running_app.pid
                            app.status = running_app.status
        except Exception as e:
            logger.warning(f"获取运行中的应用失败: {e}")

        apps_data = [
            {
                "package_name": app.package_name,
                "name": app.app_name,
                "is_running": app.is_running,
                "pid": app.pid,
                "status": app.status.value if app.status else None
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
