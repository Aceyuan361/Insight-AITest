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
