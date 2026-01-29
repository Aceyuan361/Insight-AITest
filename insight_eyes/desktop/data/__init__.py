"""
数据存储管理模块
提供SQLite数据库管理、数据访问和数据导出功能

注意：核心层 (insight_eyes.core) 提供了共享的数据模型和简化的数据库实现。
如果需要与 Web 版共享数据结构，可以从核心层导入：
    from insight_eyes.core.models import Session, Device, MetricsData
    from insight_eyes.core.database import DatabaseManager
"""
from .database import DatabaseManager
from .repository import MetricsRepository, AlertRepository, SessionRepository
from .exporter import DataExporter
from .session_manager import SessionManager

__all__ = [
    'DatabaseManager',
    'MetricsRepository',
    'AlertRepository',
    'SessionRepository',
    'DataExporter',
    'SessionManager'
]
