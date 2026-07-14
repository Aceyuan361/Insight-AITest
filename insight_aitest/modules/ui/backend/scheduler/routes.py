# -*- coding: utf-8 -*-
"""UI 定时调度 API。

端点：
  POST   /schedules          创建定时任务
  GET    /schedules          列出所有定时任务
  GET    /schedules/{id}     定时任务详情
  PUT    /schedules/{id}     更新定时任务
  DELETE /schedules/{id}     删除定时任务
  POST   /schedules/{id}/run 立即触发一次
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from insight_aitest.modules.ui.backend.scheduler.database import ScheduledUIBatchDatabase
from insight_aitest.modules.ui.backend.scheduler.manager import get_ui_scheduler_manager

router = APIRouter(prefix="/schedules", tags=["ui"])


def _get_sched_db() -> ScheduledUIBatchDatabase:
    import insight_aitest.modules.ui.backend.deps as ui_deps
    return ScheduledUIBatchDatabase(ui_deps._DB_PATH)


class SchedCreate(BaseModel):
    name: str
    cron_expression: str = "* * * * *"
    case_ids: list[int] = []
    base_url: str | None = None
    browser_config: dict | None = None
    enabled: bool = True


class SchedUpdate(BaseModel):
    name: str | None = None
    cron_expression: str | None = None
    case_ids: list[int] | None = None
    base_url: str | None = None
    browser_config: dict | None = None
    enabled: bool | None = None


def _sched_out(s) -> dict:
    config = s.config or {}
    return {
        "id": s.id,
        "name": s.name,
        "cron_expression": s.cron_expression,
        "case_ids": s.case_ids,
        "base_url": config.get("base_url"),
        "browser_config": config.get("browser_config"),
        "enabled": s.enabled,
        "last_run_at": s.last_run_at.isoformat() if s.last_run_at else None,
        "last_status": s.last_status,
        "last_batch_run_id": s.last_batch_run_id,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


@router.post("", status_code=201)
async def create_schedule(body: SchedCreate) -> dict:
    db = _get_sched_db()
    from insight_aitest.modules.ui.backend.scheduler.manager import _parse_cron
    try:
        _parse_cron(body.cron_expression)
    except ValueError as e:
        raise HTTPException(422, str(e))
    if not body.case_ids:
        raise HTTPException(422, "请至少选择一个用例")
    sid = db.create(
        name=body.name,
        cron_expression=body.cron_expression,
        case_ids=body.case_ids,
        config={"base_url": body.base_url, "browser_config": body.browser_config},
        enabled=body.enabled,
    )
    if body.enabled:
        get_ui_scheduler_manager().add_job(sid, body.cron_expression)
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
    if body.cron_expression:
        from insight_aitest.modules.ui.backend.scheduler.manager import _parse_cron
        try:
            _parse_cron(body.cron_expression)
        except ValueError as e:
            raise HTTPException(422, str(e))

    # 构建 config 更新
    existing = db.get(sched_id)
    config = existing.config or {}
    if body.base_url is not None:
        config["base_url"] = body.base_url
    if body.browser_config is not None:
        config["browser_config"] = body.browser_config

    kwargs = body.model_dump(exclude_none=True)
    # 移除 base_url/browser_config（它们嵌套在 config 里）
    kwargs.pop("base_url", None)
    kwargs.pop("browser_config", None)
    kwargs["config"] = config

    db.update(sched_id, **kwargs)
    updated = db.get(sched_id)
    mgr = get_ui_scheduler_manager()
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
    get_ui_scheduler_manager().remove_job(sched_id)
    return {"deleted": sched_id}


@router.post("/{sched_id}/run")
async def trigger_schedule(sched_id: int) -> dict:
    db = _get_sched_db()
    if not db.get(sched_id):
        raise HTTPException(404, "定时任务不存在")
    if not get_ui_scheduler_manager().trigger_now(sched_id):
        raise HTTPException(500, "触发失败")
    return {"triggered": sched_id}
