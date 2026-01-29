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


@router.get("/sessions")
async def list_sessions(limit: int = 100):
    """列出所有会话"""
    try:
        import os
        db_path = os.path.join(os.path.expanduser("~"), ".insight_eye", "monitoring.db")
        db = DatabaseManager(db_path)
        sessions = db.list_sessions(limit=limit)

        return [
            SessionResponse(
                id=s.id,
                device_id=s.device_id,
                app_package=s.app_package,
                platform=getattr(s, 'platform', 'android'),
                status=s.status.value,
                start_time=s.start_time.isoformat(),
                end_time=s.end_time.isoformat() if s.end_time else None,
                duration=s.duration,
            )
            for s in sessions
        ]
    except Exception as e:
        logger.error(f"获取会话列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}")
async def get_session(session_id: int):
    """获取会话详情"""
    try:
        import os
        db_path = os.path.join(os.path.expanduser("~"), ".insight_eye", "monitoring.db")
        db = DatabaseManager(db_path)
        session = db.get_session(session_id)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
