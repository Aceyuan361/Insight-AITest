# -*- coding: utf-8 -*-
"""AI 模块数据库（AIDatabase，spec C + P0-1 ORM 迁移）—— 瘦身后只管会话/消息。

KB 相关（documents/chunks/向量）已上提为 platform.services.kb.database.KBDatabase。
独立 ai.db 文件（~/.insight_eye/ai.db）。

P0-1：从裸 sqlite3 + threading.local 迁移到平台 session_scope + ORM。
对外方法签名/返回类型完全不变（业务层 routes/agent/tests 零改动）。
旧库若无 rag_enabled 列，ensure_schema 幂等补列（替代原 _migrate_schema hack）。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from insight_aitest.platform.persistence import Base, ensure_schema, get_engine, session_scope
from insight_aitest.modules.ai.backend.persistence.models import (
    Citation,
    Conversation,
    ConversationDocument,
    Message,
    Role,
    Task,
    TaskStatus,
)


def _ensure_rag_enabled(db_path: str) -> None:
    """增量迁移：给旧 conversations 表补 rag_enabled 列（幂等，替代原 _migrate_schema）。

    sqlite < 3.35 无 ADD COLUMN IF NOT EXISTS，用 try-except 列已存在兜底。
    """
    import sqlite3

    with sqlite3.connect(db_path) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(conversations)")}
        if "rag_enabled" not in cols:
            conn.execute(
                "ALTER TABLE conversations ADD COLUMN rag_enabled BOOLEAN NOT NULL DEFAULT 1"
            )
        conn.commit()


def _ensure_task_columns(db_path: str) -> None:
    """增量迁移：给旧 agent_tasks 表补子项目2 增强列 + project_id/version_id/use_kb（幂等）。"""
    import sqlite3

    with sqlite3.connect(db_path) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(agent_tasks)")}
        for col, col_type in [
            ("context_json", "JSON"),
            ("strategies_json", "JSON"),
            ("selected_strategy", "TEXT"),
            ("uploaded_files", "JSON"),
            ("project_id", "INTEGER"),
            ("version_id", "INTEGER"),
            ("use_kb", "BOOLEAN"),
            ("source_mode", "TEXT"),
        ]:
            if col not in cols:
                conn.execute(f"ALTER TABLE agent_tasks ADD COLUMN {col} {col_type}")
        # source_mode 补默认值（旧库新增列时为 NULL，回填 'full'）
        conn.execute("UPDATE agent_tasks SET source_mode = 'full' WHERE source_mode IS NULL")

        # 补 agent_tasks.conversation_id 列（缺陷2修复：task 关联会话）
        if "conversation_id" not in cols:
            conn.execute("ALTER TABLE agent_tasks ADD COLUMN conversation_id INTEGER")

        # 补 messages.task_id 列（缺陷2修复：消息关联 task）
        msg_cols = {row[1] for row in conn.execute("PRAGMA table_info(messages)")}
        if "task_id" not in msg_cols:
            conn.execute("ALTER TABLE messages ADD COLUMN task_id INTEGER")
        conn.commit()


def _ensure_conversation_project_column(db_path: str) -> None:
    """增量迁移：给旧 conversations 表补 project_id + summary_json 列（幂等）。"""
    import sqlite3

    with sqlite3.connect(db_path) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(conversations)")}
        if "project_id" not in cols:
            conn.execute("ALTER TABLE conversations ADD COLUMN project_id INTEGER")
        if "summary_json" not in cols:
            conn.execute("ALTER TABLE conversations ADD COLUMN summary_json JSON")
        conn.commit()


def _ensure_thinking_columns(db_path: str) -> None:
    """增量迁移：conversations 补 thinking_level（TEXT），messages 补 thinking/attachments_json。

    历史迁移链：
    1. 旧库无 thinking 列 → 新建 thinking_level TEXT DEFAULT 'off'。
    2. 旧库有 thinking_enabled (BOOLEAN) → 迁移到 thinking_level (TEXT)：True→'medium'，False→'off'。
       SQLite 不能 RENAME COLUMN（旧版本），用「建新列 + 拷贝 + 保留旧列」策略（旧列冗余但无害）。
    """
    import sqlite3

    with sqlite3.connect(db_path) as conn:
        conv_cols = {row[1] for row in conn.execute("PRAGMA table_info(conversations)")}
        if "thinking_level" not in conv_cols:
            conn.execute(
                "ALTER TABLE conversations ADD COLUMN thinking_level TEXT NOT NULL DEFAULT 'off'"
            )
            # 从旧 thinking_enabled (BOOLEAN) 迁移数据
            if "thinking_enabled" in conv_cols:
                conn.execute(
                    "UPDATE conversations SET thinking_level = CASE WHEN thinking_enabled = 1 THEN 'medium' ELSE 'off' END"
                )
        msg_cols = {row[1] for row in conn.execute("PRAGMA table_info(messages)")}
        if "thinking" not in msg_cols:
            conn.execute("ALTER TABLE messages ADD COLUMN thinking TEXT")
        if "attachments_json" not in msg_cols:
            conn.execute("ALTER TABLE messages ADD COLUMN attachments_json JSON")
        conn.commit()


class AIDatabase:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        # 先 create_all（IF NOT EXISTS 建表，只建本模块表），再补增量列（旧库可能缺 rag_enabled）
        Base.metadata.create_all(
            get_engine(db_path),
            tables=[
                Conversation.__table__,
                Message.__table__,
                ConversationDocument.__table__,
                Task.__table__,
            ],
        )
        ensure_schema(
            db_path,
            [
                _ensure_rag_enabled,
                _ensure_task_columns,
                _ensure_thinking_columns,
                _ensure_conversation_project_column,
            ],
        )

    # ===== 会话 =====

    def create_conversation(
        self,
        title: str | None = None,
        rag_enabled: bool = True,
        thinking_level: str = "off",
        project_id: int | None = None,
    ) -> int:
        with session_scope(self.db_path) as s:
            c = Conversation(
                title=title or "新会话",
                rag_enabled=rag_enabled,
                thinking_level=thinking_level,
                project_id=project_id,
            )
            s.add(c)
            s.flush()
            return c.id

    def get_conversation(self, conv_id: int) -> Conversation | None:
        with session_scope(self.db_path) as s:
            return s.get(Conversation, conv_id)

    def list_conversations(self, project_id: int | None = None) -> list[Conversation]:
        stmt = select(Conversation).order_by(Conversation.updated_at.desc())
        if project_id is not None:
            stmt = stmt.where(Conversation.project_id == project_id)
        with session_scope(self.db_path) as s:
            return list(s.scalars(stmt))

    def update_conversation_title(self, conv_id: int, title: str) -> None:
        with session_scope(self.db_path) as s:
            c = s.get(Conversation, conv_id)
            if c is None:
                return
            c.title = title
            c.updated_at = datetime.now()

    def update_conversation_rag(self, conv_id: int, rag_enabled: bool) -> None:
        with session_scope(self.db_path) as s:
            c = s.get(Conversation, conv_id)
            if c is None:
                return
            c.rag_enabled = rag_enabled
            c.updated_at = datetime.now()

    def update_conversation_thinking(self, conv_id: int, thinking_level: str) -> None:
        with session_scope(self.db_path) as s:
            c = s.get(Conversation, conv_id)
            if c is None:
                return
            c.thinking_level = thinking_level
            c.updated_at = datetime.now()

    def delete_conversation(self, conv_id: int) -> bool:
        with session_scope(self.db_path) as s:
            c = s.get(Conversation, conv_id)
            if c is None:
                return False
            s.delete(c)
            return True

    def find_empty_conversation(self, project_id: int | None) -> Conversation | None:
        """查找指定项目下无消息的会话（用于创建去重）。"""
        from sqlalchemy import select as sa_select

        # 子查询：有消息的 conversation_id 集合
        msg_conv_ids = sa_select(Message.conversation_id).distinct()
        stmt = (
            select(Conversation)
            .where(
                Conversation.project_id == project_id
                if project_id is not None
                else Conversation.project_id.is_(None)
            )
            .where(~Conversation.id.in_(msg_conv_ids))
            .order_by(Conversation.created_at.desc())
            .limit(1)
        )
        with session_scope(self.db_path) as s:
            return s.scalars(stmt).first()

    def save_summary(self, conv_id: int, summary: dict) -> None:
        """保存会话上下文摘要。"""
        with session_scope(self.db_path) as s:
            c = s.get(Conversation, conv_id)
            if c is None:
                return
            c.summary_json = summary
            c.updated_at = datetime.now()

    def get_summary(self, conv_id: int) -> dict | None:
        """读取会话上下文摘要。"""
        with session_scope(self.db_path) as s:
            c = s.get(Conversation, conv_id)
            return c.summary_json if c else None

    # ===== 消息 =====

    def add_message(
        self,
        conversation_id: int,
        role: Role,
        content: str,
        citations: list | None = None,
        thinking: str | None = None,
        attachments: list | None = None,
        task_id: int | None = None,
    ) -> int:
        # Citation 对象 -> dict（存 JSON 列）
        cits = (
            [c.__dict__ if hasattr(c, "__dict__") else c for c in citations] if citations else None
        )
        with session_scope(self.db_path) as s:
            m = Message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                citations=cits,
                thinking=thinking,
                attachments=attachments,
                task_id=task_id,
            )
            s.add(m)
            c = s.get(Conversation, conversation_id)
            if c is not None:
                c.updated_at = datetime.now()
            s.flush()
            return m.id

    def list_messages(self, conversation_id: int, limit: int | None = None) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
        )
        if limit:
            stmt = stmt.limit(limit)
        with session_scope(self.db_path) as s:
            msgs = list(s.scalars(stmt))
        # desc + limit 取最近 N 条，反转回时间正序（业务层期望消息按时间升序）
        msgs.reverse()
        # JSON 列里的 dict -> Citation 对象（业务层期望 m.citations 是 Citation 列表）。
        # None -> []（与原 dataclass 默认值一致，避免 routes 层对 None 迭代报错）。
        for m in msgs:
            if m.citations:
                m.citations = [Citation(**c) if isinstance(c, dict) else c for c in m.citations]
            else:
                m.citations = []
        return msgs

    def list_messages_by_task(self, task_id: int, limit: int | None = None) -> list[Message]:
        """按 task_id 查询消息（用于 agent_chat 加载对话历史）。"""
        stmt = (
            select(Message)
            .where(Message.task_id == task_id)
            .order_by(Message.created_at.desc())
        )
        if limit:
            stmt = stmt.limit(limit)
        with session_scope(self.db_path) as s:
            msgs = list(s.scalars(stmt))
        msgs.reverse()
        for m in msgs:
            if m.citations:
                m.citations = [Citation(**c) if isinstance(c, dict) else c for c in m.citations]
            else:
                m.citations = []
        return msgs

    # ===== Agent Task（子项目2）=====

    def create_task(
        self,
        intent: str,
        plan: list | None = None,
        uploaded_files: list | None = None,
        project_id: int | None = None,
        version_id: int | None = None,
        use_kb: bool = False,
        conversation_id: int | None = None,
    ) -> int:
        """创建 task。plan 为空时走新流程（understand→strategize）。
        
        conversation_id 非 None 时将 task 关联到已有会话（修复会话拆分问题）。
        """
        with session_scope(self.db_path) as s:
            t = Task(
                intent=intent,
                plan_json=plan or [],
                total_steps=len(plan) if plan else 0,
                status=TaskStatus.UNDERSTANDING if not plan else TaskStatus.PENDING_CONFIRM,
                uploaded_files=uploaded_files or [],
                project_id=project_id,
                version_id=version_id,
                use_kb=use_kb,
                conversation_id=conversation_id,
            )
            s.add(t)
            s.flush()
            return t.id

    def get_task(self, task_id: int) -> Task | None:
        with session_scope(self.db_path) as s:
            return s.get(Task, task_id)

    def list_tasks(self, limit: int = 50, project_id: int | None = None) -> list[Task]:
        stmt = select(Task).order_by(Task.created_at.desc()).limit(limit)
        if project_id is not None:
            stmt = stmt.where(Task.project_id == project_id)
        with session_scope(self.db_path) as s:
            return list(s.scalars(stmt))

    def update_task_status(
        self,
        task_id: int,
        status: TaskStatus,
        error: str | None = None,
        result: dict | None = None,
    ) -> bool:
        with session_scope(self.db_path) as s:
            t = s.get(Task, task_id)
            if t is None:
                return False
            t.status = status
            t.updated_at = datetime.now()
            if error is not None:
                t.error = error
            if result is not None:
                t.result_json = result
            if status in (TaskStatus.DONE, TaskStatus.FAILED, TaskStatus.CANCELLED):
                t.finished_at = datetime.now()
            return True

    def update_task_step(self, task_id: int, current_step: int, result: dict | None = None) -> bool:
        """更新当前执行步骤 + 累积结果。"""
        with session_scope(self.db_path) as s:
            t = s.get(Task, task_id)
            if t is None:
                return False
            t.current_step = current_step
            t.updated_at = datetime.now()
            if result is not None:
                existing = dict(t.result_json) if t.result_json else {}
                steps = existing.get("steps", [])
                steps.append(result)
                existing["steps"] = steps
                t.result_json = existing
            return True

    def update_task_context(
        self, task_id: int, context: dict, status: TaskStatus | None = None
    ) -> bool:
        """更新理解摘要 context_json。"""
        with session_scope(self.db_path) as s:
            t = s.get(Task, task_id)
            if t is None:
                return False
            t.context_json = context
            t.updated_at = datetime.now()
            if status is not None:
                t.status = status
            return True

    def update_task_strategies(
        self, task_id: int, strategies: list, status: TaskStatus | None = None
    ) -> bool:
        """更新策略选项 strategies_json。"""
        with session_scope(self.db_path) as s:
            t = s.get(Task, task_id)
            if t is None:
                return False
            t.strategies_json = strategies
            t.updated_at = datetime.now()
            if status is not None:
                t.status = status
            return True

    def select_task_strategy(self, task_id: int, strategy_id: str, plan: list) -> bool:
        """用户选择了策略，更新 selected_strategy + plan_json，进入执行。"""
        with session_scope(self.db_path) as s:
            t = s.get(Task, task_id)
            if t is None:
                return False
            t.selected_strategy = strategy_id
            t.plan_json = plan
            t.total_steps = len(plan)
            t.status = TaskStatus.RUNNING
            t.updated_at = datetime.now()
            return True

    def update_task_source_mode(self, task_id: int, source_mode: str) -> None:
        """更新 task 的来源模式（full/quick_analyze/quick_image/batch 等）。"""
        with session_scope(self.db_path) as s:
            t = s.get(Task, task_id)
            if t is not None:
                t.source_mode = source_mode
                t.updated_at = datetime.now()

    def delete_task(self, task_id: int) -> bool:
        with session_scope(self.db_path) as s:
            t = s.get(Task, task_id)
            if t is None:
                return False
            s.delete(t)
            return True

    def count_conversations_by_project(self, project_id: int | None) -> int:
        """统计某项目下的会话数（project_id=None 统计未分类）。"""
        from sqlalchemy import func

        stmt = select(func.count(Conversation.id))
        if project_id is not None:
            stmt = stmt.where(Conversation.project_id == project_id)
        else:
            stmt = stmt.where(Conversation.project_id.is_(None))
        with session_scope(self.db_path) as s:
            return s.scalar(stmt) or 0

    def count_tasks_by_project(self, project_id: int | None) -> int:
        """统计某项目下的 Agent 任务数（project_id=None 统计未分类）。"""
        from sqlalchemy import func

        stmt = select(func.count(Task.id))
        if project_id is not None:
            stmt = stmt.where(Task.project_id == project_id)
        else:
            stmt = stmt.where(Task.project_id.is_(None))
        with session_scope(self.db_path) as s:
            return s.scalar(stmt) or 0
