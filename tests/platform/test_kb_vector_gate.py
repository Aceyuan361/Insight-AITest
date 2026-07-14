# -*- coding: utf-8 -*-
"""向量检索门禁测试。

验证 vector_enabled=False 时：
- KBDatabase 构造不炸（即使旧库有维度不一致的 vec0 表）
- retrieve 返回空列表
- 用例生成链路（Generator）走纯 LLM 无参考资料

以及 vector_enabled=True 时维度不一致仍抛 ValueError（保留数据完整性校验）。
"""
from __future__ import annotations

import sqlite3

import pytest

from insight_aitest.platform.services.kb.database import KBDatabase
from insight_aitest.platform.services.kb.retriever import NullRetriever


# ===== 构造期门禁（修复核心 bug）=====


def _seed_legacy_vec0_table(db_path: str, dim: int = 2048) -> None:
    """在 db_path 下建一个声明维度=dim 的旧 vec0 表（模拟历史索引库）。"""
    import sqlite_vec

    conn = sqlite3.connect(db_path)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    conn.execute(
        f"CREATE VIRTUAL TABLE chunk_embeddings USING vec0("
        f"chunk_id INTEGER PRIMARY KEY, embedding FLOAT[{dim}])"
    )
    conn.commit()
    conn.close()


def test_vector_disabled_skips_vec_init_no_crash(tmp_path):
    """vector_enabled=False + 旧库维度 2048 → 构造不炸，_vec_available=False。

    这是用户报告的崩溃 bug 的回归测试：设置里没开向量检索，
    但库曾有 2048 维索引，构造 KBDatabase 时抛 ValueError。
    """
    db_path = str(tmp_path / "kb.db")
    _seed_legacy_vec0_table(db_path, dim=2048)

    # vector_enabled=False：跳过 vec0 初始化，不读也不校验旧表
    db = KBDatabase(db_path, embed_dim=4, vector_enabled=False)
    assert db._vec_available is False
    # 文档 CRUD 仍可用（走 ORM 表）
    doc_id = db.create_document("test.pdf", "/store/test.pdf", "hash123", "application/pdf")
    assert doc_id is not None


def test_vector_enabled_mismatch_still_raises(tmp_path):
    """vector_enabled=True + 维度不一致 → 仍抛 ValueError（保留数据完整性校验）。

    门禁只跳过 vector_enabled=False 的情况，True 时维度校验照常。
    """
    db_path = str(tmp_path / "kb.db")
    _seed_legacy_vec0_table(db_path, dim=2048)

    with pytest.raises(ValueError, match="embed_dim 不一致"):
        KBDatabase(db_path, embed_dim=4, vector_enabled=True)


def test_vector_disabled_does_not_create_vec_table(tmp_path):
    """vector_enabled=False → 不创建 vec0 表（彻底跳过向量相关初始化）。"""
    db_path = str(tmp_path / "kb.db")
    db = KBDatabase(db_path, embed_dim=4, vector_enabled=False)
    assert db._vec_available is False

    conn = db.get_connection()
    tables = {
        r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    assert "chunk_embeddings" not in tables, "vector_enabled=False 不应创建 vec0 表"


def test_vector_enabled_creates_vec_table(tmp_path):
    """vector_enabled=True（默认）→ 正常创建 vec0 表（现有行为不变）。"""
    db_path = str(tmp_path / "kb.db")
    db = KBDatabase(db_path, embed_dim=8, vector_enabled=True)
    assert db._vec_available is True

    conn = db.get_connection()
    tables = {
        r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    assert "chunk_embeddings" in tables


def test_default_vector_enabled_is_true(tmp_path):
    """KBDatabase 默认 vector_enabled=True（向后兼容现有调用）。"""
    db = KBDatabase(str(tmp_path / "kb.db"), embed_dim=8)
    assert db._vec_available is True


# ===== NullRetriever（use_kb=False 的运行期短路）=====


def test_null_retriever_returns_empty():
    """NullRetriever.retrieve 永远返回空列表。"""
    r = NullRetriever()
    assert r.retrieve("登录测试") == []
    assert r.retrieve("登录测试", top_k=5) == []
    assert r.retrieve("登录测试", document_ids=[1, 2]) == []


# ===== 端到端：use_kb 透传到 task 记录 =====


def test_create_task_stores_use_kb(tmp_path, monkeypatch):
    """create_task(use_kb=True) → task 记录的 use_kb 字段为 True。"""
    monkeypatch.setenv("INSIGHT_EYE_AI_LLM_API_KEY", "sk-test")
    from insight_aitest.modules.ai.backend.persistence.database import AIDatabase

    db = AIDatabase(str(tmp_path / "ai.db"))

    # use_kb=True
    tid_kb = db.create_task("测试意图1", use_kb=True)
    task_kb = db.get_task(tid_kb)
    assert task_kb.use_kb is True

    # use_kb=False（默认）
    tid_no = db.create_task("测试意图2", use_kb=False)
    task_no = db.get_task(tid_no)
    assert task_no.use_kb is False

    # 默认值（不传 use_kb）
    tid_def = db.create_task("测试意图3")
    task_def = db.get_task(tid_def)
    assert task_def.use_kb is False


def test_use_kb_column_migration_idempotent(tmp_path, monkeypatch):
    """_ensure_task_columns 幂等补 use_kb 列（旧库无此列时自动 ALTER）。"""
    monkeypatch.setenv("INSIGHT_EYE_AI_LLM_API_KEY", "sk-test")
    from insight_aitest.modules.ai.backend.persistence.database import AIDatabase

    db_path = str(tmp_path / "ai.db")
    # 第一次构造：建表 + 补列
    AIDatabase(db_path)
    conn = sqlite3.connect(db_path)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(agent_tasks)")}
    assert "use_kb" in cols
    conn.close()

    # 第二次构造：幂等（不报错）
    AIDatabase(db_path)
    conn = sqlite3.connect(db_path)
    cols2 = {row[1] for row in conn.execute("PRAGMA table_info(agent_tasks)")}
    assert "use_kb" in cols2
    conn.close()
