# -*- coding: utf-8 -*-
"""文档 API 集成测试。每个测试用独立 tmp 目录的 DB，避免单例污染。"""

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _setup_app(tmp_path, monkeypatch):
    """构造一个用 tmp 目录的 app：patch 环境变量让 load_config 指向 tmp。

    文档 API 已迁移到 kb 模块（/api/modules/kb/documents）。
    """
    monkeypatch.setenv("INSIGHT_EYE_AI_LLM_API_KEY", "sk-test")
    monkeypatch.setenv("INSIGHT_EYE_AI_EMBED_DIM", "4")
    import insight_aitest.modules.ai.backend.deps as deps
    import insight_aitest.platform.services.kb.deps as kb_deps
    import insight_aitest.modules.ai.backend.persistence.database as _ai_db_mod
    deps._db = None
    deps._agent = None
    kb_deps._llm_config = None
    kb_deps._kb_db = None
    kb_deps._llm = None
    kb_deps._vector_store = None
    kb_deps._retriever = None
    kb_deps._config_file = None
    cfg = deps.get_config()
    cfg.db_path = str(tmp_path / "kb.db")
    cfg.docs_dir = str(tmp_path / "docs")
    deps._db = _ai_db_mod.AIDatabase(str(tmp_path / "ai.db"))

    from insight_aitest.modules.kb.backend.routes import router as kb_router
    app = FastAPI()
    app.include_router(kb_router, prefix="/api/modules/kb")
    return TestClient(app)


def test_list_documents_empty(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    r = c.get("/api/modules/kb/documents")
    assert r.status_code == 200
    assert r.json() == []


def test_upload_and_get_status(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    r = c.post("/api/modules/kb/documents",
               files={"file": ("test.md", b"# Hello\ncontent here", "text/markdown")})
    assert r.status_code == 200
    body = r.json()
    assert body["filename"] == "test.md"
    assert body["id"] > 0
    r = c.get("/api/modules/kb/documents")
    assert len(r.json()) >= 1
    r = c.get(f"/api/modules/kb/documents/{body['id']}")
    assert r.status_code == 200


def test_upload_dedup(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    content = b"# dup\nsame content"
    r1 = c.post("/api/modules/kb/documents",
                files={"file": ("a.md", content, "text/markdown")})
    r2 = c.post("/api/modules/kb/documents",
                files={"file": ("b.md", content, "text/markdown")})
    assert r1.json()["id"] == r2.json()["id"]  # 同内容去重


def test_delete_document(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    r = c.post("/api/modules/kb/documents",
               files={"file": ("x.md", b"# x", "text/markdown")})
    doc_id = r.json()["id"]
    r = c.delete(f"/api/modules/kb/documents/{doc_id}")
    assert r.status_code == 200
    r = c.get(f"/api/modules/kb/documents/{doc_id}")
    assert r.status_code == 404


def test_upload_unsupported_format(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    r = c.post("/api/modules/kb/documents",
               files={"file": ("x.xyz", b"stuff", "application/octet-stream")})
    assert r.status_code == 400
