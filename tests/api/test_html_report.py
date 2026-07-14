# -*- coding: utf-8 -*-
"""HTML 报告生成器测试。"""

from __future__ import annotations

from datetime import datetime

from insight_aitest.modules.api.backend.persistence.models import RunRecord, RunStatus, StepResult
from insight_aitest.modules.api.backend.report.html_report import render_run_html


def _sample_run(passed: bool = True) -> RunRecord:
    step = StepResult(
        step_index=0,
        request={"method": "GET", "url": "http://x/api", "headers": {}, "body": None},
        status_code=200,
        response_body={"ok": True},
        response_headers={"content-type": "application/json"},
        elapsed_ms=42,
        assertions=[
            {
                "type": "status",
                "target": "200",
                "expected": "200",
                "actual": "200",
                "passed": True,
            }
        ],
        extracts={"token": "abc"},
        error=None,
        passed=passed,
    )
    now = datetime.now()
    return RunRecord(
        id=1,
        case_id=10,
        case_title="登录接口",
        case_snapshot={},
        status=RunStatus.PASSED if passed else RunStatus.FAILED,
        total_steps=1,
        passed_steps=1 if passed else 0,
        started_at=now,
        finished_at=now,
        duration_ms=42,
        steps=[step],
        error=None,
    )


def test_render_html_contains_basic_info():
    run = _sample_run(passed=True)
    html = render_run_html(run)
    assert "<html" in html.lower()
    assert "登录接口" in html
    assert "passed" in html.lower() or "通过" in html
    assert "GET" in html
    assert "http://x/api" in html
    assert "42" in html  # elapsed_ms


def test_render_html_shows_failed_status():
    run = _sample_run(passed=False)
    html = render_run_html(run)
    assert "failed" in html.lower() or "失败" in html


def test_render_html_shows_step_assertions():
    run = _sample_run(passed=True)
    html = render_run_html(run)
    assert "status" in html  # assertion type
    assert "200" in html


# ===== 端点测试 =====

from fastapi.testclient import TestClient  # noqa: E402

from insight_aitest.platform.kernel import build_app  # noqa: E402


def _ensure_run_in_db(db) -> int:
    """向给定 run db 写入一条记录，返回 run id（让 DB 自增 id，避免硬编码冲突）。"""
    run = _sample_run(passed=True)
    # 不预设 id，由 DB 自增分配
    run.id = None
    return db.create_run(run)


def test_run_report_html_endpoint(tmp_path, monkeypatch):
    """端点：用临时 db 注入，GET 报告返回 text/html。"""
    from insight_aitest.modules.api.backend import deps as api_deps
    from insight_aitest.modules.api.backend.persistence.database import RunDatabase

    test_db = RunDatabase(str(tmp_path / "api.db"))
    monkeypatch.setattr(api_deps, "get_run_db", lambda: test_db)

    app = build_app()
    client = TestClient(app)
    rid = _ensure_run_in_db(test_db)
    resp = client.get(f"/api/modules/api/runs/{rid}/report.html")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert "登录接口" in resp.text


def test_run_report_html_404(tmp_path, monkeypatch):
    """端点：不存在的 run id 返回 404。"""
    from insight_aitest.modules.api.backend import deps as api_deps
    from insight_aitest.modules.api.backend.persistence.database import RunDatabase

    test_db = RunDatabase(str(tmp_path / "api.db"))
    monkeypatch.setattr(api_deps, "get_run_db", lambda: test_db)

    app = build_app()
    client = TestClient(app)
    resp = client.get("/api/modules/api/runs/999999/report.html")
    assert resp.status_code == 404
