# -*- coding: utf-8 -*-
"""UI 定时调度管理器（APScheduler 单例）。

复用 API 模块 scheduler/manager.py 的模式（BackgroundScheduler + CronTrigger）。
jobs 从 DB 重建（scheduler 重启时从 ui_scheduled_batches 表恢复）。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _parse_cron(expr: str) -> dict:
    """将 5 段 cron 表达式解析为 APScheduler CronTrigger 参数。"""
    parts = expr.strip().split()
    if len(parts) != 5:
        raise ValueError(f"cron 表达式必须是 5 段（分 时 日 月 周），收到: {expr}")
    return {
        "minute": parts[0],
        "hour": parts[1],
        "day": parts[2],
        "month": parts[3],
        "day_of_week": parts[4],
    }


def _run_scheduled_ui_batch(sched_id: int) -> None:
    """定时任务回调：执行批量 UI 用例并记录结果。"""
    import insight_aitest.modules.ui.backend.deps as ui_deps
    from insight_aitest.modules.ui.backend.scheduler.database import ScheduledUIBatchDatabase

    db_path = ui_deps._DB_PATH
    sched_db = ScheduledUIBatchDatabase(db_path)
    sched = sched_db.get(sched_id)
    if sched is None or not sched.enabled:
        return

    case_ids = sched.case_ids
    if not case_ids:
        logger.warning(f"定时任务 {sched_id}: case_ids 为空，跳过")
        return

    config = sched.config or {}
    base_url = config.get("base_url")
    browser_config = config.get("browser_config")

    # 创建 batch run 记录
    from insight_aitest.modules.ui.backend.persistence.batch_models import (
        BatchRunStatus,
        UIBatchRun,
    )

    batch_db = ui_deps.get_batch_db()
    batch = UIBatchRun(
        id=None,
        name=f"[定时] {sched.name}",
        case_ids=case_ids,
        config=config,
        status=BatchRunStatus.RUNNING,
        total=len(case_ids),
        passed=0,
        failed=0,
        error=0,
        case_run_ids=[],
        started_at=datetime.now(),
        finished_at=None,
    )
    batch_id = batch_db.create(batch)

    # 在事件循环中执行（APScheduler 回调在后台线程，需新建事件循环）
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        from insight_aitest.modules.ui.backend.routes.batch import _run_batch_task
        loop.run_until_complete(
            _run_batch_task(batch_id, case_ids, base_url, browser_config)
        )
        loop.close()

        result_batch = batch_db.get(batch_id)
        status = result_batch.status.value if result_batch and result_batch.status else "unknown"
        sched_db.record_run(sched_id, status, batch_id)
    except Exception as e:
        logger.exception(f"定时任务 {sched_id} 执行异常")
        sched_db.record_run(sched_id, "error", batch_id)


class UISchedulerManager:
    """调度管理器（延迟初始化单例）。"""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._sched: BackgroundScheduler | None = None

    @property
    def scheduler(self) -> BackgroundScheduler:
        if self._sched is None:
            self._sched = BackgroundScheduler(daemon=True)
            self._sched.start()
            self._reload_jobs()
        return self._sched

    def _reload_jobs(self) -> None:
        from insight_aitest.modules.ui.backend.scheduler.database import ScheduledUIBatchDatabase

        sched_db = ScheduledUIBatchDatabase(self.db_path)
        self._sched.remove_all_jobs()
        for sched in sched_db.list_enabled():
            try:
                cron_params = _parse_cron(sched.cron_expression)
                self._sched.add_job(
                    _run_scheduled_ui_batch,
                    trigger=CronTrigger(**cron_params),
                    args=[sched.id],
                    id=f"ui_sched_{sched.id}",
                    replace_existing=True,
                )
                logger.info(f"重建 UI 定时任务: ui_sched_{sched.id} ({sched.name}) cron={sched.cron_expression}")
            except Exception as e:
                logger.error(f"重建 UI 定时任务 {sched.id} 失败: {e}")

    def add_job(self, sched_id: int, cron_expression: str) -> bool:
        try:
            cron_params = _parse_cron(cron_expression)
            self.scheduler.add_job(
                _run_scheduled_ui_batch,
                trigger=CronTrigger(**cron_params),
                args=[sched_id],
                id=f"ui_sched_{sched_id}",
                replace_existing=True,
            )
            return True
        except Exception as e:
            logger.error(f"添加 UI 定时任务 {sched_id} 失败: {e}")
            return False

    def remove_job(self, sched_id: int) -> None:
        job_id = f"ui_sched_{sched_id}"
        if self._sched and self._sched.get_job(job_id):
            self._sched.remove_job(job_id)

    def reload(self) -> None:
        if self._sched:
            self._reload_jobs()

    def trigger_now(self, sched_id: int) -> bool:
        try:
            self.scheduler.add_job(
                _run_scheduled_ui_batch,
                args=[sched_id],
                id=f"ui_trigger_{sched_id}_{datetime.now().strftime('%H%M%S')}",
            )
            return True
        except Exception as e:
            logger.error(f"手动触发 UI 定时任务 {sched_id} 失败: {e}")
            return False

    def shutdown(self) -> None:
        if self._sched:
            self._sched.shutdown(wait=False)
            self._sched = None


_manager: UISchedulerManager | None = None


def get_ui_scheduler_manager(db_path: str | None = None) -> UISchedulerManager:
    global _manager
    import insight_aitest.modules.ui.backend.deps as ui_deps
    if _manager is None:
        _manager = UISchedulerManager(db_path or ui_deps._DB_PATH)
    return _manager
