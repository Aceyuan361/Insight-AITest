# -*- coding: utf-8 -*-
"""仪表盘聚合 provider：跨模块汇总执行结果/用例/性能会话。

由 kernel 启动时调用 build_dashboard_provider() 注入到 platform API。
平台层不直接持有各模块 DB，而是通过各模块的 deps 单例取数据后合并。

聚合维度：
- executions: E(API) + F(UI) 最近执行（schema 对称：status/duration_ms/...），带 module 标记
- stats: API/UI 各自的 通过率/总数/平均耗时
- testcases: D 的用例总数 + 按 last_result 分布（pass/fail/blocked/error/未执行）
- monitoring: B 的会话总数 + 活跃（running）会话数
"""

from __future__ import annotations

from typing import Any


def _safe_call(fn, *args, default=None, **kwargs):
    """安全调用：模块缺失或 DB 异常时降级为 default，不阻断聚合。"""
    try:
        return fn(*args, **kwargs)
    except Exception:
        return default


def _status_value(status: Any) -> str:
    """归一化 status：enum 取 .value，str 原样，None 返回空串。"""
    if status is None:
        return ""
    return status.value if hasattr(status, "value") else str(status)


def _aggregate_executions(
    api_runs: list[dict], ui_runs: list[dict], limit_each: int = 20
) -> list[dict]:
    """合并 E/F 的 run 摘要为统一列表，按时间倒序，带 module 标记。"""
    items = []
    for r in api_runs[:limit_each]:
        items.append({**r, "module": "api"})
    for r in ui_runs[:limit_each]:
        items.append({**r, "module": "ui"})

    # started_at 可能是 datetime 对象或 None，归一化为可比较字符串避免 TypeError
    def _sort_key(x: dict) -> str:
        sa = x.get("started_at")
        if sa is None:
            return ""
        return sa.isoformat() if hasattr(sa, "isoformat") else str(sa)

    items.sort(key=_sort_key, reverse=True)
    return items[: (limit_each * 2)]


def _run_stats(runs: list[dict]) -> dict[str, Any]:
    """单模块 run 统计：总数/通过数/通过率/平均耗时。"""
    total = len(runs)
    if total == 0:
        return {"total": 0, "passed": 0, "pass_rate": 0.0, "avg_duration_ms": 0}
    passed = sum(1 for r in runs if r.get("status") == "passed")
    durations = [r.get("duration_ms") or 0 for r in runs]
    return {
        "total": total,
        "passed": passed,
        "pass_rate": round(passed / total, 4),
        "avg_duration_ms": round(sum(durations) / total) if durations else 0,
    }


def build_dashboard_provider():
    """构造仪表盘聚合函数（闭包，由 kernel 调用后注入 set_dashboard_provider）。"""

    def _provide() -> dict[str, Any]:
        # 延迟 import 各模块 deps（避免平台层启动期循环依赖）
        from insight_aitest.modules.api.backend.deps import get_run_db as get_api_db
        from insight_aitest.modules.ui.backend.deps import get_run_db as get_ui_db
        from insight_aitest.modules.testcase.backend.deps import get_tc_db

        # 工厂调用本身可能抛异常（DB 初始化失败/模块缺失），统一用 _safe_call 保护
        def _list_runs(get_db_fn, limit=200):
            db = _safe_call(get_db_fn)
            if db is None:
                return []
            return _safe_call(db.list_runs, limit=limit, default=[]) or []

        api_runs = _list_runs(get_api_db)
        ui_runs = _list_runs(get_ui_db)

        executions = _aggregate_executions(api_runs, ui_runs, limit_each=20)

        # 用例统计（D 的 last_result 分布）
        tc_stats = {"total": 0, "by_result": {}}
        tc_db = _safe_call(get_tc_db)
        cases = _safe_call(tc_db.list_cases, default=[]) if tc_db else []
        tc_stats["total"] = len(cases)
        by_result: dict[str, int] = {}
        for c in cases:
            # last_result 可能为 None（未执行）
            key = getattr(c, "last_result", None) or "not_run"
            by_result[key] = by_result.get(key, 0) + 1
        tc_stats["by_result"] = by_result

        # 性能会话统计（B）
        monitoring = {"total_sessions": 0, "active_sessions": 0}
        try:
            from insight_aitest.platform.persistence.database import DatabaseManager

            dm = _safe_call(DatabaseManager.default)
            if dm is not None:
                sessions = _safe_call(dm.list_sessions, default=[]) or []
                monitoring["total_sessions"] = len(sessions)
                # Session.status 是 SessionStatus enum（list_sessions 构造时 SessionStatus(r.status)），
                # 不能直接 == "running" 比较，取 .value
                monitoring["active_sessions"] = sum(
                    1 for s in sessions if _status_value(getattr(s, "status", None)) == "running"
                )
        except Exception:
            pass  # monitoring 不可用时保持 0

        return {
            "executions": executions,
            "stats": {
                "api": _run_stats(api_runs),
                "ui": _run_stats(ui_runs),
            },
            "testcases": tc_stats,
            "monitoring": monitoring,
        }

    return _provide
