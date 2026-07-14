# -*- coding: utf-8 -*-
"""sqlite-vec 向量存取（平台共享服务）。

职责：chunks 原文已在 KBDatabase 写入 → 批量 embed → 写入 chunk_embeddings。
查询：KNN 检索（MATCH ... ORDER BY distance LIMIT k）→ JOIN chunks/documents 取原文与文档元信息。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from insight_aitest.platform.services.kb.models import Chunk, Document, EmbedStatus, ScoredChunk

if TYPE_CHECKING:
    from insight_aitest.platform.services.llm.config import LLMConfig
    from insight_aitest.platform.services.llm.client import LLMClient
    from insight_aitest.platform.services.kb.database import KBDatabase


def _vec_to_str(vec: list[float]) -> str:
    return "[" + ",".join(str(x) for x in vec) + "]"


class VectorStore:
    def __init__(self, db: "KBDatabase", llm: "LLMClient", config: "LLMConfig") -> None:
        self.db = db
        self.llm = llm
        self.config = config

    def upsert_chunks(self, document_id: int, chunks: list[Chunk]) -> None:
        """读该文档所有 chunk（含 DB id）→ 批量 embed → 写 chunk_embeddings → 更新 embed_status。

        前置：调用方应已 KBDatabase.insert_chunks，chunks 表里已有记录。
        本方法参数 chunks 仅用于触发（实际从 DB 读以拿到 id）。
        """
        db_chunks = self.db.get_chunks_by_document(document_id)
        if not db_chunks:
            return
        texts = [c.text for c in db_chunks]
        batch = self.config.embed_batch_size
        conn = self.db.get_connection()
        for i in range(0, len(texts), batch):
            batch_texts = texts[i : i + batch]
            batch_chunks = db_chunks[i : i + batch]
            try:
                vecs = self.llm.embed(batch_texts)
            except Exception as e:
                # 记录日志（用户配错 key/地址时能在后端日志看到，而非静默失败）
                try:
                    from logzero import logger

                    logger.warning(
                        f"[kb] embedding 批次失败（{len(batch_texts)} 块）: {type(e).__name__}: {e}"
                    )
                except Exception:
                    pass
                for c in batch_chunks:
                    self.db.update_chunk_embed_status(c.id, EmbedStatus.FAILED)
                continue
            for c, vec in zip(batch_chunks, vecs):
                conn.execute(
                    "INSERT OR REPLACE INTO chunk_embeddings (chunk_id, embedding) VALUES (?, ?)",
                    (c.id, _vec_to_str(vec)),
                )
                self.db.update_chunk_embed_status(c.id, EmbedStatus.OK)
            conn.commit()

    def search(
        self,
        query_vec: list[float],
        top_k: int,
        document_ids: list[int] | None = None,
        project_id: int | None = None,
    ) -> list[ScoredChunk]:
        if not self.db._vec_available:
            return []
        conn = self.db.get_connection()
        vec_str = _vec_to_str(query_vec)
        select_cols = (
            "ce.chunk_id, ce.distance, c.text, c.chunk_index, "
            "c.char_start, c.char_end, c.document_id, "
            "d.filename, d.storage_path, d.mime_type, d.char_count, "
            "d.chunk_count, d.status, d.error_message, d.content_hash, "
            "d.created_at, d.updated_at"
        )
        joins = (
            "FROM chunk_embeddings ce "
            "JOIN chunks c ON c.id = ce.chunk_id "
            "JOIN documents d ON d.id = c.document_id"
        )
        # 动态拼 WHERE：project_id 过滤（KB 升级，隔离检索范围）+ document_ids 过滤
        where_clauses = []
        params: list = []
        if document_ids:
            placeholders = ",".join("?" * len(document_ids))
            where_clauses.append(f"c.document_id IN ({placeholders})")
            params.extend(document_ids)
        if project_id is not None:
            where_clauses.append("d.project_id = ?")
            params.append(project_id)
        where_sql = ("WHERE " + " AND ".join(where_clauses) + " AND ") if where_clauses else "WHERE "
        rows = conn.execute(
            f"SELECT {select_cols} {joins} "
            f"{where_sql}ce.embedding MATCH ? AND k = ? "
            f"ORDER BY ce.distance",
            [*params, vec_str, top_k],
        ).fetchall()

        from insight_aitest.platform.services.kb.database import _parse_dt
        from insight_aitest.platform.services.kb.models import DocumentStatus

        results = []
        for r in rows:
            chunk = Chunk(
                id=r["chunk_id"],
                document_id=r["document_id"],
                chunk_index=r["chunk_index"],
                text=r["text"],
                char_start=r["char_start"],
                char_end=r["char_end"],
                embed_status=EmbedStatus.OK,
            )
            doc = Document(
                id=r["document_id"],
                filename=r["filename"],
                storage_path=r["storage_path"],
                mime_type=r["mime_type"],
                char_count=r["char_count"],
                chunk_count=r["chunk_count"],
                status=DocumentStatus(r["status"]),
                error_message=r["error_message"],
                content_hash=r["content_hash"],
                created_at=_parse_dt(r["created_at"]),
                updated_at=_parse_dt(r["updated_at"]),
            )
            # 归一化向量的 L2 距离 d：||a-b||²=2(1-cos) → cos 相似度 = 1 - d²/2
            # distance 越小越相似，转成 [0,1] 的余弦相似度作为 score
            d = float(r["distance"])
            score = max(0.0, 1.0 - (d * d) / 2.0)
            results.append(ScoredChunk(chunk=chunk, score=score, document=doc))
        return results

    def delete_document(self, document_id: int) -> None:
        """删 chunk_embeddings 中该文档的向量（chunks 表由外键 CASCADE）。"""
        conn = self.db.get_connection()
        chunk_ids = [
            r["id"]
            for r in conn.execute(
                "SELECT id FROM chunks WHERE document_id = ?", (document_id,)
            ).fetchall()
        ]
        for cid in chunk_ids:
            conn.execute("DELETE FROM chunk_embeddings WHERE chunk_id = ?", (cid,))
        conn.commit()
