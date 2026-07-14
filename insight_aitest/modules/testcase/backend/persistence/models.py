# -*- coding: utf-8 -*-
"""测试用例数据模型（spec D §3.2/§3.3 + P0-1 ORM 迁移）。

首版实现功能用例（FUNCTIONAL），API/性能/UI 预埋待对应子系统就绪后激活。

P0-1 迁移：``TestCase`` 从手写 dataclass 改为 ``MappedAsDataclass`` ORM 模型，
同名同字段替换——业务层（routes/generator/tests）构造与属性访问用法不变。
枚举字段 Python 侧仍是枚举，存储为 ``.value`` TEXT（``values_callable``），
与旧库存字节兼容。tags 旧库存是逗号分隔 TEXT，用平台 ``CommaList`` 桥接。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, DateTime, Enum as SAEnum, Index, Integer, Text
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from insight_aitest.platform.persistence import Base
from insight_aitest.platform.persistence.types import CommaList, enum_values


class CaseType(Enum):
    FUNCTIONAL = "functional"  # 功能用例（首版实现）
    API = "api"  # 接口用例（预埋，E 就绪后激活）
    PERFORMANCE = "performance"  # 性能用例（预埋，B 就绪后激活）
    UI = "ui"  # UI 用例（预埋，F 就绪后激活）


class CaseStatus(Enum):
    DRAFT = "draft"  # 待审阅（刚生成或刚建，未确认）
    REVIEWED = "reviewed"  # 已审阅（人工确认内容正确）
    READY = "ready"  # 就绪（可导出执行）
    DEPRECATED = "deprecated"  # 废弃


class CasePriority(Enum):
    P0 = "p0"
    P1 = "p1"
    P2 = "p2"
    P3 = "p3"


class TestType(Enum):
    """测试设计方法（生成时用，代入资深测试思维）。"""

    __test__ = False  # 避免 pytest 误收集（类名以 Test 开头）
    POSITIVE = "positive"  # 正向
    NEGATIVE = "negative"  # 异常/反向
    BOUNDARY = "boundary"  # 边界值
    EDGE = "edge"  # 极端场景


# SAEnum 默认按 name 存（FUNCTIONAL），旧库存的是 .value（functional），故强制按 .value 存。


class TestCase(MappedAsDataclass, Base):
    """测试用例（ORM 模型，即业务层 DTO）。

    注意：``__test__ = False`` 避免 pytest 误收集（类名以 Test 开头）。
    字段顺序与默认值保持与原 dataclass 一致，构造用法不变。

    project_id/version_id：可空逻辑外键（跨 DB 文件，不加 FK 约束）。
    旧数据 NULL = 未分类。ensure_schema 幂等补列。
    task_id/batch_id：AI 生成用例的反向追溯（task_id→Agent task，batch_id→批次）。
    """

    __test__ = False
    __tablename__ = "testcases"
    __table_args__ = (
        Index("idx_testcases_type", "type"),
        Index("idx_testcases_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, init=False)
    title: Mapped[str] = mapped_column(Text, default="")
    type: Mapped[CaseType] = mapped_column(
        SAEnum(CaseType, values_callable=enum_values), default=CaseType.FUNCTIONAL
    )
    description: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[CasePriority] = mapped_column(
        SAEnum(CasePriority, values_callable=enum_values), default=CasePriority.P2
    )
    status: Mapped[CaseStatus] = mapped_column(
        SAEnum(CaseStatus, values_callable=enum_values), default=CaseStatus.DRAFT
    )
    test_design: Mapped[TestType] = mapped_column(
        SAEnum(TestType, values_callable=enum_values), default=TestType.POSITIVE
    )
    preconditions: Mapped[str] = mapped_column(Text, default="")
    content: Mapped[dict] = mapped_column("content_json", JSON, default_factory=dict)
    tags: Mapped[list[str]] = mapped_column(CommaList, default_factory=list)
    source: Mapped[str] = mapped_column(Text, default="manual")  # "manual" | "ai:glm-4-flash"
    project_id: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    version_id: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    task_id: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    batch_id: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, default=None
    )  # 闭环支撑：E/F 执行后回填
    last_result: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None
    )  # pass|fail|blocked|error
    created_at: Mapped[datetime] = mapped_column(DateTime, default_factory=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default_factory=datetime.now)
