# -*- coding: utf-8 -*-
"""Agent Task 引擎测试：plan 生成、skill 执行、task API 闭环。

用 FakeLLM 顶替真实 LLM，不依赖 API key。
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient


class FakeLLM:
    """假 LLM：plan 生成返回固定 JSON，chat 返回空。"""

    def chat(self, messages, **kwargs):
        # 返回一个 plan JSON（用于 Planner 测试）
        return """```json
[
  {"skill": "rag_search", "desc": "检索登录相关文档", "params": {"query": "登录"}},
  {"skill": "write_functional_case", "desc": "生成功能用例", "params": {"query": "登录功能", "design": "positive"}}
]
```"""

    def stream_chat(self, messages, **kwargs):
        yield ""

    def embed(self, texts):
        return [[0.1] * 4 for _ in texts]

    def embed_query(self, text):
        return [0.1] * 4


def _setup_app(tmp_path, monkeypatch):
    """构造用 tmp 目录的 app。"""
    monkeypatch.setenv("INSIGHT_EYE_AI_LLM_API_KEY", "sk-test")
    monkeypatch.setenv("INSIGHT_EYE_AI_EMBED_DIM", "4")

    import insight_aitest.modules.ai.backend.deps as deps
    import insight_aitest.platform.services.kb.deps as kb_deps
    import insight_aitest.modules.ai.backend.persistence.database as ai_db_mod
    import insight_aitest.modules.testcase.backend.deps as tc_deps
    import insight_aitest.modules.testcase.backend.persistence.database as tc_db_mod

    # 重置所有单例
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

    # 注入 FakeLLM
    fake = FakeLLM()
    kb_deps._llm = fake
    kb_deps._llm_config = cfg

    from insight_aitest.modules.ai.backend.routes import router as ai_router
    app = FastAPI()
    app.include_router(ai_router, prefix="/api/modules/ai")
    return TestClient(app)


def test_planner_generates_plan(tmp_path, monkeypatch):
    """Planner 能从意图生成有效的 plan JSON。"""
    _setup_app(tmp_path, monkeypatch)
    from insight_aitest.modules.ai.backend.agent.planner import Planner
    from insight_aitest.platform.services.llm.config import LLMConfig

    cfg = LLMConfig(llm_api_key="fake")
    planner = Planner(FakeLLM(), cfg)
    plan = planner.generate_plan("帮我写登录用例")

    assert isinstance(plan, list)
    assert len(plan) >= 1
    # 每步必须有 skill 和 desc
    for step in plan:
        assert "skill" in step
        assert "desc" in step
        assert step["skill"] in ("rag_search", "write_functional_case", "write_api_case")


def test_planner_fallback_on_bad_llm(tmp_path, monkeypatch):
    """LLM 返回非 JSON 时降级为默认 plan。"""
    _setup_app(tmp_path, monkeypatch)
    from insight_aitest.modules.ai.backend.agent.planner import Planner
    from insight_aitest.platform.services.llm.config import LLMConfig

    class BadLLM:
        def chat(self, messages, **kwargs):
            return "我无法理解这个任务"

    cfg = LLMConfig(llm_api_key="fake")
    planner = Planner(BadLLM(), cfg)
    plan = planner.generate_plan("测试意图")

    # 降级：至少有一个 rag_search 步骤
    assert len(plan) == 1
    assert plan[0]["skill"] == "rag_search"


def test_task_crud_via_api(tmp_path, monkeypatch):
    """Task API 闭环：创建（understand+strategize）→ 查询 → 列表 → 取消。"""
    c = _setup_app(tmp_path, monkeypatch)

    # 创建 task（新流程：understand → strategize → pending_select）
    r = c.post("/api/modules/ai/tasks", json={"intent": "帮我写登录用例"})
    assert r.status_code == 200
    task = r.json()
    assert task["status"] == "pending_select"
    assert len(task["strategies"]) >= 1  # 应该有策略选项
    assert task["context"]["summary"]  # 应该有理解摘要
    task_id = task["id"]

    # 查询单个
    r = c.get(f"/api/modules/ai/tasks/{task_id}")
    assert r.status_code == 200
    assert r.json()["id"] == task_id

    # 列表
    r = c.get("/api/modules/ai/tasks")
    assert r.status_code == 200
    assert len(r.json()) >= 1

    # 取消（删除）
    r = c.delete(f"/api/modules/ai/tasks/{task_id}")
    assert r.status_code == 200


def test_planner_understand_and_strategize(tmp_path, monkeypatch):
    """Planner 两阶段：understand + propose_strategies。"""
    _setup_app(tmp_path, monkeypatch)
    from insight_aitest.modules.ai.backend.agent.planner import Planner

    planner = Planner(FakeLLM(), __import__(
        "insight_aitest.platform.services.llm.config", fromlist=["LLMConfig"]
    ).LLMConfig(llm_api_key="fake"))

    # understand
    context = planner.understand("测登录功能", [
        {"filename": "需求.md", "content": "# 登录功能\n支持账号密码和手机验证码登录"}
    ])
    assert "summary" in context
    assert "scope" in context

    # propose_strategies
    strategies = planner.propose_strategies(context)
    assert len(strategies) >= 1
    for s in strategies:
        assert "id" in s
        assert "label" in s
        assert "plan" in s


def test_skill_catalog():
    """skill 注册表包含 3 个核心 skill。"""
    from insight_aitest.modules.ai.backend.agent.skills import SKILLS

    assert "rag_search" in SKILLS
    assert "write_functional_case" in SKILLS
    assert "write_api_case" in SKILLS
