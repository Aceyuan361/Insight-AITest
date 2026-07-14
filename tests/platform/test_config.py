# -*- coding: utf-8 -*-
"""LLMConfig 测试：思考级别（thinking_level，会话级，off/low/medium/high）。"""
from insight_aitest.platform.services.llm.config import LLMConfig


def test_llm_config_defaults():
    """基本冒烟：默认配置可构造。"""
    cfg = LLMConfig(llm_api_key="fake")
    assert cfg.llm_api_key == "fake"


def test_thinking_level_default_off(tmp_path):
    """会话 thinking_level 默认 'off'（替代旧的 enable_thinking=False）。"""
    from insight_aitest.modules.ai.backend.persistence.database import AIDatabase

    db = AIDatabase(str(tmp_path / "ai.db"))
    cid = db.create_conversation("test")
    conv = db.get_conversation(cid)
    assert conv.thinking_level == "off"


def test_thinking_level_persisted_value(tmp_path):
    """创建会话时可指定 thinking_level，且可被持久化读取（替代旧的环境变量覆盖）。"""
    from insight_aitest.modules.ai.backend.persistence.database import AIDatabase

    db = AIDatabase(str(tmp_path / "ai.db"))
    cid = db.create_conversation("test", thinking_level="high")
    conv = db.get_conversation(cid)
    assert conv.thinking_level == "high"
    # 更新为 low 后落库生效
    db.update_conversation_thinking(cid, "low")
    assert db.get_conversation(cid).thinking_level == "low"
