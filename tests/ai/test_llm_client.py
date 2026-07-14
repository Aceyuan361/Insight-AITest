# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

from insight_aitest.platform.services.llm.config import AIConfig
from insight_aitest.platform.services.llm.client import LLMClient, LLMConfigError


def _cfg():
    return AIConfig(llm_api_key="sk-test", embed_dim=8)


def test_embed_calls_openai():
    client = LLMClient(_cfg())
    fake_resp = MagicMock()
    fake_resp.data = [MagicMock(embedding=[0.1] * 8, index=0),
                      MagicMock(embedding=[0.2] * 8, index=1)]
    with patch.object(client._client.embeddings, "create", return_value=fake_resp) as m:
        vecs = client.embed(["a", "b"])
    assert len(vecs) == 2
    # embed 返回的是归一化向量（L2 范数 = 1）
    import math
    for v in vecs:
        assert abs(math.sqrt(sum(x * x for x in v)) - 1.0) < 1e-6
    m.assert_called_once()


def test_embed_query_returns_single_vector():
    client = LLMClient(_cfg())
    fake_resp = MagicMock()
    fake_resp.data = [MagicMock(embedding=[0.5] * 8, index=0)]
    with patch.object(client._client.embeddings, "create", return_value=fake_resp):
        v = client.embed_query("hello")
    import math
    assert abs(math.sqrt(sum(x * x for x in v)) - 1.0) < 1e-6


def test_chat_returns_content():
    client = LLMClient(_cfg())
    fake_resp = MagicMock()
    fake_resp.choices = [MagicMock(message=MagicMock(content="回答"))]
    with patch.object(client._client.chat.completions, "create", return_value=fake_resp) as m:
        ans = client.chat([{"role": "user", "content": "问"}])
    assert ans == "回答"
    m.assert_called_once()


def test_stream_chat_yields_tokens():
    client = LLMClient(_cfg())

    def fake_stream():
        for tok in ["你", "好", "世界"]:
            ch = MagicMock()
            ch.choices = [MagicMock(delta=MagicMock(content=tok))]
            yield ch

    with patch.object(client._client.chat.completions, "create", return_value=fake_stream()):
        toks = list(client.stream_chat([{"role": "user", "content": "hi"}]))
    assert toks == ["你", "好", "世界"]


def test_missing_key_raises_on_chat():
    cfg = AIConfig(llm_api_key="", embed_dim=8)
    client = LLMClient(cfg)
    import pytest
    with pytest.raises(LLMConfigError):
        client.chat([{"role": "user", "content": "x"}])


def test_chat_with_image_uses_vision_model():
    """多模态对话：用 vision_model，构造正确的 data URL message。"""
    cfg = AIConfig(
        llm_api_key="sk-test",
        embed_dim=8,
        chat_model="chat-m",
        vision_model="vision-m",
    )
    client = LLMClient(cfg)
    fake_resp = MagicMock()
    fake_resp.choices = [MagicMock(message=MagicMock(content="OCR 文字结果"))]
    with patch.object(client._client.chat.completions, "create", return_value=fake_resp) as m:
        ans = client.chat_with_image("提取文字", "BASE64DATA", mime="image/png")
    assert ans == "OCR 文字结果"
    call_kwargs = m.call_args.kwargs
    assert call_kwargs["model"] == "vision-m"  # 用 vision_model
    content = call_kwargs["messages"][0]["content"]
    assert content[0] == {"type": "text", "text": "提取文字"}
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"] == "data:image/png;base64,BASE64DATA"


def test_chat_with_image_falls_back_to_chat_model():
    """vision_model 空时回退 chat_model。"""
    cfg = AIConfig(llm_api_key="sk-test", embed_dim=8, chat_model="chat-m", vision_model="")
    client = LLMClient(cfg)
    fake_resp = MagicMock()
    fake_resp.choices = [MagicMock(message=MagicMock(content="ok"))]
    with patch.object(client._client.chat.completions, "create", return_value=fake_resp) as m:
        client.chat_with_image("p", "b64")
    assert m.call_args.kwargs["model"] == "chat-m"


def test_chat_with_image_missing_key_raises():
    cfg = AIConfig(llm_api_key="", embed_dim=8)
    client = LLMClient(cfg)
    import pytest
    with pytest.raises(LLMConfigError):
        client.chat_with_image("p", "b64")
