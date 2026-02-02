# -*- coding: utf-8 -*-
"""
监控控制 API
"""
from fastapi import APIRouter, HTTPException
from logzero import logger

from insight_eyes.core.device_manager import DeviceManager
from insight_eyes.core.database import DatabaseManager
from insight_eyes.web.api.schemas import StartMonitoringRequest, StopMonitoringRequest, SessionResponse


router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.post("/start", response_model=SessionResponse)
async def start_monitoring(request: StartMonitoringRequest):
    """开始监控"""
    try:
        # 传递采样间隔和平台到核心层
        session = await DeviceManager.start_session(
            request.device_id,
            request.app_package,
            platform=request.platform,  # 添加平台参数
            sampling_interval=request.sampling_interval
        )
        logger.info(f"启动监控会话: {session.id}, 平台: {request.platform}, 采样间隔: {request.sampling_interval}ms")

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
async def stop_monitoring(request: StopMonitoringRequest):
    """停止监控"""
    try:
        await DeviceManager.stop_session(request.session_id)
        logger.info(f"停止监控会话: {request.session_id}")
        return {"status": "stopped", "session_id": request.session_id}
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


@router.get("/sessions/{session_id}/metrics")
async def get_session_metrics(session_id: int, limit: int = 1000):
    """获取会话的所有指标数据"""
    try:
        import os
        db_path = os.path.join(os.path.expanduser("~"), ".insight_eye", "monitoring.db")
        db = DatabaseManager(db_path)
        metrics = db.get_metrics(session_id)

        # 限制返回数量
        if limit and len(metrics) > limit:
            metrics = metrics[:limit]

        return metrics
    except Exception as e:
        logger.error(f"获取会话指标失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/statistics")
async def get_session_statistics(session_id: int):
    """获取会话的统计数据"""
    try:
        import os
        db_path = os.path.join(os.path.expanduser("~"), ".insight_eye", "monitoring.db")
        db = DatabaseManager(db_path)

        # 获取指标数据
        metrics = db.get_metrics(session_id)
        if not metrics:
            return {}

        # 计算统计
        from insight_eyes.desktop.data.repository import MetricsRepository
        repo = MetricsRepository(db)
        return repo.get_statistics(session_id)
    except Exception as e:
        logger.error(f"获取会话统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/alerts")
async def get_session_alerts(session_id: int):
    """获取会话的告警记录"""
    try:
        import os
        db_path = os.path.join(os.path.expanduser("~"), ".insight_eye", "monitoring.db")
        db = DatabaseManager(db_path)
        alerts = db.get_alerts(session_id=session_id)

        return alerts
    except Exception as e:
        logger.error(f"获取会话告警失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: int):
    """删除指定会话及其相关数据"""
    try:
        import os
        db_path = os.path.join(os.path.expanduser("~"), ".insight_eye", "monitoring.db")
        db = DatabaseManager(db_path)

        # 删除会话（数据库会级联删除相关数据）
        success = db.delete_session(session_id)

        if success:
            logger.info(f"删除会话: {session_id}")
            return {"status": "deleted", "session_id": session_id}
        else:
            raise HTTPException(status_code=404, detail="Session not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/batch-delete")
async def batch_delete_sessions(session_ids: list[int]):
    """批量删除会话"""
    try:
        import os
        db_path = os.path.join(os.path.expanduser("~"), ".insight_eye", "monitoring.db")
        db = DatabaseManager(db_path)

        success_count = 0
        failed_ids = []

        for session_id in session_ids:
            try:
                if db.delete_session(session_id):
                    success_count += 1
                else:
                    failed_ids.append(session_id)
            except Exception as e:
                logger.error(f"删除会话 {session_id} 失败: {e}")
                failed_ids.append(session_id)

        logger.info(f"批量删除完成: 成功 {success_count}, 失败 {len(failed_ids)}")

        return {
            "success": success_count,
            "failed": len(failed_ids),
            "failed_ids": failed_ids
        }
    except Exception as e:
        logger.error(f"批量删除会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
