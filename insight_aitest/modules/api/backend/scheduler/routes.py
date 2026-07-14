# -*- coding: utf-8 -*-
"""定时调度任务 API。

端点：
  POST   /schedules          创建定时任务
  GET    /schedules          列出所有定时任务
  GET    /schedules/{id}     定时任务详情
  PUT    /schedules/{id}     更新定时任务
  DELETE /schedules/{id}     删除定时任务
  POST   /schedules/{id}/run 立即触发一次
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from insight_aitest.modules.api.backend.scheduler.database import ScheduledSuiteDatabase
from insight_aitest.modules.api.backend.scheduler.manager import get_scheduler_manager

router = APIRouter(prefix="/schedules", tags=["api"])


def _get_sched_db() -> ScheduledSuiteDatabase:
    import os
    db_path = os.path.expanduser("~/.insight_eye/api.db")
    return ScheduledSuiteDatabase(db_path)


class SchedCreate(BaseModel):
    name: str
    suite_id: int
    cron_expression: str = "* * * * *"
    environment_id: int | None = None
    enabled: bool = True


class SchedUpdate(BaseModel):
    name: str | None = None
    suite_id: int | None = None
    cron_expression: str | None = None
    environment_id: int | None = None
    enabled: bool | None = None


def _sched_out(s) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "suite_id": s.suite_id,
        "cron_expression": s.cron_expression,
        "environment_id": s.environment_id,
        "enabled": s.enabled,
        "last_run_at": s.last_run_at.isoformat() if s.last_run_at else None,
        "last_status": s.last_status,
        "last_suite_run_id": s.last_suite_run_id,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


@router.post("", status_code=201)
async def create_schedule(body: SchedCreate) -> dict:
    db = _get_sched_db()
    # 验证 cron 表达式
    from insight_aitest.modules.api.backend.scheduler.manager import _parse_cron
    try:
        _parse_cron(body.cron_expression)
    except ValueError as e:
        raise HTTPException(422, str(e))
    sid = db.create(
        name=body.name, suite_id=body.suite_id, cron_expression=body.cron_expression,
        environment_id=body.environment_id, enabled=body.enabled,
    )
    # 添加到 scheduler
    if body.enabled:
        get_scheduler_manager().add_job(sid, body.cron_expression)
    return _sched_out(db.get(sid))


@router.get("")
async def list_schedules() -> list[dict]:
    db = _get_sched_db()
    return [_sched_out(s) for s in db.list()]


@router.get("/{sched_id}")
async def get_schedule(sched_id: int) -> dict:
    db = _get_sched_db()
    s = db.get(sched_id)
    if not s:
        raise HTTPException(404, "定时任务不存在")
    return _sched_out(s)


@router.put("/{sched_id}")
async def update_schedule(sched_id: int, body: SchedUpdate) -> dict:
    db = _get_sched_db()
    if not db.get(sched_id):
        raise HTTPException(404, "定时任务不存在")
    # 验证 cron
    if body.cron_expression:
        from insight_aitest.modules.api.backend.scheduler.manager import _parse_cron
        try:
            _parse_cron(body.cron_expression)
        except ValueError as e:
            raise HTTPException(422, str(e))
    db.update(sched_id, **body.model_dump(exclude_none=True))
    updated = db.get(sched_id)
    # 同步 scheduler job
    mgr = get_scheduler_manager()
    if updated.enabled:
        mgr.add_job(sched_id, updated.cron_expression)
    else:
        mgr.remove_job(sched_id)
    return _sched_out(updated)


@router.delete("/{sched_id}")
async def delete_schedule(sched_id: int) -> dict:
    db = _get_sched_db()
    if not db.delete(sched_id):
        raise HTTPException(404, "定时任务不存在")
    get_scheduler_manager().remove_job(sched_id)
    return {"deleted": sched_id}


@router.post("/{sched_id}/run")
async def trigger_schedule(sched_id: int) -> dict:
    """立即触发一次执行（不等 cron）。"""
    db = _get_sched_db()
    if not db.get(sched_id):
        raise HTTPException(404, "定时任务不存在")
    if not get_scheduler_manager().trigger_now(sched_id):
        raise HTTPException(500, "触发失败")
    return {"triggered": sched_id}
