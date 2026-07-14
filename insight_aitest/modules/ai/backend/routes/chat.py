# -*- coding: utf-8 -*-
"""对话 API：非流式 /chat + SSE 流式 /chat/stream。"""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel

from insight_aitest.modules.ai.backend.deps import get_agent, get_db, get_config
from insight_aitest.modules.ai.backend.persistence.database import AIDatabase
from insight_aitest.modules.ai.backend.persistence.models import Role

router = APIRouter(prefix="/chat", tags=["ai-chat"])


class ChatRequest(BaseModel):
    conversation_id: int
    query: str
    history_turns: int = 6
    document_ids: list[int] | None = None
    thinking_level: str | None = None  # off/low/medium/high；None 时回退会话级配置
    attachments: list[dict] | None = None
    use_kb: bool | None = None  # 请求级覆盖会话级 rag_enabled（None→用会话配置）


class ChatResponse(BaseModel):
    answer: str
    citations: list[dict]


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest, agent=Depends(get_agent), db: AIDatabase = Depends(get_db)
) -> ChatResponse:
    conv = db.get_conversation(body.conversation_id)
    if not conv:
        raise HTTPException(404, "会话不存在")
    history = db.list_messages(body.conversation_id, limit=body.history_turns * 2)
    history_msgs = [{"role": m.role.value, "content": m.content} for m in history]
    # use_rag：请求级 use_kb 优先（None→用会话级 rag_enabled）
    use_rag = body.use_kb if body.use_kb is not None else conv.rag_enabled
    # KB 升级：按会话所属项目隔离检索（project_id 来自 Conversation，杜绝跨项目污染）
    proj_id = getattr(conv, "project_id", None)
    result = agent.answer(
        body.query, history_msgs, body.document_ids, use_rag=use_rag, project_id=proj_id
    )
    db.add_message(body.conversation_id, Role.USER, body.query)
    db.add_message(body.conversation_id, Role.ASSISTANT, result.answer, result.citations)
    return ChatResponse(
        answer=result.answer,
        citations=[c.__dict__ for c in result.citations],
    )


def _sse(event_type: str, data) -> str:
    payload = (
        data
        if isinstance(data, str)
        else json.dumps(data, ensure_ascii=False, default=lambda o: o.__dict__)
    )
    return f"event: {event_type}\ndata: {payload}\n\n"


@router.post("/stream")
async def chat_stream(
    body: ChatRequest, agent=Depends(get_agent), db: AIDatabase = Depends(get_db)
):
    conv = db.get_conversation(body.conversation_id)
    if not conv:
        raise HTTPException(404, "会话不存在")
    history = db.list_messages(body.conversation_id, limit=body.history_turns * 2)
    history_msgs = [{"role": m.role.value, "content": m.content} for m in history]
    db.add_message(body.conversation_id, Role.USER, body.query, attachments=body.attachments)

    thinking_switch = (
        body.thinking_level
        if body.thinking_level is not None
        else getattr(conv, "thinking_level", "off")
    )
    # 防御：迁移中途脏数据（None / 非标准值）兜底为 off
    if not thinking_switch or thinking_switch not in ("off", "low", "medium", "high"):
        thinking_switch = "off"

    full_answer = [""]  # 用 list 闭包可变
    thinking_text = [""]
    citations_holder = [[]]

    # use_rag：请求级 use_kb 优先（None→用会话级 rag_enabled）
    use_rag = body.use_kb if body.use_kb is not None else conv.rag_enabled
    # KB 升级：按会话所属项目隔离检索（project_id 来自 Conversation）
    proj_id = getattr(conv, "project_id", None)

    async def event_gen():
        try:
            async for event in agent.stream_answer_async(
                body.query,
                history_msgs,
                body.document_ids,
                use_rag=use_rag,
                thinking_level=thinking_switch,
                project_id=proj_id,
            ):
                if event.type == "citations":
                    citations_holder[0] = event.data
                    # spec §6.4：data 包成 {"citations":[...]}，对齐前端解析
                    yield _sse("citations", {"citations": [c.__dict__ for c in event.data]})
                elif event.type == "thinking":
                    thinking_text[0] += event.data
                    yield _sse("thinking", {"text": event.data})
                elif event.type == "token":
                    full_answer[0] += event.data
                    yield _sse("token", {"text": event.data})
                elif event.type == "done":
                    db.add_message(
                        body.conversation_id,
                        Role.ASSISTANT,
                        full_answer[0],
                        citations_holder[0],
                        thinking=thinking_text[0] or None,
                    )
                    yield _sse("done", {})
                elif event.type == "error":
                    # 写入错误占位消息，保证历史完整（避免 DB 残留孤立 user 消息）
                    db.add_message(
                        body.conversation_id,
                        Role.ASSISTANT,
                        f"⚠️ 回复失败：{event.data}",
                    )
                    yield _sse("error", {"code": "internal", "message": str(event.data)})
        except Exception as e:
            # 写入错误占位消息，保证历史完整（避免 DB 残留孤立 user 消息）
            db.add_message(
                body.conversation_id,
                Role.ASSISTANT,
                f"⚠️ 回复失败：{e}",
            )
            yield _sse("error", {"code": "internal", "message": str(e)})

    return StreamingResponse(event_gen(), media_type="text/event-stream")


_ATTACHMENT_ID_RE = re.compile(r"^[a-f0-9]+\.[a-zA-Z0-9]+$")
_PREVIEW_MAX_CHARS = 2000


def _is_image_mime(mime: str) -> bool:
    return mime.startswith("image/")


def _extract_preview_text(filename: str, path: Path) -> str | None:
    """文档类附件：用 KB loader 抽纯文本前 N 字。失败返回 None。"""
    try:
        from insight_aitest.platform.services.kb.loader import get_loader

        loader = get_loader(filename)
        doc = loader.load(path)
        return doc.content[:_PREVIEW_MAX_CHARS]
    except Exception:
        # 不支持的格式 / 解析失败 → 不阻塞上传，仅 preview_text=None
        return None


@router.post("/attachments")
async def upload_attachments(
    files: list[UploadFile] = File(...),
    config=Depends(get_config),
) -> dict:
    """上传会话附件 → 存原始文件 + 返回附件元数据列表。

    图片：kind=image，preview_text=None。
    文档：kind=document，preview_text=KB loader 抽取纯文本前 2000 字。
    不入知识库（只服务本次对话预览）。
    """
    attachments_dir = Path(config.docs_dir) / "attachments"
    attachments_dir.mkdir(parents=True, exist_ok=True)

    result = []
    for f in files:
        content = await f.read()
        if len(content) > config.max_upload_mb * 1024 * 1024:
            raise HTTPException(413, f"附件超过 {config.max_upload_mb}MB 限制")
        ext = Path(f.filename or "").suffix
        basename = f"{uuid.uuid4().hex}{ext}"
        storage_path = attachments_dir / basename
        storage_path.write_bytes(content)

        mime = f.content_type or "application/octet-stream"
        kind = "image" if _is_image_mime(mime) else "document"
        preview_text = None
        if kind == "document":
            preview_text = _extract_preview_text(f.filename or "", storage_path)

        result.append(
            {
                "id": basename,
                "filename": f.filename,
                "mime": mime,
                "kind": kind,
                "size": len(content),
                "preview_text": preview_text,
            }
        )

    return {"attachments": result}


@router.get("/attachments/{attachment_id}")
async def download_attachment(
    attachment_id: str,
    config=Depends(get_config),
):
    """下载附件原始文件。attachment_id = storage basename（uuid.ext）。"""
    if not _ATTACHMENT_ID_RE.match(attachment_id):
        raise HTTPException(400, "非法附件 ID")

    path = Path(config.docs_dir) / "attachments" / attachment_id
    if not path.exists():
        raise HTTPException(404, "附件不存在")

    return FileResponse(str(path), filename=attachment_id)
