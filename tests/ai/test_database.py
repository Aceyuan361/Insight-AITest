# -*- coding: utf-8 -*-
"""数据库测试。

KB 表（documents/chunks）已在 KBDatabase（platform.services.kb）；
会话/消息表在 AIDatabase（ai 模块）。两类分开测。
"""

from insight_aitest.modules.ai.backend.persistence.database import AIDatabase
from insight_aitest.platform.services.kb.database import KBDatabase
from insight_aitest.platform.services.kb.models import Chunk, DocumentStatus, EmbedStatus
from insight_aitest.modules.ai.backend.persistence.models import Role

# ===== KBDatabase（文档/分块/向量）=====


def _kb(tmp_path):
    return KBDatabase(str(tmp_path / "kb.db"), embed_dim=8)


def test_creates_schema(tmp_path):
    db = _kb(tmp_path)
    conn = db.get_connection()
    tables = {
        r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    assert "documents" in tables
    assert "chunks" in tables


def test_document_crud(tmp_path):
    db = _kb(tmp_path)
    doc_id = db.create_document("a.pdf", "/store/a.pdf", "abc123", "application/pdf")
    doc = db.get_document(doc_id)
    assert doc.filename == "a.pdf"
    assert doc.status == DocumentStatus.PENDING
    assert doc.content_hash == "abc123"

    db.update_document_status(doc_id, DocumentStatus.READY, char_count=100, chunk_count=3)
    doc = db.get_document(doc_id)
    assert doc.status == DocumentStatus.READY
    assert doc.char_count == 100

    docs = db.list_documents()
    assert len(docs) == 1
    assert db.delete_document(doc_id) is True
    assert db.get_document(doc_id) is None


def test_content_hash_dedup(tmp_path):
    db = _kb(tmp_path)
    db.create_document("a.pdf", "/p1", "hash1", "application/pdf")
    found = db.find_by_content_hash("hash1")
    assert found is not None and found.filename == "a.pdf"
    assert db.find_by_content_hash("nope") is None


def test_chunks_crud(tmp_path):
    db = _kb(tmp_path)
    doc_id = db.create_document("a.pdf", "/p", "h", "application/pdf")
    chunks = [
        Chunk(document_id=doc_id, chunk_index=0, text="c0", char_start=0, char_end=2),
        Chunk(document_id=doc_id, chunk_index=1, text="c1", char_start=2, char_end=4),
    ]
    ids = db.insert_chunks(doc_id, chunks)
    assert len(ids) == 2
    db.update_chunk_embed_status(ids[0], EmbedStatus.OK)
    got = db.get_chunks_by_document(doc_id)
    assert len(got) == 2
    assert got[0].embed_status == EmbedStatus.OK


def test_kb_legacy_db_compat(tmp_path):
    """旧（裸 sqlite3）schema 建库 + 样例数据 → 新 ORM KBDatabase 打开读写（spec §8.3）。

    P0-1 数据兼容红线：存量用户 kb.db 必须被新代码直接读写，历史文档/分块可见。
    vec0 表由 KBDatabase 按配置 embed_dim 创建（旧库无 vec0，新建即可）。
    """
    import sqlite3

    legacy = tmp_path / "kb.db"
    # 旧 schema（documents/chunks，无 vec0）
    with sqlite3.connect(legacy) as raw:
        raw.executescript("""
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT NOT NULL,
            storage_path TEXT NOT NULL, mime_type TEXT, char_count INTEGER DEFAULT 0,
            chunk_count INTEGER DEFAULT 0, status TEXT NOT NULL DEFAULT 'pending',
            error_message TEXT, content_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT, document_id INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL, text TEXT NOT NULL,
            char_start INTEGER NOT NULL, char_end INTEGER NOT NULL,
            embed_status TEXT NOT NULL DEFAULT 'pending',
            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE);
        CREATE INDEX idx_chunks_document ON chunks(document_id);
        CREATE INDEX idx_documents_status ON documents(status);
        """)
        raw.execute(
            "INSERT INTO documents (filename, storage_path, content_hash, status) "
            "VALUES ('存量.md', '/p/存量.md', 'hash_old', 'ready')"
        )
        raw.execute(
            "INSERT INTO chunks (document_id, chunk_index, text, char_start, char_end, embed_status) "
            "VALUES (1, 0, '存量内容', 0, 4, 'ok')"
        )
        raw.commit()

    # 新 ORM 代码打开（embed_dim=4 建 vec0；存量 documents/chunks 不动）
    db = KBDatabase(str(legacy), embed_dim=4)

    # 存量文档/分块可读、字段正确（枚举/JSON 正确还原）
    docs = db.list_documents()
    assert len(docs) == 1
    assert docs[0].filename == "存量.md"
    assert docs[0].status == DocumentStatus.READY
    chunks = db.get_chunks_by_document(docs[0].id)
    assert len(chunks) == 1
    assert chunks[0].text == "存量内容"
    assert chunks[0].embed_status == EmbedStatus.OK

    # 新增正常
    new_id = db.create_document("新.md", "/p/新.md", "hash_new", "text/markdown")
    assert db.get_document(new_id).filename == "新.md"
    assert len(db.list_documents()) == 2


# ===== AIDatabase（会话/消息）=====


def _ai(tmp_path):
    return AIDatabase(str(tmp_path / "ai.db"))


def test_conversation_and_message_crud(tmp_path):
    db = _ai(tmp_path)
    conv_id = db.create_conversation()
    conv = db.get_conversation(conv_id)
    assert conv.title == "新会话"
    db.update_conversation_title(conv_id, "需求答疑")
    assert db.get_conversation(conv_id).title == "需求答疑"

    db.add_message(conv_id, Role.USER, "你好")
    msgs = db.list_messages(conv_id)
    assert len(msgs) == 1
    assert msgs[0].role == Role.USER
    assert msgs[0].content == "你好"

    assert db.delete_conversation(conv_id) is True
    assert db.list_messages(conv_id) == []


def test_conversation_rag_enabled_roundtrip(tmp_path):
    """会话 rag_enabled 字段读写 + 默认 True（spec C.1）。"""
    db = _ai(tmp_path)
    cid = db.create_conversation()
    assert db.get_conversation(cid).rag_enabled is True

    cid2 = db.create_conversation("纯聊", rag_enabled=False)
    assert db.get_conversation(cid2).rag_enabled is False

    db.update_conversation_rag(cid2, True)
    assert db.get_conversation(cid2).rag_enabled is True
    assert db.get_conversation(cid2).title == "纯聊"  # 切换 rag 不影响 title

    # list 也带 rag_enabled
    convs = {c.id: c for c in db.list_conversations()}
    assert convs[cid].rag_enabled is True
    assert convs[cid2].rag_enabled is True


def test_migrate_adds_rag_enabled_to_old_db(tmp_path):
    """旧库（无 rag_enabled 列）打开时自动迁移加列，旧会话默认 True。"""
    import sqlite3

    path = str(tmp_path / "ai.db")
    # 模拟旧版 schema
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE conversations (id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "title TEXT NOT NULL DEFAULT '新会话', "
        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
        "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    conn.execute("INSERT INTO conversations (title) VALUES ('旧会话')")
    conn.commit()
    conn.close()

    # 用 AIDatabase 打开 → 应自动迁移
    db = AIDatabase(path)
    conv = db.list_conversations()[0]
    assert conv.title == "旧会话"
    assert conv.rag_enabled is True  # 旧会话默认开

    # 幂等：再开一次不报错
    db2 = AIDatabase(path)
    assert db2.list_conversations()[0].rag_enabled is True


# ===== Task（source_mode 字段，子项目2.1）=====


def test_task_has_source_mode_column(tmp_path):
    """新建 task 带 source_mode 字段，默认 'full'。"""
    from insight_aitest.modules.ai.backend.persistence.database import AIDatabase
    db = AIDatabase(str(tmp_path / "ai.db"))
    task_id = db.create_task(intent="test", project_id=1)
    task = db.get_task(task_id)
    assert hasattr(task, "source_mode")
    assert task.source_mode == "full"


def test_update_task_source_mode(tmp_path):
    """update_task_source_mode 能更新 source_mode 并持久化。"""
    from insight_aitest.modules.ai.backend.persistence.database import AIDatabase
    db = AIDatabase(str(tmp_path / "ai.db"))
    task_id = db.create_task(intent="test", project_id=1)
    db.update_task_source_mode(task_id, "quick_analyze")

    task = db.get_task(task_id)
    assert task.source_mode == "quick_analyze"


def test_migrate_adds_source_mode_to_old_db(tmp_path):
    """旧库（无 source_mode 列）打开时自动迁移加列，旧 task 默认 'full'。"""
    import sqlite3
    from insight_aitest.modules.ai.backend.persistence.database import AIDatabase

    path = str(tmp_path / "ai.db")
    # 模拟旧版 agent_tasks schema（无 source_mode；含 ORM SELECT 需要的基础列）
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE agent_tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "intent TEXT NOT NULL DEFAULT '', "
        "plan_json JSON, status TEXT NOT NULL DEFAULT 'planning', "
        "current_step INTEGER DEFAULT 0, total_steps INTEGER DEFAULT 0, "
        "result_json JSON, error TEXT, "
        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
        "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
        "finished_at TIMESTAMP)"
    )
    conn.execute("INSERT INTO agent_tasks (intent) VALUES ('旧任务')")
    conn.commit()
    conn.close()

    # 用 AIDatabase 打开 → 应自动迁移加 source_mode 列（+ 其它增强列）
    db = AIDatabase(path)
    tasks = db.list_tasks()
    assert len(tasks) == 1
    assert tasks[0].source_mode == "full"  # 迁移默认值
