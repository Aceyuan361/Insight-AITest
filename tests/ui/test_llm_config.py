# -*- coding: utf-8 -*-
"""LLMConfig vision_model 字段向后兼容测试。"""
from insight_aitest.platform.services.llm.config import LLMConfig, load_config


def test_vision_model_default_empty():
    cfg = LLMConfig()
    assert cfg.vision_model == ""


def test_vision_model_env_override(monkeypatch):
    monkeypatch.setenv("INSIGHT_EYE_AI_VISION_MODEL", "glm-4v")
    cfg = load_config(config_file="/nonexistent/path.json")
    assert cfg.vision_model == "glm-4v"
