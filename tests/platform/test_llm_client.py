# -*- coding: utf-8 -*-
"""LLMClient 流式测试：stream_chat_raw 读 reasoning_content + content。"""
from unittest.mock import MagicMock


def _make_delta(content=None, reasoning=None):
    """构造 OpenAI delta mock。

    显式置 reasoning_content / reasoning（生产代码用 getattr 安全降级）。
    MagicMock 会为未设属性自动返回 truthy 子 mock，故两个 reasoning 字段都要显式
    设成目标值或空，避免 stream_chat_raw 误判成 reasoning 事件。
    """
    d = MagicMock()
    d.content = content
    d.reasoning_content = reasoning
    d.reasoning = reasoning  # 生产代码会回退读这个字段（OpenAI o 系列原生 SDK）
    return d


def _make_chunk(delta):
    chunk = MagicMock()
    chunk.choices = [MagicMock()]
    chunk.choices[0].delta = delta
    return chunk


def test_stream_chat_raw_yields_reasoning_and_content():
    """stream_chat_raw 同时 yield reasoning 和 content 元组。"""
    from insight_aitest.platform.services.llm.client import LLMClient
    from insight_aitest.platform.services.llm.config import LLMConfig

    cfg = LLMConfig(llm_api_key="sk-test", chat_model="test")
    client = LLMClient.__new__(LLMClient)  # 绕过 OpenAI 真实连接
    client._config = cfg
    client._client = MagicMock()
    client._chat_model = "test"
    client._embed_client = client._client

    chunks = [
        _make_chunk(_make_delta(reasoning="首先分析")),
        _make_chunk(_make_delta(reasoning="需求")),
        _make_chunk(_make_delta(content="答案是")),
        _make_chunk(_make_delta(content="42")),
    ]
    client._client.chat.completions.create.return_value = iter(chunks)

    result = list(client.stream_chat_raw([{"role": "user", "content": "q"}]))
    assert result == [
        ("reasoning", "首先分析"),
        ("reasoning", "需求"),
        ("content", "答案是"),
        ("content", "42"),
    ]


def test_stream_chat_filters_reasoning():
    """旧 stream_chat 只 yield content 文本（向后兼容）。"""
    from insight_aitest.platform.services.llm.client import LLMClient
    from insight_aitest.platform.services.llm.config import LLMConfig

    cfg = LLMConfig(llm_api_key="sk-test", chat_model="test")
    client = LLMClient.__new__(LLMClient)
    client._config = cfg
    client._client = MagicMock()
    client._chat_model = "test"
    client._embed_client = client._client

    chunks = [
        _make_chunk(_make_delta(reasoning="思考")),
        _make_chunk(_make_delta(content="回答")),
    ]
    client._client.chat.completions.create.return_value = iter(chunks)

    result = list(client.stream_chat([{"role": "user", "content": "q"}]))
    assert result == ["回答"]


def test_stream_chat_raw_no_reasoning_field():
    """模型不吐 reasoning_content 时不报错（getattr 安全降级）。"""
    from insight_aitest.platform.services.llm.client import LLMClient
    from insight_aitest.platform.services.llm.config import LLMConfig

    cfg = LLMConfig(llm_api_key="sk-test", chat_model="test")
    client = LLMClient.__new__(LLMClient)
    client._config = cfg
    client._client = MagicMock()
    client._chat_model = "test"
    client._embed_client = client._client

    d = MagicMock()
    d.content = "only content"
    d.reasoning_content = None
    d.reasoning = None  # 生产代码用 getattr 回退读此字段，必须为 falsy
    chunks = [_make_chunk(d)]
    client._client.chat.completions.create.return_value = iter(chunks)

    result = list(client.stream_chat_raw([{"role": "user", "content": "q"}]))
    assert result == [("content", "only content")]
