# -*- coding: utf-8 -*-
"""定时调度任务数据模型。

ScheduledSuite 表存储 cron 调度配置。APScheduler 持久化用内存 JobStore
（调度配置自身存 SQLite，scheduler 重启时从 DB 重建 jobs）。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, Text
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from insight_aitest.platform.persistence import Base


class ScheduledSuite(MappedAsDataclass, Base, kw_only=True):
    """定时执行任务（ORM 模型）。"""

    __test__ = False
    __tablename__ = "scheduled_suites"
    __table_args__ = (
        Index("idx_scheduled_enabled", "enabled"),
    )

    id: Mapped[int | None] = mapped_column(
        Integer, primary_key=True, autoincrement=True, default=None
    )
    name: Mapped[str] = mapped_column(Text, default="")
    suite_id: Mapped[int] = mapped_column(Integer)
    cron_expression: Mapped[str] = mapped_column(Text, default="* * * * *")
    environment_id: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    last_status: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    last_suite_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default_factory=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default_factory=datetime.now)
