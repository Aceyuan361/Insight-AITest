# -*- coding: utf-8 -*-
"""文档上传/列表/详情/删除/重建索引。

底层 KBDatabase/VectorStore 已上提为平台服务（platform.services.kb），
文档操作通过平台单例进行。
"""

from __future__ import annotations

import hashlib
import threading
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel

from insight_aitest.platform.services.llm.config import AIConfig
from insight_aitest.platform.services.kb.database import KBDatabase
from insight_aitest.platform.services.kb.models import DocumentStatus
from insight_aitest.platform.services.kb.loader import get_loader
from insight_aitest.platform.services.kb.loader.base import UnsupportedFormatError
from insight_aitest.platform.services.kb.ingest import process_document
from insight_aitest.modules.ai.backend.deps import get_config, get_kb_db, get_llm, get_vector_store

router = APIRouter(prefix="/documents", tags=["ai-documents"])


class DocumentOut(BaseModel):
    id: int
    filename: str
    status: str
    char_count: int
    chunk_count: int
    error_message: str | None
    created_at: str

    @classmethod
    def from_doc(cls, doc) -> "DocumentOut":
        return cls(
            id=doc.id,
            filename=doc.filename,
            status=doc.status.value,
            char_count=doc.char_count,
            chunk_count=doc.chunk_count,
            error_message=doc.error_message,
            created_at=doc.created_at.isoformat(),
        )


def _doc_to_out(doc) -> DocumentOut:
    return DocumentOut.from_doc(doc)


@router.get("", response_model=list[DocumentOut])
async def list_documents(db: KBDatabase = Depends(get_kb_db)) -> list[DocumentOut]:
    return [_doc_to_out(d) for d in db.list_documents()]


@router.post("", response_model=DocumentOut)
async def upload_document(
    file: UploadFile,
    db: KBDatabase = Depends(get_kb_db),
    cfg: AIConfig = Depends(get_config),
) -> DocumentOut:
    # 1. 校验扩展名
    try:
        get_loader(file.filename or "")
    except UnsupportedFormatError:
        raise HTTPException(400, f"不支持的文件格式: {file.filename}")

    # 2. 读内容 + 校验大小
    content = await file.read()
    if len(content) > cfg.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"文件超过 {cfg.max_upload_mb}MB 限制")

    # 3. 去重
    content_hash = hashlib.sha256(content).hexdigest()
    existing = db.find_by_content_hash(content_hash)
    if existing:
        return _doc_to_out(existing)

    # 4. 存原始文件
    ext = Path(file.filename or "").suffix
    docs_dir = Path(cfg.docs_dir)
    docs_dir.mkdir(parents=True, exist_ok=True)
    storage_path = docs_dir / f"{uuid.uuid4().hex}{ext}"
    storage_path.write_bytes(content)

    # 5. 入库
    doc_id = db.create_document(file.filename, str(storage_path), content_hash, file.content_type)

    # 6. 后台线程处理
    def _bg():
        try:
            llm = get_llm()
            vs = get_vector_store()
            process_document(doc_id, db, vs, llm, cfg)
        except Exception as e:
            db.update_document_status(
                doc_id, DocumentStatus.PARSE_FAILED, error_message=f"处理异常: {e}"
            )

    threading.Thread(target=_bg, daemon=True).start()

    return _doc_to_out(db.get_document(doc_id))


@router.get("/{doc_id}", response_model=DocumentOut)
async def get_document(doc_id: int, db: KBDatabase = Depends(get_kb_db)) -> DocumentOut:
    doc = db.get_document(doc_id)
    if not doc:
        raise HTTPException(404, "文档不存在")
    return _doc_to_out(doc)


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: int, db: KBDatabase = Depends(get_kb_db), vs=Depends(get_vector_store)
) -> dict:
    doc = db.get_document(doc_id)
    if not doc:
        raise HTTPException(404, "文档不存在")
    # 删向量（必须先于删 chunks，因 vec0 不走 CASCADE）
    try:
        vs.delete_document(doc_id)
    except Exception:
        pass
    # 删原始文件
    try:
        Path(doc.storage_path).unlink(missing_ok=True)
    except Exception:
        pass
    db.delete_document(doc_id)
    return {"deleted": doc_id}


@router.post("/{doc_id}/reindex", response_model=DocumentOut)
async def reindex_document(doc_id: int, db: KBDatabase = Depends(get_kb_db)) -> DocumentOut:
    """重新索引（换 embedding 模型后用）。删旧向量与 chunks，状态置 pending。"""
    doc = db.get_document(doc_id)
    if not doc:
        raise HTTPException(404, "文档不存在")
    conn = db.get_connection()
    chunk_ids = [
        r["id"]
        for r in conn.execute("SELECT id FROM chunks WHERE document_id = ?", (doc_id,)).fetchall()
    ]
    for cid in chunk_ids:
        conn.execute("DELETE FROM chunk_embeddings WHERE chunk_id = ?", (cid,))
    conn.execute("DELETE FROM chunks WHERE document_id = ?", (doc_id,))
    conn.commit()
    db.update_document_status(doc_id, DocumentStatus.PENDING)
    return _doc_to_out(db.get_document(doc_id))
