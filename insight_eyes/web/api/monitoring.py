# -*- coding: utf-8 -*-
"""
监控控制 API
"""
from fastapi import APIRouter, HTTPException
from logzero import logger

from insight_eyes.core.device_manager import DeviceManager
from insight_eyes.core.database import DatabaseManager
from insight_eyes.web.api.schemas import StartMonitoringRequest, SessionResponse


router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.post("/start", response_model=SessionResponse)
async def start_monitoring(request: StartMonitoringRequest):
    """开始监控"""
    try:
        session = await DeviceManager.start_session(request.device_id, request.app_package)
        logger.info(f"启动监控会话: {session.id}")

        return SessionResponse(
            id=session.id,
            device_id=session.device_id,
            app_package=session.app_package,
            platform=getattr(session, 'platform', 'android'),
            status=session.status.value,
            start_time=session.start_time.isoformat(),
            end_time=session.end_time.isoformat() if session.end_time else None,
            duration=session.duration,
        )
    except Exception as e:
        logger.error(f"启动监控失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_monitoring(session_id: int):
    """停止监控"""
    try:
        await DeviceManager.stop_session(session_id)
        logger.info(f"停止监控会话: {session_id}")
        return {"status": "stopped", "session_id": session_id}
    except Exception as e:
        logger.error(f"停止监控失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
