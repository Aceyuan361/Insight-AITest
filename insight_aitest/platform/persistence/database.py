# -*- coding: utf-8 -*-
"""数据库管理器（spec P0-1 ORM 迁移）。

核心层数据库管理，提供统一的数据库操作接口。
P0-1：从裸 sqlite3 + threading.local（单例双重检查锁）迁移到平台 session_scope + ORM。
对外方法签名/返回类型完全不变（业务层 device_manager/performance routes 零改动）。

业务层 DTO（``platform.services.models.session.Session`` / ``metrics.MetricsData``）
保留不变；本类内部用 ORM 行模型（monitoring_models）持久化，负责 Row ↔ DTO 转换。
单例语义保留（device_manager 多处 ``DatabaseManager(db_path)`` 拿同一实例）。
旧库若无 app_name 列，ensure_schema 幂等补列（替代原 _init_database 的 ALTER hack）。
"""

from __future__ import annotations

import threading
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional

if TYPE_CHECKING:
    from insight_aitest.platform.services.models.metrics import MetricsData
    from insight_aitest.platform.services.models.session import Session

from sqlalchemy import select

from insight_aitest.platform.persistence import (
    Base,
    ensure_schema,
    get_engine,
    session_scope,
)
from insight_aitest.platform.persistence.monitoring_models import (
    AlertRow,
    MetricsRow,
    SessionRow,
)


def _ensure_app_name(db_path: str) -> None:
    """增量迁移：给旧 sessions 表补 app_name 列（幂等，替代原 _init_database 的 ALTER hack）。"""
    import sqlite3

    with sqlite3.connect(db_path) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(sessions)")}
        if "app_name" not in cols:
            conn.execute("ALTER TABLE sessions ADD COLUMN app_name TEXT")
        conn.commit()


def _ensure_session_project_column(db_path: str) -> None:
    """增量迁移：给旧 sessions 表补 project_id 列（幂等）。"""
    import sqlite3

    with sqlite3.connect(db_path) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(sessions)")}
        if "project_id" not in cols:
            conn.execute("ALTER TABLE sessions ADD COLUMN project_id INTEGER")
        conn.commit()


class DatabaseManager:
    """数据库管理器 - 线程安全的数据库操作（单例）。

    单例保留：device_manager 多处 ``DatabaseManager(db_path)`` 期望拿同一实例。
    内部已无 sqlite3 连接，改用平台 session_scope（scoped_session 已线程隔离）。
    """

    _instance: Optional["DatabaseManager"] = None
    _lock = threading.Lock()

    def __new__(cls, db_path: Optional[str] = None) -> "DatabaseManager":
        # 双重检查锁单例（保留原语义）
        if cls._instance is not None:
            return cls._instance
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    @classmethod
    def default(cls) -> "DatabaseManager":
        """返回默认 monitoring.db 的单例（收敛 device_manager 散落的硬编码路径）。"""
        import os

        return cls(os.path.join(os.path.expanduser("~"), ".insight_eye", "monitoring.db"))

    def __init__(self, db_path: Optional[str] = None) -> None:
        if getattr(self, "_initialized", False):
            return
        if db_path is None:
            raise ValueError("db_path is required on first initialization")
        self.db_path = db_path
        self._initialized = True
        # 建 ORM 表（IF NOT EXISTS，存量表不动；只建本模块的 3 张表）+ 补增量列
        Base.metadata.create_all(
            get_engine(db_path),
            tables=[SessionRow.__table__, MetricsRow.__table__, AlertRow.__table__],
        )
        ensure_schema(db_path, [_ensure_app_name, _ensure_session_project_column])

    # ==================== 会话管理 ====================

    def create_session(
        self,
        device_id: str,
        app_package: str,
        platform: str = "android",
        tags: Optional[dict[str, Any]] = None,
        sampling_interval: int = 1000,
        project_id: Optional[int] = None,
    ) -> "Session":
        """创建新的监控会话。返回 Session DTO（与原签名一致）。"""
        from insight_aitest.platform.services.models.session import Session, SessionStatus

        if not device_id or not device_id.strip():
            raise ValueError("device_id cannot be empty")
        if not app_package or not app_package.strip():
            raise ValueError("app_package cannot be empty")
        if platform not in ("android", "ios"):
            raise ValueError(f"Invalid platform: {platform}. Must be 'android' or 'ios'")

        # 获取应用友好名称（可选，失败用包名）——保留原行为
        app_name = app_package
        try:
            from insight_aitest.platform.services.device_adapters.app_enumerator import (
                AppEnumeratorFactory,
            )
            from insight_aitest.platform.services.device_common import Platform

            platform_enum = Platform.ANDROID if platform == "android" else Platform.IOS
            enumerator = AppEnumeratorFactory.create_enumerator(device_id, platform_enum)
            if enumerator:
                apps = enumerator.enumerate_apps(include_system_apps=False)
                for app in apps:
                    if app.package_name == app_package:
                        app_name = app.app_name
                        break
        except Exception as e:
            try:
                from logzero import logger

                logger.debug(f"获取应用名称失败: {e}，使用包名代替")
            except Exception:
                pass

        now = datetime.now()
        row = SessionRow(
            device_id=device_id,
            app_package=app_package,
            app_name=app_name,
            platform=platform,
            start_time=now,
            status=SessionStatus.RUNNING.value,
            sampling_interval=sampling_interval,
            project_id=project_id,
        )
        with session_scope(self.db_path) as s:
            s.add(row)
            s.flush()
            session_id = row.id

        return Session(
            id=session_id,
            device_id=device_id,
            app_package=app_package,
            app_name=app_name,
            platform=platform,
            start_time=now,
            status=SessionStatus.RUNNING,
            sampling_interval=sampling_interval,
            project_id=project_id,
        )

    def update_session(self, session_id: int, **kwargs: Any) -> None:
        """更新会话信息（可更新字段：status/end_time/duration）。

        end_time 兼容旧调用方传 isoformat 字符串（device_manager 传字符串），
        这里统一转 datetime（DateTime 列不接受字符串）。
        """
        with session_scope(self.db_path) as s:
            row = s.get(SessionRow, session_id)
            if row is None:
                return
            for key in ("status", "end_time", "duration"):
                if key in kwargs:
                    val = kwargs[key]
                    if key == "end_time" and isinstance(val, str):
                        val = datetime.fromisoformat(val)
                    setattr(row, key, val)

    def get_session(self, session_id: int) -> Optional["Session"]:
        from insight_aitest.platform.services.models.session import Session, SessionStatus

        with session_scope(self.db_path) as s:
            row = s.get(SessionRow, session_id)
            if row is None:
                return None
            return Session(
                id=row.id,
                device_id=row.device_id,
                app_package=row.app_package,
                platform=row.platform,
                start_time=row.start_time,
                end_time=row.end_time,
                status=SessionStatus(row.status),
                duration=row.duration,
                sampling_interval=row.sampling_interval,
                project_id=row.project_id,
            )

    def list_sessions(
        self,
        device_id: Optional[str] = None,
        limit: Optional[int] = None,
        project_id: Optional[int] = None,
    ) -> List["Session"]:
        from insight_aitest.platform.services.models.session import Session, SessionStatus

        stmt = select(SessionRow)
        if device_id:
            stmt = stmt.where(SessionRow.device_id == device_id)
        if project_id is not None:
            stmt = stmt.where(SessionRow.project_id == project_id)
        stmt = stmt.order_by(SessionRow.start_time.desc())
        if limit:
            stmt = stmt.limit(limit)
        with session_scope(self.db_path) as s:
            rows = list(s.scalars(stmt))
        return [
            Session(
                id=r.id,
                device_id=r.device_id,
                app_package=r.app_package,
                platform=r.platform,
                start_time=r.start_time,
                end_time=r.end_time,
                status=SessionStatus(r.status),
                duration=r.duration,
                sampling_interval=r.sampling_interval,
                project_id=r.project_id,
            )
            for r in rows
        ]

    def delete_session(self, session_id: int) -> bool:
        with session_scope(self.db_path) as s:
            row = s.get(SessionRow, session_id)
            if row is None:
                return False
            s.delete(row)
            return True

    def count_sessions_by_project(self, project_id: int | None) -> int:
        """统计某项目下的监控会话数（project_id=None 统计未分类）。"""
        from sqlalchemy import func

        stmt = select(func.count(SessionRow.id))
        if project_id is not None:
            stmt = stmt.where(SessionRow.project_id == project_id)
        else:
            stmt = stmt.where(SessionRow.project_id.is_(None))
        with session_scope(self.db_path) as s:
            return s.scalar(stmt) or 0

    # ==================== 性能指标管理 ====================

    def save_metrics(self, session_id: int, metrics) -> None:
        """保存性能指标数据。metrics: MetricsData DTO。"""
        row = MetricsRow(
            session_id=session_id,
            timestamp=metrics.timestamp,
            cpu=metrics.cpu,
            memory=metrics.memory,
            fps=metrics.fps,
            network_up=metrics.network_up,
            network_down=metrics.network_down,
            battery_level=metrics.battery,
        )
        with session_scope(self.db_path) as s:
            s.add(row)

    def get_metrics(
        self,
        session_id: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List["MetricsData"]:
        from insight_aitest.platform.services.models.metrics import MetricsData

        stmt = select(MetricsRow).where(MetricsRow.session_id == session_id)
        if start_time:
            stmt = stmt.where(MetricsRow.timestamp >= start_time)
        if end_time:
            stmt = stmt.where(MetricsRow.timestamp <= end_time)
        stmt = stmt.order_by(MetricsRow.timestamp.asc())
        with session_scope(self.db_path) as s:
            rows = list(s.scalars(stmt))
        return [
            MetricsData(
                timestamp=r.timestamp,
                cpu=r.cpu,
                memory=r.memory,
                fps=r.fps,
                network_up=r.network_up,
                network_down=r.network_down,
                battery=r.battery_level,
            )
            for r in rows
        ]

    # ==================== 告警管理 ====================

    def save_alert(self, session_id: int, alert: dict[str, Any]) -> int:
        row = AlertRow(
            session_id=session_id,
            alert_type=alert.get("alert_type"),
            metric_name=alert.get("metric_name"),
            current_value=alert.get("current_value"),
            threshold_value=alert.get("threshold_value"),
            severity=alert.get("severity"),
            description=alert.get("description"),
        )
        with session_scope(self.db_path) as s:
            s.add(row)
            s.flush()
            return row.id

    def get_alerts(
        self,
        session_id: int = None,
        alert_type: str = None,
        severity: str = None,
        resolved: bool = None,
        limit: int = None,
    ) -> list[dict[str, Any]]:
        stmt = select(AlertRow)
        if session_id:
            stmt = stmt.where(AlertRow.session_id == session_id)
        if alert_type:
            stmt = stmt.where(AlertRow.alert_type == alert_type)
        if severity:
            stmt = stmt.where(AlertRow.severity == severity)
        if resolved is not None:
            stmt = stmt.where(AlertRow.resolved == (1 if resolved else 0))
        stmt = stmt.order_by(AlertRow.timestamp.desc())
        if limit:
            stmt = stmt.limit(limit)
        with session_scope(self.db_path) as s:
            rows = list(s.scalars(stmt))
        return [
            {
                "id": r.id,
                "session_id": r.session_id,
                "timestamp": r.timestamp,
                "alert_type": r.alert_type,
                "metric_name": r.metric_name,
                "current_value": r.current_value,
                "threshold_value": r.threshold_value,
                "severity": r.severity,
                "description": r.description,
                "resolved": bool(r.resolved),
            }
            for r in rows
        ]

    def get_session_statistics(self, session_id: int) -> dict[str, Any]:
        """获取会话的统计数据。保留原计算逻辑（max/min/avg/median）。"""
        metrics = self.get_metrics(session_id)
        if not metrics:
            return {}

        def calculate_stats(values: list[float]) -> dict[str, float]:
            if not values:
                return {}
            sorted_values = sorted(values)
            n = len(sorted_values)
            mid = n // 2
            if n % 2 == 0:
                median = (sorted_values[mid - 1] + sorted_values[mid]) / 2
            else:
                median = sorted_values[mid]
            return {
                "max": max(values),
                "min": min(values),
                "avg": sum(values) / len(values),
                "median": median,
                "count": len(values),
            }

        # 保留原字段访问语义（MetricsData 属性）
        fps_values = [m.fps for m in metrics if m.fps is not None]
        cpu_values = [m.cpu for m in metrics if m.cpu is not None]
        memory_values = [m.memory for m in metrics if m.memory is not None]
        network_up_values = [m.network_up for m in metrics if m.network_up is not None]
        network_down_values = [m.network_down for m in metrics if m.network_down is not None]

        result: dict[str, Any] = {}
        if fps_values:
            result["fps"] = calculate_stats(fps_values)
        if cpu_values:
            result["cpu_app"] = calculate_stats(cpu_values)
        if memory_values:
            result["memory_pss"] = calculate_stats(memory_values)
        if network_up_values:
            result["network_up"] = calculate_stats(network_up_values)
        if network_down_values:
            result["network_down"] = calculate_stats(network_down_values)
        return result

    # ==================== 数据维护 ====================

    def close(self) -> None:
        """兼容原接口（ORM session 由 session_scope 自管，无需显式关闭）。"""
        pass
