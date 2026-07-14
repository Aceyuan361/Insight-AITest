# -*- coding: utf-8 -*-
"""UI 自动化执行数据模型（spec F §5 + P0-1 ORM 迁移）。

RunRecord = 一次执行；UIStepResult = 单步结果。执行历史不可变（快照式）。
字段与 E 的 StepResult 有差异：UI 步骤是视觉驱动，有 screenshot/action_log/assert_passed。

P0-1：RunRecord 从手写 dataclass 改为 ``MappedAsDataclass`` ORM 模型，
同名同字段替换——业务层（routes/executor/tests）用法不变。
- steps 嵌在 ``results_json`` 的 JSON 列（UIStepResult 仍是 dataclass，序列化为 list[dict]）；
  UIRunDatabase.create_run/get_run 负责 UIStepResult ↔ dict 桥接（既有模式）。
- 枚举字段（RunStatus）Python 侧仍是枚举，存 ``.value`` TEXT。
- UIStepResult 是单步结果的内存/dataclass 模型，不入 ORM（嵌 JSON 列）。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, DateTime, Enum as SAEnum, Index, Integer, Text
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from insight_aitest.platform.persistence import Base
from insight_aitest.platform.persistence.types import enum_values


class RunStatus(Enum):  # NOTE: 与 api/models.py RunStatus 重复；跨模块抽取影响 149 处引用，暂保留
    PASSED = "passed"  # 全部步骤通过（assert 全真）
    FAILED = "failed"  # 有 assert 失败（操作已执行）
    ERROR = "error"  # 引擎/环境异常（浏览器崩溃、LLM 调用失败、变量未定义等）


@dataclass
class UIStepResult:
    """单步结果（内存模型，嵌在 RunRecord.results_json 的 JSON 列里，不入 ORM）。"""

    step_index: int  # 0-based
    kind: str  # action | assert | extract
    prompt: str  # 归一化后的整句（实际喂给 Midscene 的）
    screenshot: str | None  # 截图路径（失败步必截）
    action_log: str | None  # Midscene 返回的操作日志（成功时）
    assert_passed: bool | None  # assert 步：True/False；非 assert 步 None
    extracts: dict  # 本步提取到的 {var_name: value}
    elapsed_ms: int
    error: str | None  # 本步异常（None=正常）
    passed: bool  # error is None 且（非 assert 步 或 assert_passed）


class RunRecord(MappedAsDataclass, Base, kw_only=True):
    """执行记录（ORM 模型，即业务层 DTO）。

    ``steps`` 对应 DB 列 ``results_json``（JSON）。Python 侧是 list[UIStepResult]；
    UIRunDatabase.create_run/get_run 负责 UIStepResult 对象 ↔ dict 的序列化桥接。
    类级 ``kw_only=True``：所有字段仅关键字传参（executor 已全用 kw）。
    """

    __test__ = False
    __tablename__ = "ui_runs"
    __table_args__ = (
        Index("idx_ui_runs_case", "case_id"),
        Index("idx_ui_runs_status", "status"),
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
    base_url_used: Mapped[str] = mapped_column(Text)
    project_id: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    error: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default_factory=datetime.now)
