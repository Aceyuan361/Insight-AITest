# -*- coding: utf-8 -*-
"""API 自动化执行数据模型（spec E §3 + P0-1 ORM 迁移）。

RunRecord = 一次执行；StepResult = 单步结果。执行历史不可变（快照式）。

P0-1：RunRecord 从手写 dataclass 改为 ``MappedAsDataclass`` ORM 模型，
同名同字段替换——业务层（routes/executor/tests）用法不变。
- steps 嵌在 ``results_json`` 的 JSON 列（StepResult 仍是 dataclass，序列化为 list[dict]）；
  RunDatabase.create_run/get_run 负责 StepResult ↔ dict 桥接（既有模式）。
- 枚举字段（RunStatus）Python 侧仍是枚举，存 ``.value`` TEXT。
- StepResult 是单步结果的内存/dataclass 模型，不入 ORM（嵌 JSON 列）。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import JSON, DateTime, Enum as SAEnum, Index, Integer, Text
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from insight_aitest.platform.persistence import Base
from insight_aitest.platform.persistence.types import enum_values


class RunStatus(Enum):  # NOTE: 与 ui/models.py RunStatus 重复；跨模块抽取影响 149 处引用，暂保留
    PASSED = "passed"  # 全部断言通过
    FAILED = "failed"  # 有断言不通过（请求已发出）
    ERROR = "error"  # 引擎/环境异常（网络错、JSON 解析失败、变量未定义等）


@dataclass
class StepResult:
    """单步结果（内存模型，嵌在 RunRecord.results_json 的 JSON 列里，不入 ORM）。"""

    step_index: int  # 0-based
    request: dict  # 实际发出的 {method, url, headers, body}
    status_code: int | None  # 响应状态码（请求失败则 None）
    response_body: Any  # 响应体（优先 JSON，失败存原始文本，超 64KB 截断）
    response_headers: dict  # 响应头
    elapsed_ms: int  # 耗时
    assertions: list[dict]  # [{type, target, expected, actual, passed}]
    extracts: dict  # 本步提取到的 {var_name: value}
    error: str | None  # 本步异常（None=正常）
    passed: bool  # 本步断言全过 = True


class RunRecord(MappedAsDataclass, Base, kw_only=True):
    """执行记录（ORM 模型，即业务层 DTO）。

    ``steps`` 对应 DB 列 ``results_json``（JSON）。Python 侧是 list[StepResult]；
    RunDatabase.create_run/get_run 负责 StepResult 对象 ↔ dict 的序列化桥接。
    类级 ``kw_only=True``：所有字段仅关键字传参（executor 已全用 kw），
    回避 dataclass 的默认参数后跟非默认参数顺序约束。
    """

    __test__ = False
    __tablename__ = "runs"
    __table_args__ = (
        Index("idx_runs_case", "case_id"),
        Index("idx_runs_status", "status"),
    )

    id: Mapped[int | None] = mapped_column(
        Integer, primary_key=True, autoincrement=True, default=None
    )
    case_id: Mapped[int] = mapped_column(Integer)
    case_title: Mapped[str] = mapped_column(Text)
    case_snapshot: Mapped[dict] = mapped_column(JSON)
    status: Mapped[RunStatus] = mapped_column(SAEnum(RunStatus, values_callable=enum_values))
    total_steps: Mapped[int] = mapped_column(Integer)
    passed_steps: Mapped[int] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[datetime] = mapped_column(DateTime)
    duration_ms: Mapped[int] = mapped_column(Integer)
    steps: Mapped[list] = mapped_column("results_json", JSON)
    project_id: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    error: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default_factory=datetime.now)
