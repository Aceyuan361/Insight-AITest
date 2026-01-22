"""
测试数据库迁移到支持 iOS 平台
"""
import os
import sqlite3
import tempfile
import unittest
import gc
import time
from insight_eyes.desktop.data.database import DatabaseManager
from logzero import logger


class TestIOSPlatformMigration(unittest.TestCase):
    """测试 iOS 平台迁移功能"""

    def setUp(self):
        """每个测试前创建临时数据库"""
        self.temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.db = None
        # 重置单例，确保每个测试使用新的实例
        DatabaseManager._instance = None

    def tearDown(self):
        """每个测试后清理临时数据库"""
        # 关闭数据库连接
        if self.db:
            try:
                self.db.close()
            except:
                pass

        # 重置单例
        DatabaseManager._instance = None
        DatabaseManager._db_path_cached = None

        # 强制垃圾回收，确保所有连接关闭
        gc.collect()

        # Windows 需要等待文件锁释放
        max_retries = 10
        for i in range(max_retries):
            try:
                if os.path.exists(self.db_path):
                    # 同时删除 WAL 和 SHM 文件
                    for ext in ['', '-wal', '-shm']:
                        file_path = self.db_path + ext
                        if os.path.exists(file_path):
                            os.remove(file_path)
                break
            except PermissionError:
                if i < max_retries - 1:
                    time.sleep(0.2)
                    gc.collect()
                else:
                    # 最后一次尝试失败，忽略错误
                    logger.warning(f"无法删除临时数据库文件: {self.db_path}")

    def _create_old_database(self):
        """创建旧版本数据库（只支持 android）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建旧版本的 devices 表（只有 android 约束）
        cursor.execute('''
            CREATE TABLE devices (
                device_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                platform TEXT NOT NULL CHECK(platform IN ('android')),
                model TEXT,
                os_version TEXT,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 创建其他必要的表（外键依赖）
        cursor.execute('''
            CREATE TABLE apps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                package_name TEXT NOT NULL,
                app_name TEXT,
                first_monitored TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(device_id, package_name),
                FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE monitoring_sessions (
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

        cursor.execute('''
            CREATE TABLE performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                cpu_app REAL,
                cpu_system REAL,
                memory_app_private REAL,
                memory_pss REAL,
                memory_vss REAL,
                fps REAL,
                fps_jank_count INTEGER,
                network_up_speed REAL,
                network_down_speed REAL,
                battery_level REAL,
                battery_temp REAL,
                device_temp REAL,
                network_type TEXT,
                FOREIGN KEY (session_id) REFERENCES monitoring_sessions(id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE alerts (
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

        cursor.execute('''
            CREATE TABLE config_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                config_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        ''')

        # 插入测试数据
        cursor.execute('''
            INSERT INTO devices (device_id, name, platform, model, os_version)
            VALUES ('test-device-001', 'Test Android Device', 'android', 'Pixel 5', '11')
        ''')

        cursor.execute('''
            INSERT INTO devices (device_id, name, platform, model, os_version)
            VALUES ('test-device-002', 'Another Android Device', 'android', 'Samsung S21', '12')
        ''')

        conn.commit()
        conn.close()

    def test_old_database_migration(self):
        """测试从旧数据库迁移到支持 iOS"""
        # 1. 创建旧版本数据库
        self._create_old_database()

        # 2. 验证旧数据库只有 android 约束
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='devices'")
        old_sql = cursor.fetchone()[0]
        conn.close()

        self.assertIn("CHECK(platform IN ('android'))", old_sql)
        self.assertNotIn('ios', old_sql)

        # 3. 初始化 DatabaseManager（应该触发迁移）
        self.db = DatabaseManager(db_path=self.db_path)

        # 4. 验证迁移后的表结构包含 ios
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='devices'")
        new_sql = cursor.fetchone()[0]
        conn.close()

        self.assertIn("CHECK(platform IN ('android', 'ios'))", new_sql)

        # 5. 验证旧数据已恢复
        devices = self.db.get_all_devices()
        self.assertEqual(len(devices), 2)
        self.assertEqual(devices[0]['device_id'], 'test-device-001')
        self.assertEqual(devices[0]['platform'], 'android')
        self.assertEqual(devices[1]['device_id'], 'test-device-002')

        logger.info("旧数据库迁移测试通过")

    def test_new_database_creation(self):
        """测试新创建的数据库直接支持 iOS"""
        # 直接创建新数据库（不存在旧版本）
        self.db = DatabaseManager(db_path=self.db_path)

        # 验证表结构包含 ios
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='devices'")
        result = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(result, "devices 表应该存在")
        sql = result[0]
        self.assertIn("CHECK(platform IN ('android', 'ios'))", sql)

        logger.info("新数据库创建测试通过")

    def test_insert_ios_device(self):
        """测试插入 iOS 设备"""
        self.db = DatabaseManager(db_path=self.db_path)

        # 插入 iOS 设备
        rowcount = self.db.upsert_device(
            device_id='ios-device-001',
            name='Test iPhone',
            platform='ios',
            model='iPhone 13',
            os_version='15.0'
        )

        self.assertEqual(rowcount, 1)

        # 验证设备已插入
        device = self.db.get_device('ios-device-001')
        self.assertIsNotNone(device)
        self.assertEqual(device['platform'], 'ios')
        self.assertEqual(device['model'], 'iPhone 13')

        logger.info("iOS 设备插入测试通过")

    def test_insert_android_device_still_works(self):
        """测试 Android 设备插入仍然正常工作"""
        self.db = DatabaseManager(db_path=self.db_path)

        # 插入 Android 设备
        rowcount = self.db.upsert_device(
            device_id='android-device-001',
            name='Test Android Phone',
            platform='android',
            model='Pixel 6',
            os_version='12'
        )

        self.assertEqual(rowcount, 1)

        # 验证设备已插入
        device = self.db.get_device('android-device-001')
        self.assertIsNotNone(device)
        self.assertEqual(device['platform'], 'android')

        logger.info("Android 设备插入测试通过")

    def test_invalid_platform_rejected(self):
        """测试无效平台被拒绝"""
        self.db = DatabaseManager(db_path=self.db_path)

        # 尝试插入无效平台（应该失败）
        with self.assertRaises(Exception):
            self.db.upsert_device(
                device_id='invalid-device',
                name='Invalid Device',
                platform='windows',  # 无效平台
                model='Test',
                os_version='1.0'
            )

        logger.info("无效平台拒绝测试通过")


if __name__ == '__main__':
    unittest.main()
