# -*- coding: utf-8 -*-
"""上下文修复相关数据库测试。"""

from insight_aitest.modules.ai.backend.persistence.database import AIDatabase
from insight_aitest.modules.ai.backend.persistence.models import Role


def _db(tmp_path):
    return AIDatabase(str(tmp_path / "ai.db"))


def test_message_has_task_id_column(tmp_path):
    """Message 模型应有 task_id 列（nullable，用于关联 agent task）。"""
    db = _db(tmp_path)
    conv_id = db.create_conversation()
    task_id = db.create_task(intent="demo")
    msg_id = db.add_message(conv_id, Role.USER, "hello", task_id=task_id)
    msgs = db.list_messages(conv_id)
    assert len(msgs) == 1
    assert msgs[0].task_id == task_id


def test_list_messages_returns_recent_not_oldest(tmp_path):
    """list_messages(limit=N) 应返回最近 N 条（而非最早 N 条）。

    缺陷2根因：原实现 .asc() + .limit() 取最早 N 条，导致长会话丢失最近上下文。
    """
    db = _db(tmp_path)
    conv_id = db.create_conversation()
    # 插入 5 条消息
    for i in range(5):
        db.add_message(conv_id, Role.USER, f"msg-{i}")
    # limit=3 应返回 msg-2, msg-3, msg-4（最近 3 条），而非 msg-0, msg-1, msg-2
    msgs = db.list_messages(conv_id, limit=3)
    assert len(msgs) == 3
    assert msgs[0].content == "msg-2"
    assert msgs[1].content == "msg-3"
    assert msgs[2].content == "msg-4"


def test_list_messages_by_task(tmp_path):
    """list_messages_by_task 按 task_id 过滤消息。"""
    db = _db(tmp_path)
    conv_id = db.create_conversation()
    # Create a real task first (FK constraint requires existing task)
    task_id = db.create_task(intent="test task")
    db.add_message(conv_id, Role.USER, "task1-user", task_id=task_id)
    db.add_message(conv_id, Role.ASSISTANT, "task1-assistant", task_id=task_id)
    # Create second task
    task_id2 = db.create_task(intent="test task 2")
    db.add_message(conv_id, Role.USER, "task2-user", task_id=task_id2)
    msgs = db.list_messages_by_task(task_id)
    assert len(msgs) == 2
    assert msgs[0].content == "task1-user"
    assert msgs[1].content == "task1-assistant"


def test_find_empty_conversation(tmp_path):
    """find_empty_conversation 返回无消息的会话（用于创建去重）。"""
    db = _db(tmp_path)
    # 无会话时返回 None
    assert db.find_empty_conversation(project_id=None) is None
    # 创建一个会话但不加消息
    conv_id = db.create_conversation(project_id=1)
    found = db.find_empty_conversation(project_id=1)
    assert found is not None
    assert found.id == conv_id
    # 加一条消息后不再算空
    db.add_message(conv_id, Role.USER, "hello")
    assert db.find_empty_conversation(project_id=1) is None


def test_save_and_get_summary(tmp_path):
    """Conversation 可保存和读取 summary_json。"""
    db = _db(tmp_path)
    conv_id = db.create_conversation()
    summary = {"topics": ["登录测试"], "decisions": ["选策略A"], "artifacts": [], "open_questions": []}
    db.save_summary(conv_id, summary)
    result = db.get_summary(conv_id)
    assert result is not None
    assert result["topics"] == ["登录测试"]
    assert result["decisions"] == ["选策略A"]
