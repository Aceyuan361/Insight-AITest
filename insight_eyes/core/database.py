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
                app_name TEXT,
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'running',
                duration INTEGER DEFAULT 0,
                platform TEXT NOT NULL CHECK(platform IN ('android', 'ios')),
                tags TEXT,
                sampling_interval INTEGER DEFAULT 1000
            )
        ''')

        # 如果 app_name 列不存在，添加该列（用于数据库升级）
        try:
            conn.execute('ALTER TABLE sessions ADD COLUMN app_name TEXT')
        except Exception:
            pass  # 列已存在

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

        # 创建异常告警表
        conn.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                alert_type TEXT NOT NULL,
                metric_name TEXT,
                current_value REAL,
                threshold_value REAL,
                severity TEXT CHECK(severity IN ('warning', 'critical')),
                description TEXT,
                resolved BOOLEAN DEFAULT 0,
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

        # 告警表索引
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_alerts_session_time
            ON alerts(session_id, timestamp DESC)
        ''')

        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_alerts_type
            ON alerts(alert_type, timestamp DESC)
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

        # 获取应用友好名称（可选，如果获取失败则使用包名）
        app_name = app_package  # 默认使用包名
        try:
            from insight_eyes.desktop.core.app_enumerator import AppEnumeratorFactory
            from insight_eyes.public.common import Platform

            platform_enum = Platform.ANDROID if platform == 'android' else Platform.IOS
            enumerator = AppEnumeratorFactory.create_enumerator(device_id, platform_enum)
            if enumerator:
                apps = enumerator.enumerate_apps(include_system_apps=False)
                for app in apps:
                    if app.package_name == app_package:
                        app_name = app.app_name
                        break
        except Exception as e:
            logger.debug(f"获取应用名称失败: {e}，使用包名代替")

        with self.transaction() as conn:
            cursor = conn.execute('''
                INSERT INTO sessions (device_id, app_package, app_name, platform, start_time, status, sampling_interval)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (device_id, app_package, app_name, platform, datetime.now().isoformat(), SessionStatus.RUNNING.value, sampling_interval))
            session_id = cursor.lastrowid

        return Session(
            id=session_id,
            device_id=device_id,
            app_package=app_package,
            app_name=app_name,
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

    def delete_session(self, session_id: int) -> bool:
        """删除会话

        Args:
            session_id: 会话ID

        Returns:
            是否成功删除（如果会话不存在返回 False）
        """
        with self.transaction() as conn:
            cursor = conn.execute('DELETE FROM sessions WHERE id = ?', (session_id,))
            # 返回是否删除了行（rowcount > 0 表示找到了并删除了会话）
            return cursor.rowcount > 0

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

    # ==================== 告警管理 ====================

    def save_alert(self, session_id: int, alert: Dict[str, Any]) -> int:
        """保存告警记录

        Args:
            session_id: 会话ID
            alert: 告警数据，包含:
                - alert_type: 告警类型
                - metric_name: 指标名称
                - current_value: 当前值
                - threshold_value: 阈值
                - severity: 严重程度 ('warning' 或 'critical')
                - description: 描述信息

        Returns:
            告警记录ID
        """
        with self.transaction() as conn:
            cursor = conn.execute('''
                INSERT INTO alerts (
                    session_id, alert_type, metric_name,
                    current_value, threshold_value, severity, description
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_id,
                alert.get('alert_type'),
                alert.get('metric_name'),
                alert.get('current_value'),
                alert.get('threshold_value'),
                alert.get('severity'),
                alert.get('description')
            ))
            return cursor.lastrowid

    def get_alerts(
        self,
        session_id: int = None,
        alert_type: str = None,
        severity: str = None,
        resolved: bool = None,
        limit: int = None
    ) -> List[Dict[str, Any]]:
        """查询告警记录

        Args:
            session_id: 会话ID过滤
            alert_type: 告警类型过滤
            severity: 严重程度过滤
            resolved: 是否已解决过滤
            limit: 返回数量限制

        Returns:
            告警记录列表
        """
        conn = self.get_connection()
        query = 'SELECT * FROM alerts WHERE 1=1'
        params = []

        if session_id:
            query += ' AND session_id = ?'
            params.append(session_id)

        if alert_type:
            query += ' AND alert_type = ?'
            params.append(alert_type)

        if severity:
            query += ' AND severity = ?'
            params.append(severity)

        if resolved is not None:
            query += ' AND resolved = ?'
            params.append(1 if resolved else 0)

        query += ' ORDER BY timestamp DESC'

        if limit:
            query += ' LIMIT ?'
            params.append(limit)

        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_session_statistics(self, session_id: int) -> Dict[str, Any]:
        """获取会话的统计数据

        Args:
            session_id: 会话ID

        Returns:
            包含各项指标统计数据的字典，格式为：
            {
                "fps": {"max": 60, "min": 30, "avg": 55.5, "median": 56.0},
                "cpu_app": {"max": 80, "min": 5, "avg": 45.2, "median": 44.0},
                "memory_pss": {"max": 500, "min": 100, "avg": 250.5, "median": 245.0},
                "network_up": {"max": 1000, "min": 0, "avg": 125.5, "median": 100.0},
                "network_down": {"max": 5000, "min": 0, "avg": 1500.5, "median": 1400.0}
            }
        """
        conn = self.get_connection()

        # 获取所有指标数据
        metrics = self.get_metrics(session_id)
        if not metrics:
            return {}

        # 计算统计的辅助函数
        def calculate_stats(values: List[float]) -> Dict[str, float]:
            """计算最大值、最小值、平均值、中位数"""
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
                "count": len(values)
            }

        # 收集各项指标的值
        fps_values = [m["fps"] for m in metrics if m.get("fps") is not None]
        cpu_app_values = [m["cpu_app"] for m in metrics if m.get("cpu_app") is not None]
        memory_pss_values = [m["memory_pss"] for m in metrics if m.get("memory_pss") is not None]
        network_up_values = [m["network_up_speed"] for m in metrics if m.get("network_up_speed") is not None]
        network_down_values = [m["network_down_speed"] for m in metrics if m.get("network_down_speed") is not None]

        # 构建结果
        result = {}

        if fps_values:
            result["fps"] = calculate_stats(fps_values)

        if cpu_app_values:
            result["cpu_app"] = calculate_stats(cpu_app_values)

        if memory_pss_values:
            result["memory_pss"] = calculate_stats(memory_pss_values)

        if network_up_values:
            result["network_up"] = calculate_stats(network_up_values)

        if network_down_values:
            result["network_down"] = calculate_stats(network_down_values)

        return result

    # ==================== 数据维护 ====================

    def close(self) -> None:
        """关闭数据库连接"""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
