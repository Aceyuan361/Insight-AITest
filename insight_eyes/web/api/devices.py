# -*- coding: utf-8 -*-
"""
设备管理 API
"""
from fastapi import APIRouter, HTTPException
from logzero import logger

from insight_eyes.core.device_manager import DeviceManager
from insight_eyes.core.models.device import Device


router = APIRouter(prefix="/api/devices", tags=["devices"])


@router.get("")
async def list_devices():
    """扫描并列出可用设备"""
    try:
        devices = DeviceManager.scan_devices()
        logger.info(f"扫描到 {len(devices)} 个设备")
        return devices
    except Exception as e:
        logger.error(f"设备扫描失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{device_id}")
async def get_device(device_id: str):
    """获取指定设备信息"""
    devices = DeviceManager.scan_devices()
    for device in devices:
        if device.device_id == device_id:
            return device
    raise HTTPException(status_code=404, detail="Device not found")


@router.post("/{device_id}/connect")
async def connect_device(device_id: str):
    """连接指定设备"""
    try:
        from insight_eyes.desktop.core.device_adapters import DeviceAdapterFactory
        from insight_eyes.desktop.core.models import DeviceType
        from insight_eyes.public.common import Platform

        devices = DeviceManager.scan_devices()
        device = next((d for d in devices if d.device_id == device_id), None)

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
    """断开设备连接"""
    try:
        from insight_eyes.desktop.core.device_adapters import DeviceAdapterFactory
        from insight_eyes.desktop.core.models import DeviceType
        from insight_eyes.public.common import Platform

        devices = DeviceManager.scan_devices()
        device = next((d for d in devices if d.device_id == device_id), None)

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
    """刷新设备列表（重新扫描）"""
    try:
        devices = DeviceManager.scan_devices()
        logger.info(f"刷新设备列表: 发现 {len(devices)} 个设备")
        return devices
    except Exception as e:
        logger.error(f"刷新设备列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{device_id}/apps")
async def get_device_apps(device_id: str, include_system: bool = False):
    """获取设备应用列表"""
    try:
        from insight_eyes.desktop.core.app_enumerator import AppEnumeratorFactory
        from insight_eyes.desktop.core.models import DeviceType
        from insight_eyes.public.common import Platform

        devices = DeviceManager.scan_devices()
        device = next((d for d in devices if d.device_id == device_id), None)

        if not device:
            raise HTTPException(status_code=404, detail="Device not found")

        platform = Platform.ANDROID if device.type == DeviceType.ANDROID else Platform.IOS

        enumerator = AppEnumeratorFactory.create_enumerator(device_id, platform)
        if not enumerator:
            raise HTTPException(status_code=500, detail="Failed to create app enumerator")

        apps = enumerator.enumerate_apps(include_system_apps=include_system)

        try:
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
