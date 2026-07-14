# -*- coding: utf-8 -*-
"""document_ids 贯穿链路测试：create_task -> context_json -> generate-batch plan params。"""

from unittest.mock import MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient


class _FakeLLM:
    def chat(self, messages, **kwargs):
        txt = messages[0]["content"] if messages else ""
        if "分析并输出一个 JSON 对象" in txt:
            return '{"summary": "测试", "scope": ["登录"]}'
        return '[{"id":"A","label":"批量生成","description":"从需求文档提取测试点","plan":[{"skill":"extract_test_points","desc":"提取测试点","params":{"query":"登录测试"}}]}]'

    def stream_chat(self, messages, **kwargs):
        yield ""

    def stream_chat_raw(self, messages, **kwargs):
        yield ("content", "")

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
    kb_deps._kb_db = None
    kb_deps._llm = None
    kb_deps._vector_store = None
    kb_deps._retriever = None
    kb_deps._config_file = None
    tc_deps._tc_db = None

    cfg = deps.get_config()
    cfg.db_path = str(tmp_path / "kb.db")
    cfg.docs_dir = str(tmp_path / "docs")
    deps._db = ai_db_mod.AIDatabase(str(tmp_path / "ai.db"))
    tc_deps._tc_db = tc_db_mod.TestCaseDatabase(str(tmp_path / "testcase.db"))

    fake = _FakeLLM()
    kb_deps._llm = fake
    kb_deps._llm_config = cfg

    # mock generator
    from insight_aitest.modules.testcase.backend.persistence.models import (
        CaseType, CaseStatus, CasePriority, TestType, TestCase,
    )
    def _fake_generate(point, **kwargs):
        return TestCase(
            title=f"用例-{getattr(point, 'summary', '')}",
            type=CaseType.FUNCTIONAL, description="测试描述",
            priority=CasePriority.P2, status=CaseStatus.DRAFT,
            test_design=TestType.POSITIVE, preconditions="无",
            content={"steps": [{"no": 1, "action": "操作", "data": ""}], "expected": "预期"},
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


def test_create_task_persists_document_ids(tmp_path, monkeypatch):
    """create_task 应将 document_ids 持久化到 task.context_json。"""
    c = _setup_app(tmp_path, monkeypatch)
    r = c.post("/api/modules/ai/tasks", json={
        "intent": "从需求文档生成用例",
        "project_id": 1,
        "document_ids": [10, 20, 30],
    })
    assert r.status_code == 200
    task = r.json()
    assert task["context"]["document_ids"] == [10, 20, 30]


def test_planner_injects_document_ids_into_plan(tmp_path, monkeypatch):
    """planner.propose_strategies 应把 document_ids 注入到 extract_test_points 的 params。"""
    monkeypatch.setenv("INSIGHT_EYE_AI_LLM_API_KEY", "sk-test")
    monkeypatch.setenv("INSIGHT_EYE_AI_EMBED_DIM", "4")

    import insight_aitest.modules.ai.backend.deps as deps
    import insight_aitest.platform.services.kb.deps as kb_deps
    deps._planner = None
    deps._db = None
    kb_deps._llm_config = None
    kb_deps._llm = None

    cfg = deps.get_config()
    fake = _FakeLLM()
    kb_deps._llm = fake
    kb_deps._llm_config = cfg

    planner = deps.get_planner()
    context = {"summary": "从需求文档生成用例", "scope": ["登录", "注册"], "document_ids": [10, 20]}
    strategies = planner.propose_strategies(context, document_ids=[10, 20])

    found = False
    for strat in strategies:
        for step in strat.get("plan", []):
            if step["skill"] == "extract_test_points":
                assert step["params"].get("document_ids") == [10, 20]
                found = True
    assert found, "extract_test_points 步骤应包含注入的 document_ids"


def test_write_cases_batch_passes_document_ids(tmp_path, monkeypatch):
    """_write_cases_batch 应把 document_ids 和 project_id 传给 generator.generate。"""
    monkeypatch.setenv("INSIGHT_EYE_AI_LLM_API_KEY", "sk-test")
    monkeypatch.setenv("INSIGHT_EYE_AI_EMBED_DIM", "4")

    import insight_aitest.modules.ai.backend.deps as deps
    import insight_aitest.platform.services.kb.deps as kb_deps
    import insight_aitest.modules.testcase.backend.deps as tc_deps
    import insight_aitest.modules.testcase.backend.persistence.database as tc_db_mod
    kb_deps._llm_config = None
    kb_deps._llm = None
    tc_deps._tc_db = None
    cfg = deps.get_config()
    tc_deps._tc_db = tc_db_mod.TestCaseDatabase(str(tmp_path / "tc.db"))

    from insight_aitest.modules.testcase.backend.persistence.models import (
        CaseType, CaseStatus, CasePriority, TestType, TestCase,
    )
    received_kwargs = {}
    def _fake_generate(point, **kwargs):
        received_kwargs.update(kwargs)
        return TestCase(
            title=f"用例-{getattr(point, 'summary', '')}",
            type=CaseType.FUNCTIONAL, description="描述",
            priority=CasePriority.P2, status=CaseStatus.DRAFT,
            test_design=TestType.POSITIVE, preconditions="无",
            content={"steps": [], "expected": "预期"},
        )
    mock_gen = MagicMock()
    mock_gen.generate = _fake_generate
    tc_deps._generator = mock_gen

    from insight_aitest.modules.ai.backend.agent.skills import SKILLS, SkillContext
    from insight_aitest.platform.services.kb.retriever import NullRetriever
    ctx = SkillContext(
        llm=MagicMock(), config=cfg, retriever=NullRetriever(),
        generator=mock_gen, case_db=tc_deps._tc_db,
        project_id=5, version_id=None,
    )
    skill = SKILLS["write_cases_batch"]
    result = skill.execute(
        {"test_points": [{"id": "tp1", "summary": "登录测试", "suggested_type": "functional", "suggested_design": "positive"}],
         "task_id": 1, "document_ids": [10, 20]},
        ctx,
    )
    assert result["generated"] == 1
    assert received_kwargs.get("document_ids") == [10, 20]
    assert received_kwargs.get("project_id") == 5


def test_generate_batch_plan_includes_document_ids(tmp_path, monkeypatch):
    """generate-batch 端点的 plan params 应包含 document_ids（从 task.context_json 取）。"""
    c = _setup_app(tmp_path, monkeypatch)
    r = c.post("/api/modules/ai/tasks", json={
        "intent": "从需求文档生成用例",
        "project_id": 1,
        "document_ids": [10, 20],
    })
    assert r.status_code == 200
    task_id = r.json()["id"]

    r2 = c.post(f"/api/modules/ai/tasks/{task_id}/generate-batch", json={
        "test_points": [{"id": "tp1", "summary": "登录", "suggested_type": "functional", "suggested_design": "positive"}],
    })
    assert r2.status_code == 200
    plan = r2.json()["plan"]
    assert plan[0]["params"]["document_ids"] == [10, 20]
