# -*- coding: utf-8 -*-
"""知识库文档上传/列表/详情/删除/重建索引 + 预览/导出/编辑/标签/版本。

从 ai 模块迁移为独立 kb 模块。底层 KBDatabase/VectorStore 已是平台服务
（platform.services.kb），文档操作通过平台单例进行。

KB 升级新增：project_id/version_id 分类筛选 + 上传时关联项目 +
文档预览/导出/编辑 + 标签与元数据管理 + 版本管理。
"""

from __future__ import annotations

import hashlib
import json
import threading
import uuid
import zipfile
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from insight_aitest.platform.services.llm.config import AIConfig
from insight_aitest.platform.services.kb.database import KBDatabase
from insight_aitest.platform.services.kb.models import DocumentStatus
from insight_aitest.platform.services.kb.loader import get_loader
from insight_aitest.platform.services.kb.loader.base import UnsupportedFormatError
from insight_aitest.platform.services.kb.ingest import process_document
from insight_aitest.modules.ai.backend.deps import get_config, get_kb_db, get_llm, get_vector_store

router = APIRouter(prefix="/documents", tags=["kb-documents"])


class DocumentOut(BaseModel):
    id: int
    filename: str
    status: str
    char_count: int
    chunk_count: int
    error_message: str | None
    project_id: int | None = None
    version_id: int | None = None
    tags: list[str] = []
    doc_type: str = ""
    description: str = ""
    created_at: str

    @classmethod
    def from_doc(cls, doc) -> "DocumentOut":
        # tags 列存 JSON 数组字符串，解析为 list；解析失败降级空列表
        try:
            tags = json.loads(doc.tags) if getattr(doc, "tags", "") else []
            if not isinstance(tags, list):
                tags = []
        except (json.JSONDecodeError, TypeError):
            tags = []
        return cls(
            id=doc.id,
            filename=doc.filename,
            status=doc.status.value,
            char_count=doc.char_count,
            chunk_count=doc.chunk_count,
            error_message=doc.error_message,
            project_id=doc.project_id,
            version_id=doc.version_id,
            tags=[str(t) for t in tags],
            doc_type=getattr(doc, "doc_type", "") or "",
            description=getattr(doc, "description", "") or "",
            created_at=doc.created_at.isoformat(),
        )


def _doc_to_out(doc) -> DocumentOut:
    return DocumentOut.from_doc(doc)


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    project_id: int | None = None,
    version_id: int | None = None,
    db: KBDatabase = Depends(get_kb_db),
) -> list[DocumentOut]:
    return [_doc_to_out(d) for d in db.list_documents(project_id=project_id, version_id=version_id)]


@router.post("", response_model=DocumentOut)
async def upload_document(
    file: UploadFile,
    project_id: int | None = None,
    version_id: int | None = None,
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

    # 5. 入库（关联项目/版本）
    doc_id = db.create_document(
        file.filename,
        str(storage_path),
        content_hash,
        file.content_type,
        project_id=project_id,
        version_id=version_id,
    )

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


# ===== KB 升级：预览 / 导出 / 编辑 / 标签 / 版本 =====


def _reindex_in_bg(doc_id: int, db: KBDatabase) -> None:
    """后台重新索引文档（删旧 chunks+向量 → 重新解析分块向量化）。复用 ingest 管线。"""
    try:
        llm = get_llm()
        vs = get_vector_store()
        cfg = get_config()
        # 先清旧 chunks + 向量（与 reindex 端点同逻辑）
        conn = db.get_connection()
        chunk_ids = [
            r["id"]
            for r in conn.execute(
                "SELECT id FROM chunks WHERE document_id = ?", (doc_id,)
            ).fetchall()
        ]
        for cid in chunk_ids:
            conn.execute("DELETE FROM chunk_embeddings WHERE chunk_id = ?", (cid,))
        conn.execute("DELETE FROM chunks WHERE document_id = ?", (doc_id,))
        conn.commit()
        db.update_document_status(doc_id, DocumentStatus.PENDING)
        process_document(doc_id, db, vs, llm, cfg)
    except Exception as e:
        db.update_document_status(
            doc_id, DocumentStatus.PARSE_FAILED, error_message=f"重新索引失败: {e}"
        )


# ----- 预览 -----


@router.get("/{doc_id}/content")
async def get_document_content(
    doc_id: int, db: KBDatabase = Depends(get_kb_db)
) -> dict:
    """返回文档解析后的纯文本（拼接 chunks）。用于前端预览/编辑加载。"""
    doc = db.get_document(doc_id)
    if not doc:
        raise HTTPException(404, "文档不存在")
    text = db.get_document_content(doc_id)
    return {
        "document_id": doc_id,
        "filename": doc.filename,
        "mime_type": doc.mime_type,
        "text": text,
        "char_count": len(text),
    }


# ----- 导出 -----


@router.get("/{doc_id}/raw")
async def download_document_raw(
    doc_id: int, db: KBDatabase = Depends(get_kb_db)
) -> FileResponse:
    """下载文档原始文件（保留原扩展名）。"""
    doc = db.get_document(doc_id)
    if not doc:
        raise HTTPException(404, "文档不存在")
    path = Path(doc.storage_path)
    if not path.exists():
        raise HTTPException(404, "原始文件不存在（可能已被删除）")
    return FileResponse(
        str(path), filename=doc.filename, media_type=doc.mime_type or "application/octet-stream"
    )


@router.get("/export/zip")
async def export_documents_zip(
    project_id: int | None = None,
    version_id: int | None = None,
    db: KBDatabase = Depends(get_kb_db),
) -> StreamingResponse:
    """批量导出文档为 zip（按项目/版本过滤）。流式下载。"""
    docs = db.list_documents(project_id=project_id, version_id=version_id)
    if not docs:
        raise HTTPException(404, "没有可导出的文档")

    def _gen():
        buf = BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for doc in docs:
                p = Path(doc.storage_path)
                if p.exists():
                    # 文件名去重：同名文件加 id 前缀
                    arcname = f"{doc.id}_{doc.filename}"
                    zf.write(str(p), arcname)
        buf.seek(0)
        yield from buf

    return StreamingResponse(
        _gen(),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=kb_export.zip"},
    )


# ----- 编辑保存 -----


class DocumentContentUpdate(BaseModel):
    """编辑保存请求体。text 用于纯文本编辑；file 为二进制替换（FormData 走另一端点）。"""

    text: str
    note: str = ""  # 版本说明


@router.put("/{doc_id}/content", response_model=DocumentOut)
async def update_document_content(
    doc_id: int,
    body: DocumentContentUpdate,
    db: KBDatabase = Depends(get_kb_db),
) -> DocumentOut:
    """编辑保存（纯文本）：保留旧版本快照 → 替换 chunks 文本 → 后台 reindex。

    适用 txt/md/html 等纯文本格式。二进制格式（docx/xlsx）用 /raw 下载编辑后走上传替换。
    """
    doc = db.get_document(doc_id)
    if not doc:
        raise HTTPException(404, "文档不存在")

    # 1. 保留旧版本快照（旧 chunks 拼成的文本 → 新版本文件）
    old_text = db.get_document_content(doc_id)
    if old_text:
        old_path = Path(doc.storage_path)
        # 旧文本另存为版本文件
        version_dir = old_path.parent / "versions"
        version_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = version_dir / f"{doc_id}_v{uuid.uuid4().hex[:8]}{old_path.suffix}"
        snapshot_path.write_text(old_text, encoding="utf-8")
        db.create_version_snapshot(
            doc_id,
            str(snapshot_path),
            hashlib.sha256(old_text.encode()).hexdigest(),
            len(old_text),
            doc.chunk_count,
            note=body.note or "编辑前快照",
        )

    # 2. 替换 chunks 文本 + 同步原始文件
    db.replace_document_content(doc_id, body.text)
    # 同步写回原始文件（保持 storage_path 与内容一致）
    try:
        Path(doc.storage_path).write_text(body.text, encoding="utf-8")
    except Exception:
        pass

    # 3. 后台 reindex
    threading.Thread(target=_reindex_in_bg, args=(doc_id, db), daemon=True).start()
    return _doc_to_out(db.get_document(doc_id))


@router.put("/{doc_id}/file", response_model=DocumentOut)
async def update_document_file(
    doc_id: int,
    file: UploadFile,
    note: str = "二进制编辑保存",
    db: KBDatabase = Depends(get_kb_db),
    cfg: AIConfig = Depends(get_config),
) -> DocumentOut:
    """编辑保存（二进制文件 docx/xlsx）：保留旧版本快照 → 写新文件 → reindex。

    前端在线编辑器（SuperDoc/Univer）导出 Blob 后通过 FormData 上传到此端点。
    """
    doc = db.get_document(doc_id)
    if not doc:
        raise HTTPException(404, "文档不存在")

    content = await file.read()
    if len(content) > cfg.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"文件超过 {cfg.max_upload_mb}MB 限制")

    # 1. 保留旧版本快照
    old_path = Path(doc.storage_path)
    if old_path.exists():
        version_dir = old_path.parent / "versions"
        version_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = version_dir / f"{doc_id}_v{uuid.uuid4().hex[:8]}{old_path.suffix}"
        snapshot_path.write_bytes(old_path.read_bytes())
        db.create_version_snapshot(
            doc_id,
            str(snapshot_path),
            doc.content_hash,
            doc.char_count,
            doc.chunk_count,
            note=note,
        )

    # 2. 写新文件（保留原扩展名，覆盖 storage_path）
    ext = Path(doc.filename).suffix
    new_path = old_path.parent / f"{uuid.uuid4().hex}{ext}"
    new_path.write_bytes(content)
    new_hash = hashlib.sha256(content).hexdigest()
    db.update_document_file(doc_id, str(new_path), new_hash)

    # 3. 后台 reindex
    threading.Thread(target=_reindex_in_bg, args=(doc_id, db), daemon=True).start()
    return _doc_to_out(db.get_document(doc_id))


# ----- 标签与元数据 -----


class DocumentMetaUpdate(BaseModel):
    tags: list[str] | None = None
    doc_type: str | None = None
    description: str | None = None


@router.put("/{doc_id}/meta", response_model=DocumentOut)
async def update_document_meta(
    doc_id: int,
    body: DocumentMetaUpdate,
    db: KBDatabase = Depends(get_kb_db),
) -> DocumentOut:
    """更新文档标签/类型/描述。tags 存 JSON 数组字符串。"""
    doc = db.get_document(doc_id)
    if not doc:
        raise HTTPException(404, "文档不存在")
    tags_str = json.dumps(body.tags, ensure_ascii=False) if body.tags is not None else None
    db.update_document_meta(
        doc_id, tags=tags_str, doc_type=body.doc_type, description=body.description
    )
    return _doc_to_out(db.get_document(doc_id))


@router.get("/tags/all")
async def list_all_tags(
    project_id: int | None = None, db: KBDatabase = Depends(get_kb_db)
) -> list[dict]:
    """聚合返回所有标签及计数（供标签云）。"""
    return db.list_tags(project_id=project_id)


# ----- 版本管理 -----


class VersionOut(BaseModel):
    id: int
    document_id: int
    version_no: int
    char_count: int
    chunk_count: int
    note: str
    is_current: int
    created_at: str

    @classmethod
    def from_version(cls, v) -> "VersionOut":
        return cls(
            id=v.id,
            document_id=v.document_id,
            version_no=v.version_no,
            char_count=v.char_count,
            chunk_count=v.chunk_count,
            note=v.note or "",
            is_current=v.is_current,
            created_at=v.created_at.isoformat(),
        )


@router.get("/{doc_id}/versions", response_model=list[VersionOut])
async def list_document_versions(
    doc_id: int, db: KBDatabase = Depends(get_kb_db)
) -> list[VersionOut]:
    """列出文档的版本历史（按版本号降序）。"""
    doc = db.get_document(doc_id)
    if not doc:
        raise HTTPException(404, "文档不存在")
    return [VersionOut.from_version(v) for v in db.list_versions(doc_id)]


@router.get("/{doc_id}/versions/{version_no}/content")
async def get_version_content(
    doc_id: int, version_no: int, db: KBDatabase = Depends(get_kb_db)
) -> dict:
    """读取指定历史版本的纯文本内容（用于版本对比）。"""
    doc = db.get_document(doc_id)
    if not doc:
        raise HTTPException(404, "文档不存在")
    v = db.get_version(doc_id, version_no)
    if v is None:
        raise HTTPException(404, "版本不存在")
    # 从快照文件读取
    path = Path(v.storage_path)
    text = ""
    if path.exists():
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            # 二进制快照无法直接读文本
            text = ""
    return {
        "document_id": doc_id,
        "version_no": version_no,
        "text": text,
        "char_count": v.char_count,
        "note": v.note,
        "created_at": v.created_at.isoformat(),
    }


@router.post("/{doc_id}/rollback/{version_no}", response_model=DocumentOut)
async def rollback_to_version(
    doc_id: int, version_no: int, db: KBDatabase = Depends(get_kb_db)
) -> DocumentOut:
    """回滚到指定版本：当前内容另存快照 → 目标版本写回 → 后台 reindex。"""
    doc = db.get_document(doc_id)
    if not doc:
        raise HTTPException(404, "文档不存在")
    target = db.rollback_version(doc_id, version_no)
    if target is None:
        raise HTTPException(404, "版本不存在")
    # 后台 reindex
    threading.Thread(target=_reindex_in_bg, args=(doc_id, db), daemon=True).start()
    return _doc_to_out(db.get_document(doc_id))
