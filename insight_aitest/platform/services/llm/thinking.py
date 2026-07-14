# -*- coding: utf-8 -*-
"""思考级别（reasoning effort）解析工具。

把统一的 thinking_level（off/low/medium/high）按模型族转成各家 OpenAI 兼容 API 的原生参数：
- OpenAI o 系列 / gpt-5：reasoning_effort
- 智谱 GLM-4.6 / 4.5-thinking：thinking={"type": "enabled"}
- DeepSeek-R1 / Reasoner：原生推理模型，无需参数（开了就推理）
- QwQ / 通义推理模型：原生推理模型，无需参数
- 普通模型（gpt-4o-mini / glm-4-plus 等）：不支持，返回空 dict

模型支持探测：is_reasoning_model(model) 判断该模型是否支持思考级别调整。
"""

from __future__ import annotations

import re

# 思考级别枚举
ThinkingLevel = str  # "off" | "low" | "medium" | "high"

# 各家 reasoning_effort 的档位映射（OpenAI o/gpt-5 用 minimal/low/medium/high）
_OPENAI_EFFORT_MAP = {
    "low": "low",
    "medium": "medium",
    "high": "high",
}

# 支持思考级别调整的模型族正则（按 vendor 分组，便于前端复用提示）
_REASONING_MODEL_PATTERNS = [
    # OpenAI o 系列 / gpt-5（o1-mini/o1-preview 除外，它们不支持 reasoning_effort）
    re.compile(r"^(o1|o3|o4|gpt-5)", re.IGNORECASE),
    # 智谱 GLM thinking 系列
    re.compile(r"glm.*think", re.IGNORECASE),
    re.compile(r"glm-4\.6", re.IGNORECASE),
    re.compile(r"glm-4\.5", re.IGNORECASE),
    # DeepSeek 推理系列
    re.compile(r"deepseek.*r", re.IGNORECASE),
    re.compile(r"deepseek.*reason", re.IGNORECASE),
    # 通义 QwQ / Qwen 推理
    re.compile(r"qwq", re.IGNORECASE),
    re.compile(r"qwen.*think", re.IGNORECASE),
    # Claude thinking
    re.compile(r"claude.*think", re.IGNORECASE),
    # 通用后缀
    re.compile(r"-thinking$", re.IGNORECASE),
    re.compile(r"-reasoner$", re.IGNORECASE),
    re.compile(r"-r1$", re.IGNORECASE),
]

# 不支持 reasoning_effort 的 OpenAI 早期推理模型（o1-mini/o1-preview）
# 注入 reasoning_effort 会 400，需排除（视为「原生推理但不接受级别参数」）
_OPENAI_REASONING_EXCLUDED = re.compile(r"^o1-(mini|preview)", re.IGNORECASE)

# 原生推理模型（开了就推理，不需要也不接受 thinking 参数，传了反而报错）
# 这类模型 thinking_level 仅用于前端展示语义，后端不注入参数
_NATIVE_REASONING_PATTERNS = [
    re.compile(r"deepseek.*r", re.IGNORECASE),
    re.compile(r"deepseek.*reason", re.IGNORECASE),
    re.compile(r"qwq", re.IGNORECASE),
    re.compile(r"-reasoner$", re.IGNORECASE),
    re.compile(r"-r1$", re.IGNORECASE),
]


def is_reasoning_model(model: str) -> bool:
    """该模型是否支持思考级别调整（前端用来决定选择器是否置灰）。"""
    # o1-mini/o1-preview 是推理模型但不接受 reasoning_effort 参数 → 视为不支持级别调整
    if _OPENAI_REASONING_EXCLUDED.match(model):
        return False
    return any(p.search(model) for p in _REASONING_MODEL_PATTERNS)


def _is_native_reasoning(model: str) -> bool:
    """该模型是否为原生推理模型（不接受 thinking 参数，传了会报错）。"""
    return any(p.search(model) for p in _NATIVE_REASONING_PATTERNS)


def _is_openai_reasoning(model: str) -> bool:
    """OpenAI o 系列 / gpt-5（用 reasoning_effort 参数）。o1-mini/o1-preview 除外。"""
    if _OPENAI_REASONING_EXCLUDED.match(model):
        return False
    return bool(re.match(r"^(o1|o3|o4|gpt-5)", model, re.IGNORECASE))


def _is_glm_reasoning(model: str) -> bool:
    """智谱 GLM thinking 系列（用 thinking={"type":"enabled"}）。"""
    return bool(
        re.search(r"glm.*think", model, re.IGNORECASE)
        or re.match(r"glm-4\.[56]", model, re.IGNORECASE)
    )


def resolve_thinking_params(model: str, level: ThinkingLevel = "off") -> dict:
    """把 thinking_level 转成模型原生参数 dict，合并进 LLM 调用 kwargs。

    返回 {} 表示不注入任何参数（普通模型 / level=off / 原生推理模型）。
    调用方：kwargs.update(resolve_thinking_params(model, level))。
    """
    if not level or level == "off":
        return {}

    # 原生推理模型：开了就推理，不接受参数（传 thinking/reasoning_effort 会报错）
    if _is_native_reasoning(model):
        return {}

    # OpenAI o 系列 / gpt-5：reasoning_effort
    if _is_openai_reasoning(model):
        effort = _OPENAI_EFFORT_MAP.get(level, "medium")
        return {"reasoning_effort": effort}

    # 智谱 GLM：thinking={"type":"enabled"}
    if _is_glm_reasoning(model):
        # GLM 目前只有开/关，不分级；level!=off 即开启
        return {"thinking": {"type": "enabled"}}

    # 其他模型不支持，不注入（避免报错）
    return {}
