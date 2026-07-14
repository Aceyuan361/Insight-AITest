# -*- coding: utf-8 -*-
"""套件数据模型（spec E.1 §2 + P0-1 ORM 迁移）。

P0-1：Suite/SuiteRunRecord 从手写 dataclass 改为 ``MappedAsDataclass`` ORM 模型，
同名同字段替换——业务层（routes/suite_executor/tests）用法不变。
- case_ids/setup/teardown/suite_snapshot/case_run_ids 均为 list/dict，存 JSON 列（原生 JSON）。
- 枚举字段（SuiteRunStatus）Python 侧仍是枚举，存 ``.value`` TEXT。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, DateTime, Enum as SAEnum, Index, Integer, Text
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from insight_aitest.platform.persistence import Base
from insight_aitest.platform.persistence.types import enum_values


class SuiteRunStatus(Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class Suite(MappedAsDataclass, Base, kw_only=True):
    """套件（ORM 模型，即业务层 DTO）。case_ids/setup/teardown 存 JSON 列。"""

    __test__ = False
    __tablename__ = "suites"

    id: Mapped[int | None] = mapped_column(
        Integer, primary_key=True, autoincrement=True, default=None
    )
    name: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    case_ids: Mapped[list[int]] = mapped_column("case_ids_json", JSON, default_factory=list)
    setup: Mapped[list] = mapped_column("setup_json", JSON, default_factory=list)
    teardown: Mapped[list] = mapped_column("teardown_json", JSON, default_factory=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default_factory=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default_factory=datetime.now)


class SuiteRunRecord(MappedAsDataclass, Base, kw_only=True):
    """套件执行记录（ORM 模型，即业务层 DTO）。suite_snapshot/case_run_ids 存 JSON 列。"""

    __test__ = False
    __tablename__ = "suite_runs"
    __table_args__ = (
        Index("idx_suite_runs_suite", "suite_id"),
        Index("idx_suite_runs_status", "status"),
    )

    id: Mapped[int | None] = mapped_column(
        Integer, primary_key=True, autoincrement=True, default=None
    )
    suite_id: Mapped[int] = mapped_column(Integer)
    suite_name: Mapped[str] = mapped_column(Text)
    suite_snapshot: Mapped[dict] = mapped_column("suite_snapshot_json", JSON)
    environment_id: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    environment_name: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    status: Mapped[SuiteRunStatus] = mapped_column(
        SAEnum(SuiteRunStatus, values_callable=enum_values)
    )
    total: Mapped[int] = mapped_column(Integer)
    done: Mapped[int] = mapped_column(Integer)
    case_run_ids: Mapped[list[int]] = mapped_column("case_run_ids_json", JSON)
    setup_status: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    started_at: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    error: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default_factory=datetime.now)
