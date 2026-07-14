# -*- coding: utf-8 -*-
"""AI 模块数据模型（瘦身后 + P0-1 ORM 迁移）。

KB 相关模型（Document/Chunk/ParsedDocument/ScoredChunk/DocumentStatus/EmbedStatus）
已上提为 platform.services.kb.models。这里只保留会话/消息相关：Conversation/Message/Role/Citation。

P0-1：Conversation/Message 从手写 dataclass 改为 ``MappedAsDataclass`` ORM 模型，
同名同字段替换——业务层（routes/agent/tests）用法不变。
- 枚举字段（Role）Python 侧仍是枚举，存储 ``.value`` TEXT（``values_callable``）。
- Message 的 citations 嵌在 ``citations_json`` 的 JSON 列（存 Citation 的 dict 列表）；
  ``add_message``/``list_messages`` 负责 Citation↔dict 桥接（既有模式，非新增开销）。
- rag_enabled 存 INTEGER 0/1（与旧库一致），Python 侧 bool。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, Boolean, DateTime, Enum as SAEnum, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from insight_aitest.platform.persistence import Base
from insight_aitest.platform.persistence.types import enum_values


class Role(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Conversation(MappedAsDataclass, Base):
    """会话（ORM 模型，即业务层 DTO）。"""

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, init=False)
    title: Mapped[str] = mapped_column(Text, default="新会话")
    # server_default="1" 让 DB 端有默认（迁移用裸 INSERT 不传 rag_enabled 时兜底）；
    # default=True 是 Python 端 dataclass 默认（ORM 构造时用）。
    rag_enabled: Mapped[bool] = mapped_column(Boolean, server_default="1", default=True)
    # 思考级别：off/low/medium/high（off=普通对话，其余按模型族探测注入 reasoning 参数）
    thinking_level: Mapped[str] = mapped_column(Text, server_default="off", default="off")
    project_id: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    summary_json: Mapped[dict | None] = mapped_column("summary_json", JSON, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default_factory=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default_factory=datetime.now)


class Message(MappedAsDataclass, Base):
    """消息（ORM 模型，即业务层 DTO）。

    ``citations`` 对应 DB 列 ``citations_json``（JSON）。Python 侧是 list[Citation] 或 list[dict]；
    AIDatabase.add_message/list_messages 负责 Citation 对象 ↔ dict 的序列化桥接。
    """

    __tablename__ = "messages"
    __table_args__ = (
        Index("idx_messages_conversation", "conversation_id", "created_at"),
        Index("idx_messages_task", "task_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, init=False)
    conversation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("conversations.id", ondelete="CASCADE")
    )
    task_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=True, default=None
    )
    role: Mapped[Role] = mapped_column(SAEnum(Role, values_callable=enum_values), default=Role.USER)
    content: Mapped[str] = mapped_column(Text, default="")
    citations: Mapped[list | None] = mapped_column(
        "citations_json", JSON, nullable=True, default=None
    )
    thinking: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    attachments: Mapped[list | None] = mapped_column(
        "attachments_json", JSON, nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default_factory=datetime.now)


# 会话↔文档关联表（复合主键）。无独立业务 DTO，仅持久化用。
class ConversationDocument(MappedAsDataclass, Base):
    __tablename__ = "conversation_documents"

    conversation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("conversations.id", ondelete="CASCADE"), primary_key=True
    )
    document_id: Mapped[int] = mapped_column(Integer, primary_key=True)


@dataclass
class Citation:
    """Agent 输出 / 存入 messages.citations_json。不入库为独立表（嵌 JSON 列）。"""

    document_id: int
    document_name: str
    chunk_index: int
    snippet: str
    score: float


# ============ Agent Task（子项目2）============


class TaskStatus(str, Enum):
    """Agent 任务状态机。"""

    PLANNING = "planning"  # 初始（兼容旧流程）
    UNDERSTANDING = "understanding"  # 正在理解文档
    STRATEGIZING = "strategizing"  # 正在生成策略
    PENDING_CONFIRM = "pending_confirm"  # 兼容旧：plan 已生成等确认
    PENDING_SELECT = "pending_select"  # 策略已生成，等用户选择
    RUNNING = "running"  # 正在执行
    DONE = "done"  # 全部完成
    FAILED = "failed"  # 执行失败
    CANCELLED = "cancelled"  # 用户取消


class Task(MappedAsDataclass, Base):
    """Agent 任务（计划→确认→执行的持久化实体）。

    与 Conversation 松关联（可选 conversation_id，首版不强制）。
    plan_json 是 LLM 生成的步骤数组：[{skill, desc, params}]。
    result_json 累积每步产出：{steps: [{...}], case_ids: [...], summary: "..."}。

    子项目2 增强字段：
    - context_json：文档理解摘要 {summary, scope: []}
    - strategies_json：测试策略选项 [{id, label, description, plan: []}]
    - selected_strategy：用户选中的策略 id
    - uploaded_files：本次上传的文件名列表
    """

    __tablename__ = "agent_tasks"
    __table_args__ = (Index("idx_tasks_status", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, init=False)
    intent: Mapped[str] = mapped_column(Text, default="")
    plan_json: Mapped[list] = mapped_column(JSON, default_factory=list)
    status: Mapped[TaskStatus] = mapped_column(
        SAEnum(TaskStatus, values_callable=enum_values), default=TaskStatus.PLANNING
    )
    current_step: Mapped[int] = mapped_column(Integer, default=0)
    total_steps: Mapped[int] = mapped_column(Integer, default=0)
    result_json: Mapped[dict] = mapped_column("result_json", JSON, default_factory=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    # 子项目2 增强字段（ensure_schema 幂等补列，旧数据 NULL/默认值兼容）
    context_json: Mapped[dict] = mapped_column("context_json", JSON, default_factory=dict)
    strategies_json: Mapped[list] = mapped_column("strategies_json", JSON, default_factory=list)
    selected_strategy: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    uploaded_files: Mapped[list] = mapped_column("uploaded_files", JSON, default_factory=list)
    project_id: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    version_id: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    use_kb: Mapped[bool] = mapped_column(Boolean, nullable=True, default=False)
    # 用例生成来源模式（full=完整 agent 闭环 / quick_analyze=轻量分析+生成 /
    # quick_image=轻量截图生成 / batch=两阶段批量）-- 区分 /tasks/quick 等轻量入口
    source_mode: Mapped[str] = mapped_column(Text, default="full")
    # 缺陷2修复：task 关联会话（nullable，task 结果可写入会话历史）
    conversation_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default_factory=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default_factory=datetime.now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
