# -*- coding: utf-8 -*-
"""OpenAI 兼容 LLM 客户端（平台共享服务）。chat 与 embedding 用同一 base_url + key。

从 ai 模块上提，ai 和 testcase 模块共用。不抽象 Provider——首版只有 OpenAI 兼容一个实现。
"""

from __future__ import annotations

import time
from typing import Iterator

from insight_aitest.platform.services.llm.config import LLMConfig
from insight_aitest.platform.services.llm.thinking import resolve_thinking_params

ChatMessage = dict  # {role, content}


class LLMConfigError(Exception):
    """LLM 配置错误（如 key 缺失）。"""


class LLMUnavailableError(Exception):
    """LLM 服务不可用（网络/限流/超时，重试耗尽后抛出）。"""


# 重试配置（瞬时错误：限流/超时/连接失败）
_MAX_RETRIES = 3
_RETRY_DELAYS = [1, 2, 4]  # 指数退避秒数
# 可重试的 OpenAI SDK 异常（瞬时）
_RETRYABLE = (
    "RateLimitError",
    "APITimeoutError",
    "APIConnectionError",
    "InternalServerError",
)


def _is_retryable(e: Exception) -> bool:
    """判断异常是否可重试（限流/超时/连接/5xx 内部错误）。"""
    return any(type(e).__name__ == name for name in _RETRYABLE)


def _retry_call(fn, *args, **kwargs):
    """带指数退避的重试包装。瞬时错误重试 ≤3 次（1s/2s/4s），耗尽后抛 LLMUnavailableError。

    不可重试的错误（AuthenticationError/BadRequestError/NotFoundError）原样抛出。
    """
    last_exc = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_exc = e
            if not _is_retryable(e) or attempt == _MAX_RETRIES:
                break
            time.sleep(_RETRY_DELAYS[min(attempt, len(_RETRY_DELAYS) - 1)])
    # 重试耗尽：瞬时错误转 LLMUnavailableError，配置/参数错误原样抛
    if last_exc is None:
        raise RuntimeError("_retry_call 退出但无异常（不应发生）")
    if _is_retryable(last_exc):
        raise LLMUnavailableError(
            f"LLM 服务不可用（重试 {_MAX_RETRIES} 次后仍失败）: {last_exc}"
        ) from last_exc
    raise last_exc


def _normalize(vec: list[float]) -> list[float]:
    """L2 归一化：归一化向量的 L2 距离等价于余弦距离（用于 RAG 召回）。"""
    import math

    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0:
        return vec
    return [x / norm for x in vec]


class LLMClient:
    def __init__(self, config: LLMConfig) -> None:
        from openai import OpenAI

        self._config = config
        self._client = OpenAI(
            base_url=config.llm_base_url,
            api_key=config.llm_api_key or "missing",
            timeout=config.llm_timeout,
        )
        self._chat_model = config.chat_model
        self._embed_model = config.embed_model
        # embedding 可走独立端点（当 chat 端点无 embedding 模型时，如 agnes → 智谱 embedding）
        # embed_base_url/embed_api_key 留空则与 chat 共用主 client（向后兼容）
        embed_base = config.embed_base_url or config.llm_base_url
        embed_key = config.embed_api_key or config.llm_api_key or "missing"
        if embed_base == config.llm_base_url and embed_key == (config.llm_api_key or "missing"):
            self._embed_client = self._client  # 共用，避免多余连接
        else:
            self._embed_client = OpenAI(
                base_url=embed_base,
                api_key=embed_key,
                timeout=config.llm_timeout,
            )

    def _ensure_key(self) -> None:
        if not self._config.llm_api_key:
            raise LLMConfigError("未配置 LLM API Key，请在设置中配置。")

    def embed(self, texts: list[str]) -> list[list[float]]:
        # embedding 用独立 client（embed_base_url 配置时）；key 检查覆盖 embed_api_key 回退链
        embed_key = self._config.embed_api_key or self._config.llm_api_key
        if not embed_key:
            raise LLMConfigError("未配置 LLM API Key，请在设置中配置。")
        resp = self._embed_client.embeddings.create(model=self._embed_model, input=texts)
        # 按 index 排序确保顺序与输入一致
        ordered = sorted(resp.data, key=lambda d: d.index)
        # L2 归一化：sqlite-vec 默认用 L2（欧氏）距离，归一化后
        # L2 距离与余弦距离等价（||a-b||² = 2(1-cos)），RAG 召回更准
        return [_normalize(d.embedding) for d in ordered]

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]

    def chat(self, messages: list[ChatMessage], thinking_level: str = "off", **kwargs) -> str:
        self._ensure_key()
        # 合并思考级别参数（按模型族探测，off/不支持时为空 dict）
        kwargs.update(resolve_thinking_params(self._chat_model, thinking_level))
        resp = _retry_call(
            self._client.chat.completions.create,
            model=self._chat_model,
            messages=messages,
            **kwargs,
        )
        content = resp.choices[0].message.content or ""
        if not content.strip():
            raise LLMUnavailableError("模型返回空回复，请重试或检查模型配置")
        return content

    def chat_with_image(
        self, prompt: str, image_base64: str, mime: str = "image/png", **kwargs
    ) -> str:
        """多模态对话：发文本 + 图片（OpenAI 兼容 vision 协议），返回文本。

        用 vision_model（空则回退 chat_model，与 ui executor 一致）。
        图片以 data URL 形式传入：data:<mime>;base64,<image_base64>。
        """
        self._ensure_key()
        model = self._config.vision_model or self._chat_model
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{image_base64}"},
                    },
                ],
            }
        ]
        resp = _retry_call(
            self._client.chat.completions.create,
            model=model,
            messages=messages,
            **kwargs,
        )
        content = resp.choices[0].message.content or ""
        if not content.strip():
            raise LLMUnavailableError("模型返回空回复，请重试或检查视觉模型配置")
        return content

    def chat_with_images(self, prompt: str, images: list[tuple[str, str]], **kwargs) -> str:
        """多图多模态对话：发文本 + 多张图片（OpenAI 兼容 vision 协议），返回文本。

        images: [(image_base64, mime), ...] 列表，至少 1 张。
        每张图以 data URL 形式传入 content 数组。
        用 vision_model（空则回退 chat_model，与 chat_with_image 一致）。
        """
        assert images, "chat_with_images 至少需要 1 张图片"
        self._ensure_key()
        model = self._config.vision_model or self._chat_model
        content: list[dict] = [{"type": "text", "text": prompt}]
        for image_base64, mime in images:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{image_base64}"},
                }
            )
        messages = [{"role": "user", "content": content}]
        resp = _retry_call(
            self._client.chat.completions.create,
            model=model,
            messages=messages,
            **kwargs,
        )
        content_out = resp.choices[0].message.content or ""
        if not content_out.strip():
            raise LLMUnavailableError("模型返回空回复，请重试或检查视觉模型配置")
        return content_out

    def stream_chat_raw(
        self, messages: list[ChatMessage], thinking_level: str = "off", **kwargs
    ) -> Iterator[tuple[str, str]]:
        """流式聊天（原始）：yield (kind, text) 元组。

        kind="reasoning" ← delta.reasoning_content（GLM/DeepSeek-R1 类）或 delta.reasoning（OpenAI o 系列原生 SDK）。
        kind="content"   ← delta.content（正常回答）。
        模型不吐 reasoning 时只 yield content（getattr 安全降级）。
        thinking_level 按 model 探测注入 reasoning_effort/thinking 参数。
        流式启动时重试（首 chunk 前），流中途断不重试（避免重复内容）。
        流结束后若既无 content 也无 reasoning → 抛 LLMUnavailableError（空回复检测）。
        """
        self._ensure_key()
        # 合并思考级别参数（按模型族探测，off/不支持时为空 dict）
        kwargs.update(resolve_thinking_params(self._chat_model, thinking_level))
        # 流式启动重试（create 调用本身可能因限流/超时失败）
        stream = _retry_call(
            self._client.chat.completions.create,
            model=self._chat_model,
            messages=messages,
            stream=True,
            **kwargs,
        )
        has_any = False
        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta:
                # 兼容两家字段名：GLM/DeepSeek 用 reasoning_content，OpenAI o 系列原生 SDK 用 reasoning
                reasoning = getattr(delta, "reasoning_content", None) or getattr(
                    delta, "reasoning", None
                )
                if reasoning:
                    has_any = True
                    yield ("reasoning", reasoning)
                if delta.content:
                    has_any = True
                    yield ("content", delta.content)
        # 空回复检测：整条流既无 content 也无 reasoning → 异常（不静默返回空）
        if not has_any:
            raise LLMUnavailableError("模型流式返回为空，请重试或检查模型配置")

    def stream_chat(self, messages: list[ChatMessage], **kwargs) -> Iterator[str]:
        """流式聊天（兼容旧）：只 yield content 文本（过滤 reasoning）。"""
        for kind, text in self.stream_chat_raw(messages, **kwargs):
            if kind == "content":
                yield text


def test_connection(base_url: str, api_key: str, model: str, timeout: int = 20) -> tuple[bool, str]:
    """用临时 client 探测连通性（不发正式 chat，用 models.list 或最小 chat 请求）。

    返回 (ok, message)。成功时 message 为模型名或 "ok"；失败时为错误描述。
    不影响全局单例，不读取配置文件——纯临时 client。
    """
    from openai import OpenAI

    if not base_url:
        return False, "Base URL 为空"
    if not api_key:
        return False, "API Key 为空"
    if not model:
        return False, "模型名为空"
    try:
        client = OpenAI(base_url=base_url, api_key=api_key, timeout=timeout)
        # 先尝试 models.list（轻量，部分 OpenAI 兼容端点不支持）
        try:
            models = client.models.list()
            ids = [m.id for m in models.data]
            # 若目标模型在列表中，直接确认；否则仍用 chat 探测（list 不全或模型名自由输入）
            if model in ids:
                return True, f"ok（{model} 在模型列表中）"
        except Exception:
            pass  # list 不支持也无妨，下面用 chat 探测
        # 用最小 chat 请求确认 key + model 可用
        client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
        )
        return True, f"ok（{model} 响应正常）"
    except Exception as e:
        name = type(e).__name__
        msg = str(e)
        # 常见错误分类提示
        if "Authentication" in name or "401" in msg or "api key" in msg.lower():
            return False, f"认证失败：API Key 无效（{name}）"
        if "NotFound" in name or "404" in msg or "model" in msg.lower():
            return False, f"模型不存在或无权访问：{model}（{name}）"
        if "Connection" in name or "Timeout" in name or "timed out" in msg.lower():
            return False, f"连接失败：{msg}（{name}）"
        return False, f"{name}: {msg}"
