# -*- coding: utf-8 -*-
"""平台知识库数据库（KBDatabase，spec P0-1 ORM 迁移）。

从 ai 模块上提：只管 documents/chunks/chunk_embeddings + 索引 + sqlite-vec。
ai 模块的 AIDatabase 瘦身为只管 conversations/messages。
独立 kb.db 文件（~/.insight_eye/kb.db）。

P0-1：documents/chunks 走平台 ORM（session_scope）；chunk_embeddings（vec0 虚拟表）
仍走原生 sqlite3 通道（sqlite-vec 扩展运行时加载，ORM 无法管理虚拟表）。
``get_connection()`` 保留——vector_store.py / retriever / documents 路由的原生 SQL
（含 vec0 + chunks/documents 三表 JOIN）依赖它，签名不变、内部透明。
"""

from __future__ import annotations

import os
import re
import sqlite3
import threading
from datetime import datetime

from sqlalchemy import select

from insight_aitest.platform.persistence import Base, get_engine, session_scope
from insight_aitest.platform.services.kb.models import (
    Chunk,
    Document,
    DocumentStatus,
    DocumentVersion,
    EmbedStatus,
)


def _ensure_project_columns(db_path: str) -> None:
    """增量迁移：给旧 documents 表补 project_id/version_id 列（幂等）。

    sqlite < 3.35 无 ADD COLUMN IF NOT EXISTS，用 PRAGMA 检查列是否已存在。
    """
    import sqlite3

    with sqlite3.connect(db_path) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(documents)")}
        if "project_id" not in cols:
            conn.execute("ALTER TABLE documents ADD COLUMN project_id INTEGER")
        if "version_id" not in cols:
            conn.execute("ALTER TABLE documents ADD COLUMN version_id INTEGER")
        conn.commit()


def _ensure_document_meta_columns(db_path: str) -> None:
    """增量迁移：给 documents 表补 tags/doc_type/description 列（KB 升级，幂等）。

    tags 存 JSON 数组字符串；doc_type/description 存纯文本。旧数据 NULL → 空串。
    """
    import sqlite3

    with sqlite3.connect(db_path) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(documents)")}
        if "tags" not in cols:
            conn.execute("ALTER TABLE documents ADD COLUMN tags TEXT DEFAULT ''")
        if "doc_type" not in cols:
            conn.execute("ALTER TABLE documents ADD COLUMN doc_type TEXT DEFAULT ''")
        if "description" not in cols:
            conn.execute("ALTER TABLE documents ADD COLUMN description TEXT DEFAULT ''")
        conn.commit()


class KBDatabase:
    def __init__(self, db_path: str, embed_dim: int = 1536, vector_enabled: bool = True) -> None:
        self.db_path = db_path
        self._embed_dim = embed_dim
        self._local = threading.local()  # vec0 原生连接仍用线程本地（ORM 通道另走 session_scope）
        self._vec_available: bool = False
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        # documents/chunks/document_versions 建 ORM 表（IF NOT EXISTS，存量表不动；只建本模块表）
        Base.metadata.create_all(
            get_engine(db_path),
            tables=[Document.__table__, Chunk.__table__, DocumentVersion.__table__],
        )
        # 增量迁移：旧 documents 表补 project_id/version_id 列（幂等）
        _ensure_project_columns(db_path)
        # 增量迁移：documents 表补 tags/doc_type/description 列（KB 升级，幂等）
        _ensure_document_meta_columns(db_path)
        # vec0 扩展加载：仅扩展加载/建表失败时降级（缺可选依赖）。
        # 维度不一致（ValueError）是数据完整性错误，必须抛出。
        # vector_enabled=False 时跳过 vec0 初始化——不读也不校验旧表，
        # 文档 CRUD 仍走 ORM 表正常工作。避免旧库维度不一致时构造崩溃。
        if not vector_enabled:
            self._vec_available = False
            return
        try:
            self._init_vec_table()
            self._vec_available = True
        except ValueError:
            raise
        except Exception as e:
            try:
                from logzero import logger

                logger.warning(f"sqlite-vec 不可用，向量检索降级: {e}")
            except Exception:
                pass
            self._vec_available = False

    def get_connection(self) -> sqlite3.Connection:
        """vec0 原生连接（vector_store/retriever/documents 路由的原生 SQL 用）。

        每条连接加载 sqlite-vec 扩展（扩展是连接级，非进程级）。
        与 ORM session 通道相互独立，各自管各自的事务。
        """
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            if self._vec_available:
                try:
                    import sqlite_vec

                    conn.enable_load_extension(True)
                    sqlite_vec.load(conn)
                    conn.enable_load_extension(False)
                except Exception:
                    pass
            self._local.conn = conn
        return self._local.conn

    def _init_vec_table(self) -> None:
        """加载 sqlite-vec 扩展并建 vec0 虚拟表。

        维度一致性：若 vec0 表已存在，校验其声明维度与 self._embed_dim 一致。
        """
        import sqlite_vec

        conn = self.get_connection()
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)

        existing = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='chunk_embeddings'"
        ).fetchone()
        if existing:
            sql_row = conn.execute(
                "SELECT sql FROM sqlite_master WHERE name='chunk_embeddings'"
            ).fetchone()
            m = re.search(r"FLOAT\[(\d+)\]", sql_row["sql"])
            if m and int(m.group(1)) != self._embed_dim:
                raise ValueError(
                    f"embed_dim 不一致：vec0 表声明 {m.group(1)}，当前配置 {self._embed_dim}。"
                    "换 embedding 模型需重新索引所有文档。"
                )
            return
        conn.execute(
            f"CREATE VIRTUAL TABLE IF NOT EXISTS chunk_embeddings USING vec0("
            f"chunk_id INTEGER PRIMARY KEY, embedding FLOAT[{self._embed_dim}])"
        )
        conn.commit()

    # ===== 文档（ORM 通道）=====

    def create_document(
        self,
        filename: str,
        storage_path: str,
        content_hash: str,
        mime_type: str | None,
        project_id: int | None = None,
        version_id: int | None = None,
    ) -> int:
        with session_scope(self.db_path) as s:
            d = Document(
                filename=filename,
                storage_path=storage_path,
                content_hash=content_hash,
                mime_type=mime_type,
                project_id=project_id,
                version_id=version_id,
            )
            s.add(d)
            s.flush()
            return d.id

    def get_document(self, doc_id: int) -> Document | None:
        with session_scope(self.db_path) as s:
            return s.get(Document, doc_id)

    def list_documents(
        self,
        status_filter: str | None = None,
        project_id: int | None = None,
        version_id: int | None = None,
    ) -> list[Document]:
        stmt = select(Document)
        if status_filter:
            stmt = stmt.where(Document.status == DocumentStatus(status_filter))
        if project_id is not None:
            stmt = stmt.where(Document.project_id == project_id)
        if version_id is not None:
            stmt = stmt.where(Document.version_id == version_id)
        stmt = stmt.order_by(Document.created_at.desc())
        with session_scope(self.db_path) as s:
            return list(s.scalars(stmt))

    def count_by_project(self, project_id: int | None) -> int:
        """统计某项目下的文档数（project_id=None 统计未分类）。"""
        from sqlalchemy import func

        stmt = select(func.count(Document.id))
        if project_id is not None:
            stmt = stmt.where(Document.project_id == project_id)
        else:
            stmt = stmt.where(Document.project_id.is_(None))
        with session_scope(self.db_path) as s:
            return s.scalar(stmt) or 0

    def update_document_status(
        self,
        doc_id: int,
        status: DocumentStatus,
        error_message: str | None = None,
        char_count: int | None = None,
        chunk_count: int | None = None,
    ) -> None:
        with session_scope(self.db_path) as s:
            d = s.get(Document, doc_id)
            if d is None:
                return
            d.status = status
            d.updated_at = datetime.now()
            if error_message is not None:
                d.error_message = error_message
            if char_count is not None:
                d.char_count = char_count
            if chunk_count is not None:
                d.chunk_count = chunk_count

    def delete_document(self, doc_id: int) -> bool:
        with session_scope(self.db_path) as s:
            d = s.get(Document, doc_id)
            if d is None:
                return False
            s.delete(d)
            return True

    def find_by_content_hash(self, content_hash: str) -> Document | None:
        stmt = select(Document).where(Document.content_hash == content_hash)
        with session_scope(self.db_path) as s:
            return s.scalars(stmt).first()

    # ===== 文档元数据 / 内容 / 版本（KB 升级新增）=====

    def update_document_meta(
        self,
        doc_id: int,
        tags: str | None = None,
        doc_type: str | None = None,
        description: str | None = None,
    ) -> None:
        """更新文档标签/类型/描述。tags 为 JSON 数组字符串。仅更新非 None 字段。"""
        with session_scope(self.db_path) as s:
            d = s.get(Document, doc_id)
            if d is None:
                return
            if tags is not None:
                d.tags = tags
            if doc_type is not None:
                d.doc_type = doc_type
            if description is not None:
                d.description = description
            d.updated_at = datetime.now()

    def list_tags(self, project_id: int | None = None) -> list[dict]:
        """聚合返回标签及计数（供标签云）。tags 列存 JSON 数组字符串。"""
        import json

        stmt = select(Document.tags)
        if project_id is not None:
            stmt = stmt.where(Document.project_id == project_id)
        counts: dict[str, int] = {}
        with session_scope(self.db_path) as s:
            for (raw,) in s.execute(stmt):
                try:
                    tags = json.loads(raw) if raw else []
                except (json.JSONDecodeError, TypeError):
                    tags = []
                for t in tags:
                    t = str(t).strip()
                    if t:
                        counts[t] = counts.get(t, 0) + 1
        return [{"tag": k, "count": v} for k, v in sorted(counts.items(), key=lambda x: -x[1])]

    def get_document_content(self, doc_id: int) -> str:
        """获取文档纯文本。优先拼接 chunks；无 chunks（处理中/未分块）时直接解析原始文件。"""
        stmt = (
            select(Chunk.text)
            .where(Chunk.document_id == doc_id)
            .order_by(Chunk.chunk_index)
        )
        with session_scope(self.db_path) as s:
            parts = [row[0] for row in s.execute(stmt)]
        if parts:
            return "\n".join(parts)
        # 无 chunks：直接解析原始文件（处理中文档/纯文本编辑场景）
        doc = self.get_document(doc_id)
        if doc and doc.storage_path:
            from pathlib import Path

            p = Path(doc.storage_path)
            if p.exists():
                try:
                    from insight_aitest.platform.services.kb.loader import get_loader

                    loader = get_loader(doc.filename)
                    parsed = loader.load(p)
                    return parsed.content
                except Exception:
                    return ""
        return ""

    def replace_document_content(self, doc_id: int, new_text: str) -> None:
        """编辑保存：用新文本替换文档全部分块（单块整文）。

        只更新 chunks 表文本（纯文本编辑场景）；向量化由路由层后台 reindex 触发。
        保留 chunk 的 char_start/char_end 为 0..len，使 chunks 不变量 text[0:len]==text 成立。
        """
        conn = self.get_connection()
        # 删旧 chunks（含向量由路由层 VectorStore 处理，这里只清 chunks 文本行）
        conn.execute("DELETE FROM chunks WHERE document_id = ?", (doc_id,))
        conn.execute(
            "INSERT INTO chunks (document_id, chunk_index, text, char_start, char_end, embed_status) "
            "VALUES (?, 0, ?, 0, ?, 'pending')",
            (doc_id, new_text, len(new_text)),
        )
        conn.execute(
            "UPDATE documents SET char_count = ?, chunk_count = 1, updated_at = ? WHERE id = ?",
            (len(new_text), datetime.now().isoformat(), doc_id),
        )
        conn.commit()

    def get_chunks_text(
        self,
        document_ids: list[int] | None = None,
        project_id: int | None = None,
        max_chars: int = 5000,
    ) -> list[tuple[str, str, int]]:
        """拼接文档 chunk 原文（HybridRetriever L3 兜底 + 手动档文档选择）。

        Returns: [(filename, text, document_id), ...]
        """
        # 无范围限制时不做全库扫描，避免大量数据加载
        if not document_ids and project_id is None:
            return []

        stmt = (
            select(Chunk.text, Document.filename, Document.id)
            .join(Document, Chunk.document_id == Document.id)
            .order_by(Chunk.document_id, Chunk.chunk_index)
            .limit(2000)
        )
        if document_ids:
            stmt = stmt.where(Chunk.document_id.in_(document_ids))
        if project_id is not None:
            stmt = stmt.where(Document.project_id == project_id)

        with session_scope(self.db_path) as s:
            rows = list(s.execute(stmt))

        doc_texts: dict[int, tuple[str, str]] = {}  # doc_id -> (filename, text)
        for text, filename, doc_id in rows:
            if doc_id not in doc_texts:
                doc_texts[doc_id] = (filename or f"doc_{doc_id}", "")
            name, existing = doc_texts[doc_id]
            if len(existing) < max_chars:
                doc_texts[doc_id] = (name, existing + (text or "") + "\n")

        return [
            (name, text[:max_chars], did)
            for did, (name, text) in doc_texts.items()
        ]

    def update_document_file(
        self,
        doc_id: int,
        storage_path: str,
        content_hash: str | None = None,
    ) -> None:
        """编辑保存（二进制文件场景）：更新 storage_path/content_hash，状态置 pending 待 reindex。"""
        with session_scope(self.db_path) as s:
            d = s.get(Document, doc_id)
            if d is None:
                return
            d.storage_path = storage_path
            if content_hash is not None:
                d.content_hash = content_hash
            d.status = DocumentStatus.PENDING
            d.char_count = 0
            d.chunk_count = 0
            d.error_message = None
            d.updated_at = datetime.now()

    # ===== 版本管理 =====

    def create_version_snapshot(
        self,
        doc_id: int,
        storage_path: str,
        content_hash: str | None,
        char_count: int,
        chunk_count: int,
        note: str = "",
    ) -> int:
        """为文档当前内容创建版本快照，version_no 自增。返回新 version_id。"""
        with session_scope(self.db_path) as s:
            # 取该文档最大 version_no
            from sqlalchemy import func

            next_no = (
                s.scalar(
                    select(func.max(DocumentVersion.version_no)).where(
                        DocumentVersion.document_id == doc_id
                    )
                )
                or 0
            ) + 1
            v = DocumentVersion(
                document_id=doc_id,
                version_no=next_no,
                storage_path=storage_path,
                content_hash=content_hash,
                char_count=char_count,
                chunk_count=chunk_count,
                note=note,
                is_current=0,
            )
            s.add(v)
            s.flush()
            return v.id

    def list_versions(self, doc_id: int) -> list[DocumentVersion]:
        """列出版本历史（按版本号降序，最新在前）。"""
        stmt = (
            select(DocumentVersion)
            .where(DocumentVersion.document_id == doc_id)
            .order_by(DocumentVersion.version_no.desc())
        )
        with session_scope(self.db_path) as s:
            return list(s.scalars(stmt))

    def get_version(self, doc_id: int, version_no: int) -> DocumentVersion | None:
        stmt = select(DocumentVersion).where(
            DocumentVersion.document_id == doc_id,
            DocumentVersion.version_no == version_no,
        )
        with session_scope(self.db_path) as s:
            return s.scalars(stmt).first()

    def rollback_version(self, doc_id: int, version_no: int) -> DocumentVersion | None:
        """回滚到指定版本：把当前内容另存一个版本快照，然后把目标版本的 storage_path
        写回 documents 表，状态置 pending 待 reindex。返回目标版本记录。"""
        target = self.get_version(doc_id, version_no)
        if target is None:
            return None
        # 先把当前内容存为快照（避免回滚后丢失当前版本）
        cur = self.get_document(doc_id)
        if cur is not None:
            self.create_version_snapshot(
                doc_id,
                cur.storage_path,
                cur.content_hash,
                cur.char_count,
                cur.chunk_count,
                note=f"回滚前快照（从 v{version_no} 回滚）",
            )
        # 把目标版本写回 documents
        self.update_document_file(doc_id, target.storage_path, target.content_hash)
        return target

    # ===== 分块（ORM 通道；向量由 VectorStore 走 get_connection 写 chunk_embeddings）=====

    def insert_chunks(self, document_id: int, chunks: list[Chunk]) -> list[int]:
        ids: list[int] = []
        with session_scope(self.db_path) as s:
            for c in chunks:
                c.document_id = document_id
                c.embed_status = EmbedStatus.PENDING
                s.add(c)
                s.flush()
                ids.append(c.id)
        return ids

    def update_chunk_embed_status(self, chunk_id: int, status: EmbedStatus) -> None:
        """走 vec0 原生连接（非 ORM session）。

        原因：VectorStore.upsert_chunks 在同一原生连接里写 chunk_embeddings（vec0）的同时
        逐块调本方法更新 embed_status。若走 ORM session 会开第二个写事务，在 WAL 下与
        vec0 写事务互锁（database is locked）。用同一个原生连接保持单写事务，避免锁冲突。
        """
        conn = self.get_connection()
        conn.execute("UPDATE chunks SET embed_status = ? WHERE id = ?", (status.value, chunk_id))
        conn.commit()

    def get_chunks_by_document(self, doc_id: int) -> list[Chunk]:
        stmt = select(Chunk).where(Chunk.document_id == doc_id).order_by(Chunk.chunk_index)
        with session_scope(self.db_path) as s:
            return list(s.scalars(stmt))


# ===== 迁移：旧 ai_kb.db → kb.db + ai.db =====


def migrate_from_legacy(ai_kb_path: str, kb_db_path: str, ai_db_path: str) -> bool:
    """旧 ai_kb.db 拆成 kb.db（文档/分块/向量）+ ai.db（会话/消息）。已迁移则跳过。

    返回 True 表示执行了迁移，False 表示跳过（已迁移或无旧库）。
    注意：不实例化 KBDatabase（它会强制 vec0 维度校验）。用原生 sqlite 建普通表 schema，
    vec0 表由后续真正打开 kb.db 的 KBDatabase 按配置 embed_dim 创建。
    """
    if os.path.exists(kb_db_path):
        return False  # 已迁移
    if not os.path.exists(ai_kb_path):
        return False  # 纯新装，无旧库

    src = sqlite3.connect(ai_kb_path)
    src.row_factory = sqlite3.Row

    # —— 建 kb.db 的普通表 schema（documents/chunks，不含 vec0）——
    kb_conn = sqlite3.connect(kb_db_path)
    kb_conn.executescript("""
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT NOT NULL,
        storage_path TEXT NOT NULL, mime_type TEXT, char_count INTEGER DEFAULT 0,
        chunk_count INTEGER DEFAULT 0, status TEXT NOT NULL DEFAULT 'pending',
        error_message TEXT, content_hash TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT, document_id INTEGER NOT NULL,
        chunk_index INTEGER NOT NULL, text TEXT NOT NULL,
        char_start INTEGER NOT NULL, char_end INTEGER NOT NULL,
        embed_status TEXT NOT NULL DEFAULT 'pending',
        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE);
    CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
    CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
    """)

    # 搬 documents
    for row in src.execute("SELECT * FROM documents").fetchall():
        kb_conn.execute(
            "INSERT OR IGNORE INTO documents (id, filename, storage_path, mime_type, "
            "char_count, chunk_count, status, error_message, content_hash, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                row["id"],
                row["filename"],
                row["storage_path"],
                row["mime_type"],
                row["char_count"],
                row["chunk_count"],
                row["status"],
                row["error_message"],
                row["content_hash"],
                row["created_at"],
                row["updated_at"],
            ),
        )
    # 搬 chunks
    for row in src.execute("SELECT * FROM chunks").fetchall():
        kb_conn.execute(
            "INSERT OR IGNORE INTO chunks (id, document_id, chunk_index, text, "
            "char_start, char_end, embed_status) VALUES (?,?,?,?,?,?,?)",
            (
                row["id"],
                row["document_id"],
                row["chunk_index"],
                row["text"],
                row["char_start"],
                row["char_end"],
                row["embed_status"],
            ),
        )
    kb_conn.commit()
    kb_conn.close()

    # —— 建 ai.db（会话/消息）：用 AIDatabase 建 schema，再用原生 sqlite 搬数据 ——
    from insight_aitest.modules.ai.backend.persistence.database import AIDatabase

    AIDatabase(ai_db_path)  # 建 schema（create_all + ensure_schema）
    ai_conn = sqlite3.connect(ai_db_path)
    ai_conn.row_factory = sqlite3.Row
    for tbl in ("conversations", "messages", "conversation_documents"):
        try:
            rows = src.execute(f"SELECT * FROM {tbl}").fetchall()
        except Exception:
            continue
        if not rows:
            continue
        cols = rows[0].keys()
        placeholders = ",".join("?" * len(cols))
        collist = ",".join(cols)
        for row in rows:
            ai_conn.execute(
                f"INSERT OR IGNORE INTO {tbl} ({collist}) VALUES ({placeholders})",
                tuple(row[c] for c in cols),
            )
    ai_conn.commit()
    ai_conn.close()
    src.close()
    # 释放 AIDatabase 创建时缓存的 ORM engine（否则 Windows 下占用文件句柄无法 rename）
    from insight_aitest.platform.persistence.engine import dispose_all

    dispose_all()

    # 旧库重命名备份（不删）
    os.rename(ai_kb_path, ai_kb_path + ".migrated")
    return True


# ===== 辅助 =====


def _parse_dt(val) -> datetime:
    """供 vector_store/retriever 的原生 SQL 结果行用（ORM 通道已自带 datetime 转换）。"""
    if val is None:
        return datetime.now()
    try:
        return datetime.fromisoformat(str(val))
    except (ValueError, TypeError):
        return datetime.now()
