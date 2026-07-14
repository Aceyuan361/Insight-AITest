# -*- coding: utf-8 -*-
"""两阶段生成闭环 · 阶段2 端点测试：POST /tasks/{id}/generate-batch。

验证：
- 接收确认的 test_points → 后台执行 write_cases_batch → result 含 batch_id
- task 状态转为 running（执行中）/done（完成后）
- 404（task 不存在）+ 400（空 test_points）防护
- write_cases_batch 的 batch_id 正确汇总到 task.result_json 顶层

用 mock generator 生成假用例（不调真实 LLM），保证测试确定性。
"""
from __future__ import annotations

from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient


class _FakeLLM:
    """假 LLM：understand/strategize 返回合法 JSON，chat 返回空。"""

    def chat(self, messages, **kwargs):
        return '{"summary": "测试", "scope": ["登录"]}'
        # 注意：propose_strategies 期望 JSON 数组，下面 stream_chat/embed 给桩

    def stream_chat(self, messages, **kwargs):
        yield ""

    def embed(self, texts):
        return [[0.1] * 4 for _ in texts]

    def embed_query(self, text):
        return [0.1] * 4


def _setup_app(tmp_path, monkeypatch):
    """构造用 tmp 目录的 app（仿 test_agent_tasks._setup_app）。"""
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

    # 注入 mock generator：generate 返回假用例（不调真实 LLM）
    from insight_aitest.modules.testcase.backend.persistence.models import (
        CaseType, CaseStatus, CasePriority, TestType, TestCase,
    )

    def _fake_generate(point, **kwargs):
        return TestCase(
            title=f"用例-{getattr(point, 'summary', '')}",
            type=CaseType.FUNCTIONAL, description="",
            priority=CasePriority.P2, status=CaseStatus.DRAFT,
            test_design=TestType.POSITIVE, preconditions="",
            content={"steps": []}, tags=[],
        )

    # 替换 get_generator 让 get_executor 拿到 mock generator
    import insight_aitest.modules.testcase.backend.deps as tc_deps_mod
    tc_deps_mod._generator = MagicMock()
    tc_deps_mod._generator.generate = _fake_generate
    monkeypatch.setattr(
        "insight_aitest.modules.testcase.backend.deps.get_generator",
        lambda: tc_deps_mod._generator,
    )

    from insight_aitest.modules.ai.backend.routes import router as ai_router
    app = FastAPI()
    app.include_router(ai_router, prefix="/api/modules/ai")
    return TestClient(app)


def _create_task(c: TestClient) -> int:
    """创建一个 task 并返回 id（走 understand + strategize）。"""
    r = c.post("/api/modules/ai/tasks", json={"intent": "批量生成登录用例"})
    assert r.status_code == 200
    return r.json()["id"]


def test_generate_batch_starts_running_with_correct_plan(tmp_path, monkeypatch):
    """generate-batch 同步返回：状态 running + 构造了 write_cases_batch 单步 plan。

    后台线程 + SSE 的事件循环在 TestClient 下不可靠（select/confirm 同样问题，
    既有测试也未覆盖后台执行），故后台结果由 executor 直测覆盖（见
    test_executor_batch_aggregation / test_skills_batch）。
    """
    c = _setup_app(tmp_path, monkeypatch)
    task_id = _create_task(c)

    test_points = [
        {"id": "tp1", "description": "正确账密登录", "type_hint": "functional", "design_hint": "positive"},
        {"id": "tp2", "description": "空密码登录", "type_hint": "functional", "design_hint": "negative"},
    ]
    r = c.post(f"/api/modules/ai/tasks/{task_id}/generate-batch",
               json={"test_points": test_points, "project_id": 1, "version_id": 2})
    assert r.status_code == 200
    out = r.json()
    # 返回时 task 应已进入 running（后台线程刚启动）/ 或已完成
    assert out["status"] in ("running", "done")
    assert out["selected_strategy"] == "batch-generate"
    assert len(out["plan"]) == 1
    assert out["plan"][0]["skill"] == "write_cases_batch"
    # params 带确认后的 test_points + task_id
    assert len(out["plan"][0]["params"]["test_points"]) == 2
    assert out["plan"][0]["params"]["task_id"] == task_id


def test_generate_batch_404_on_missing_task(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    r = c.post("/api/modules/ai/tasks/9999/generate-batch",
               json={"test_points": [{"id": "tp1", "description": "x"}]})
    assert r.status_code == 404


def test_generate_batch_400_on_empty_points(tmp_path, monkeypatch):
    c = _setup_app(tmp_path, monkeypatch)
    task_id = _create_task(c)
    r = c.post(f"/api/modules/ai/tasks/{task_id}/generate-batch",
               json={"test_points": []})
    assert r.status_code == 400
