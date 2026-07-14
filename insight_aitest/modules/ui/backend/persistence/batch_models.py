# -*- coding: utf-8 -*-
"""UI 批量执行数据模型。

UIBatchRun = 一次批量执行（勾选多个 UI 用例，共享配置，顺序执行）。
case_run_ids 关联每条 case 的子 RunRecord id（来自 ui_runs 表）。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, DateTime, Enum as SAEnum, Index, Integer, Text
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from insight_aitest.platform.persistence import Base
from insight_aitest.platform.persistence.types import enum_values


class BatchRunStatus(Enum):
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"


class UIBatchRun(MappedAsDataclass, Base, kw_only=True):
    """批量执行记录（ORM 模型）。"""

    __tablename__ = "ui_batch_runs"
    __table_args__ = (
        Index("idx_ui_batch_status", "status"),
    )

    id: Mapped[int | None] = mapped_column(
        Integer, primary_key=True, autoincrement=True, default=None
    )
    name: Mapped[str] = mapped_column(Text)
    case_ids: Mapped[list] = mapped_column(JSON)  # [int, int, ...]
    config: Mapped[dict] = mapped_column(JSON)  # {base_url?, browser_config?}
    status: Mapped[BatchRunStatus] = mapped_column(
        SAEnum(BatchRunStatus, values_callable=enum_values)
    )
    total: Mapped[int] = mapped_column(Integer)
    passed: Mapped[int] = mapped_column(Integer)
    failed: Mapped[int] = mapped_column(Integer)
    error: Mapped[int] = mapped_column(Integer)
    case_run_ids: Mapped[list] = mapped_column(JSON)  # [int, ...] 子 run id
    started_at: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default_factory=datetime.now)
