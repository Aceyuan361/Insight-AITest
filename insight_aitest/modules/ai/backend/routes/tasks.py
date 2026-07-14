# -*- coding: utf-8 -*-
"""Agent Task API：/api/modules/ai/tasks/*

全自主 Agent 闭环：
- POST /tasks：提交意图（+可选文件）→ understand + strategize → 返回 pending_select task
- POST /tasks/upload：上传文件 → 进知识库 + 返回解析内容
- POST /tasks/{id}/select：用户选择策略 → 全自主执行
- POST /tasks/{id}/confirm：兼容旧流程（直接确认 plan 执行）
- GET /tasks：列出所有 task
- GET /tasks/{id}：查询 task 状态 + 进度 + 策略
- GET /tasks/{id}/stream：SSE 流式推送执行进度
- DELETE /tasks/{id}：取消 task
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import threading
import uuid
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from insight_aitest.modules.ai.backend.deps import (
    get_config,
    get_db,
    get_executor,
    get_kb_db,
    get_llm,
    get_planner,
)
from insight_aitest.modules.ai.backend.persistence.database import AIDatabase
from insight_aitest.modules.ai.backend.persistence.models import TaskStatus, Role
from insight_aitest.modules.ai.backend.agent.prompts import build_agent_chat_message
from insight_aitest.modules.ai.backend.agent.reactor import ReActAgent, ReActConfig

router = APIRouter(prefix="/tasks", tags=["ai-tasks"])


def _task_sse(event_type: str, data: Any) -> str:
    """SSE 事件封装（与 chat.py 的 _sse 同格式）。"""
    payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event_type}\ndata: {payload}\n\n"


# ===== 任务事件队列注册表（select/confirm 注册 → stream 消费）=====
# task_id → (asyncio.Queue, loop)；executor 在后台线程通过 queue 推送细粒度事件
_task_queues: dict[int, tuple[asyncio.Queue, asyncio.AbstractEventLoop]] = {}


def _register_queue(task_id: int) -> tuple[asyncio.Queue, asyncio.AbstractEventLoop]:
    """为 task 创建事件队列并注册（在调用方的事件循环里建 queue）。"""
    loop = asyncio.get_running_loop()
    q: asyncio.Queue = asyncio.Queue()
    _task_queues[task_id] = (q, loop)
    return q, loop


def _unregister_queue(task_id: int) -> None:
    _task_queues.pop(task_id, None)


def _run_task_plan(executor, task_id, plan, db, queue, loop) -> None:
    """执行 plan：react_enabled 时用 ReActAgent，否则回退到 executor.run。

    LLMClient/LLMConfig 来自 executor.ctx（get_executor 构建的 SkillContext）。
    """
    config = getattr(executor.ctx, "config", None)
    react_cfg = config.react_config() if hasattr(config, "react_config") else ReActConfig()
    if react_cfg.enabled:
        agent = ReActAgent(executor, executor.ctx.llm, config, react_cfg)
        agent.run(task_id, plan, db, queue=queue, loop=loop)
    else:
        executor.run(task_id, plan, db, queue=queue, loop=loop)


# ===== Schemas =====


class TaskCreateRequest(BaseModel):
    intent: str = Field(..., min_length=1)
    project_id: int | None = None
    version_id: int | None = None
    files: list[dict] | None = None  # [{filename, content}] 已上传并解析的文件内容
    thinking_level: str | None = None  # off/low/medium/high（None → 读全局默认 off）
    use_kb: bool = False  # 是否启用知识库检索（默认关——不是所有需求文档都需要 RAG 召回）
    document_ids: list[int] | None = None  # 需求文档的知识库 ID
    conversation_id: int | None = None  # 关联已有会话（后续任务继承同一会话，修复拆分问题）


class TaskConfirmRequest(BaseModel):
    selected_steps: list[int] | None = None


class TaskSelectRequest(BaseModel):
    strategy_id: str
    project_id: int | None = None
    version_id: int | None = None
    use_kb: bool | None = None  # 可选覆盖（默认从 task context_json 读）


class GenerateBatchRequest(BaseModel):
    """两阶段生成闭环阶段2：用户确认测试点范围后的批量生成请求。

    test_points 是用户在 TestPointCard 里确认（可能裁减）后的测试点列表，
    每条结构为 {id, summary, suggested_type, suggested_design, rationale}
    （兼容旧结构 {id, description, type_hint, design_hint}）。
    """

    test_points: list[dict]
    project_id: int | None = None
    version_id: int | None = None
    use_kb: bool | None = None  # 可选覆盖（默认从 task context_json 读）


class QuickTaskRequest(BaseModel):
    """轻量预配置任务请求：跳过 understand/strategize，直接构建 plan 执行。

    - analyze_generate：从需求文档（query + document_ids）提取测试点 → 批量生成用例
    - image_generate：从 UI 截图生成 UI 用例
    """

    mode: Literal["analyze_generate", "image_generate"]
    query: str | None = None
    document_ids: list[int] | None = None
    images: list[dict] | None = None
    base_url: str | None = None
    point_summary: str = ""
    project_id: int | None = None
    version_id: int | None = None
    use_kb: bool = True


class PlanStepOut(BaseModel):
    skill: str
    desc: str
    params: dict


class StrategyOut(BaseModel):
    id: str
    label: str
    description: str
    plan: list[PlanStepOut]


class TaskOut(BaseModel):
    id: int
    intent: str
    plan: list[PlanStepOut]
    status: str
    current_step: int
    total_steps: int
    result: dict
    error: str | None
    context: dict
    strategies: list[StrategyOut]
    selected_strategy: str | None
    uploaded_files: list[str]
    project_id: int | None = None
    version_id: int | None = None
    use_kb: bool = False
    source_mode: str = "full"
    conversation_id: int | None = None
    created_at: str
    updated_at: str
    finished_at: str | None


def _task_to_out(task) -> TaskOut:
    return TaskOut(
        id=task.id,
        intent=task.intent,
        plan=[PlanStepOut(**s) if isinstance(s, dict) else s for s in (task.plan_json or [])],
        status=task.status.value,
        current_step=task.current_step,
        total_steps=task.total_steps,
        result=task.result_json or {},
        error=task.error,
        context=task.context_json or {},
        strategies=[
            StrategyOut(
                id=s.get("id", ""),
                label=s.get("label", ""),
                description=s.get("description", ""),
                plan=[PlanStepOut(**p) if isinstance(p, dict) else p for p in s.get("plan", [])],
            )
            for s in (task.strategies_json or [])
        ],
        selected_strategy=task.selected_strategy,
        uploaded_files=task.uploaded_files or [],
        project_id=task.project_id,
        version_id=task.version_id,
        use_kb=bool(getattr(task, "use_kb", False) or False),
        source_mode=getattr(task, "source_mode", "full") or "full",
        conversation_id=getattr(task, "conversation_id", None),
        created_at=task.created_at.isoformat() if task.created_at else "",
        updated_at=task.updated_at.isoformat() if task.updated_at else "",
        finished_at=task.finished_at.isoformat() if task.finished_at else None,
    )


def _sse(event_type: str, data: Any) -> str:
    payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n"


def _fetch_kb_documents(document_ids: list[int], kb_db) -> list[dict]:
    """从知识库获取文档内容（用于后续任务继承文档上下文）。
    
    当用户创建后续任务但没有上传新文件时，使用已有的 document_ids
    从 KB 获取文档内容，拼入 uploaded_files 格式供 planner.understand 使用。
    
    Returns: [{"filename": str, "content": str}, ...]
    """
    docs = []
    for doc_id in document_ids:
        try:
            doc = kb_db.get_document(doc_id)
            filename = doc.filename if doc else f"document_{doc_id}"
            content = kb_db.get_document_content(doc_id)
            if content:
                docs.append({"filename": filename, "content": content[:5000]})
        except Exception:
            continue
    return docs


def _synthesize_task_context(task) -> list[dict]:
    """从 task 字段合成上下文消息（向后兼容：旧 task 无持久化消息时使用）。
    
    返回 message dict 列表（role + content），按时间顺序排列。
    """
    msgs: list[dict] = []
    # 1. 用户意图
    if task.intent:
        msgs.append({"role": "user", "content": task.intent})
    # 2. 需求理解
    ctx = task.context_json or {}
    if isinstance(ctx, dict):
        summary = ctx.get("summary", "")
        scope = ctx.get("scope", [])
        if summary:
            scope_text = ", ".join(scope[:5]) if scope else ""
            understand = f"【需求理解】{summary}"
            if scope_text:
                understand += f"\n\n涉及范围：{scope_text}"
            msgs.append({"role": "assistant", "content": understand})
    # 3. 策略建议
    strategies = task.strategies_json or []
    if strategies:
        lines = []
        for s in strategies:
            label = s.get("label", "")
            desc = s.get("description", "")
            lines.append(f"- **{label}**：{desc}")
        if lines:
            msgs.append({"role": "assistant", "content": "【测试策略建议】\n\n" + "\n".join(lines)})
    # 4. 策略选择
    if task.selected_strategy:
        selected_label = task.selected_strategy
        for s in strategies:
            if s.get("id") == task.selected_strategy:
                selected_label = s.get("label", task.selected_strategy)
                break
        msgs.append({"role": "user", "content": f"选择策略：{selected_label}"})
    # 5. 执行结果
    result = task.result_json or {}
    if isinstance(result, dict) and result.get("summary"):
        status_emoji = "✅" if task.status and task.status.value == "done" else ""
        msgs.append({"role": "assistant", "content": f"{status_emoji} {result['summary']}".strip()})
    return msgs


# ===== File parsing =====


def _parse_file_content(filename: str, content: bytes, llm, config) -> str:
    """解析上传文件为纯文本。文本用 loader，图片用 vision。"""
    ext = Path(filename).suffix.lower()
    if ext in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
        # 图片：用 vision 模型描述
        mime = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }.get(ext, "image/png")
        b64 = base64.b64encode(content).decode()
        try:
            return llm.chat_with_image(
                "请详细描述这个 UI 截图/设计稿的内容，包括页面布局、交互元素、输入框、按钮等。",
                b64,
                mime=mime,
            )
        except Exception as e:
            return f"[图片解析失败: {e}]"
    else:
        # 文本文件：用 KB loader 解析
        try:
            from insight_aitest.platform.services.kb.loader import get_loader

            tmp_path = Path(config.docs_dir) / f"_tmp_{uuid.uuid4().hex}{ext}"
            tmp_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path.write_bytes(content)
            loader = get_loader(filename)
            parsed = loader.load(tmp_path)
            tmp_path.unlink(missing_ok=True)
            return parsed.content[:5000]  # 截断防止超长
        except Exception as e:
            return f"[文件解析失败: {e}]"


# ===== Endpoints =====


@router.get("", response_model=list[TaskOut])
async def list_tasks(
    project_id: int | None = None,
    db: AIDatabase = Depends(get_db),
) -> list[TaskOut]:
    return [_task_to_out(t) for t in db.list_tasks(project_id=project_id)]


@router.post("/upload")
async def upload_files(
    files: list[UploadFile] = File(...),
    config=Depends(get_config),
    llm=Depends(
        lambda: __import__("insight_aitest.platform.services.kb.deps", fromlist=["get_llm"]).get_llm()
    ),
) -> dict:
    """上传文件 → 解析内容返回（供前端拼入 task 创建请求）。

    文件同时存入知识库（永久资产）。
    """
    parsed_files = []
    document_ids = []  # 存入知识库的文档ID列表，供前端回传贯穿全链路
    for f in files:
        content = await f.read()
        if len(content) > config.max_upload_mb * 1024 * 1024:
            raise HTTPException(413, f"文件超过 {config.max_upload_mb}MB 限制")
        text = _parse_file_content(f.filename or "unknown", content, llm, config)
        parsed_files.append({"filename": f.filename, "content": text})

        # 同时存入知识库（复用 kb 模块的 ingest）
        try:
            from insight_aitest.platform.services.kb.deps import get_kb_db
            from insight_aitest.platform.services.kb.models import DocumentStatus
            from insight_aitest.platform.services.kb.ingest import process_document

            kb_db = get_kb_db()
            content_hash = hashlib.sha256(content).hexdigest()
            existing = kb_db.find_by_content_hash(content_hash)
            if existing:
                # 文件已存在，复用已有文档ID
                document_ids.append(existing.id)
            else:
                ext = Path(f.filename or "").suffix
                docs_dir = Path(config.docs_dir)
                docs_dir.mkdir(parents=True, exist_ok=True)
                storage_path = docs_dir / f"{uuid.uuid4().hex}{ext}"
                storage_path.write_bytes(content)
                doc_id = kb_db.create_document(
                    f.filename, str(storage_path), content_hash, f.content_type
                )
                document_ids.append(doc_id)

                # 后台索引
                def _bg(did=doc_id):
                    try:
                        from insight_aitest.platform.services.kb.deps import (
                            get_llm as _get_llm,
                            get_vector_store as _get_vs,
                        )

                        process_document(did, kb_db, _get_vs(), _get_llm(), config)
                    except Exception:
                        kb_db.update_document_status(did, DocumentStatus.PARSE_FAILED)

                threading.Thread(target=_bg, daemon=True).start()
        except Exception:
            pass  # 知识库存入失败不阻塞任务

    return {"files": parsed_files, "document_ids": document_ids}


@router.post("", response_model=TaskOut)
async def create_task(
    body: TaskCreateRequest,
    db: AIDatabase = Depends(get_db),
    planner=Depends(get_planner),
    kb_db=Depends(get_kb_db),
) -> TaskOut:
    """提交意图 + 文件内容 → understand + strategize → 返回 pending_select task。"""
    uploaded_files = body.files or []

    # 修复上下文丢失：后续任务无新文件时，从 KB 获取已有文档内容
    if not uploaded_files and body.document_ids:
        kb_docs = _fetch_kb_documents(body.document_ids, kb_db)
        if kb_docs:
            uploaded_files = kb_docs

    filenames = [f["filename"] for f in uploaded_files]

    # 解析或创建 Conversation（修复会话拆分：Task 创建时即绑定 Conversation）
    conv_id = body.conversation_id
    conv_created_here = conv_id is None
    if conv_created_here:
        conv_id = db.create_conversation(
            title=body.intent[:50] if body.intent else "新任务",
            project_id=body.project_id,
        )

    # 创建 task（UNDERSTANDING 状态，关联 conversation）
    task_id = db.create_task(
        body.intent,
        uploaded_files=filenames,
        project_id=body.project_id,
        version_id=body.version_id,
        use_kb=body.use_kb,
        conversation_id=conv_id,
    )

    # 持久化用户意图消息（修复上下文丢失：后续 agent_chat 可加载历史）
    db.add_message(conv_id, Role.USER, body.intent, task_id=task_id)

    # 阶段 A：理解
    context = planner.understand(body.intent, uploaded_files)
    context["document_ids"] = body.document_ids or []
    context["project_id"] = body.project_id
    db.update_task_context(task_id, context, status=TaskStatus.STRATEGIZING)

    # 持久化理解结果消息
    summary_text = context.get("summary", body.intent)
    scope_text = ", ".join(context.get("scope", [])[:5]) if context.get("scope") else ""
    understand_msg = f"【需求理解】{summary_text}"
    if scope_text:
        understand_msg += f"\n\n涉及范围：{scope_text}"
    db.add_message(conv_id, Role.ASSISTANT, understand_msg, task_id=task_id)

    # 阶段 B：策略生成
    strategies = planner.propose_strategies(context, document_ids=body.document_ids)
    db.update_task_strategies(task_id, strategies, status=TaskStatus.PENDING_SELECT)

    # 持久化策略消息
    strategy_lines = []
    for s in strategies:
        label = s.get("label", "")
        desc = s.get("description", "")
        strategy_lines.append(f"- **{label}**：{desc}")
    if strategy_lines:
        db.add_message(
            conv_id, Role.ASSISTANT,
            "【测试策略建议】\n\n" + "\n".join(strategy_lines),
            task_id=task_id,
        )

    return _task_to_out(db.get_task(task_id))


@router.post("/stream")
async def create_task_stream(
    body: TaskCreateRequest,
    db: AIDatabase = Depends(get_db),
    planner=Depends(get_planner),
    kb_db=Depends(get_kb_db),
):
    """流式创建任务：understand + strategize 的 LLM 调用走 token 级 SSE。

    事件序列：
    - phase      {phase: "understanding"|"strategizing"}
    - thinking   {text}（reasoning token，实时推送思考过程）
    - understand_done {summary, scope}
    - strategies_done {strategies}
    - done       {task}（完整 TaskOut）
    - error      {message}

    与 POST /tasks 同语义，但推送思考过程。前端默认调此端点，失败可降级回 POST /tasks。
    """
    uploaded_files = body.files or []

    # 修复上下文丢失：后续任务无新文件时，从 KB 获取已有文档内容
    if not uploaded_files and body.document_ids:
        kb_docs = _fetch_kb_documents(body.document_ids, kb_db)
        if kb_docs:
            uploaded_files = kb_docs

    filenames = [f["filename"] for f in uploaded_files]
    thinking_level = body.thinking_level or "off"

    # 解析或创建 Conversation（修复会话拆分：Task 创建时即绑定 Conversation）
    conv_id = body.conversation_id
    conv_created_here = conv_id is None
    if conv_created_here:
        conv_id = db.create_conversation(
            title=body.intent[:50] if body.intent else "新任务",
            project_id=body.project_id,
        )

    task_id = db.create_task(
        body.intent,
        uploaded_files=filenames,
        project_id=body.project_id,
        version_id=body.version_id,
        use_kb=body.use_kb,
        conversation_id=conv_id,
    )

    # 持久化用户意图消息（修复上下文丢失）
    db.add_message(conv_id, Role.USER, body.intent, task_id=task_id)

    # 同步 planner 生成器在执行器线程里跑（阻塞 LLM 调用不占事件循环），
    # 通过 asyncio.Queue 喂给 async 生成器。复用 rag.py 的线程→协程桥接模式。
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()
    SENTINEL = object()
    ERROR_SENTINEL = object()
    error_holder: list[str] = []

    def _produce():
        """执行器线程：跑 understand_stream + propose_strategies_stream，结果塞 queue。"""
        try:
            # 阶段 A：理解
            context: dict = {"summary": body.intent, "scope": [body.intent]}
            for kind, data in planner.understand_stream(
                body.intent, uploaded_files, thinking_level
            ):
                if kind == "result":
                    context = data  # 回填：stream 的 result 是最终理解结果
                asyncio.run_coroutine_threadsafe(
                    queue.put(("understand", kind, data)), loop
                ).result()
                if kind == "error":
                    return
            context["document_ids"] = body.document_ids or []
            context["project_id"] = body.project_id
            db.update_task_context(task_id, context, status=TaskStatus.STRATEGIZING)

            # 持久化理解结果消息
            summary_text = context.get("summary", body.intent)
            scope_text = ", ".join(context.get("scope", [])[:5]) if context.get("scope") else ""
            understand_msg = f"【需求理解】{summary_text}"
            if scope_text:
                understand_msg += f"\n\n涉及范围：{scope_text}"
            db.add_message(conv_id, Role.ASSISTANT, understand_msg, task_id=task_id)

            # 阶段 B：策略生成
            strategies: list[dict] = []
            for kind, data in planner.propose_strategies_stream(context, thinking_level, document_ids=body.document_ids):
                if kind == "result":
                    strategies = data  # 回填：stream 的 result 是最终策略列表
                asyncio.run_coroutine_threadsafe(
                    queue.put(("strategize", kind, data)), loop
                ).result()
                if kind == "error":
                    return
            db.update_task_strategies(task_id, strategies, status=TaskStatus.PENDING_SELECT)

            # 持久化策略消息
            strategy_lines = []
            for s in strategies:
                label = s.get("label", "")
                desc = s.get("description", "")
                strategy_lines.append(f"- **{label}**：{desc}")
            if strategy_lines:
                db.add_message(
                    conv_id, Role.ASSISTANT,
                    "【测试策略建议】\n\n" + "\n".join(strategy_lines),
                    task_id=task_id,
                )
        except Exception as e:
            error_holder.append(str(e))
            asyncio.run_coroutine_threadsafe(queue.put(ERROR_SENTINEL), loop).result()
            return
        asyncio.run_coroutine_threadsafe(queue.put(SENTINEL), loop).result()

    loop.run_in_executor(None, _produce)

    async def event_gen():
        try:
            # 阶段 A 起始
            yield _task_sse("phase", {"phase": "understanding"})
            in_strategize = False
            while True:
                item = await queue.get()
                if item is SENTINEL:
                    break
                if item is ERROR_SENTINEL:
                    msg = error_holder[0] if error_holder else "未知错误"
                    # 理解/策略阶段失败：直接删除任务（不残留 FAILED 行，避免切换 tab 后出现重复会话）
                    db.delete_task(task_id)
                    if conv_created_here:
                        db.delete_conversation(conv_id)
                    yield _task_sse("error", {"message": msg})
                    return
                stage, kind, data = item
                # 进入策略阶段时推一次 phase 事件
                if stage == "strategize" and not in_strategize:
                    in_strategize = True
                    yield _task_sse("phase", {"phase": "strategizing"})
                if kind == "thinking":
                    yield _task_sse("thinking", {"text": data})
                elif kind == "result":
                    if stage == "understand":
                        yield _task_sse("understand_done", data)
                    else:
                        yield _task_sse("strategies_done", {"strategies": data})
                elif kind == "error":
                    # 同上：失败直接删除，不留 FAILED 残留
                    db.delete_task(task_id)
                    if conv_created_here:
                        db.delete_conversation(conv_id)
                    yield _task_sse("error", {"message": str(data)})
                    return
            yield _task_sse("done", {"task": _task_to_out(db.get_task(task_id)).model_dump()})
        except Exception as e:
            # 兜底异常同样删除失败任务
            db.delete_task(task_id)
            if conv_created_here:
                db.delete_conversation(conv_id)
            yield _task_sse("error", {"message": str(e)})

    return StreamingResponse(event_gen(), media_type="text/event-stream")


class AgentChatRequest(BaseModel):
    """Agent 工作台轻对话模式请求。

    task_id 非 None 时接入消息持久化：加载历史 + 写入 user/assistant 消息。
    """

    message: str
    thinking_level: str | None = None
    task_id: int | None = None
    history_turns: int = 6


@router.post("/chat")
async def agent_chat(
    body: AgentChatRequest,
    llm=Depends(get_llm),
    config=Depends(get_config),
    db: AIDatabase = Depends(get_db),
):
    """Agent 工作台轻对话模式：流式对话回复 + 思维链。

    与 POST /tasks（重任务）的区别：
    - 不走 understand/strategize/execute，直接对话回复
    - 事件：thinking / token / done / error（与 chat.py 同格式）

    task_id 非 None 时接入消息持久化：加载历史消息 + 写入 user/assistant 消息，
    让 agent 在用户反馈时有上下文记忆（修复缺陷2 反馈失忆）。
    task_id 为 None 时退化为原行为：纯流式回复，不写 DB。

    用 LLMClient.stream_chat_raw 直接流式（带 reasoning），系统提示用 Agent 人设。
    """
    thinking_level = body.thinking_level or "off"
    if thinking_level not in ("off", "low", "medium", "high"):
        thinking_level = "off"

    # task_id 非 None：加载历史 + 持久化 user/assistant 消息
    conv_id: int | None = None
    history_msgs: list[dict] = []
    has_task_context = False
    if body.task_id is not None:
        from insight_aitest.platform.persistence import session_scope
        from insight_aitest.modules.ai.backend.persistence.models import Task

        task = db.get_task(body.task_id)
        if task is not None:
            has_task_context = True
            # 解析 conversation：B1 修复后 task 创建时已绑定，此处保留向后兼容
            if task.conversation_id is None:
                # 向后兼容：旧 task 无 conversation_id，懒惰创建
                conv_id = db.create_conversation(
                    title=task.intent[:20] if task.intent else "任务对话",
                    project_id=task.project_id,
                )
                with session_scope(db.db_path) as s:
                    t = s.get(Task, body.task_id)
                    if t is not None:
                        t.conversation_id = conv_id
            else:
                conv_id = task.conversation_id

            # 加载历史消息（按 task_id，最近 history_turns*2 条，时间正序）
            history = db.list_messages_by_task(
                body.task_id, limit=body.history_turns * 2
            )
            for m in history:
                history_msgs.append({"role": m.role.value, "content": m.content})

            # 若历史为空（旧 task 无持久化消息）→ 从 task 字段合成上下文
            if not history_msgs:
                synthesized = _synthesize_task_context(task)
                history_msgs.extend(synthesized)

            # 注入 task 上下文摘要（若有）作为额外 system 消息
            if task.context_json:
                ctx_summary = task.context_json.get("summary") if isinstance(
                    task.context_json, dict
                ) else None
                if ctx_summary:
                    history_msgs.insert(
                        0,
                        {
                            "role": "system",
                            "content": f"【任务上下文】{ctx_summary}",
                        },
                    )

            # 注入 document_ids 信息（告知 LLM 可用文档）
            doc_ids = (task.context_json or {}).get("document_ids", []) if isinstance(task.context_json, dict) else []
            if doc_ids:
                history_msgs.insert(
                    0,
                    {
                        "role": "system",
                        "content": f"【关联文档】本任务基于 {len(doc_ids)} 份需求文档（文档ID: {doc_ids}）。用户可能要求基于这些文档继续工作。",
                    },
                )

            # 注入任务状态信息
            status_info = f"【任务状态】当前任务状态: {task.status.value}。"
            if task.result_json and isinstance(task.result_json, dict):
                summary = task.result_json.get("summary", "")
                if summary:
                    status_info += f"\n执行结果: {summary}"
            history_msgs.insert(0, {"role": "system", "content": status_info})

            # 注入会话上下文摘要（长会话时替代被截断的早期消息）
            from insight_aitest.modules.ai.backend.agent.summarizer import (
                summarize_context, format_summary_for_injection,
            )
            conv_summary = summarize_context(conv_id, db, llm)
            if conv_summary:
                history_msgs.insert(
                    0,
                    {
                        "role": "system",
                        "content": format_summary_for_injection(conv_summary),
                    },
                )

            # 持久化 user 消息（在 LLM 调用前）
            db.add_message(conv_id, Role.USER, body.message, task_id=body.task_id)

    # 构造 LLM 消息列表：[system] + history + [user]
    system_msg = build_agent_chat_message(has_task_context=has_task_context)
    llm_messages = (
        [{"role": "system", "content": system_msg}] + history_msgs + [{"role": "user", "content": body.message}]
    )

    # 收集完整回复（流式结束后持久化 assistant 消息）
    full_answer_holder: list[str] = []

    async def event_gen():
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()
        SENTINEL = object()
        ERROR_SENTINEL = object()
        error_holder: list[str] = []

        def _produce():
            try:
                for kind, text in llm.stream_chat_raw(
                    llm_messages,
                    thinking_level=thinking_level,
                ):
                    if kind != "reasoning":
                        full_answer_holder.append(text)
                    asyncio.run_coroutine_threadsafe(queue.put((kind, text)), loop).result()
            except Exception as e:
                error_holder.append(str(e))
                asyncio.run_coroutine_threadsafe(queue.put(ERROR_SENTINEL), loop).result()
                return
            asyncio.run_coroutine_threadsafe(queue.put(SENTINEL), loop).result()

        loop.run_in_executor(None, _produce)
        try:
            while True:
                item = await queue.get()
                if item is SENTINEL:
                    break
                if item is ERROR_SENTINEL:
                    yield _task_sse(
                        "error", {"message": error_holder[0] if error_holder else "未知错误"}
                    )
                    return
                kind, text = item
                if kind == "reasoning":
                    yield _task_sse("thinking", {"text": text})
                else:
                    yield _task_sse("token", {"text": text})
            # 流式结束：持久化 assistant 消息（仅 task_id 模式且有内容）
            answer = "".join(full_answer_holder).strip()
            if body.task_id is not None and conv_id is not None and answer:
                db.add_message(
                    conv_id, Role.ASSISTANT, answer, task_id=body.task_id
                )
            yield _task_sse("done", {})
        except Exception as e:
            yield _task_sse("error", {"message": str(e)})

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@router.post("/{task_id}/select", response_model=TaskOut)
async def select_strategy(
    task_id: int,
    body: TaskSelectRequest,
    db: AIDatabase = Depends(get_db),
) -> TaskOut:
    """用户选择策略 → 全自主执行。"""
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.status != TaskStatus.PENDING_SELECT:
        raise HTTPException(400, f"任务状态 {task.status.value}，无法选择")

    # 找到选中的策略
    selected = None
    for s in task.strategies_json or []:
        if s.get("id") == body.strategy_id:
            selected = s
            break
    if not selected:
        raise HTTPException(400, f"策略 {body.strategy_id} 不存在")

    plan = selected.get("plan", [])
    # 从 task context 注入 document_ids（LLM 可能生成了空 []，始终用真实值覆盖）
    doc_ids = (task.context_json or {}).get("document_ids", [])
    if doc_ids:
        for step in plan:
            if step.get("skill") in {
                "extract_test_points", "write_cases_batch",
                "write_functional_case", "write_api_case", "write_ui_case_from_image",
                "generate_data_driven_api_case",
            }:
                step["params"]["document_ids"] = doc_ids
    db.select_task_strategy(task_id, body.strategy_id, plan)

    # 持久化策略选择消息
    strategy_label = selected.get("label", body.strategy_id)
    conv_id = task.conversation_id
    if conv_id is not None:
        db.add_message(
            conv_id, Role.USER,
            f"选择策略：{strategy_label}",
            task_id=task_id,
        )

    # 注册事件队列供 SSE 消费（executor 推送细粒度子步骤事件）
    queue, loop = _register_queue(task_id)

    # use_kb：请求体优先，否则从 task 记录读
    use_kb = body.use_kb if body.use_kb is not None else bool(getattr(task, "use_kb", False))

    # 后台线程执行
    def _run():
        try:
            executor = get_executor(body.project_id, body.version_id, use_kb=use_kb, task_id=task_id, task_db=db, queue=queue, evt_loop=loop)
            _run_task_plan(executor, task_id, plan, db, queue, loop)
        except Exception as e:
            db.update_task_status(task_id, TaskStatus.FAILED, error=str(e))
        finally:
            _unregister_queue(task_id)

    threading.Thread(target=_run, daemon=True).start()

    return _task_to_out(db.get_task(task_id))


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(task_id: int, db: AIDatabase = Depends(get_db)) -> TaskOut:
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    return _task_to_out(task)


@router.get("/{task_id}/messages")
async def get_task_messages(task_id: int, db: AIDatabase = Depends(get_db)) -> dict:
    """返回任务关联的消息列表（用于前端刷新后重建对话历史）。
    
    若 task 有 conversation_id，同时返回同会话下其他任务的消息，
    实现跨任务历史连续（修复会话拆分后的历史丢失问题）。
    """
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    
    messages = db.list_messages_by_task(task_id)
    
    # 跨任务合并：同 conversation 下其他 task 的消息也纳入
    conv_id = task.conversation_id
    if conv_id is not None:
        conv_messages = db.list_messages(conv_id)
        # 只保留未在当前 task messages 中的消息（去重，按 message id）
        existing_ids = {m.id for m in messages}
        for m in conv_messages:
            if m.id not in existing_ids and m.task_id is not None and m.task_id != task_id:
                messages.append(m)
        # 按创建时间升序排列
        messages.sort(key=lambda m: m.created_at if m.created_at else "")
    
    return {
        "task_id": task_id,
        "conversation_id": conv_id,
        "messages": [
            {
                "role": m.role.value,
                "content": m.content,
                "citations": [c.__dict__ if hasattr(c, '__dict__') else c for c in (m.citations or [])],
                "thinking": m.thinking,
                "attachments": m.attachments,
                "task_id": m.task_id,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
    }


@router.post("/{task_id}/confirm", response_model=TaskOut)
async def confirm_task(
    task_id: int,
    body: TaskConfirmRequest | None = None,
    db: AIDatabase = Depends(get_db),
) -> TaskOut:
    """兼容旧流程：直接确认 plan 执行（无策略选择）。"""
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.status != TaskStatus.PENDING_CONFIRM:
        raise HTTPException(400, f"任务状态 {task.status.value}，无法确认")

    plan = task.plan_json
    if body and body.selected_steps is not None:
        plan = [task.plan_json[i] for i in body.selected_steps if i < len(task.plan_json)]

    db.update_task_status(task_id, TaskStatus.RUNNING)

    # 注册事件队列供 SSE 消费
    queue, loop = _register_queue(task_id)

    def _run():
        try:
            executor = get_executor(task_id=task_id, task_db=db, queue=queue)
            _run_task_plan(executor, task_id, plan, db, queue, loop)
        except Exception as e:
            db.update_task_status(task_id, TaskStatus.FAILED, error=str(e))
        finally:
            _unregister_queue(task_id)

    threading.Thread(target=_run, daemon=True).start()
    return _task_to_out(db.get_task(task_id))


@router.post("/{task_id}/generate-batch", response_model=TaskOut)
async def generate_batch(
    task_id: int,
    body: GenerateBatchRequest,
    db: AIDatabase = Depends(get_db),
) -> TaskOut:
    """两阶段用例生成闭环 · 阶段2：用户确认测试点范围后批量生成用例。

    接收 TestPointCard 确认后的 test_points → 构造以 write_cases_batch 为单步
    的 plan → 后台线程顺序执行（**不走 ReAct**，spec B2：生成是写动作）→
    result.batch_id 驱动前端 CaseReviewCard 加载。

    与 select/confirm 的区别：plan 由本端点按确认的测试点即时构造（非 planner 产出），
    执行机制复用 executor.run + 事件队列 + SSE（streamTask 监听进度）。
    """
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    if not body.test_points:
        raise HTTPException(400, "test_points 不能为空")

    # 构造单步 plan：write_cases_batch 接收确认后的测试点
    document_ids = (task.context_json or {}).get("document_ids", [])
    plan = [
        {
            "skill": "write_cases_batch",
            "desc": f"批量生成用例（{len(body.test_points)} 个测试点）",
            "params": {
                "test_points": body.test_points,
                "task_id": task_id,
                "document_ids": document_ids,
            },
        }
    ]
    db.select_task_strategy(task_id, "batch-generate", plan)

    # 注册事件队列供 SSE 消费
    queue, loop = _register_queue(task_id)

    # use_kb：请求体优先，否则从 task 记录读
    use_kb = body.use_kb if body.use_kb is not None else bool(getattr(task, "use_kb", False))

    def _run():
        try:
            # 直接调 executor.run（顺序模式，不走 ReAct —— 生成不走反思循环）
            executor = get_executor(body.project_id, body.version_id, use_kb=use_kb)
            executor.run(task_id, plan, db, queue=queue, loop=loop)
        except Exception as e:
            db.update_task_status(task_id, TaskStatus.FAILED, error=str(e))
        finally:
            _unregister_queue(task_id)

    threading.Thread(target=_run, daemon=True).start()
    return _task_to_out(db.get_task(task_id))


@router.post("/quick", response_model=TaskOut)
async def create_quick_task(
    body: QuickTaskRequest,
    db: AIDatabase = Depends(get_db),
) -> TaskOut:
    """轻量预配置任务：跳过 understand/strategize，直接构建 plan 执行。

    取代 testcase 模块废弃的 /analyze + /generate + /generate-from-image 路由，
    统一走 agent 执行系统。source_mode 标记来源（quick_analyze / quick_image），
    便于区分完整 agent 闭环（full）与轻量入口。

    - analyze_generate：Analyzer.analyze() 提取测试点 → write_cases_batch 批量生成
    - image_generate：write_ui_case_from_image 从截图生成 UI 用例
    """
    source_mode = f"quick_{body.mode.split('_')[0]}"  # quick_analyze / quick_image
    intent = body.query or f"[{body.mode}]"

    task_id = db.create_task(
        intent=intent,
        project_id=body.project_id,
        version_id=body.version_id,
    )
    db.update_task_source_mode(task_id, source_mode)

    if body.mode == "analyze_generate":
        from insight_aitest.modules.testcase.backend.deps import get_analyzer

        analyzer = get_analyzer()
        points = analyzer.analyze(body.query or "", document_ids=body.document_ids)
        if not points:
            db.update_task_status(task_id, TaskStatus.FAILED, error="未提取到测试点")
            return _task_to_out(db.get_task(task_id))

        test_points = [
            {
                "id": p.id,
                "summary": p.summary,
                "suggested_type": p.suggested_type.value,
                "suggested_design": p.suggested_design.value,
                "rationale": p.rationale,
            }
            for p in points
        ]
        plan = [
            {
                "skill": "write_cases_batch",
                "desc": f"批量生成用例（{len(test_points)} 个测试点）",
                "params": {
                    "test_points": test_points,
                    "task_id": task_id,
                    "document_ids": body.document_ids or [],
                },
            }
        ]
    else:  # image_generate
        plan = [
            {
                "skill": "write_ui_case_from_image",
                "desc": "从截图生成 UI 用例",
                "params": {
                    "images": body.images or [],
                    "base_url": body.base_url or "",
                    "point_summary": body.point_summary,
                },
            }
        ]

    db.select_task_strategy(task_id, source_mode, plan)
    db.update_task_status(task_id, TaskStatus.RUNNING)

    queue, loop = _register_queue(task_id)

    def _run():
        try:
            executor = get_executor(
                body.project_id, body.version_id, use_kb=body.use_kb,
                task_id=task_id, task_db=db, queue=queue,
            )
            executor.run(task_id, plan, db, queue=queue, loop=loop)
        except Exception as e:
            db.update_task_status(task_id, TaskStatus.FAILED, error=str(e))
        finally:
            _unregister_queue(task_id)

    threading.Thread(target=_run, daemon=True).start()
    return _task_to_out(db.get_task(task_id))


@router.get("/{task_id}/stream")
async def stream_task(
    task_id: int,
    db: AIDatabase = Depends(get_db),
):
    """SSE 流式推送 task 状态变化。

    优先消费 executor 的事件队列（细粒度子步骤：analyze/fix 轮次可见）；
    队列不存在时回退到 DB 轮询（兼容旧 task 或队列已清理）。
    """
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")

    async def event_gen():
        registered = _task_queues.get(task_id)
        if registered is not None:
            # —— 队列模式：消费 executor 推送的细粒度事件 ——
            queue, _ = registered
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    # 队列空闲：检查 task 是否已终止（队列可能已注销）
                    t = db.get_task(task_id)
                    if t is None:
                        yield _sse("error", {"message": "任务不存在"})
                        return
                    if (
                        t.status in (TaskStatus.DONE, TaskStatus.FAILED, TaskStatus.CANCELLED)
                        and task_id not in _task_queues
                    ):
                        # executor 已结束并注销队列 → 推终态后退出
                        result = t.result_json or {}
                        if t.status == TaskStatus.DONE:
                            yield _sse("done", {"result": result})
                        elif t.status == TaskStatus.FAILED:
                            yield _sse(
                                "error", {"result": result, "message": t.error or "执行失败"}
                            )
                        else:
                            yield _sse("cancelled", {})
                        return
                    continue
                # event 是 TaskEvent（type + data）
                yield _sse(event.type, event.data)
                if event.type in ("done", "error", "cancelled"):
                    return
            return

        # —— 回退模式：DB 轮询（队列不存在）——
        last_step = -1
        last_status = None
        while True:
            task = db.get_task(task_id)
            if task is None:
                yield _sse("error", {"message": "任务不存在"})
                return

            # 状态变化推送（含 understanding/strategizing/pending_select）
            if task.status != last_status:
                last_status = task.status
                if task.status == TaskStatus.PENDING_SELECT:
                    yield _sse(
                        "strategies_ready",
                        {
                            "context": task.context_json or {},
                            "strategies": task.strategies_json or [],
                        },
                    )

            # 步骤变化推送
            if task.current_step != last_step:
                last_step = task.current_step
                plan = task.plan_json or []
                if last_step < len(plan) and task.status == TaskStatus.RUNNING:
                    step = plan[last_step]
                    yield _sse(
                        "step_start",
                        {
                            "step_index": last_step,
                            "skill": step.get("skill"),
                            "desc": step.get("desc"),
                            "current": last_step + 1,
                            "total": task.total_steps,
                        },
                    )

            # 终态推送
            if task.status in (TaskStatus.DONE, TaskStatus.FAILED, TaskStatus.CANCELLED):
                result = task.result_json or {}
                for sr in result.get("steps", []):
                    if "error" in sr:
                        yield _sse(
                            "step_error", {"step_index": sr.get("step_index"), "error": sr["error"]}
                        )
                    else:
                        yield _sse(
                            "step_done",
                            {"step_index": sr.get("step_index"), "result": sr.get("result", {})},
                        )
                if task.status == TaskStatus.DONE:
                    yield _sse("done", {"result": result})
                elif task.status == TaskStatus.FAILED:
                    yield _sse("error", {"result": result, "message": task.error or "执行失败"})
                else:
                    yield _sse("cancelled", {})
                return

            await asyncio.sleep(0.5)

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@router.delete("/{task_id}")
async def cancel_task(task_id: int, db: AIDatabase = Depends(get_db)) -> dict:
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    # 用户显式删除 → 直接硬删除（不再区分状态先cancel再删，避免二次删除）
    db.delete_task(task_id)
    return {"deleted": task_id}


# ===== KB 管理端点（文档列表 + 重索引）=====


@router.get("/kb/documents")
async def list_kb_documents(
    project_id: int | None = None,
    kb_db=Depends(get_kb_db),
) -> list[dict]:
    """返回项目下的知识库文档列表（含类型标签，供手动档文档选择器使用）。"""
    docs = kb_db.list_documents(project_id=project_id if project_id else None)
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "doc_type": d.doc_type or "",
            "mime_type": d.mime_type or "",
            "status": d.status.value if hasattr(d.status, "value") else str(d.status),
            "char_count": d.char_count or 0,
            "chunk_count": d.chunk_count or 0,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in docs
    ]


@router.post("/kb/reindex")
async def reindex_documents(
    document_ids: list[int],
    kb_db=Depends(get_kb_db),
    config=Depends(get_config),
) -> dict:
    """重新向量化指定文档（用于向量开启后批量重建索引）。"""
    from insight_aitest.platform.services.kb.ingest import process_document

    results = []
    for doc_id in document_ids:
        try:
            doc = kb_db.get_document(doc_id)
            if doc is None:
                results.append({"id": doc_id, "status": "not_found"})
                continue
            # 在后台线程重新处理（需传入全部依赖）
            def _bg(did=doc_id):
                try:
                    from insight_aitest.platform.services.kb.deps import (
                        get_llm as _get_llm,
                        get_vector_store as _get_vs,
                    )

                    process_document(did, kb_db, _get_vs(), _get_llm(), config)
                except Exception:
                    from insight_aitest.platform.services.kb.models import DocumentStatus

                    kb_db.update_document_status(did, DocumentStatus.EMBED_FAILED)

            import threading

            threading.Thread(target=_bg, daemon=True).start()
            results.append({"id": doc_id, "status": "reindexing"})
        except Exception as e:
            results.append({"id": doc_id, "status": "error", "error": str(e)})

    return {"results": results}


@router.get("/kb/stats")
async def kb_stats(
    project_id: int | None = None,
    config=Depends(get_config),
    kb_db=Depends(get_kb_db),
) -> dict:
    """KB 检索范围统计（前端可视化：显示文档数/片段数/向量化状态）。"""
    from insight_aitest.platform.persistence import session_scope
    from insight_aitest.platform.services.kb.models import Document, Chunk
    from sqlalchemy import func

    with session_scope(kb_db.db_path) as s:
        doc_q = s.query(func.count(Document.id))
        chunk_q = s.query(func.count(Chunk.id))
        pid = project_id if project_id else None
        if pid is not None:
            doc_q = doc_q.filter(Document.project_id == pid)
            chunk_q = chunk_q.filter(Chunk.document_id.in_(
                s.query(Document.id).filter(Document.project_id == pid)
            ))
        total_docs = doc_q.scalar() or 0
        total_chunks = chunk_q.scalar() or 0

    return {
        "total_docs": total_docs,
        "total_chunks": total_chunks,
        "vector_enabled": getattr(config, "vector_enabled", False),
        "embed_model": getattr(config, "embed_model", ""),
    }
