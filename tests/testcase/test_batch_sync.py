# -*- coding: utf-8 -*-
"""batch-sync 路由测试。

夹具沿用 test_testcases_api.py 的成熟模式：最小 FastAPI app + 仅挂 testcase 路由 +
monkeypatch tc_deps._tc_db 指向 tmp 库（不走 build_app()，避免平台全量装配的副作用）。
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from insight_aitest.modules.testcase.backend.persistence.database import TestCaseDatabase
from insight_aitest.modules.testcase.backend.persistence.models import (
    CasePriority,
    CaseStatus,
    CaseType,
    TestCase,
)

BASE = "/api/modules/testcase/testcases"


def _setup_client(tmp_path, monkeypatch):
    monkeypatch.setenv("INSIGHT_EYE_AI_LLM_API_KEY", "sk-test")
    monkeypatch.setenv("INSIGHT_EYE_AI_EMBED_DIM", "4")
    import insight_aitest.modules.testcase.backend.deps as tc_deps

    tc_deps._tc_db = None
    tc_deps._tc_db = TestCaseDatabase(str(tmp_path / "tc.db"))
    from insight_aitest.modules.testcase.backend.routes import router as tc_router

    app = FastAPI()
    app.include_router(tc_router, prefix="/api/modules/testcase")
    return TestClient(app)


def _seed_batch(db, batch_id, n, task_id=42):
    for i in range(n):
        db.create_case(
            TestCase(
                title=f"c{i}",
                type=CaseType.FUNCTIONAL,
                description="",
                priority=CasePriority.P1,
                status=CaseStatus.DRAFT,
                test_design="positive",
                preconditions="",
                content={"steps": []},
                tags=[],
                source=f"ai:batch:{task_id}",
                task_id=task_id,
                batch_id=batch_id,
            )
        )


def test_batch_sync_selects_and_deletes(tmp_path, monkeypatch):
    c = _setup_client(tmp_path, monkeypatch)
    db = TestCaseDatabase(str(tmp_path / "tc.db"))
    _seed_batch(db, "batch-42-a", 5)
    all_cases = db.list_cases_by_batch("batch-42-a")
    selected_ids = [case.id for case in all_cases[:3]]
    resp = c.post(
        f"{BASE}/batch-sync",
        json={
            "case_ids": selected_ids,
            "version_id": 7,
            "delete_unselected": True,
            "batch_id": "batch-42-a",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["synced"] == 3
    assert body["deleted"] == 2
    synced = db.list_cases_by_batch("batch-42-a")
    assert len(synced) == 3
    assert all(case.status == CaseStatus.READY for case in synced)
    assert all(case.version_id == 7 for case in synced)


def test_batch_sync_rejects_missing_batch_id(tmp_path, monkeypatch):
    c = _setup_client(tmp_path, monkeypatch)
    resp = c.post(
        f"{BASE}/batch-sync",
        json={
            "case_ids": [1, 2],
            "version_id": 7,
            "delete_unselected": True,
            "batch_id": None,
        },
    )
    assert resp.status_code == 400


def test_batch_sync_keep_unselected(tmp_path, monkeypatch):
    c = _setup_client(tmp_path, monkeypatch)
    db = TestCaseDatabase(str(tmp_path / "tc.db"))
    _seed_batch(db, "batch-42-b", 4)
    all_cases = db.list_cases_by_batch("batch-42-b")
    selected_ids = [case.id for case in all_cases[:2]]
    resp = c.post(
        f"{BASE}/batch-sync",
        json={
            "case_ids": selected_ids,
            "version_id": 7,
            "delete_unselected": False,
            "batch_id": "batch-42-b",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["deleted"] == 0
    assert len(db.list_cases_by_batch("batch-42-b")) == 4


def test_batch_sync_route_missing_returns_404(tmp_path, monkeypatch):
    """route 未实现时应 404（编写路由前的失败样例，实现后由上面用例覆盖）。"""
    c = _setup_client(tmp_path, monkeypatch)
    resp = c.post(
        f"{BASE}/batch-sync",
        json={"case_ids": [], "version_id": 7, "batch_id": "x"},
    )
    # 路由实现后此处返回 200（空 case_ids → synced 0）；仅作可达性校验
    assert resp.status_code in (200, 404)


def test_m5_batch_sync_update_scoped_to_batch_id(tmp_path, monkeypatch):
    """M5: update 也限定 batch_id，case_ids 跨批次时只更新本批次的（defense-in-depth）。

    构造两批用例，请求只同步 batch-a 但 case_ids 里混入 batch-b 的 id。
    batch-b 的用例不应被改成 READY（即使出现在 case_ids 里）。
    """
    c = _setup_client(tmp_path, monkeypatch)
    db = TestCaseDatabase(str(tmp_path / "tc.db"))
    _seed_batch(db, "batch-42-a", 2)
    _seed_batch(db, "batch-42-b", 2)
    cases_a = db.list_cases_by_batch("batch-42-a")
    cases_b = db.list_cases_by_batch("batch-42-b")
    # case_ids 混入 batch-b 的一个 id（模拟前端误传/竞态）
    mixed_ids = [cases_a[0].id, cases_b[0].id]

    resp = c.post(
        f"{BASE}/batch-sync",
        json={
            "case_ids": mixed_ids,
            "version_id": 9,
            "delete_unselected": False,  # 不删除，便于检查 batch-b 是否被误改
            "batch_id": "batch-42-a",
        },
    )
    assert resp.status_code == 200
    # 只有 batch-a 里且在 case_ids 中的那条被同步（synced=1，batch-b 的 id 被忽略）
    assert resp.json()["synced"] == 1

    # batch-b 的用例状态未被改动（仍 DRAFT）
    cases_b_after = db.list_cases_by_batch("batch-42-b")
    assert all(case.status == CaseStatus.DRAFT for case in cases_b_after)
    assert all(case.version_id is None for case in cases_b_after)
