# -*- coding: utf-8 -*-
from insight_aitest.modules.ai.backend.agent.prompts import build_system_message


def test_system_message_with_citations():
    chunks = [
        ("需求.pdf", "性能监控支持 Android"),
        ("API.md", "接口前缀 /api/modules"),
    ]
    msg = build_system_message(chunks)
    assert "参考资料" in msg
    assert "[1]" in msg
    assert "需求.pdf" in msg
    assert "性能监控支持 Android" in msg
    assert "[2]" in msg


def test_system_message_empty_chunks():
    """空检索降级提示。"""
    msg = build_system_message([])
    assert "参考资料为空" in msg or "未基于知识库" in msg
