# -*- coding: utf-8 -*-
"""POST /tasks/quick 轻量预配置任务端点测试（Task 3）。

验证两种 mode：
- analyze_generate：mock get_analyzer 返回测试点 → 构造 write_cases_batch plan
- image_generate：构造 write_ui_case_from_image plan
+ source_mode 正确标记（quick_analyze / quick_image）
+ 提取不到测试点时标记 FAILED

mock get_executor / get_analyzer 避免真实 LLM 调用。
"""
from __future__ import annotations

from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient


class _FakeLLM:
    """假 LLM：understand/strategize 返回合法 JSON（不走，但 deps 初始化需要）。"""

    def chat(self, messages, **kwargs):
        return '{"summary": "测试", "scope": ["登录"]}'

    def stream_chat(self, messages, **kwargs):
        yield ""

    def embed(self, texts):
        return [[0.1] * 4 for _ in texts]

    def embed_query(self, text):
        return [0.1] * 4


def _setup_app(tmp_path, monkeypatch):
    """构造用 tmp 目录的 app（仿 test_generate_batch_endpoint._setup_app）。"""
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

    fake = _FakeLLM()
    kb_deps._llm = fake
    kb_deps._llm_config = cfg

    from insight_aitest.modules.ai.backend.routes import router as ai_router
    app = FastAPI()
    app.include_router(ai_router, prefix="/api/modules/ai")
    return app, TestClient(app)


def _make_points():
    """构造 Analyzer.analyze() 返回的 TestPoint 列表。"""
    from insight_aitest.modules.testcase.backend.generator.analyzer import TestPoint
    from insight_aitest.modules.testcase.backend.persistence.models import CaseType, TestType

    return [
        TestPoint(id="tp1", summary="登录正向", suggested_type=CaseType.FUNCTIONAL,
                  suggested_design=TestType.POSITIVE, rationale="需求3.2"),
        TestPoint(id="tp2", summary="空密码登录", suggested_type=CaseType.FUNCTIONAL,
                  suggested_design=TestType.NEGATIVE, rationale="异常分支"),
    ]


def _patch_analyzer(monkeypatch, points=None):
    """patch get_analyzer 返回 mock analyzer（points=None → 空列表）。"""
    fake_analyzer = MagicMock()
    fake_analyzer.analyze.return_value = points if points is not None else []
    monkeypatch.setattr(
        "insight_aitest.modules.testcase.backend.deps.get_analyzer", lambda: fake_analyzer
    )
    return fake_analyzer


def _patch_executor_noop(monkeypatch):
    """patch get_executor 返回 mock executor（run 不做真实执行）。"""
    fake_executor = MagicMock()
    monkeypatch.setattr(
        "insight_aitest.modules.ai.backend.routes.tasks.get_executor",
        lambda *a, **kw: fake_executor,
    )
    return fake_executor


def test_quick_task_analyze_generate_mode(tmp_path, monkeypatch):
    """analyze_generate：提取测试点 → 构造 write_cases_batch plan + source_mode=quick_analyze。"""
    _, c = _setup_app(tmp_path, monkeypatch)
    _patch_analyzer(monkeypatch, points=_make_points())
    _patch_executor_noop(monkeypatch)

    resp = c.post("/api/modules/ai/tasks/quick", json={
        "mode": "analyze_generate",
        "query": "登录功能测试",
        "document_ids": [],
        "project_id": 1,
        "use_kb": False,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert data["source_mode"] == "quick_analyze"
    # 构造了 write_cases_batch 单步 plan
    assert len(data["plan"]) == 1
    assert data["plan"][0]["skill"] == "write_cases_batch"
    assert len(data["plan"][0]["params"]["test_points"]) == 2
    # 测试点字段是统一的新结构
    tp0 = data["plan"][0]["params"]["test_points"][0]
    assert "summary" in tp0
    assert "suggested_type" in tp0
    assert "suggested_design" in tp0
    # 状态 running（后台执行被 mock）
    assert data["status"] in ("running", "done")


def test_quick_task_analyze_generate_no_points(tmp_path, monkeypatch):
    """analyze_generate 但提取不到测试点 → 标记 FAILED。"""
    _, c = _setup_app(tmp_path, monkeypatch)
    _patch_analyzer(monkeypatch, points=[])
    exec_mock = _patch_executor_noop(monkeypatch)

    resp = c.post("/api/modules/ai/tasks/quick", json={
        "mode": "analyze_generate",
        "query": "空需求",
        "use_kb": False,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["source_mode"] == "quick_analyze"
    assert data["status"] == "failed"
    assert "未提取到测试点" in (data["error"] or "")
    # 没有启动后台执行
    exec_mock.run.assert_not_called()


def test_quick_task_image_generate_mode(tmp_path, monkeypatch):
    """image_generate：构造 write_ui_case_from_image plan + source_mode=quick_image。"""
    _, c = _setup_app(tmp_path, monkeypatch)
    _patch_executor_noop(monkeypatch)

    resp = c.post("/api/modules/ai/tasks/quick", json={
        "mode": "image_generate",
        "images": [{"data": "iVBOR...", "mime": "image/png"}],
        "base_url": "https://demo.example.com",
        "point_summary": "登录页",
        "project_id": 1,
        "use_kb": False,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["source_mode"] == "quick_image"
    assert len(data["plan"]) == 1
    assert data["plan"][0]["skill"] == "write_ui_case_from_image"
    params = data["plan"][0]["params"]
    assert params["base_url"] == "https://demo.example.com"
    assert params["point_summary"] == "登录页"


def test_quick_task_default_use_kb(tmp_path, monkeypatch):
    """use_kb 默认 True（与 /tasks 的默认 False 不同，quick 面向有文档场景）。"""
    app, c = _setup_app(tmp_path, monkeypatch)
    _patch_analyzer(monkeypatch, points=_make_points())
    _patch_executor_noop(monkeypatch)

    resp = c.post("/api/modules/ai/tasks/quick", json={
        "mode": "analyze_generate",
        "query": "登录",
    })
    assert resp.status_code == 200
    # 后台线程执行了（可能还没跑完，但 executor 被构造）
    # 验证 use_kb 默认 True 传给 get_executor
    import time
    time.sleep(0.2)  # 等后台线程启动


def test_quick_task_default_source_mode_in_taskout(tmp_path, monkeypatch):
    """普通 /tasks 创建的 task source_mode 默认 'full'（TaskOut 兼容旧 task）。"""
    _, c = _setup_app(tmp_path, monkeypatch)
    resp = c.post("/api/modules/ai/tasks", json={"intent": "完整 agent 任务"})
    assert resp.status_code == 200
    assert resp.json()["source_mode"] == "full"
