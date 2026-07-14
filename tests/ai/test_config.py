# -*- coding: utf-8 -*-
import json

from insight_aitest.platform.services.llm.config import LLMConfig, load_config


def test_default_config(monkeypatch):
    monkeypatch.delenv("INSIGHT_EYE_AI_LLM_API_KEY", raising=False)
    cfg = load_config(config_file="/tmp/fake_nonexistent_ai_config.json")
    assert cfg.llm_base_url == "https://api.openai.com/v1"
    assert cfg.chat_model == "gpt-4o-mini"
    assert cfg.embed_dim == 1536
    assert cfg.chunk_size == 500
    assert cfg.chunk_overlap == 80
    assert cfg.top_k == 4
    assert cfg.api_key_set is False


def test_env_overrides_default(monkeypatch):
    monkeypatch.setenv("INSIGHT_EYE_AI_LLM_API_KEY", "sk-test")
    monkeypatch.setenv("INSIGHT_EYE_AI_CHAT_MODEL", "qwen-plus")
    monkeypatch.setenv("INSIGHT_EYE_AI_EMBED_DIM", "1024")
    cfg = load_config(config_file="/tmp/fake_nonexistent_ai_config.json")
    assert cfg.llm_api_key == "sk-test"
    assert cfg.chat_model == "qwen-plus"
    assert cfg.embed_dim == 1024
    assert cfg.api_key_set is True


def test_file_overrides_default(monkeypatch, tmp_path):
    monkeypatch.delenv("INSIGHT_EYE_AI_LLM_API_KEY", raising=False)
    cfg_file = tmp_path / "ai_config.json"
    cfg_file.write_text(json.dumps({
        "llm_api_key": "sk-from-file",
        "chat_model": "claude-via-proxy",
        "embed_dim": 768,
    }), encoding="utf-8")
    cfg = load_config(config_file=str(cfg_file))
    assert cfg.llm_api_key == "sk-from-file"
    assert cfg.chat_model == "claude-via-proxy"
    assert cfg.embed_dim == 768


def test_env_overrides_file(monkeypatch, tmp_path):
    """环境变量优先级 > 配置文件。"""
    cfg_file = tmp_path / "ai_config.json"
    cfg_file.write_text(json.dumps({"llm_api_key": "sk-from-file"}), encoding="utf-8")
    monkeypatch.setenv("INSIGHT_EYE_AI_LLM_API_KEY", "sk-from-env")
    cfg = load_config(config_file=str(cfg_file))
    assert cfg.llm_api_key == "sk-from-env"


def test_llm_config_chunk_defaults():
    """LLMConfig 默认 chunk_strategy=recursive, semantic_breakpoint=2.58。"""
    cfg = LLMConfig()
    assert cfg.chunk_strategy == "recursive"
    assert cfg.semantic_breakpoint == 2.58


def test_llm_config_chunk_env_override(monkeypatch):
    """env 变量能覆盖 chunk_strategy 和 semantic_breakpoint。"""
    monkeypatch.setenv("INSIGHT_EYE_AI_CHUNK_STRATEGY", "semantic")
    monkeypatch.setenv("INSIGHT_EYE_AI_SEMANTIC_BREAKPOINT", "1.5")
    cfg = load_config(config_file="/nonexistent/path.json")  # 跳过文件加载
    assert cfg.chunk_strategy == "semantic"
    assert cfg.semantic_breakpoint == 1.5
