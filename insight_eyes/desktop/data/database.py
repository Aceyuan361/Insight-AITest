"""
SQLite数据库管理器
负责数据库初始化、连接管理、数据存储和查询
"""
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from contextlib import contextmanager
import json
import os
from logzero import logger


class DatabaseManager:
    """SQLite数据库管理器 - 线程安全的数据库操作

    使用双重检查锁定模式（Double-Checked Locking）实现单例：
    - Python GIL 保证对象引用读取的原子性
    - 使用 Lock 保护实例创建过程
    - 使用 threading.local() 为每个线程提供独立的数据库连接

    注意：首次创建时指定的 db_path 将被记住，后续调用使用不同路径将忽略
    """

    # 单例模式
    _instance = None
    _lock = threading.Lock()
    _db_path_cached = None  # 缓存首次创建时使用的 db_path

    def __new__(cls, db_path: str = None):
        """实现单例模式，确保全局只有一个数据库管理器实例

        使用双重检查锁定模式：
        1. 快速检查（无锁）：如果实例已存在，直接返回
        2. 锁保护检查：在锁内再次检查，防止竞态条件
        3. 创建实例：仅在首次调用时创建

        Args:
            db_path: 数据库文件路径（仅首次调用有效）

        Returns:
            DatabaseManager: 单例实例
        """
        # 快速路径：实例已存在
        if cls._instance is not None:
            return cls._instance

        # 慢速路径：需要创建实例
        with cls._lock:
            # 双重检查：可能在等待锁时已被其他线程创建
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                # 缓存 db_path
                if db_path:
                    cls._db_path_cached = db_path
            return cls._instance

    def __init__(self, db_path: str = None):
        """
        初始化数据库管理器（线程安全）

        注意：由于单例模式，初始化只会在首次调用时执行。
        如果提供了不同的 db_path，将使用首次创建时的路径。

        Args:
            db_path: 数据库文件路径，默认为应用数据目录下的insight_eye.db
        """
        # 检查是否已初始化（防止重复初始化）
        if hasattr(self, '_initialized') and self._initialized:
            return

        # 使用首次创建时缓存的 db_path，如果没有则使用参数或默认值
        actual_db_path = self._db_path_cached or db_path
        if actual_db_path is None:
            # 默认数据库路径
            app_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            actual_db_path = os.path.join(app_dir, 'data', 'insight_eye.db')

        # 确保数据目录存在
        os.makedirs(os.path.dirname(actual_db_path), exist_ok=True)

        self.db_path = actual_db_path
        self._local = threading.local()
        self._initialized = True

        # 初始化数据库表结构
        self._init_database()

    def get_connection(self) -> sqlite3.Connection:
        """
        获取线程本地的数据库连接

        Returns:
            sqlite3.Connection: 数据库连接对象
        """
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            # 优化SQLite性能
            self._local.conn.execute('PRAGMA journal_mode=WAL')  # 写前日志模式
            self._local.conn.execute('PRAGMA synchronous=NORMAL')  # 平衡模式
            self._local.conn.execute('PRAGMA cache_size=10000')  # 增加缓存
            self._local.conn.execute('PRAGMA temp_store=MEMORY')  # 临时表在内存中
            self._local.conn.row_factory = sqlite3.Row  # 返回字典格式
        return self._local.conn

    @contextmanager
    def transaction(self):
        """
        事务上下文管理器

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

    def _init_database(self):
        """初始化数据库表结构"""
        conn = self.get_connection()

        # 创建设备表
        conn.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                platform TEXT NOT NULL CHECK(platform IN ('android')),
                model TEXT,
                os_version TEXT,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 创建App表
        conn.execute('''
            CREATE TABLE IF NOT EXISTS apps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                package_name TEXT NOT NULL,
                app_name TEXT,
                first_monitored TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(device_id, package_name),
                FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
            )
        ''')

        # 创建监控会话表
        conn.execute('''
            CREATE TABLE IF NOT EXISTS monitoring_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                package_name TEXT NOT NULL,
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP,
                sample_interval INTEGER DEFAULT 1000,
                tags TEXT,
                FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
            )
        ''')

        # 创建性能指标表
        conn.execute('''
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                -- App级指标
                cpu_app REAL,
                cpu_system REAL,
                memory_app_private REAL,
                memory_pss REAL,
                memory_vss REAL,
                fps REAL,
                fps_jank_count INTEGER,
                network_up_speed REAL,
                network_down_speed REAL,
                -- 设备级指标
                battery_level REAL,
                battery_temp REAL,
                device_temp REAL,
                network_type TEXT,
                FOREIGN KEY (session_id) REFERENCES monitoring_sessions(id) ON DELETE CASCADE
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
                FOREIGN KEY (session_id) REFERENCES monitoring_sessions(id) ON DELETE CASCADE
            )
        ''')

        # 创建配置模板表
        conn.execute('''
            CREATE TABLE IF NOT EXISTS config_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                config_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        ''')

        # 创建索引以优化查询性能
        self._create_indexes()

        conn.commit()

    def _create_indexes(self):
        """创建数据库索引以提升查询性能"""
        conn = self.get_connection()

        # 性能指标表索引
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_metrics_session_time
            ON performance_metrics(session_id, timestamp DESC)
        ''')

        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_metrics_timestamp
            ON performance_metrics(timestamp DESC)
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

        # 会话表索引
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_sessions_device_time
            ON monitoring_sessions(device_id, start_time DESC)
        ''')

        conn.commit()

    # ==================== 设备管理 ====================

    def upsert_device(self, device_id: str, name: str, platform: str,
                      model: str = None, os_version: str = None) -> int:
        """
        插入或更新设备信息

        Args:
            device_id: 设备ID
            name: 设备名称
            platform: 平台类型 ('android')
            model: 设备型号
            os_version: 系统版本

        Returns:
            受影响的行数
        """
        with self.transaction() as conn:
            cursor = conn.execute('''
                INSERT INTO devices (device_id, name, platform, model, os_version, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(device_id) DO UPDATE SET
                    name = excluded.name,
                    model = excluded.model,
                    os_version = excluded.os_version,
                    last_seen = CURRENT_TIMESTAMP
            ''', (device_id, name, platform, model, os_version))
            return cursor.rowcount

    def get_device(self, device_id: str) -> Optional[Dict]:
        """
        获取设备信息

        Args:
            device_id: 设备ID

        Returns:
            设备信息字典，如果不存在则返回None
        """
        conn = self.get_connection()
        cursor = conn.execute(
            'SELECT * FROM devices WHERE device_id = ?',
            (device_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_devices(self) -> List[Dict]:
        """
        获取所有设备列表

        Returns:
            设备列表
        """
        conn = self.get_connection()
        cursor = conn.execute('SELECT * FROM devices ORDER BY last_seen DESC')
        return [dict(row) for row in cursor.fetchall()]

    # ==================== App管理 ====================

    def upsert_app(self, device_id: str, package_name: str, app_name: str = None) -> int:
        """
        插入或更新App信息

        Args:
            device_id: 设备ID
            package_name: 包名
            app_name: App名称

        Returns:
            App的ID
        """
        with self.transaction() as conn:
            cursor = conn.execute('''
                INSERT INTO apps (device_id, package_name, app_name, first_monitored)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(device_id, package_name) DO UPDATE SET
                    app_name = excluded.app_name
                RETURNING id
            ''', (device_id, package_name, app_name))
            return cursor.fetchone()[0]

    def get_apps_by_device(self, device_id: str) -> List[Dict]:
        """
        获取设备上的所有App

        Args:
            device_id: 设备ID

        Returns:
            App列表
        """
        conn = self.get_connection()
        cursor = conn.execute(
            'SELECT * FROM apps WHERE device_id = ? ORDER BY first_monitored DESC',
            (device_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    # ==================== 监控会话管理 ====================

    def create_session(self, device_id: str, package_name: str,
                       sample_interval: int = 1000, tags: Dict = None) -> int:
        """
        创建新的监控会话

        Args:
            device_id: 设备ID
            package_name: 包名
            sample_interval: 采样间隔(毫秒)
            tags: 测试场景标记

        Returns:
            会话ID
        """
        tags_json = json.dumps(tags) if tags else None
        with self.transaction() as conn:
            cursor = conn.execute('''
                INSERT INTO monitoring_sessions (device_id, package_name, sample_interval, tags, start_time)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (device_id, package_name, sample_interval, tags_json))
            return cursor.lastrowid

    def end_session(self, session_id: int):
        """
        结束监控会话

        Args:
            session_id: 会话ID
        """
        with self.transaction() as conn:
            conn.execute('''
                UPDATE monitoring_sessions
                SET end_time = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (session_id,))

    def get_session(self, session_id: int) -> Optional[Dict]:
        """
        获取会话信息

        Args:
            session_id: 会话ID

        Returns:
            会话信息字典
        """
        conn = self.get_connection()
        cursor = conn.execute('SELECT * FROM monitoring_sessions WHERE id = ?', (session_id,))
        row = cursor.fetchone()
        if row:
            result = dict(row)
            # 解析tags JSON，添加异常处理防止反序列化攻击
            if result.get('tags'):
                try:
                    result['tags'] = json.loads(result['tags'])
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse tags JSON for session {session_id}: {e}")
                    result['tags'] = {}
            return result
        return None

    def get_recent_sessions(self, limit: int = 10, device_id: str = None) -> List[Dict]:
        """
        获取最近的会话列表

        Args:
            limit: 返回数量限制
            device_id: 过滤设备ID

        Returns:
            会话列表
        """
        conn = self.get_connection()
        if device_id:
            cursor = conn.execute('''
                SELECT * FROM monitoring_sessions
                WHERE device_id = ?
                ORDER BY start_time DESC
                LIMIT ?
            ''', (device_id, limit))
        else:
            cursor = conn.execute('''
                SELECT * FROM monitoring_sessions
                ORDER BY start_time DESC
                LIMIT ?
            ''', (limit,))

        results = []
        for row in cursor.fetchall():
            result = dict(row)
            if result.get('tags'):
                try:
                    result['tags'] = json.loads(result['tags'])
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse tags JSON for session: {e}")
                    result['tags'] = {}
            results.append(result)
        return results

    # ==================== 性能指标管理 ====================

    def save_metrics(self, session_id: int, metrics: Dict[str, Any]) -> int:
        """
        保存性能指标数据

        Args:
            session_id: 会话ID
            metrics: 指标数据字典，包含:
                - cpu_app: App CPU使用率
                - cpu_system: 系统CPU使用率
                - memory_app_private: App私有内存(MB)
                - memory_pss: PSS内存(MB)
                - memory_vss: VSS内存(MB)
                - fps: 帧率
                - fps_jank_count: 卡顿次数
                - network_up_speed: 上行速度(KB/s)
                - network_down_speed: 下行速度(KB/s)
                - battery_level: 电池电量(%)
                - battery_temp: 电池温度(°C)
                - device_temp: 设备温度(°C)
                - network_type: 网络类型

        Returns:
            插入记录的ID
        """
        with self.transaction() as conn:
            cursor = conn.execute('''
                INSERT INTO performance_metrics (
                    session_id, cpu_app, cpu_system,
                    memory_app_private, memory_pss, memory_vss,
                    fps, fps_jank_count,
                    network_up_speed, network_down_speed,
                    battery_level, battery_temp, device_temp, network_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_id,
                metrics.get('cpu_app'),
                metrics.get('cpu_system'),
                metrics.get('memory_app_private'),
                metrics.get('memory_pss'),
                metrics.get('memory_vss'),
                metrics.get('fps'),
                metrics.get('fps_jank_count'),
                metrics.get('network_up_speed'),
                metrics.get('network_down_speed'),
                metrics.get('battery_level'),
                metrics.get('battery_temp'),
                metrics.get('device_temp'),
                metrics.get('network_type')
            ))
            return cursor.lastrowid

    def get_metrics(self, session_id: int,
                    start_time: datetime = None,
                    end_time: datetime = None) -> List[Dict]:
        """
        查询指定会话的性能指标数据

        Args:
            session_id: 会话ID
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            指标数据列表
        """
        conn = self.get_connection()
        query = 'SELECT * FROM performance_metrics WHERE session_id = ?'
        params = [session_id]

        if start_time:
            query += ' AND timestamp >= ?'
            params.append(start_time.isoformat())

        if end_time:
            query += ' AND timestamp <= ?'
            params.append(end_time.isoformat())

        query += ' ORDER BY timestamp ASC'

        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_metrics_by_timerange(self, start_time: datetime, end_time: datetime,
                                  device_id: str = None,
                                  package_name: str = None) -> List[Dict]:
        """
        按时间范围查询指标数据

        Args:
            start_time: 开始时间
            end_time: 结束时间
            device_id: 过滤设备ID
            package_name: 过滤包名

        Returns:
            指标数据列表
        """
        conn = self.get_connection()
        query = '''
            SELECT m.* FROM performance_metrics m
            JOIN monitoring_sessions s ON m.session_id = s.id
            WHERE m.timestamp >= ? AND m.timestamp <= ?
        '''
        params = [start_time.isoformat(), end_time.isoformat()]

        if device_id:
            query += ' AND s.device_id = ?'
            params.append(device_id)

        if package_name:
            query += ' AND s.package_name = ?'
            params.append(package_name)

        query += ' ORDER BY m.timestamp ASC'

        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    # ==================== 告警管理 ====================

    def save_alert(self, session_id: int, alert: Dict) -> int:
        """
        保存告警记录

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

    def get_alerts(self, session_id: int = None,
                   alert_type: str = None,
                   severity: str = None,
                   resolved: bool = None,
                   limit: int = None) -> List[Dict]:
        """
        查询告警记录

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

    def resolve_alert(self, alert_id: int):
        """
        标记告警为已解决

        Args:
            alert_id: 告警ID
        """
        with self.transaction() as conn:
            conn.execute('UPDATE alerts SET resolved = 1 WHERE id = ?', (alert_id,))

    # ==================== 配置模板管理 ====================

    def save_template(self, name: str, config: Dict, description: str = None) -> int:
        """
        保存配置模板

        Args:
            name: 模板名称
            config: 配置字典
            description: 模板描述

        Returns:
            模板ID
        """
        config_json = json.dumps(config, ensure_ascii=False, indent=2)
        with self.transaction() as conn:
            cursor = conn.execute('''
                INSERT INTO config_templates (name, config_json, description)
                VALUES (?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    config_json = excluded.config_json,
                    description = excluded.description
                RETURNING id
            ''', (name, config_json, description))
            return cursor.fetchone()[0]

    def get_template(self, name: str) -> Optional[Dict]:
        """
        获取配置模板

        Args:
            name: 模板名称

        Returns:
            模板配置字典
        """
        conn = self.get_connection()
        cursor = conn.execute(
            'SELECT * FROM config_templates WHERE name = ?',
            (name,)
        )
        row = cursor.fetchone()
        if row:
            result = dict(row)
            try:
                result['config'] = json.loads(result['config_json'])
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse config JSON for template {name}: {e}")
                result['config'] = {}
            return result
        return None

    def get_all_templates(self) -> List[Dict]:
        """
        获取所有配置模板

        Returns:
            模板列表
        """
        conn = self.get_connection()
        cursor = conn.execute('SELECT * FROM config_templates ORDER BY created_at DESC')
        results = []
        for row in cursor.fetchall():
            result = dict(row)
            try:
                result['config'] = json.loads(result['config_json'])
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse config JSON for template: {e}")
                result['config'] = {}
            results.append(result)
        return results

    def delete_template(self, name: str) -> bool:
        """
        删除配置模板

        Args:
            name: 模板名称

        Returns:
            是否成功删除
        """
        with self.transaction() as conn:
            cursor = conn.execute(
                'DELETE FROM config_templates WHERE name = ?',
                (name,)
            )
            return cursor.rowcount > 0

    # ==================== 数据维护 ====================

    def cleanup_old_data(self, retention_days: int = 7) -> Dict[str, int]:
        """
        清理过期数据

        Args:
            retention_days: 保留天数，默认7天

        Returns:
            删除统计信息，包含各表删除的记录数
        """
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        cutoff_str = cutoff_date.isoformat()

        stats = {}

        with self.transaction() as conn:
            # 清理性能指标数据（级联删除会关联的告警）
            # 先找出要删除的会话
            cursor = conn.execute('''
                SELECT id FROM monitoring_sessions
                WHERE start_time < ? AND end_time IS NOT NULL
            ''', (cutoff_str,))
            old_sessions = [row[0] for row in cursor.fetchall()]

            # 删除性能指标
            if old_sessions:
                # 使用参数化查询防止SQL注入
                placeholders = ','.join(['?' for _ in old_sessions])

                cursor = conn.execute(
                    f'DELETE FROM performance_metrics WHERE session_id IN ({placeholders})',
                    old_sessions
                )
                stats['metrics_deleted'] = cursor.rowcount

                # 删除告警
                cursor = conn.execute(
                    f'DELETE FROM alerts WHERE session_id IN ({placeholders})',
                    old_sessions
                )
                stats['alerts_deleted'] = cursor.rowcount

                # 删除会话
                cursor = conn.execute(
                    f'DELETE FROM monitoring_sessions WHERE id IN ({placeholders})',
                    old_sessions
                )
                stats['sessions_deleted'] = cursor.rowcount
            else:
                stats['metrics_deleted'] = 0
                stats['alerts_deleted'] = 0
                stats['sessions_deleted'] = 0

        # 执行VACUUM以回收空间
        self.get_connection().execute('VACUUM')

        return stats

    def backup_database(self, backup_path: str) -> bool:
        """
        备份数据库到指定路径

        Args:
            backup_path: 备份文件路径

        Returns:
            是否成功
        """
        try:
            # 确保备份目录存在
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)

            # 使用SQLite的备份API
            source = self.get_connection()
            dest = sqlite3.connect(backup_path)

            source.backup(dest)
            dest.close()
            return True
        except Exception as e:
            print(f"备份数据库失败: {e}")
            return False

    def get_database_stats(self) -> Dict:
        """
        获取数据库统计信息

        Returns:
            统计信息字典
        """
        conn = self.get_connection()
        stats = {}

        # 表记录数统计
        tables = ['devices', 'apps', 'monitoring_sessions',
                 'performance_metrics', 'alerts', 'config_templates']

        for table in tables:
            cursor = conn.execute(f'SELECT COUNT(*) FROM {table}')
            stats[f'{table}_count'] = cursor.fetchone()[0]

        # 数据库大小
        stats['db_size_bytes'] = os.path.getsize(self.db_path)
        stats['db_size_mb'] = stats['db_size_bytes'] / (1024 * 1024)

        # 数据库文件路径
        stats['db_path'] = self.db_path

        return stats

    def cleanup(self):
        """
        清理数据库资源
        关闭所有线程本地的数据库连接
        """
        try:
            self.close()
            logger.info("数据库资源已清理")
        except Exception as e:
            logger.error(f"清理数据库资源时出错: {e}")

    def close(self):
        """关闭数据库连接"""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
