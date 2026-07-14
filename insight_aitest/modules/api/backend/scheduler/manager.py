# -*- coding: utf-8 -*-
"""APScheduler 调度管理器（单例）。

- 模块加载时启动 BackgroundScheduler（APScheduler 后台线程）
- jobs 从 DB 重建（scheduler 重启时从 ScheduledSuite 表恢复）
- cron 表达式格式：分 时 日 月 周（标准 5 段 cron）
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

if TYPE_CHECKING:
    from insight_aitest.modules.api.backend.scheduler.database import ScheduledSuiteDatabase

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _parse_cron(expr: str) -> dict:
    """将 5 段 cron 表达式解析为 APScheduler CronTrigger 参数。

    格式: minute hour day month day_of_week
    """
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


def _run_scheduled_suite(sched_id: int) -> None:
    """定时任务回调：执行套件并记录结果。

    延迟 import 避免循环依赖。
    """
    import insight_aitest.modules.api.backend.deps as api_deps
    from insight_aitest.modules.api.backend.scheduler.database import ScheduledSuiteDatabase
    from insight_aitest.modules.api.backend.routes.suites import _run_suite_task

    db_path = api_deps._DB_PATH
    sched_db = ScheduledSuiteDatabase(db_path)
    sched = sched_db.get(sched_id)
    if sched is None or not sched.enabled:
        return

    suite_db = api_deps.get_suite_db()
    suite_run_db = api_deps.get_suite_run_db()
    env_db = api_deps.get_env_db()

    suite = suite_db.get(sched.suite_id)
    if suite is None:
        logger.warning(f"定时任务 {sched_id}: 套件 {sched.suite_id} 不存在，跳过")
        return

    env = None
    if sched.environment_id is not None:
        env = env_db.get(sched.environment_id)

    from datetime import datetime
    from insight_aitest.modules.api.backend.persistence.suite_models import SuiteRunRecord, SuiteRunStatus

    sr = SuiteRunRecord(
        id=None,
        suite_id=suite.id,
        suite_name=suite.name,
        suite_snapshot={
            "case_ids": suite.case_ids,
            "setup": suite.setup,
            "teardown": suite.teardown,
        },
        environment_id=sched.environment_id,
        environment_name=env.name if env else None,
        status=SuiteRunStatus.RUNNING,
        total=len(suite.case_ids),
        done=0,
        case_run_ids=[],
        setup_status=None,
        started_at=datetime.now(),
        finished_at=None,
        error=None,
    )
    srid = suite_run_db.create(sr)

    suite_def = {
        "id": suite.id, "name": suite.name,
        "case_ids": suite.case_ids, "setup": suite.setup, "teardown": suite.teardown,
    }
    try:
        _run_suite_task(srid, suite_def, env, suite_run_db)
        from insight_aitest.modules.api.backend.persistence.suite_models import SuiteRunStatus
        result_sr = suite_run_db.get(srid)
        status = result_sr.status.value if result_sr and result_sr.status else "unknown"
        sched_db.record_run(sched_id, status, srid)
    except Exception as e:
        logger.exception(f"定时任务 {sched_id} 执行异常")
        sched_db.record_run(sched_id, "error", srid)


class SchedulerManager:
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
        """从 DB 重建所有 enabled 的 jobs。"""
        from insight_aitest.modules.api.backend.scheduler.database import ScheduledSuiteDatabase

        sched_db = ScheduledSuiteDatabase(self.db_path)
        # 清除旧 jobs
        self._sched.remove_all_jobs()
        for sched in sched_db.list_enabled():
            try:
                cron_params = _parse_cron(sched.cron_expression)
                self._sched.add_job(
                    _run_scheduled_suite,
                    trigger=CronTrigger(**cron_params),
                    args=[sched.id],
                    id=f"sched_{sched.id}",
                    replace_existing=True,
                )
                logger.info(f"重建定时任务: sched_{sched.id} ({sched.name}) cron={sched.cron_expression}")
            except Exception as e:
                logger.error(f"重建定时任务 {sched.id} 失败: {e}")

    def add_job(self, sched_id: int, cron_expression: str) -> bool:
        """添加或更新一个调度 job。"""
        try:
            cron_params = _parse_cron(cron_expression)
            self.scheduler.add_job(
                _run_scheduled_suite,
                trigger=CronTrigger(**cron_params),
                args=[sched_id],
                id=f"sched_{sched_id}",
                replace_existing=True,
            )
            return True
        except Exception as e:
            logger.error(f"添加定时任务 {sched_id} 失败: {e}")
            return False

    def remove_job(self, sched_id: int) -> None:
        """移除调度 job。"""
        job_id = f"sched_{sched_id}"
        if self._sched and self._sched.get_job(job_id):
            self._sched.remove_job(job_id)

    def reload(self) -> None:
        """手动重建所有 jobs（配置变更后调用）。"""
        if self._sched:
            self._reload_jobs()

    def trigger_now(self, sched_id: int) -> bool:
        """立即触发一次执行（不等 cron）。"""
        try:
            self.scheduler.add_job(
                _run_scheduled_suite,
                args=[sched_id],
                id=f"trigger_{sched_id}_{datetime.now().strftime('%H%M%S')}",
            )
            return True
        except Exception as e:
            logger.error(f"手动触发任务 {sched_id} 失败: {e}")
            return False

    def shutdown(self) -> None:
        if self._sched:
            self._sched.shutdown(wait=False)
            self._sched = None


# 单例
_manager: SchedulerManager | None = None


def get_scheduler_manager(db_path: str | None = None) -> SchedulerManager:
    global _manager
    import insight_aitest.modules.api.backend.deps as api_deps
    if _manager is None:
        _manager = SchedulerManager(db_path or api_deps._DB_PATH)
    return _manager
