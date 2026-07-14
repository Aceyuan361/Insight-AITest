# -*- coding: utf-8 -*-
"""附件上传/下载 API 测试。"""
import io
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _setup_app(tmp_path, monkeypatch):
    monkeypatch.setenv("INSIGHT_EYE_AI_LLM_API_KEY", "sk-test")
    monkeypatch.setenv("INSIGHT_EYE_AI_EMBED_DIM", "4")
    import insight_aitest.modules.ai.backend.deps as deps
    import insight_aitest.platform.services.kb.deps as kb_deps
    import insight_aitest.modules.ai.backend.persistence.database as ai_db_mod

    deps._db = None
    deps._agent = None
    kb_deps._llm_config = None
    kb_deps._llm = None
    kb_deps._config_file = None

    cfg = deps.get_config()
    cfg.db_path = str(tmp_path / "kb.db")
    cfg.docs_dir = str(tmp_path / "docs")
    deps._db = ai_db_mod.AIDatabase(str(tmp_path / "ai.db"))
    kb_deps._llm_config = cfg

    from insight_aitest.modules.ai.backend.routes import router as ai_router
    app = FastAPI()
    app.include_router(ai_router, prefix="/api/modules/ai")
    return TestClient(app)


def test_upload_image_attachment(tmp_path, monkeypatch):
    """上传图片 → kind=image，preview_text=None。"""
    c = _setup_app(tmp_path, monkeypatch)
    r = c.post(
        "/api/modules/ai/chat/attachments",
        files={"files": ("test.png", io.BytesIO(b"\x89PNG fake"), "image/png")},
    )
    assert r.status_code == 200
    atts = r.json()["attachments"]
    assert len(atts) == 1
    assert atts[0]["kind"] == "image"
    assert atts[0]["mime"] == "image/png"
    assert atts[0]["preview_text"] is None
    # 安全：storage_path（服务器绝对路径）不得泄露到 API 响应
    assert "storage_path" not in atts[0]
    assert "id" in atts[0]  # 前端用 id 下载，不需要路径


def test_upload_document_attachment_extracts_text(tmp_path, monkeypatch):
    """上传 .md 文档 → kind=document，preview_text 非空。"""
    c = _setup_app(tmp_path, monkeypatch)
    r = c.post(
        "/api/modules/ai/chat/attachments",
        files={"files": ("spec.md", io.BytesIO("# Title\n正文内容".encode("utf-8")), "text/markdown")},
    )
    assert r.status_code == 200
    atts = r.json()["attachments"]
    assert atts[0]["kind"] == "document"
    assert "正文内容" in atts[0]["preview_text"]


def test_download_attachment(tmp_path, monkeypatch):
    """上传后能下载回原始字节。"""
    c = _setup_app(tmp_path, monkeypatch)
    r = c.post(
        "/api/modules/ai/chat/attachments",
        files={"files": ("test.png", io.BytesIO(b"\x89PNG fake"), "image/png")},
    )
    basename = r.json()["attachments"][0]["id"]
    r2 = c.get(f"/api/modules/ai/chat/attachments/{basename}")
    assert r2.status_code == 200
    assert r2.content == b"\x89PNG fake"


def test_download_attachment_rejects_path_traversal(tmp_path, monkeypatch):
    """路径遍历攻击被拒。"""
    c = _setup_app(tmp_path, monkeypatch)
    r = c.get("/api/modules/ai/chat/attachments/..%2F..%2Fetc%2Fpasswd")
    assert r.status_code in (400, 404)
