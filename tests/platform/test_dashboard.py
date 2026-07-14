# -*- coding: utf-8 -*-
"""仪表盘聚合逻辑单测（纯函数 + _provide 闭包集成）。"""
import datetime
from unittest.mock import MagicMock

from insight_aitest.platform.api.dashboard import (
    _aggregate_executions,
    _run_stats,
    build_dashboard_provider,
)


def test_run_stats_empty():
    assert _run_stats([]) == {"total": 0, "passed": 0, "pass_rate": 0.0, "avg_duration_ms": 0}


def test_run_stats_with_data():
    runs = [
        {"status": "passed", "duration_ms": 100},
        {"status": "failed", "duration_ms": 200},
        {"status": "passed", "duration_ms": 300},
    ]
    s = _run_stats(runs)
    assert s["total"] == 3
    assert s["passed"] == 2
    assert s["pass_rate"] == round(2 / 3, 4)
    assert s["avg_duration_ms"] == 200  # (100+200+300)/3


def test_aggregate_merges_and_sorts_by_time():
    """E/F run 合并后按 started_at 倒序，带 module 标记。"""
    t1 = datetime.datetime(2026, 6, 30, 10)
    t2 = datetime.datetime(2026, 6, 30, 11)
    t3 = datetime.datetime(2026, 6, 30, 12)
    api_runs = [
        {"id": 1, "status": "passed", "started_at": t1, "duration_ms": 100},
        {"id": 2, "status": "failed", "started_at": t3, "duration_ms": 200},
    ]
    ui_runs = [
        {"id": 10, "status": "passed", "started_at": t2, "duration_ms": 50},
    ]
    items = _aggregate_executions(api_runs, ui_runs)
    assert len(items) == 3
    # 按 started_at 倒序：t3 > t2 > t1
    assert items[0]["id"] == 2
    assert items[1]["id"] == 10
    assert items[2]["id"] == 1
    # 带 module 标记
    assert {i["module"] for i in items} == {"api", "ui"}


def test_aggregate_respects_limit():
    """每模块取 limit_each 条。"""
    api_runs = [{"id": i, "started_at": None, "duration_ms": 0} for i in range(50)]
    ui_runs = [{"id": i, "started_at": None, "duration_ms": 0} for i in range(50)]
    items = _aggregate_executions(api_runs, ui_runs, limit_each=5)
    assert len(items) == 10  # 5 + 5


def test_aggregate_with_none_started_at_no_crash():
    """started_at 为 None（混合 datetime/str/None）不应 TypeError。"""
    t = datetime.datetime(2026, 6, 30, 12)
    api_runs = [
        {"id": 1, "status": "passed", "started_at": t},
        {"id": 2, "status": "failed", "started_at": None},  # None
    ]
    items = _aggregate_executions(api_runs, [])
    assert len(items) == 2  # 不抛 TypeError


# ===== _provide 闭包集成测试（mock 各模块 deps）=====


class _FakeCase:
    """模拟 D 的 TestCase（只需 last_result 属性）。"""

    def __init__(self, last_result):
        self.last_result = last_result


class _FakeSession:
    """模拟 B 的 Session（status 是 enum-like，有 .value）。"""

    class _Status:
        def __init__(self, v):
            self.value = v

    def __init__(self, status_str):
        self.status = self._Status(status_str)


def test_provide_aggregates_all_modules(monkeypatch):
    """_provide 闭包：mock 各模块 deps，断言完整聚合结构（含 running session + None started_at）。"""
    # mock api/ui run DB
    import insight_aitest.modules.api.backend.deps as api_deps
    import insight_aitest.modules.ui.backend.deps as ui_deps
    import insight_aitest.modules.testcase.backend.deps as tc_deps

    fake_api_db = MagicMock()
    fake_api_db.list_runs.return_value = [
        {"id": 1, "status": "passed", "duration_ms": 100, "started_at": datetime.datetime(2026, 6, 30, 10)},
    ]
    fake_ui_db = MagicMock()
    fake_ui_db.list_runs.return_value = [
        {"id": 5, "status": "failed", "duration_ms": 200, "started_at": None},
    ]
    fake_tc_db = MagicMock()
    fake_tc_db.list_cases.return_value = [
        _FakeCase("passed"),
        _FakeCase("passed"),
        _FakeCase(None),  # 未执行
    ]
    monkeypatch.setattr(api_deps, "get_run_db", lambda: fake_api_db)
    monkeypatch.setattr(ui_deps, "get_run_db", lambda: fake_ui_db)
    monkeypatch.setattr(tc_deps, "get_tc_db", lambda: fake_tc_db)

    # mock monitoring DatabaseManager.default
    import insight_aitest.platform.api.dashboard as dash_mod

    fake_dm = MagicMock()
    fake_dm.list_sessions.return_value = [
        _FakeSession("running"),
        _FakeSession("completed"),
        _FakeSession("running"),
    ]
    fake_dm_cls = MagicMock()
    fake_dm_cls.default.return_value = fake_dm
    monkeypatch.setattr(dash_mod, "DatabaseManager", fake_dm_cls, raising=False)
    # dashboard.py 在 _provide 内部 import DatabaseManager，需 patch import 源
    import insight_aitest.platform.persistence.database as db_mod

    monkeypatch.setattr(db_mod, "DatabaseManager", fake_dm_cls)

    provider = build_dashboard_provider()
    result = provider()

    # executions 合并 + 按 started_at 排序（None 排末尾）
    assert len(result["executions"]) == 2
    assert result["executions"][0]["id"] == 1  # 有时间的在前
    assert result["executions"][1]["id"] == 5  # None 的在后

    # stats
    assert result["stats"]["api"]["total"] == 1
    assert result["stats"]["api"]["passed"] == 1
    assert result["stats"]["ui"]["total"] == 1
    assert result["stats"]["ui"]["passed"] == 0

    # testcases last_result 分布
    assert result["testcases"]["total"] == 3
    assert result["testcases"]["by_result"]["passed"] == 2
    assert result["testcases"]["by_result"]["not_run"] == 1

    # monitoring：active_sessions 正确统计（修复 enum 比较后）
    assert result["monitoring"]["total_sessions"] == 3
    assert result["monitoring"]["active_sessions"] == 2  # 2 个 running


def test_provide_degrades_on_module_error(monkeypatch):
    """_provide 某模块 DB 异常时，_safe_call 降级，聚合仍返回（不整体崩溃）。"""
    import insight_aitest.modules.api.backend.deps as api_deps
    import insight_aitest.modules.ui.backend.deps as ui_deps
    import insight_aitest.modules.testcase.backend.deps as tc_deps

    monkeypatch.setattr(api_deps, "get_run_db", _raise_runtime)
    monkeypatch.setattr(ui_deps, "get_run_db", lambda: MagicMock(list_runs=MagicMock(return_value=[])))
    monkeypatch.setattr(tc_deps, "get_tc_db", _raise_runtime)

    import insight_aitest.platform.persistence.database as db_mod

    monkeypatch.setattr(db_mod, "DatabaseManager", _raise_runtime_cls)

    provider = build_dashboard_provider()
    result = provider()
    # api/testcases 异常降级为空，不崩溃
    assert result["stats"]["api"]["total"] == 0
    assert result["testcases"]["total"] == 0


def _raise_runtime():
    raise RuntimeError("api db down")


class _raise_runtime_cls:
    @staticmethod
    def default():
        raise RuntimeError("monitoring down")
