# -*- coding: utf-8 -*-
import pytest

from insight_aitest.platform.services.kb.database import KBDatabase


def test_vec_table_created_with_dim(tmp_path):
    db = KBDatabase(str(tmp_path / "ai.db"), embed_dim=8)
    assert db._vec_available is True
    conn = db.get_connection()
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "chunk_embeddings" in tables


def test_embed_dim_mismatch_raises(tmp_path):
    """已存在 vec0 表声明 dim=8，再用 dim=16 打开应报错。"""
    path = str(tmp_path / "ai.db")
    KBDatabase(path, embed_dim=8)
    with pytest.raises(Exception):
        KBDatabase(path, embed_dim=16)


def test_knn_search_returns_nearest(tmp_path):
    """端到端验证 vec0 KNN：插入两条向量，查询应返回最近邻。"""
    db = KBDatabase(str(tmp_path / "ai.db"), embed_dim=4)
    conn = db.get_connection()
    conn.execute("INSERT INTO chunk_embeddings (chunk_id, embedding) VALUES (?, ?)",
                 (100, "[0.1,0.2,0.3,0.4]"))
    conn.execute("INSERT INTO chunk_embeddings (chunk_id, embedding) VALUES (?, ?)",
                 (200, "[0.9,0.8,0.7,0.6]"))
    conn.commit()
    rows = conn.execute(
        "SELECT chunk_id, distance FROM chunk_embeddings "
        "WHERE embedding MATCH ? ORDER BY distance LIMIT 1",
        ("[0.1,0.2,0.3,0.4]",)).fetchall()
    assert rows[0]["chunk_id"] == 100
    assert rows[0]["distance"] == 0.0
