# -*- coding: utf-8 -*-
"""/analyze 分析 API 测试（mock analyzer）。"""
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _setup_app(tmp_path, monkeypatch):
    monkeypatch.setenv("INSIGHT_EYE_AI_LLM_API_KEY", "sk-test")
    monkeypatch.setenv("INSIGHT_EYE_AI_EMBED_DIM", "4")
    import insight_aitest.modules.testcase.backend.deps as tc_deps
    tc_deps._tc_db = None
    from insight_aitest.modules.testcase.backend.persistence.database import TestCaseDatabase
    tc_deps._tc_db = TestCaseDatabase(str(tmp_path / "testcase.db"))
    from insight_aitest.modules.testcase.backend.routes import router as tc_router
    app = FastAPI()
    app.include_router(tc_router, prefix="/api/modules/testcase")
    return app, TestClient(app)


def test_analyze_endpoint(tmp_path, monkeypatch):
    app, c = _setup_app(tmp_path, monkeypatch)
    from insight_aitest.modules.testcase.backend.deps import get_analyzer
    from insight_aitest.modules.testcase.backend.generator.analyzer import TestPoint
    from insight_aitest.modules.testcase.backend.persistence.models import CaseType, TestType
    fake = MagicMock()
    fake.analyze.return_value = [TestPoint(
        id="tp-1", summary="登录正向", suggested_type=CaseType.FUNCTIONAL,
        suggested_design=TestType.POSITIVE, rationale="需求3.2")]
    app.dependency_overrides[get_analyzer] = lambda: fake
    r = c.post("/api/modules/testcase/testcases/analyze",
               json={"query": "核心功能"})
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["suggested_type"] == "functional"
    assert body[0]["suggested_design"] == "positive"
    assert body[0]["summary"] == "登录正向"


def test_analyze_with_document_ids(tmp_path, monkeypatch):
    app, c = _setup_app(tmp_path, monkeypatch)
    from insight_aitest.modules.testcase.backend.deps import get_analyzer
    fake = MagicMock()
    fake.analyze.return_value = []
    app.dependency_overrides[get_analyzer] = lambda: fake
    r = c.post("/api/modules/testcase/testcases/analyze",
               json={"query": "x", "document_ids": [1, 2]})
    assert r.status_code == 200
    fake.analyze.assert_called_once_with("x", [1, 2])


def test_generate_endpoint(tmp_path, monkeypatch):
    """/generate 生成即落库 draft。"""
    app, c = _setup_app(tmp_path, monkeypatch)
    from insight_aitest.modules.testcase.backend.deps import get_generator
    from insight_aitest.modules.testcase.backend.persistence.models import (
        CaseStatus, CaseType, TestCase, TestType)
    fake_gen = MagicMock()
    fake_gen.generate.return_value = TestCase(
        title="生成的用例", type=CaseType.FUNCTIONAL, test_design=TestType.POSITIVE,
        status=CaseStatus.DRAFT, content={"steps": [], "expected": "ok"}, source="ai:test")
    app.dependency_overrides[get_generator] = lambda: fake_gen
    r = c.post("/api/modules/testcase/testcases/generate", json={
        "point": {"id": "tp-1", "summary": "登录", "suggested_type": "functional",
                  "suggested_design": "positive", "rationale": "r"}})
    assert r.status_code == 201
    body = r.json()
    assert body["title"] == "生成的用例"
    assert body["status"] == "draft"
    assert body["id"] > 0  # 已落库
    # 落库后能在列表查到
    assert len(c.get("/api/modules/testcase/testcases").json()) == 1


# ===== Task 4: deprecation 标记 + 头（用例生成统一后旧路由废弃）=====


def _routes_deprecated():
    """收集 testcase generate router 中 generate 相关路由的 deprecated 标记。"""
    from insight_aitest.modules.testcase.backend.routes.generate import router as gen_router
    found = {}
    for route in gen_router.routes:
        path = getattr(route, "path", "")
        if "generate" in path or "analyze" in path:
            found[path] = getattr(route, "deprecated", False)
    return found


def test_generate_routes_marked_deprecated(tmp_path, monkeypatch):
    """3 个旧生成路由都标记 deprecated=True。"""
    _setup_app(tmp_path, monkeypatch)  # 触发 import
    deprecated = _routes_deprecated()
    assert "/testcases/analyze" in deprecated
    assert "/testcases/generate" in deprecated
    assert "/testcases/generate-from-image" in deprecated
    for path, is_dep in deprecated.items():
        assert is_dep is True, f"{path} 应标记 deprecated"


def test_analyze_sets_deprecation_headers(tmp_path, monkeypatch):
    """/analyze 响应带 Deprecation + Link 头。"""
    app, c = _setup_app(tmp_path, monkeypatch)
    from insight_aitest.modules.testcase.backend.deps import get_analyzer
    fake = MagicMock()
    fake.analyze.return_value = []
    app.dependency_overrides[get_analyzer] = lambda: fake
    r = c.post("/api/modules/testcase/testcases/analyze", json={"query": "x"})
    assert r.status_code == 200
    assert r.headers.get("Deprecation") == "true"
    assert "/api/modules/ai/tasks/quick" in r.headers.get("Link", "")


def test_generate_sets_deprecation_headers(tmp_path, monkeypatch):
    """/generate 响应带 Deprecation + Link 头。"""
    app, c = _setup_app(tmp_path, monkeypatch)
    from insight_aitest.modules.testcase.backend.deps import get_generator
    from insight_aitest.modules.testcase.backend.persistence.models import (
        CaseStatus, CaseType, TestCase, TestType)
    fake_gen = MagicMock()
    fake_gen.generate.return_value = TestCase(
        title="x", type=CaseType.FUNCTIONAL, test_design=TestType.POSITIVE,
        status=CaseStatus.DRAFT, content={"steps": []}, source="ai:t")
    app.dependency_overrides[get_generator] = lambda: fake_gen
    r = c.post("/api/modules/testcase/testcases/generate", json={
        "point": {"id": "tp-1", "summary": "s", "suggested_type": "functional",
                  "suggested_design": "positive", "rationale": "r"}})
    assert r.status_code == 201
    assert r.headers.get("Deprecation") == "true"
    assert "/api/modules/ai/tasks/quick" in r.headers.get("Link", "")

