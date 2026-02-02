# -*- coding: utf-8 -*-
"""
数据库管理器

核心层数据库管理，提供统一的数据库操作接口。
使用 sqlite3 实现线程安全的单例模式。
"""
from __future__ import annotations

import sqlite3
import threading
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
import os


class DatabaseManager:
    """数据库管理器 - 线程安全的数据库操作

    使用双重检查锁定模式（Double-Checked Locking）实现单例：
    - Python GIL 保证对象引用读取的原子性
    - 使用 Lock 保护实例创建过程
    - 使用 threading.local() 为每个线程提供独立的数据库连接
    """

    # 单例模式
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path: Optional[str] = None) -> DatabaseManager:
        """实现单例模式，确保全局只有一个数据库管理器实例

        Args:
            db_path: 数据库文件路径

        Returns:
            DatabaseManager: 单例实例
        """
        if cls._instance is not None:
            return cls._instance

        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(self, db_path: Optional[str] = None):
        """初始化数据库管理器

        Args:
            db_path: 数据库文件路径
        """
        if hasattr(self, '_initialized') and self._initialized:
            return

        if db_path is None:
            raise ValueError("db_path is required on first initialization")

        # 确保数据目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        self.db_path = db_path
        self._local = threading.local()
        self._initialized = True

        # 初始化数据库表结构
        self._init_database()

    def get_connection(self) -> sqlite3.Connection:
        """获取线程本地的数据库连接

        Returns:
            sqlite3.Connection: 数据库连接对象
        """
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False
            )
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    @contextmanager
    def transaction(self) -> Any:
        """事务上下文管理器

        Usage:
            with db.transaction():
                db.execute(...)
        """
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e

    def _init_database(self) -> None:
        """初始化数据库表结构"""
        conn = self.get_connection()

        # 创建监控会话表
        conn.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                app_package TEXT NOT NULL,
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'running',
                duration INTEGER DEFAULT 0,
                platform TEXT NOT NULL CHECK(platform IN ('android', 'ios')),
                tags TEXT,
                sampling_interval INTEGER DEFAULT 1000
            )
        ''')

        # 创建性能指标表
        conn.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                cpu REAL,
                memory REAL,
                fps REAL,
                network_up REAL,
                network_down REAL,
                battery_level REAL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        ''')

        # 创建索引
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_metrics_session
            ON metrics(session_id, timestamp DESC)
        ''')

        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_sessions_device
            ON sessions(device_id, start_time DESC)
        ''')

        conn.commit()

    # ==================== 会话管理 ====================

    def create_session(
        self,
        device_id: str,
        app_package: str,
        platform: str = 'android',
        tags: Optional[Dict[str, Any]] = None,
        sampling_interval: int = 1000
    ) -> Session:
        """创建新的监控会话

        Args:
            device_id: 设备ID
            app_package: 包名或 Bundle ID
            platform: 平台类型 ('android' 或 'ios')
            tags: 测试场景标记
            sampling_interval: 采样间隔（毫秒），默认1000ms

        Returns:
            Session: 会话对象

        Raises:
            ValueError: 如果输入参数无效
        """
        from insight_eyes.core.models.session import Session
        from insight_eyes.core.models.session import SessionStatus

        # 输入验证
        if not device_id or not device_id.strip():
            raise ValueError("device_id cannot be empty")

        if not app_package or not app_package.strip():
            raise ValueError("app_package cannot be empty")

        if platform not in ('android', 'ios'):
            raise ValueError(f"Invalid platform: {platform}. Must be 'android' or 'ios'")

        with self.transaction() as conn:
            cursor = conn.execute('''
                INSERT INTO sessions (device_id, app_package, platform, start_time, status, sampling_interval)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (device_id, app_package, platform, datetime.now().isoformat(), SessionStatus.RUNNING.value, sampling_interval))
            session_id = cursor.lastrowid

        return Session(
            id=session_id,
            device_id=device_id,
            app_package=app_package,
            platform=platform,
            start_time=datetime.now(),
            status=SessionStatus.RUNNING,
            sampling_interval=sampling_interval
        )

    def update_session(self, session_id: int, **kwargs: Any) -> None:
        """更新会话信息

        Args:
            session_id: 会话ID
            **kwargs: 要更新的字段
        """
        with self.transaction() as conn:
            fields = []
            values = []

            for key, value in kwargs.items():
                if key in ['status', 'end_time', 'duration']:
                    fields.append(f"{key} = ?")
                    values.append(value)

            if fields:
                values.append(session_id)
                query = f"UPDATE sessions SET {', '.join(fields)} WHERE id = ?"
                conn.execute(query, values)

    def get_session(self, session_id: int) -> Optional[Session]:
        """获取会话信息

        Args:
            session_id: 会话ID

        Returns:
            Session: 会话对象，如果不存在则返回None
        """
        from insight_eyes.core.models.session import Session
        from insight_eyes.core.models.session import SessionStatus

        conn = self.get_connection()
        cursor = conn.execute('SELECT * FROM sessions WHERE id = ?', (session_id,))
        row = cursor.fetchone()

        if row:
            return Session(
                id=row['id'],
                device_id=row['device_id'],
                app_package=row['app_package'],
                platform=row['platform'],
                start_time=datetime.fromisoformat(row['start_time']),
                end_time=datetime.fromisoformat(row['end_time']) if row['end_time'] else None,
                status=SessionStatus(row['status']),
                duration=row['duration'],
                sampling_interval=row['sampling_interval'] if 'sampling_interval' in row.keys() else 1000
            )
        return None

    def list_sessions(
        self,
        device_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Session]:
        """列出会话

        Args:
            device_id: 过滤设备ID
            limit: 返回数量限制

        Returns:
            会话列表
        """
        from insight_eyes.core.models.session import Session
        from insight_eyes.core.models.session import SessionStatus

        conn = self.get_connection()
        query = 'SELECT * FROM sessions WHERE 1=1'
        params = []

        if device_id:
            query += ' AND device_id = ?'
            params.append(device_id)

        query += ' ORDER BY start_time DESC'

        if limit:
            query += ' LIMIT ?'
            params.append(limit)

        cursor = conn.execute(query, params)
        sessions = []

        for row in cursor.fetchall():
            sessions.append(Session(
                id=row['id'],
                device_id=row['device_id'],
                app_package=row['app_package'],
                platform=row['platform'],
                start_time=datetime.fromisoformat(row['start_time']),
                end_time=datetime.fromisoformat(row['end_time']) if row['end_time'] else None,
                status=SessionStatus(row['status']),
                duration=row['duration'],
                sampling_interval=row['sampling_interval'] if 'sampling_interval' in row.keys() else 1000
            ))

        return sessions

    def delete_session(self, session_id: int) -> None:
        """删除会话

        Args:
            session_id: 会话ID
        """
        with self.transaction() as conn:
            conn.execute('DELETE FROM sessions WHERE id = ?', (session_id,))

    # ==================== 性能指标管理 ====================

    def save_metrics(self, session_id: int, metrics: MetricsData) -> None:
        """保存性能指标数据

        Args:
            session_id: 会话ID
            metrics: 指标数据对象
        """
        with self.transaction() as conn:
            conn.execute('''
                INSERT INTO metrics (
                    session_id, timestamp, cpu, memory, fps,
                    network_up, network_down, battery_level
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_id,
                metrics.timestamp.isoformat(),
                metrics.cpu,
                metrics.memory,
                metrics.fps,
                metrics.network_up,
                metrics.network_down,
                metrics.battery
            ))

    def get_metrics(
        self,
        session_id: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[MetricsData]:
        """查询指定会话的性能指标数据

        Args:
            session_id: 会话ID
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            指标数据列表
        """
        from insight_eyes.core.models.metrics import MetricsData

        conn = self.get_connection()
        query = 'SELECT * FROM metrics WHERE session_id = ?'
        params = [session_id]

        if start_time:
            query += ' AND timestamp >= ?'
            params.append(start_time.isoformat())

        if end_time:
            query += ' AND timestamp <= ?'
            params.append(end_time.isoformat())

        query += ' ORDER BY timestamp ASC'

        cursor = conn.execute(query, params)
        metrics_list = []

        for row in cursor.fetchall():
            metrics_list.append(MetricsData(
                timestamp=datetime.fromisoformat(row['timestamp']),
                cpu=row['cpu'],
                memory=row['memory'],
                fps=row['fps'],
                network_up=row['network_up'],
                network_down=row['network_down'],
                battery=row['battery_level']
            ))

        return metrics_list

    # ==================== 数据维护 ====================

    def close(self) -> None:
        """关闭数据库连接"""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
