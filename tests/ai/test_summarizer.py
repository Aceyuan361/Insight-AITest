# -*- coding: utf-8 -*-
"""会话上下文摘要 skill 测试。"""

from unittest.mock import MagicMock
from insight_aitest.modules.ai.backend.persistence.database import AIDatabase
from insight_aitest.modules.ai.backend.persistence.models import Role


def test_summarize_context_generates_and_caches(tmp_path, monkeypatch):
    """summarize_context 应生成摘要并缓存到 conversation.summary_json。"""
    monkeypatch.setenv("INSIGHT_EYE_AI_LLM_API_KEY", "sk-test")
    db = AIDatabase(str(tmp_path / "ai.db"))
    conv_id = db.create_conversation()
    # 插入 >20 条消息触发摘要
    for i in range(25):
        db.add_message(conv_id, Role.USER if i % 2 == 0 else Role.ASSISTANT, f"消息-{i}")

    # mock LLM 返回摘要 JSON
    mock_llm = MagicMock()
    mock_llm.chat = MagicMock(side_effect=lambda messages, **kwargs: '{"topics": ["登录测试"], "decisions": ["选策略A"], "artifacts": [{"type": "test_cases", "count": 5}], "open_questions": ["密码强度规则待确认"]}')

    from insight_aitest.modules.ai.backend.agent.summarizer import summarize_context
    summary = summarize_context(conv_id, db, mock_llm, force_refresh=True)

    assert summary is not None
    assert summary["topics"] == ["登录测试"]
    assert summary["decisions"] == ["选策略A"]

    # 验证缓存：第二次调用不应重新调 LLM
    call_count_before = mock_llm.chat.call_count
    summary2 = summarize_context(conv_id, db, mock_llm, force_refresh=False)
    assert mock_llm.chat.call_count == call_count_before  # 未增加=用了缓存
    assert summary2["topics"] == ["登录测试"]


def test_summarize_context_skips_short_history(tmp_path, monkeypatch):
    """历史消息不足阈值时应跳过摘要。"""
    monkeypatch.setenv("INSIGHT_EYE_AI_LLM_API_KEY", "sk-test")
    db = AIDatabase(str(tmp_path / "ai.db"))
    conv_id = db.create_conversation()
    db.add_message(conv_id, Role.USER, "只有一条消息")

    mock_llm = MagicMock()
    from insight_aitest.modules.ai.backend.agent.summarizer import summarize_context
    summary = summarize_context(conv_id, db, mock_llm, force_refresh=True)
    assert summary is None  # 消息太少，不生成摘要
    mock_llm.chat.assert_not_called()


def test_format_summary_for_injection():
    """format_summary_for_injection 应格式化为 system 消息内容。"""
    from insight_aitest.modules.ai.backend.agent.summarizer import format_summary_for_injection
    summary = {
        "topics": ["登录测试", "注册测试"],
        "decisions": ["选策略A"],
        "artifacts": [{"type": "test_cases"}],
        "open_questions": ["密码规则待确认"],
    }
    text = format_summary_for_injection(summary)
    assert "登录测试" in text
    assert "选策略A" in text
    assert "密码规则待确认" in text
