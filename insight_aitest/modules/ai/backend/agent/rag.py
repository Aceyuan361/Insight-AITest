# -*- coding: utf-8 -*-
"""RAG Agent：检索 → 拼 prompt → LLM。提供非流式 answer 和流式 stream_answer_async。"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import AsyncIterator, TYPE_CHECKING

from insight_aitest.modules.ai.backend.agent.prompts import (
    build_chat_only_message,
    build_system_message,
)
from insight_aitest.modules.ai.backend.persistence.models import Citation

if TYPE_CHECKING:
    from insight_aitest.platform.services.llm.config import AIConfig
    from insight_aitest.modules.ai.backend.kb.retriever import Retriever
    from insight_aitest.modules.ai.backend.kb.vector_store import ScoredChunk
    from insight_aitest.platform.services.llm.client import LLMClient


@dataclass
class StreamEvent:
    type: str  # citations | thinking | token | done | error
    data: object


@dataclass
class RagResult:
    answer: str
    citations: list[Citation]


class RagAgent:
    def __init__(self, retriever: "Retriever", llm: "LLMClient", config: "AIConfig") -> None:
        self.retriever = retriever
        self.llm = llm
        self.config = config

    def _retrieve(self, query: str, document_ids, project_id: int | None = None):
        try:
            return self.retriever.retrieve(
                query, document_ids=document_ids, project_id=project_id
            )
        except Exception:
            return []

    def _build_messages(self, query, history, scored: list["ScoredChunk"], use_rag: bool = True):
        if use_rag:
            chunks = [(s.document.filename, s.chunk.text) for s in scored]
            system = build_system_message(chunks)
        else:
            # 会话级 RAG 关闭：纯对话提示词（区别于'开RAG没命中'的降级）
            system = build_chat_only_message()
        messages = [{"role": "system", "content": system}]
        # 历史截断到最近 history_turns 轮（每轮 user+assistant = 2 条）
        limit = self.config.history_turns * 2
        messages.extend(history[-limit:])
        messages.append({"role": "user", "content": query})
        return messages

    def _to_citations(self, scored: list["ScoredChunk"]) -> list[Citation]:
        return [
            Citation(
                document_id=s.document.id,
                document_name=s.document.filename,
                chunk_index=s.chunk.chunk_index,
                snippet=s.chunk.text,
                score=s.score,
            )
            for s in scored
        ]

    def answer(
        self,
        query,
        history,
        document_ids,
        use_rag: bool = True,
        project_id: int | None = None,
    ) -> RagResult:
        scored = self._retrieve(query, document_ids, project_id=project_id) if use_rag else []
        messages = self._build_messages(query, history, scored, use_rag=use_rag)
        ans = self.llm.chat(messages)
        return RagResult(answer=ans, citations=self._to_citations(scored))

    async def stream_answer_async(
        self,
        query,
        history,
        document_ids,
        use_rag: bool = True,
        thinking_level: str = "off",
        project_id: int | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """流式 RAG：先发 citations，再流式 token（+thinking），最后 done。

        同步 stream_chat 迭代器在执行器线程里跑，token 通过 queue 喂给 async 循环。
        use_rag=False 时跳过检索，发空 citations，用纯对话提示词。
        thinking_level != "off" 时读 reasoning 发 thinking 事件（按模型族探测注入参数）。
        project_id 非 None 时按项目隔离检索（KB 升级，杜绝跨项目污染）。
        """
        scored = (
            self._retrieve(query, document_ids, project_id=project_id) if use_rag else []
        )
        citations = self._to_citations(scored)
        yield StreamEvent(type="citations", data=citations)

        messages = self._build_messages(query, history, scored, use_rag=use_rag)
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()
        SENTINEL = object()
        ERROR_SENTINEL = object()
        error_holder: list[str] = []

        def _produce():
            try:
                if thinking_level and thinking_level != "off":
                    for kind, text in self.llm.stream_chat_raw(
                        messages, thinking_level=thinking_level
                    ):
                        asyncio.run_coroutine_threadsafe(queue.put((kind, text)), loop).result()
                else:
                    for tok in self.llm.stream_chat(messages):
                        asyncio.run_coroutine_threadsafe(queue.put(("content", tok)), loop).result()
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
                    yield StreamEvent(
                        type="error", data=error_holder[0] if error_holder else "未知错误"
                    )
                    return
                kind, text = item
                if kind == "reasoning":
                    yield StreamEvent(type="thinking", data=text)
                else:
                    yield StreamEvent(type="token", data=text)
            yield StreamEvent(type="done", data=None)
        except Exception as e:
            yield StreamEvent(type="error", data=str(e))
