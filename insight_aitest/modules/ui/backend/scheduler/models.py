# -*- coding: utf-8 -*-
"""UI 定时调度 ORM 模型。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Index, Integer, Text
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from insight_aitest.platform.persistence import Base


class ScheduledUIBatch(MappedAsDataclass, Base, kw_only=True):
    """UI 定时批量执行任务。"""

    __tablename__ = "ui_scheduled_batches"
    __table_args__ = (
        Index("idx_ui_sched_enabled", "enabled"),
    )

    id: Mapped[int | None] = mapped_column(
        Integer, primary_key=True, autoincrement=True, default=None
    )
    name: Mapped[str] = mapped_column(Text)
    cron_expression: Mapped[str] = mapped_column(Text)  # 5 段 cron
    case_ids: Mapped[list] = mapped_column(JSON)  # [int, ...]
    config: Mapped[dict] = mapped_column(JSON)  # {base_url?, browser_config?}
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    last_status: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    last_batch_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default_factory=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default_factory=datetime.now)
