# -*- coding: utf-8 -*-
"""会话 CRUD。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from insight_aitest.modules.ai.backend.deps import get_config, get_db
from insight_aitest.modules.ai.backend.persistence.database import AIDatabase

router = APIRouter(prefix="/conversations", tags=["ai-conversations"])


class ConversationOut(BaseModel):
    id: int
    title: str
    rag_enabled: bool
    thinking_level: str
    project_id: int | None = None
    created_at: str
    updated_at: str


class ConversationCreate(BaseModel):
    title: str | None = None
    rag_enabled: bool | None = None
    thinking_level: str | None = None
    project_id: int | None = None


class ConversationUpdate(BaseModel):
    title: str | None = None
    rag_enabled: bool | None = None
    thinking_level: str | None = None


def _out(conv) -> ConversationOut:
    return ConversationOut(
        id=conv.id,
        title=conv.title,
        rag_enabled=conv.rag_enabled,
        thinking_level=conv.thinking_level,
        project_id=conv.project_id,
        created_at=conv.created_at.isoformat(),
        updated_at=conv.updated_at.isoformat(),
    )


@router.get("", response_model=list[ConversationOut])
async def list_conversations(
    project_id: int | None = None, db: AIDatabase = Depends(get_db)
) -> list[ConversationOut]:
    return [_out(c) for c in db.list_conversations(project_id=project_id)]


@router.post("", response_model=ConversationOut)
async def create_conversation(
    body: ConversationCreate | None = None, db: AIDatabase = Depends(get_db)
) -> ConversationOut:
    title = body.title if body and body.title else "新会话"
    rag = body.rag_enabled if body and body.rag_enabled is not None else True
    think = body.thinking_level if body and body.thinking_level is not None else "off"
    pid = body.project_id if body else None
    # 去重：复用已有的空会话（无消息），避免重复创建空会话行污染侧栏
    # 原子化 get-or-create：修复并发竞态（find+create 分离时两个请求可能各自创建）
    cid = db.get_or_create_empty_conversation(title, rag_enabled=rag, thinking_level=think, project_id=pid)
    return _out(db.get_conversation(cid))


@router.get("/{conv_id}")
async def get_conversation(conv_id: int, db: AIDatabase = Depends(get_db)) -> dict:
    conv = db.get_conversation(conv_id)
    if not conv:
        raise HTTPException(404, "会话不存在")
    messages = db.list_messages(conv_id)
    return {
        "id": conv.id,
        "title": conv.title,
        "rag_enabled": conv.rag_enabled,
        "thinking_level": conv.thinking_level,
        "created_at": conv.created_at.isoformat(),
        "updated_at": conv.updated_at.isoformat(),
        "messages": [
            {
                "role": m.role.value,
                "content": m.content,
                "citations": [c.__dict__ for c in m.citations],
                "thinking": m.thinking,
                "attachments": m.attachments,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    }


@router.patch("/{conv_id}", response_model=ConversationOut)
async def update_conversation(
    conv_id: int, body: ConversationUpdate, db: AIDatabase = Depends(get_db)
) -> ConversationOut:
    if not db.get_conversation(conv_id):
        raise HTTPException(404, "会话不存在")
    # title / rag_enabled / thinking_level 至少传一个
    if body.title is None and body.rag_enabled is None and body.thinking_level is None:
        raise HTTPException(400, "至少需要提供 title / rag_enabled / thinking_level")
    if body.title is not None:
        db.update_conversation_title(conv_id, body.title)
    if body.rag_enabled is not None:
        db.update_conversation_rag(conv_id, body.rag_enabled)
    if body.thinking_level is not None:
        db.update_conversation_thinking(conv_id, body.thinking_level)
    return _out(db.get_conversation(conv_id))


@router.delete("/{conv_id}")
async def delete_conversation(
    conv_id: int,
    db: AIDatabase = Depends(get_db),
    config=Depends(get_config),
) -> dict:
    # collect attachment ids before deletion
    messages = db.list_messages(conv_id)
    attachment_ids = []
    for m in messages:
        if m.attachments:
            for att in m.attachments:
                if isinstance(att, dict) and att.get("id"):
                    attachment_ids.append(att["id"])
    if not db.delete_conversation(conv_id):
        raise HTTPException(404, "conversation not found")
    # cleanup orphan attachment files
    from pathlib import Path as _Path
    attachments_dir = _Path(config.docs_dir) / "attachments"
    for att_id in attachment_ids:
        try:
            f = attachments_dir / att_id
            if f.exists():
                f.unlink()
        except Exception:
            pass
    return {"deleted": conv_id}
