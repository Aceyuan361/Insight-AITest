# -*- coding: utf-8 -*-
"""真实 HTTP 端到端测试：后端的 LLMClient 通过 HTTP 调用 mock LLM server。

区别于 test_e2e_mock.py（FakeLLM 直接注入单例）——本测试用真实 LLMClient
（真实 openai SDK + 真实 HTTP）连 mock server，证明：
- 后端代码零改动即可对接任何 OpenAI 兼容端点
- 换真实模型只需改 base_url + api_key

前置：mock server 已在 http://127.0.0.1:8088 启动（py scripts/mock_llm_server.py）。
未启动时本测试跳过。
"""
from __future__ import annotations

import time
import urllib.request

import pytest

MOCK_URL = "http://127.0.0.1:8088/v1"
EMBED_DIM = 8


def _mock_running() -> bool:
    try:
        urllib.request.urlopen("http://127.0.0.1:8088/health", timeout=2)
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _mock_running(),
                                reason="mock LLM server 未启动 (py scripts/mock_llm_server.py)")


def _install_real_llm_deps(tmp_path):
    """用真实 LLMClient（指向 mock server）注入平台 + ai 单例。"""
    import insight_aitest.modules.ai.backend.deps as deps
    import insight_aitest.platform.services.kb.deps as kb_deps
    from insight_aitest.platform.services.llm.config import AIConfig
    from insight_aitest.platform.services.kb.retriever import Retriever
    from insight_aitest.platform.services.kb.vector_store import VectorStore
    from insight_aitest.platform.services.llm.client import LLMClient
    from insight_aitest.modules.ai.backend.persistence.database import AIDatabase
    from insight_aitest.platform.services.kb.database import KBDatabase
    from insight_aitest.modules.ai.backend.agent.rag import RagAgent

    deps._db = None
    deps._agent = None
    kb_deps._llm_config = None
    kb_deps._kb_db = None
    kb_deps._llm = None
    kb_deps._vector_store = None
    kb_deps._retriever = None

    cfg = AIConfig(
        llm_base_url=MOCK_URL,
        llm_api_key="mock-key",
        embed_dim=EMBED_DIM,
        chunk_size=50,
        chunk_overlap=10,
    )
    cfg.db_path = str(tmp_path / "kb.db")
    cfg.docs_dir = str(tmp_path / "docs")
    cfg.config_file = str(tmp_path / "ai_config.json")
    kb_deps._llm_config = cfg

    kb_db = KBDatabase(cfg.db_path, embed_dim=EMBED_DIM)
    ai_db = AIDatabase(str(tmp_path / "ai.db"))
    llm = LLMClient(cfg)  # 真实 LLMClient，指向 mock server
    vs = VectorStore(kb_db, llm, cfg)
    retriever = Retriever(vs, None, llm, cfg)
    agent = RagAgent(retriever, llm, cfg)

    kb_deps._kb_db = kb_db
    kb_deps._llm = llm
    kb_deps._vector_store = vs
    kb_deps._retriever = retriever
    deps._db = ai_db
    deps._agent = agent
    return ai_db


def _app():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from insight_aitest.modules.ai.backend.routes import router as ai_router
    app = FastAPI()
    app.include_router(ai_router, prefix="/api/modules/ai")
    return TestClient(app)


def _wait_status(c, doc_id, target, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        st = c.get(f"/api/modules/ai/documents/{doc_id}").json()["status"]
        if st == target:
            return True
        if st in ("parse_failed", "embed_failed"):
            return False
        time.sleep(0.3)
    return False


def test_real_http_full_pipeline(tmp_path):
    """真实 HTTP：上传 → 后台用真实 LLMClient 调 mock embed → ready → 流式问答。"""
    _install_real_llm_deps(tmp_path)
    c = _app()

    md = "# 文档\nInsight-Eye 支持移动设备性能监控。\n## 指标\nCPU 内存 FPS。\n"
    r = c.post("/api/modules/ai/documents",
               files={"file": ("doc.md", md.encode("utf-8"), "text/markdown")})
    assert r.status_code == 200, r.text
    doc_id = r.json()["id"]
    assert _wait_status(c, doc_id, "ready"), \
        f"未就绪: {c.get(f'/api/modules/ai/documents/{doc_id}').json()}"

    conv = c.post("/api/modules/ai/conversations").json()
    cid = conv["id"]

    # 流式问答（真实 LLMClient → mock server stream）
    with c.stream("POST", "/api/modules/ai/chat/stream",
                  json={"conversation_id": cid, "query": "支持哪些指标?"}) as r:
        assert r.status_code == 200
        text = b"".join(r.iter_bytes()).decode("utf-8")
    assert "event: citations" in text, "缺 citations"
    assert "event: token" in text, "缺 token"
    assert "event: done" in text, "缺 done"

    # 历史落库且 assistant 带引用
    detail = c.get(f"/api/modules/ai/conversations/{cid}").json()
    asst = [m for m in detail["messages"] if m["role"] == "assistant"]
    assert asst and len(asst[-1]["citations"]) > 0, "assistant 无引用"
