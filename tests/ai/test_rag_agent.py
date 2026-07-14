# -*- coding: utf-8 -*-
import asyncio
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from insight_aitest.modules.ai.backend.agent.rag import RagAgent
from insight_aitest.platform.services.llm.config import AIConfig
from insight_aitest.platform.services.kb.models import ScoredChunk
from insight_aitest.platform.services.kb.models import (
    Chunk, Document, DocumentStatus,
)


def _scored(idx, score, text, name="a.pdf"):
    return ScoredChunk(
        chunk=Chunk(id=idx, document_id=1, chunk_index=idx, text=text,
                    char_start=0, char_end=len(text)),
        score=score,
        document=Document(id=1, filename=name, storage_path="/p", mime_type=None,
                          char_count=0, chunk_count=0, status=DocumentStatus.READY,
                          error_message=None, content_hash=None,
                          created_at=datetime.now(), updated_at=datetime.now()),
    )


def test_answer_with_citations():
    retriever = MagicMock()
    retriever.retrieve.return_value = [_scored(0, 0.9, "性能支持 Android")]
    llm = MagicMock()
    llm.chat.return_value = "根据[1]，支持 Android。"
    cfg = AIConfig(llm_api_key="k", embed_dim=4)
    agent = RagAgent(retriever, llm, cfg)
    result = agent.answer("支持什么", history=[], document_ids=None)
    assert "Android" in result.answer
    assert len(result.citations) == 1
    assert result.citations[0].document_name == "a.pdf"


def test_answer_empty_retrieval_degrades():
    retriever = MagicMock()
    retriever.retrieve.return_value = []
    llm = MagicMock()
    llm.chat.return_value = "未基于知识库的回答。"
    cfg = AIConfig(llm_api_key="k", embed_dim=4)
    agent = RagAgent(retriever, llm, cfg)
    result = agent.answer("x", history=[], document_ids=None)
    assert result.citations == []
    # system message 应含降级提示
    called_msgs = llm.chat.call_args[0][0]
    sys_msg = called_msgs[0]["content"]
    assert "未基于知识库" in sys_msg


def test_answer_rag_disabled_skips_retrieval():
    """use_rag=False：不检索，用纯对话提示词（区别于'开RAG没命中'的降级）。"""
    retriever = MagicMock()
    llm = MagicMock()
    llm.chat.return_value = "纯聊回答。"
    cfg = AIConfig(llm_api_key="k", embed_dim=4)
    agent = RagAgent(retriever, llm, cfg)
    result = agent.answer("你好", history=[], document_ids=None, use_rag=False)
    assert result.citations == []
    assert retriever.retrieve.called is False          # 完全跳过检索
    called_msgs = llm.chat.call_args[0][0]
    sys_msg = called_msgs[0]["content"]
    assert "纯对话模式" in sys_msg                       # 用纯聊提示词
    assert "未基于知识库" not in sys_msg                 # 不是降级提示


def test_stream_answer_async():
    retriever = MagicMock()
    retriever.retrieve.return_value = [_scored(0, 0.9, "x")]
    llm = MagicMock()
    llm.stream_chat.return_value = iter(["你", "好"])
    cfg = AIConfig(llm_api_key="k", embed_dim=4)
    agent = RagAgent(retriever, llm, cfg)

    async def run():
        events = []
        async for e in agent.stream_answer_async("q", [], None):
            events.append(e)
        return events

    events = asyncio.run(run())
    types = [e.type for e in events]
    assert "citations" in types
    assert types.count("token") == 2
    assert types[-1] == "done"


@pytest.mark.asyncio
async def test_stream_thinking_enabled_emits_thinking_events():
    """thinking_level != 'off' 时产出 thinking + token 事件序列。"""
    from insight_aitest.modules.ai.backend.agent.rag import RagAgent

    class FakeRetriever:
        def retrieve(self, q, document_ids=None):
            return []

    class FakeThinkingLLM:
        def stream_chat_raw(self, messages, **kwargs):
            yield ("reasoning", "分析需求")
            yield ("reasoning", "推导结论")
            yield ("content", "答案是")

        def stream_chat(self, messages, **kwargs):
            for kind, t in self.stream_chat_raw(messages):
                if kind == "content":
                    yield t

    agent = RagAgent(FakeRetriever(), FakeThinkingLLM(), __import__(
        "insight_aitest.platform.services.llm.config", fromlist=["LLMConfig"]
    ).LLMConfig(llm_api_key="fake"))
    events = []
    async for ev in agent.stream_answer_async("q", [], None, thinking_level="medium"):
        events.append(ev)
    types = [e.type for e in events]
    assert "thinking" in types
    assert "token" in types
    thinking_data = "".join(e.data for e in events if e.type == "thinking")
    assert thinking_data == "分析需求推导结论"
    token_data = "".join(e.data for e in events if e.type == "token")
    assert token_data == "答案是"


@pytest.mark.asyncio
async def test_stream_thinking_disabled_no_thinking_events():
    """thinking_level='off'（默认）不产 thinking 事件（行为不变）。"""
    from insight_aitest.modules.ai.backend.agent.rag import RagAgent

    class FakeRetriever:
        def retrieve(self, q, document_ids=None):
            return []

    class FakeLLM:
        def stream_chat(self, messages, **kwargs):
            yield "回答"

        def stream_chat_raw(self, messages, **kwargs):
            yield ("content", "回答")

    agent = RagAgent(FakeRetriever(), FakeLLM(), __import__(
        "insight_aitest.platform.services.llm.config", fromlist=["LLMConfig"]
    ).LLMConfig(llm_api_key="fake"))
    events = []
    async for ev in agent.stream_answer_async("q", [], None, thinking_level="off"):
        events.append(ev)
    types = [e.type for e in events]
    assert "thinking" not in types
    assert "token" in types
