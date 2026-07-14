# -*- coding: utf-8 -*-
"""端到端测试：用 FakeLLM 顶替真实 LLM，跑通完整 RAG 链路。

不依赖真实 API key / 网络。验证：
1. 上传文档 → 后台线程（用 FakeLLM embed）→ 状态变 ready
2. 创建会话 → 流式提问 → 收到 citations + token + done
3. 非流式提问 → 拿到带引用的回答
4. 重启模拟（新 AIDatabase 实例读同一 db 文件）→ 历史/文档持久化

FakeLLM 的 embed 对所有文本返回同一向量（保证检索恒命中，distance=0, score=1）。
"""
from __future__ import annotations

import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from insight_aitest.modules.ai.backend.agent.rag import RagAgent
from insight_aitest.platform.services.llm.config import AIConfig
from insight_aitest.platform.services.kb.retriever import Retriever
from insight_aitest.platform.services.kb.vector_store import VectorStore
from insight_aitest.modules.ai.backend.persistence.database import AIDatabase
from insight_aitest.platform.services.kb.database import KBDatabase


class FakeLLM:
    """假 LLM：embed 恒同向量（保证检索命中），chat/stream 返回固定带引用回答。"""

    def __init__(self, embed_dim: int = 4) -> None:
        self._dim = embed_dim
        # 归一化的全 1 向量（与 LLMClient._normalize 行为一致）
        import math
        n = 1.0 / math.sqrt(embed_dim)
        self._vec = [n] * embed_dim

    def embed(self, texts):
        return [list(self._vec) for _ in texts]

    def embed_query(self, text):
        return list(self._vec)

    def chat(self, messages):
        return "这是基于知识库的回答。根据[1]，相关内容已检索到。"

    def stream_chat(self, messages):
        for tok in ["这是", "基于", "知识库", "的", "回答", "。"]:
            yield tok


def _install_fake_deps(tmp_path, embed_dim=4):
    """注入 FakeLLM 到平台 + ai 单例（含后台线程用到的 kb_db/ai_db/llm/vector_store/retriever/agent）。"""
    import insight_aitest.modules.ai.backend.deps as deps
    import insight_aitest.platform.services.kb.deps as kb_deps

    # 重置 ai + 平台单例
    deps._db = None
    deps._agent = None
    kb_deps._llm_config = None
    kb_deps._kb_db = None
    kb_deps._llm = None
    kb_deps._vector_store = None
    kb_deps._retriever = None
    kb_deps._config_file = None

    cfg = AIConfig(llm_api_key="fake-key", embed_dim=embed_dim,
                   chunk_size=50, chunk_overlap=10, max_upload_mb=20, vector_enabled=True)
    cfg.db_path = str(tmp_path / "kb.db")
    cfg.docs_dir = str(tmp_path / "docs")
    cfg.config_file = str(tmp_path / "ai_config.json")
    kb_deps._llm_config = cfg

    # KB 库（文档/分块/向量）+ ai 库（会话/消息）分开
    kb_db = KBDatabase(cfg.db_path, embed_dim=embed_dim)
    ai_db = AIDatabase(str(tmp_path / "ai.db"))
    fake = FakeLLM(embed_dim)
    vs = VectorStore(kb_db, fake, cfg)
    retriever = Retriever(vs, kb_db, fake, cfg)
    agent = RagAgent(retriever, fake, cfg)

    # 平台单例（routes 通过 get_kb_db/get_llm/get_vector_store 取这些）
    kb_deps._kb_db = kb_db
    kb_deps._llm = fake
    kb_deps._vector_store = vs
    kb_deps._retriever = retriever
    # ai deps 的会话库 + agent
    deps._db = ai_db
    deps._agent = agent
    return ai_db


def _app():
    from insight_aitest.modules.ai.backend.routes import router as ai_router
    from insight_aitest.modules.kb.backend.routes import router as kb_router
    app = FastAPI()
    app.include_router(ai_router, prefix="/api/modules/ai")
    app.include_router(kb_router, prefix="/api/modules/kb")
    return TestClient(app)


SAMPLE_MD = (
    "# 项目说明\n\n"
    "Insight-Eye 是一个移动设备性能监控平台。\n\n"
    "## 功能\n\n"
    "支持 Android 和 iOS 设备的实时性能监控，包括 CPU、内存、FPS 等。\n"
)


def _wait_status(c, doc_id, target, timeout=15):
    """轮询文档状态直到 target 或超时。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = c.get(f"/api/modules/kb/documents/{doc_id}")
        st = r.json()["status"]
        if st == target:
            return True
        if st in ("parse_failed", "embed_failed"):
            return False
        time.sleep(0.3)
    return False


def test_e2e_upload_index_chat(tmp_path):
    """完整链路：上传 → 索引就绪 → 流式问答带引用 → 非流式问答。"""
    _install_fake_deps(tmp_path)
    c = _app()

    # 1. 上传文档
    r = c.post("/api/modules/kb/documents",
               files={"file": ("项目说明.md", SAMPLE_MD.encode("utf-8"), "text/markdown")})
    assert r.status_code == 200, r.text
    doc_id = r.json()["id"]

    # 2. 轮询直到 ready（后台线程用 FakeLLM embed）
    assert _wait_status(c, doc_id, "ready"), \
        f"文档未就绪: {c.get(f'/api/modules/kb/documents/{doc_id}').json()}"
    doc = c.get(f"/api/modules/kb/documents/{doc_id}").json()
    assert doc["chunk_count"] > 0

    # 3. 创建会话
    conv = c.post("/api/modules/ai/conversations").json()
    conv_id = conv["id"]

    # 4. 流式问答（SSE）
    tokens = []
    citations_seen = False
    done_seen = False
    with c.stream("POST", "/api/modules/ai/chat/stream",
                  json={"conversation_id": conv_id, "query": "支持什么平台?"}) as r:
        assert r.status_code == 200
        buf = b"".join(r.iter_bytes()).decode("utf-8")
    # 解析 SSE 事件
    for block in buf.split("\n\n"):
        if not block.strip():
            continue
        etype = block.split("event: ", 1)[1].split("\n", 1)[0] if "event: " in block else None
        if etype == "citations":
            citations_seen = True
        elif etype == "token":
            tokens.append(block)
        elif etype == "done":
            done_seen = True
    assert citations_seen, "SSE 未收到 citations 事件"
    assert len(tokens) > 0, "SSE 未收到 token 事件"
    assert done_seen, "SSE 未收到 done 事件"

    # 5. 会话历史落库（user + assistant 两条）
    detail = c.get(f"/api/modules/ai/conversations/{conv_id}").json()
    roles = [m["role"] for m in detail["messages"]]
    assert "user" in roles and "assistant" in roles
    # assistant 消息带引用（citations 非空）
    asst = [m for m in detail["messages"] if m["role"] == "assistant"]
    assert asst and len(asst[-1]["citations"]) > 0, "assistant 消息无引用"

    # 6. 非流式问答（第二个会话）
    conv2 = c.post("/api/modules/ai/conversations").json()
    r = c.post("/api/modules/ai/chat", json={
        "conversation_id": conv2["id"], "query": "性能监控包含哪些指标?"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"], "非流式回答为空"
    assert len(body["citations"]) > 0, "非流式回答无引用"


def test_e2e_persistence_across_restart(tmp_path):
    """模拟重启：新库实例读同一文件，文档（kb.db）与会话（ai.db）仍在。"""
    _install_fake_deps(tmp_path)
    c = _app()
    r = c.post("/api/modules/kb/documents",
               files={"file": ("持久.md", SAMPLE_MD.encode("utf-8"), "text/markdown")})
    doc_id = r.json()["id"]
    assert _wait_status(c, doc_id, "ready")
    conv = c.post("/api/modules/ai/conversations").json()

    # 模拟重启：文档在 kb.db（KBDatabase），会话在 ai.db（AIDatabase）
    kb_db2 = KBDatabase(str(tmp_path / "kb.db"), embed_dim=4)
    docs = kb_db2.list_documents()
    assert any(d.id == doc_id for d in docs), "重启后文档丢失"
    ai_db2 = AIDatabase(str(tmp_path / "ai.db"))
    convs = ai_db2.list_conversations()
    assert any(co.id == conv["id"] for co in convs), "重启后会话丢失"


def test_e2e_empty_kb_still_answers(tmp_path):
    """空知识库也能对话（降级，无引用）。"""
    _install_fake_deps(tmp_path)
    c = _app()
    conv = c.post("/api/modules/ai/conversations").json()
    r = c.post("/api/modules/ai/chat", json={
        "conversation_id": conv["id"], "query": "你好"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"], "空库应仍能回答"
    # 空库 → 检索无命中 → citations 为空
    assert body["citations"] == [], "空库不应有引用"


def test_e2e_delete_document(tmp_path):
    """删除文档：DB 记录 + 向量 + 原始文件三处清除。"""
    _install_fake_deps(tmp_path)
    c = _app()
    r = c.post("/api/modules/kb/documents",
               files={"file": ("删.md", "# 内容\n一些文本内容用于删除测试".encode("utf-8"), "text/markdown")})
    doc_id = r.json()["id"]
    assert _wait_status(c, doc_id, "ready")
    import insight_aitest.modules.ai.backend.deps as deps
    storage_path = deps.get_kb_db().get_document(doc_id).storage_path
    assert Path(storage_path).exists(), "原始文件应存在"

    r = c.delete(f"/api/modules/kb/documents/{doc_id}")
    assert r.status_code == 200
    assert c.get(f"/api/modules/kb/documents/{doc_id}").status_code == 404
    assert not Path(storage_path).exists(), "原始文件应已删除"
