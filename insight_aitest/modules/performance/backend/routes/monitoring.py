# -*- coding: utf-8 -*-
"""
监控控制 API
"""

from fastapi import APIRouter, HTTPException
from logzero import logger

from insight_aitest.platform.services.device_manager import DeviceManager
from insight_aitest.platform.persistence.database import DatabaseManager
from performance.backend.routes.schemas import (
    StartMonitoringRequest,
    StopMonitoringRequest,
    SessionResponse,
)

# 清除单例缓存以确保使用新代码
DatabaseManager._instance = None

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.post("/start", response_model=SessionResponse)
async def start_monitoring(request: StartMonitoringRequest):
    """开始监控"""
    try:
        # 将告警阈值转换为字典格式
        alert_thresholds_dict = None
        if request.alert_thresholds:
            alert_thresholds_dict = {
                "fps": request.alert_thresholds.fps,
                "memory": request.alert_thresholds.memory,
                "cpu": request.alert_thresholds.cpu,
                "temperature": request.alert_thresholds.temperature,
            }
            logger.info(f"使用自定义告警阈值: {alert_thresholds_dict}")
        else:
            logger.info("使用默认告警阈值")

        # 传递采样间隔、平台和告警阈值到核心层
        session = await DeviceManager.start_session(
            request.device_id,
            request.app_package,
            platform=request.platform,  # 添加平台参数
            sampling_interval=request.sampling_interval,
            alert_thresholds=alert_thresholds_dict,  # 添加告警阈值参数
            project_id=request.project_id,
        )
        logger.info(
            f"启动监控会话: {session.id}, 平台: {request.platform}, 采样间隔: {request.sampling_interval}ms"
        )

        return SessionResponse(
            id=session.id,
            device_id=session.device_id,
            app_package=session.app_package,
            app_name=session.app_name,
            platform=getattr(session, "platform", "android"),
            status=session.status.value,
            start_time=session.start_time.isoformat(),
            end_time=session.end_time.isoformat() if session.end_time else None,
            duration=session.duration,
            project_id=session.project_id,
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
async def list_sessions(limit: int = 100, project_id: int | None = None):
    """列出所有会话（可按项目过滤）"""
    try:
        import os

        db_path = os.path.join(os.path.expanduser("~"), ".insight_eye", "monitoring.db")
        db = DatabaseManager(db_path)
        sessions = db.list_sessions(limit=limit, project_id=project_id)

        return [
            SessionResponse(
                id=s.id,
                device_id=s.device_id,
                app_package=s.app_package,
                platform=getattr(s, "platform", "android"),
                status=s.status.value,
                start_time=s.start_time.isoformat(),
                end_time=s.end_time.isoformat() if s.end_time else None,
                duration=s.duration,
                project_id=s.project_id,
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
            app_name=session.app_name,
            platform=getattr(session, "platform", "android"),
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

        # 映射字段名以匹配前端期望的格式
        # MetricsData是dataclass，需要使用属性访问而不是字典访问
        formatted_metrics = []
        for m in metrics:
            formatted_metric = {
                "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                "fps": m.fps,
                "cpu_app": m.cpu,  # cpu -> cpu_app
                "memory_pss": m.memory,  # memory -> memory_pss
                "network_up_speed": m.network_up,  # network_up -> network_up_speed
                "network_down_speed": m.network_down,  # network_down -> network_down_speed
                "battery": m.battery,  # 电池电量百分比
                "temperature": m.temperature,  # 电池温度（摄氏度）
            }
            formatted_metrics.append(formatted_metric)

        return formatted_metrics
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
        # 简化实现：从数据库获取基础统计
        try:
            stats = db.get_session_statistics(session_id)
            return stats if stats else {}
        except Exception as stats_error:
            logger.debug(f"获取统计数据失败: {stats_error}，返回空统计")
            return {}
    except Exception as e:
        logger.error(f"获取会话统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/alerts")
async def get_session_alerts(session_id: int):
    """获取会话的告警记录"""
    try:
        import os

        # 在函数内动态导入以避免单例缓存问题
        from insight_aitest.platform.persistence.database import DatabaseManager

        db_path = os.path.join(os.path.expanduser("~"), ".insight_eye", "monitoring.db")

        # 强制清除单例缓存并创建新实例
        DatabaseManager._instance = None
        db = DatabaseManager(db_path)

        alerts = db.get_alerts(session_id=session_id)

        # 转换字段名以匹配前端期望的格式
        formatted_alerts = []
        for alert in alerts:
            formatted_alerts.append(
                {
                    "id": alert.get("id"),
                    "session_id": alert.get("session_id"),
                    "timestamp": alert.get("timestamp"),
                    "metric_type": alert.get("alert_type", "unknown"),
                    "severity": alert.get("severity", "warning"),
                    "description": alert.get("description", ""),
                    "threshold": alert.get("threshold_value"),
                    "current_value": alert.get("current_value"),
                }
            )

        return formatted_alerts
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

        return {"success": success_count, "failed": len(failed_ids), "failed_ids": failed_ids}
    except Exception as e:
        logger.error(f"批量删除会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
