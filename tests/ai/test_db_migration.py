# -*- coding: utf-8 -*-
"""Message/Conversation 新列迁移测试。"""


def test_conversation_has_thinking_level_column(tmp_path):
    """Conversation 表有 thinking_level 列（替代旧的 thinking_enabled），默认 'off'。"""
    from insight_aitest.modules.ai.backend.persistence.database import AIDatabase

    db = AIDatabase(str(tmp_path / "ai.db"))
    cid = db.create_conversation("test")
    conv = db.get_conversation(cid)
    assert hasattr(conv, "thinking_level")
    assert conv.thinking_level == "off"  # 默认关


def test_message_has_thinking_and_attachments_columns(tmp_path):
    """Message 表有 thinking 和 attachments 列。"""
    from insight_aitest.modules.ai.backend.persistence.database import AIDatabase
    from insight_aitest.modules.ai.backend.persistence.models import Role

    db = AIDatabase(str(tmp_path / "ai.db"))
    cid = db.create_conversation("test")
    mid = db.add_message(
        cid, Role.ASSISTANT, "回答",
        thinking="思考过程文本",
        attachments=[{"id": "a1", "filename": "f.png", "kind": "image"}],
    )
    msgs = db.list_messages(cid)
    m = [x for x in msgs if x.id == mid][0]
    assert m.thinking == "思考过程文本"
    assert m.attachments[0]["filename"] == "f.png"
