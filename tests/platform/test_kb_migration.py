# -*- coding: utf-8 -*-
"""旧 ai_kb.db → kb.db + ai.db 迁移测试。"""
import sqlite3

from insight_aitest.platform.services.kb.database import KBDatabase, migrate_from_legacy


def _make_legacy_ai_kb(path: str):
    """模拟上提前的 ai_kb.db：documents/chunks + conversations/messages 同库。"""
    conn = sqlite3.connect(path)
    conn.executescript("""
    CREATE TABLE documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT, storage_path TEXT,
        mime_type TEXT, char_count INTEGER DEFAULT 0, chunk_count INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending', error_message TEXT, content_hash TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT, document_id INTEGER, chunk_index INTEGER,
        text TEXT, char_start INTEGER, char_end INTEGER, embed_status TEXT DEFAULT 'pending');
    CREATE TABLE conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT DEFAULT '新会话',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id INTEGER, role TEXT,
        content TEXT, citations_json TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    """)
    conn.execute("INSERT INTO documents (filename, storage_path, content_hash) VALUES ('a.md', '/p/a.md', 'h1')")
    conn.execute("INSERT INTO chunks (document_id, chunk_index, text, char_start, char_end) VALUES (1, 0, 'hello', 0, 5)")
    conn.execute("INSERT INTO conversations (title) VALUES ('测试会话')")
    conn.execute("INSERT INTO messages (conversation_id, role, content) VALUES (1, 'user', '你好')")
    conn.commit()
    conn.close()


def test_migrate_splits_db(tmp_path):
    """旧 ai_kb.db 拆成 kb.db（文档/分块）+ ai.db（会话/消息）。"""
    import os
    legacy = str(tmp_path / "ai_kb.db")
    _make_legacy_ai_kb(legacy)
    kb_path = str(tmp_path / "kb.db")
    ai_path = str(tmp_path / "ai.db")

    did = migrate_from_legacy(legacy, kb_path, ai_path)
    assert did is True

    # kb.db 有 documents/chunks
    kb = KBDatabase(kb_path, embed_dim=4)
    docs = kb.list_documents()
    assert len(docs) == 1
    assert docs[0].filename == "a.md"
    chunks = kb.get_chunks_by_document(docs[0].id)
    assert len(chunks) == 1
    assert chunks[0].text == "hello"

    # ai.db 有 conversations/messages
    from insight_aitest.modules.ai.backend.persistence.database import AIDatabase
    ai = AIDatabase(ai_path)
    convs = ai.list_conversations()
    assert len(convs) == 1
    assert convs[0].title == "测试会话"
    msgs = ai.list_messages(convs[0].id)
    assert len(msgs) == 1
    assert msgs[0].content == "你好"

    # 旧库已重命名备份
    assert not os.path.exists(legacy)
    assert os.path.exists(legacy + ".migrated")


def test_migrate_idempotent_when_kb_exists(tmp_path):
    """kb.db 已存在时跳过迁移。"""
    legacy = str(tmp_path / "ai_kb.db")
    _make_legacy_ai_kb(legacy)
    kb_path = str(tmp_path / "kb.db")
    ai_path = str(tmp_path / "ai.db")
    migrate_from_legacy(legacy, kb_path, ai_path)
    # 第二次调用：legacy 已重命名为 .migrated（不存在），应返回 False
    did = migrate_from_legacy(legacy, kb_path, ai_path)
    assert did is False


def test_migrate_skips_when_no_legacy(tmp_path):
    """纯新装（无旧库）应跳过。"""
    did = migrate_from_legacy(
        ai_kb_path=str(tmp_path / "nonexistent.db"),
        kb_db_path=str(tmp_path / "kb.db"),
        ai_db_path=str(tmp_path / "ai.db"))
    assert did is False
