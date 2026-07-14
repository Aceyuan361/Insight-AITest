# -*- coding: utf-8 -*-
"""监控持久层 ORM 模型（spec P0-1，platform monitoring）。

DatabaseManager 管的 sessions/metrics/alerts 三张表的 ORM 模型。
业务层 DTO（``platform.services.models.session.Session`` /
``metrics.MetricsData``）保留不变（有 to_dict/from_dict，被 routes/device_manager/base_monitor 深度使用）；
本文件只提供持久化用的 ORM 行模型，DatabaseManager 负责 ORM Row ↔ DTO 的转换。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Text,
)
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from insight_aitest.platform.persistence import Base


class _Platform(str, Enum):
    ANDROID = "android"
    IOS = "ios"


class _Severity(str, Enum):
    WARNING = "warning"
    CRITICAL = "critical"


class SessionRow(MappedAsDataclass, Base, kw_only=True):
    """监控会话表（sessions）的 ORM 行模型。"""

    __tablename__ = "sessions"
    __table_args__ = (Index("idx_sessions_device", "device_id", "start_time"),)

    id: Mapped[int | None] = mapped_column(
        Integer, primary_key=True, autoincrement=True, default=None
    )
    device_id: Mapped[str] = mapped_column(Text)
    app_package: Mapped[str] = mapped_column(Text)
    app_name: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    start_time: Mapped[datetime] = mapped_column(DateTime, default_factory=datetime.now)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    status: Mapped[str] = mapped_column(Text, default="running")
    duration: Mapped[int] = mapped_column(Integer, default=0)
    # platform CHECK 约束保留（android/ios）；存 .value TEXT
    platform: Mapped[str] = mapped_column(Text)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    sampling_interval: Mapped[int] = mapped_column(Integer, default=1000)
    project_id: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)


class MetricsRow(MappedAsDataclass, Base, kw_only=True):
    """性能指标表（metrics）的 ORM 行模型。"""

    __tablename__ = "metrics"
    __table_args__ = (Index("idx_metrics_session", "session_id", "timestamp"),)

    id: Mapped[int | None] = mapped_column(
        Integer, primary_key=True, autoincrement=True, default=None
    )
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default_factory=datetime.now)
    cpu: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    memory: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    fps: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    network_up: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    network_down: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    battery_level: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)


class AlertRow(MappedAsDataclass, Base, kw_only=True):
    """异常告警表（alerts）的 ORM 行模型。"""

    __tablename__ = "alerts"
    __table_args__ = (
        Index("idx_alerts_session_time", "session_id", "timestamp"),
        Index("idx_alerts_type", "alert_type", "timestamp"),
    )

    id: Mapped[int | None] = mapped_column(
        Integer, primary_key=True, autoincrement=True, default=None
    )
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default_factory=datetime.now)
    alert_type: Mapped[str] = mapped_column(Text)
    metric_name: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    current_value: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    threshold_value: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    # severity CHECK 约束（warning/critical）由 SAEnum 体现；存 .value TEXT
    severity: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    description: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    resolved: Mapped[int] = mapped_column(Integer, default=0)  # BOOLEAN 存 0/1
