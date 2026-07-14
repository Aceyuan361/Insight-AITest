# -*- coding: utf-8 -*-
"""端到端集成测试：验证4个修复+3个功能的协同。

覆盖场景：
1. document_ids 贯穿：create_task -> context_json 持久化
2. 会话创建去重：连续创建复用空会话
3. 消息截断方向：list_messages 取最近 N 条
4. agent_chat 记忆：消息持久化 + 历史加载
5. 质量自检：生成后自动校验
"""

from unittest.mock import MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient


class _FakeLLM:
    """模拟 LLM：understand/strategize/analyze/generate 各返回合法 JSON。"""

    def chat(self, messages, **kwargs):
        txt = messages[-1]["content"] if messages else ""
        if "分析并输出一个 JSON 对象" in txt:
            return '{"summary": "登录注册测试", "scope": ["登录", "注册"]}'
        if "提出 3-4 个测试策略" in txt:
            return '[{"id":"A","label":"批量生成","description":"从需求文档提取","plan":[{"skill":"extract_test_points","desc":"提取测试点","params":{"query":"登录注册"}}]}]'
        if "提取" in txt and "可测点" in txt:
            return '[{"id":"tp1","summary":"登录功能","suggested_type":"functional","suggested_design":"positive","rationale":"核心功能"},{"id":"tp2","summary":"注册功能","suggested_type":"functional","suggested_design":"positive","rationale":"核心功能"}]'
        if "请根据可测点" in txt:
            return '{"title":"用例","description":"验证功能","preconditions":"无","content":{"steps":[{"no":1,"action":"操作","data":""}],"expected":"成功"}}'
        if "覆盖关系" in txt:
            return '[{"requirement_id":"tp1","requirement_summary":"登录","case_ids":[1],"match_reason":"标题匹配"},{"requirement_id":"tp2","requirement_summary":"注册","case_ids":[],"match_reason":"无匹配"}]'
        if "压缩为结构化摘要" in txt:
            return '{"topics":["登录测试"],"decisions":["选策略A"],"artifacts":[],"open_questions":[]}'
        return '{"summary":"test","scope":["test"]}'

    def stream_chat(self, messages, **kwargs):
        yield ""

    def stream_chat_raw(self, messages, **kwargs):
        yield ("content", "回复")

    def embed(self, texts):
        return [[0.1] * 4 for _ in texts]

    def embed_query(self, text):
        return [0.1] * 4


def _setup_app(tmp_path, monkeypatch):
    monkeypatch.setenv("INSIGHT_EYE_AI_LLM_API_KEY", "sk-test")
    monkeypatch.setenv("INSIGHT_EYE_AI_EMBED_DIM", "4")

    import insight_aitest.modules.ai.backend.deps as deps
    import insight_aitest.platform.services.kb.deps as kb_deps
    import insight_aitest.modules.ai.backend.persistence.database as ai_db_mod
    import insight_aitest.modules.testcase.backend.deps as tc_deps
    import insight_aitest.modules.testcase.backend.persistence.database as tc_db_mod
    deps._db = None
    deps._agent = None
    deps._planner = None
    kb_deps._llm_config = None
    kb_deps._llm = None
    kb_deps._kb_db = None
    kb_deps._vector_store = None
    kb_deps._retriever = None
    kb_deps._config_file = None
    tc_deps._tc_db = None

    cfg = deps.get_config()
    cfg.db_path = str(tmp_path / "kb.db")
    cfg.docs_dir = str(tmp_path / "docs")
    deps._db = ai_db_mod.AIDatabase(str(tmp_path / "ai.db"))
    tc_deps._tc_db = tc_db_mod.TestCaseDatabase(str(tmp_path / "tc.db"))

    kb_deps._llm = _FakeLLM()
    kb_deps._llm_config = cfg

    # mock generator
    from insight_aitest.modules.testcase.backend.persistence.models import (
        CaseType, CaseStatus, CasePriority, TestType, TestCase,
    )

    def _fake_generate(point, **kwargs):
        return TestCase(
            title=f"用例-{getattr(point, 'summary', '')}",
            type=CaseType.FUNCTIONAL, description="验证功能",
            priority=CasePriority.P2, status=CaseStatus.DRAFT,
            test_design=TestType.POSITIVE, preconditions="无",
            content={"steps": [{"no": 1, "action": "操作", "data": ""}], "expected": "成功"},
        )
    tc_deps._generator = MagicMock()
    tc_deps._generator.generate = _fake_generate
    monkeypatch.setattr(
        "insight_aitest.modules.testcase.backend.deps.get_generator",
        lambda: tc_deps._generator,
    )

    from insight_aitest.modules.ai.backend.routes import router as ai_router
    app = FastAPI()
    app.include_router(ai_router, prefix="/api/modules/ai")
    return TestClient(app)


def test_e2e_document_ids_persisted_in_context(tmp_path, monkeypatch):
    """E2E: create_task 带 document_ids -> context_json 持久化。"""
    c = _setup_app(tmp_path, monkeypatch)
    r = c.post("/api/modules/ai/tasks", json={
        "intent": "从需求文档生成用例", "project_id": 1, "document_ids": [10, 20],
    })
    assert r.status_code == 200
    assert r.json()["context"]["document_ids"] == [10, 20]


def test_e2e_conversation_dedup(tmp_path, monkeypatch):
    """E2E: 连续创建会话复用空会话。"""
    c = _setup_app(tmp_path, monkeypatch)
    r1 = c.post("/api/modules/ai/conversations", json={"project_id": 1})
    r2 = c.post("/api/modules/ai/conversations", json={"project_id": 1})
    assert r1.json()["id"] == r2.json()["id"]


def test_e2e_list_messages_recent(tmp_path, monkeypatch):
    """E2E: list_messages 取最近 N 条。"""
    _setup_app(tmp_path, monkeypatch)
    from insight_aitest.modules.ai.backend.deps import get_db
    from insight_aitest.modules.ai.backend.persistence.models import Role
    db = get_db()
    conv_id = db.create_conversation()
    for i in range(10):
        db.add_message(conv_id, Role.USER, f"msg-{i}")
    msgs = db.list_messages(conv_id, limit=4)
    assert msgs[0].content == "msg-6"
    assert msgs[-1].content == "msg-9"


def test_e2e_agent_chat_with_task_persists(tmp_path, monkeypatch):
    """E2E: agent_chat with task_id 持久化消息。"""
    c = _setup_app(tmp_path, monkeypatch)
    from insight_aitest.modules.ai.backend.deps import get_db
    db = get_db()
    task_id = db.create_task(intent="测试", project_id=1)

    r = c.post("/api/modules/ai/tasks/chat", json={
        "message": "反馈问题",
        "task_id": task_id,
    })
    assert r.status_code == 200
    msgs = db.list_messages_by_task(task_id)
    assert any(m.role.value == "user" and "反馈问题" in m.content for m in msgs)


def test_e2e_generate_batch_has_document_ids(tmp_path, monkeypatch):
    """E2E: generate-batch plan 包含 document_ids（从 context_json 取）。"""
    c = _setup_app(tmp_path, monkeypatch)
    # 创建 task 带 document_ids
    r = c.post("/api/modules/ai/tasks", json={
        "intent": "从需求文档生成用例", "project_id": 1, "document_ids": [10, 20],
    })
    task_id = r.json()["id"]
    # 调 generate-batch
    r2 = c.post(f"/api/modules/ai/tasks/{task_id}/generate-batch", json={
        "test_points": [{"id": "tp1", "summary": "登录", "suggested_type": "functional", "suggested_design": "positive"}],
    })
    assert r2.status_code == 200
    plan = r2.json()["plan"]
    assert plan[0]["params"]["document_ids"] == [10, 20]
