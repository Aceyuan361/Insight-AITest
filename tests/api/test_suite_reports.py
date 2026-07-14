# -*- coding: utf-8 -*-
"""套件报告（聚合 HTML + JUnit XML）测试。"""

from datetime import datetime

from insight_aitest.modules.api.backend.persistence.models import RunRecord, RunStatus, StepResult
from insight_aitest.modules.api.backend.report.html_report import render_junit_xml, render_suite_html


def _make_run(case_id: int, title: str, status: RunStatus, passed: int, total: int) -> RunRecord:
    return RunRecord(
        id=None,
        case_id=case_id,
        case_title=title,
        case_snapshot={},
        status=status,
        total_steps=total,
        passed_steps=passed,
        started_at=datetime(2026, 7, 9, 10, 0, 0),
        finished_at=datetime(2026, 7, 9, 10, 0, 5),
        duration_ms=5000,
        steps=[
            StepResult(
                step_index=0,
                request={"method": "GET", "url": "/api/test"},
                status_code=200,
                response_body={"ok": True},
                response_headers={},
                elapsed_ms=100,
                assertions=[{"type": "status_code", "expected": 200, "actual": 200, "passed": status == RunStatus.PASSED}],
                extracts={},
                error=None,
                passed=status == RunStatus.PASSED,
            )
        ],
    )


def _make_suite_run_dict(status: str = "completed", total: int = 3) -> dict:
    return {
        "id": 1,
        "suite_id": 10,
        "suite_name": "回归套件",
        "status": status,
        "total": total,
        "done": total,
        "case_run_ids": [101, 102, 103],
        "setup_status": "passed",
        "environment_name": "staging",
        "started_at": "2026-07-09T10:00:00",
        "finished_at": "2026-07-09T10:00:30",
        "error": None,
    }


class TestRenderSuiteHtml:
    def test_basic_render(self):
        runs = [
            _make_run(1, "登录", RunStatus.PASSED, 1, 1),
            _make_run(2, "查询", RunStatus.FAILED, 0, 1),
            _make_run(3, "删除", RunStatus.PASSED, 1, 1),
        ]
        html = render_suite_html(_make_suite_run_dict(), runs)
        assert "回归套件" in html
        assert "登录" in html
        assert "查询" in html
        assert "删除" in html
        assert "套件报告" in html

    def test_empty_runs(self):
        """无子 run 也能渲染。"""
        html = render_suite_html(_make_suite_run_dict(), [])
        assert "回归套件" in html
        assert "通过:</b> 0" in html

    def test_html_escaping(self):
        runs = [_make_run(1, "<script>alert(1)</script>", RunStatus.PASSED, 1, 1)]
        html = render_suite_html(_make_suite_run_dict(total=1), runs)
        assert "<script>" not in html  # 被转义
        assert "&lt;script&gt;" in html


class TestRenderJunitXml:
    def test_basic_xml(self):
        runs = [
            _make_run(1, "登录", RunStatus.PASSED, 1, 1),
            _make_run(2, "查询", RunStatus.FAILED, 0, 1),
        ]
        xml = render_junit_xml(_make_suite_run_dict(total=2), runs)
        assert '<?xml version="1.0" encoding="UTF-8"?>' in xml
        assert '<testsuite' in xml
        assert 'tests="2"' in xml
        assert 'failures="1"' in xml
        assert "登录" in xml
        assert "查询" in xml
        assert "<failure" in xml  # 有失败

    def test_all_passed_no_failure(self):
        runs = [_make_run(1, "OK", RunStatus.PASSED, 1, 1)]
        xml = render_junit_xml(_make_suite_run_dict(total=1), runs)
        assert "<failure" not in xml

    def test_error_case(self):
        runs = [_make_run(1, "出错", RunStatus.ERROR, 0, 1)]
        xml = render_junit_xml(_make_suite_run_dict(total=1), runs)
        assert "<error" in xml
        assert 'errors="1"' in xml

    def test_xml_escaping(self):
        runs = [_make_run(1, '用例&"<>', RunStatus.PASSED, 1, 1)]
        xml = render_junit_xml(_make_suite_run_dict(total=1), runs)
        # XML 特殊字符被转义
        assert "&amp;" in xml
        assert "&lt;" in xml
        assert "&gt;" in xml
        assert "&quot;" in xml
