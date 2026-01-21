"""
数据库初始化脚本
用于创建数据库表结构和初始化数据
"""
import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, project_root)

from insight_eyes.desktop.data import DatabaseManager


def init_database(db_path: str = None):
    """
    初始化数据库

    Args:
        db_path: 数据库文件路径，默认为应用数据目录下的insight_eye.db
    """
    print("=" * 60)
    print("Insight-Eye 数据库初始化")
    print("=" * 60)

    # 创建数据库管理器（会自动初始化表结构）
    db = DatabaseManager(db_path)

    print(f"\n数据库路径: {db.db_path}")
    print("\n数据库表结构:")

    # 检查表是否创建成功
    conn = db.get_connection()
    cursor = conn.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table'
        ORDER BY name
    """)

    tables = cursor.fetchall()
    for table in tables:
        print(f"  [OK] {table[0]}")

    # 检查索引
    cursor = conn.execute("""
        SELECT name FROM sqlite_master
        WHERE type='index'
        AND name LIKE 'idx_%'
        ORDER BY name
    """)

    indexes = cursor.fetchall()
    print(f"\n已创建 {len(indexes)} 个性能优化索引")

    # 显示数据库统计
    stats = db.get_database_stats()
    print("\n数据库统计:")
    for key, value in stats.items():
        if key.endswith('_count'):
            print(f"  {key}: {value}")

    print("\n" + "=" * 60)
    print("数据库初始化完成！")
    print("=" * 60)

    return db


def create_sample_data(db: DatabaseManager):
    """
    创建示例数据用于测试

    Args:
        db: 数据库管理器实例
    """
    print("\n创建示例数据...")

    # 1. 创建测试设备
    db.upsert_device(
        device_id='emulator-5554',
        name='Android Emulator',
        platform='android',
        model='Pixel 5',
        os_version='Android 13'
    )

    print("  [OK] 添加了1个测试设备")

    # 2. 创建测试App
    db.upsert_app('emulator-5554', 'com.example.app', 'Example App')
    db.upsert_app('emulator-5554', 'com.example.game', 'Example Game')

    print("  [OK] 添加了2个测试应用")

    # 3. 创建监控会话
    session_id = db.create_session(
        device_id='emulator-5554',
        package_name='com.example.app',
        sample_interval=1000,
        tags={'scenario': 'performance_test', 'version': '1.0.0'}
    )

    print(f"  [OK] 创建了测试会话 (ID: {session_id})")

    # 4. 添加一些模拟的性能指标数据
    import random
    from datetime import datetime, timedelta

    base_time = datetime.now() - timedelta(minutes=5)

    sample_metrics = [
        {
            'cpu_app': random.uniform(10, 30),
            'cpu_system': random.uniform(5, 15),
            'memory_app_private': random.uniform(80, 120),
            'memory_pss': random.uniform(150, 200),
            'memory_vss': random.uniform(400, 500),
            'fps': random.uniform(55, 60),
            'fps_jank_count': random.randint(0, 3),
            'network_up_speed': random.uniform(0, 100),
            'network_down_speed': random.uniform(0, 500),
            'battery_level': random.uniform(80, 100),
            'battery_temp': random.uniform(30, 40),
            'device_temp': random.uniform(35, 45),
            'network_type': 'WIFI'
        }
        for _ in range(60)  # 60个样本
    ]

    for i, metrics in enumerate(sample_metrics):
        # 修改时间戳
        timestamp = base_time + timedelta(seconds=i)
        db.get_connection().execute(
            "UPDATE performance_metrics SET timestamp = ? WHERE id = ?",
            (timestamp.isoformat(), db.save_metrics(session_id, metrics))
        )

    print(f"  [OK] 添加了 {len(sample_metrics)} 条性能指标样本")

    # 5. 添加一些测试告警
    alerts = [
        {
            'alert_type': 'high_memory',
            'metric_name': 'memory_pss',
            'current_value': 250,
            'threshold_value': 200,
            'severity': 'warning',
            'description': '内存使用超过阈值'
        },
        {
            'alert_type': 'low_fps',
            'metric_name': 'fps',
            'current_value': 45,
            'threshold_value': 50,
            'severity': 'critical',
            'description': '帧率过低，影响用户体验'
        }
    ]

    for alert in alerts:
        db.save_alert(session_id, alert)

    print(f"  [OK] 添加了 {len(alerts)} 条告警记录")

    # 6. 创建配置模板
    sample_template = {
        'devices': ['emulator-5554', 'iphone-test-001'],
        'apps': ['com.example.app'],
        'sample_interval': 1000,
        'thresholds': {
            'memory_pss': 200,
            'fps': 50,
            'cpu_app': 80
        },
        'layout': 'default'
    }

    db.save_template(
        name='测试模板',
        config=sample_template,
        description='用于测试的配置模板'
    )

    print("  [OK] 添加了1个配置模板")

    print("\n示例数据创建完成！")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='Insight-Eye 数据库初始化工具')
    parser.add_argument('--db-path', help='数据库文件路径')
    parser.add_argument('--sample-data', action='store_true',
                       help='创建示例数据')

    args = parser.parse_args()

    # 初始化数据库
    db = init_database(args.db_path)

    # 如果需要，创建示例数据
    if args.sample_data:
        create_sample_data(db)

    # 显示最终统计
    print("\n最终数据库状态:")
    stats = db.get_database_stats()
    print(f"  数据库大小: {stats['db_size_mb']:.2f} MB")
    print(f"  设备数量: {stats['devices_count']}")
    print(f"  应用数量: {stats['apps_count']}")
    print(f"  会话数量: {stats['monitoring_sessions_count']}")
    print(f"  指标记录数: {stats['performance_metrics_count']}")
    print(f"  告警记录数: {stats['alerts_count']}")
    print(f"  配置模板数: {stats['config_templates_count']}")


if __name__ == '__main__':
    main()
