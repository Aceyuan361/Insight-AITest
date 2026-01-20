"""
数据库模块使用示例
演示如何使用数据库管理模块进行数据存储、查询和导出
"""
import sys
import os

# 添加项目根目录到路径
current_dir = os.path.dirname(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.insert(0, project_root)

# 直接导入模块，避免通过 desktop/__init__.py
from insight_eyes.desktop.data.database import DatabaseManager
from insight_eyes.desktop.data.repository import MetricsRepository, AlertRepository, SessionRepository
from insight_eyes.desktop.data.exporter import DataExporter

from datetime import datetime


def main():
    """主函数 - 演示数据库模块的使用"""

    print("=" * 70)
    print("Insight-Eye 数据库模块使用示例")
    print("=" * 70)

    # 1. 初始化数据库
    print("\n[步骤1] 初始化数据库...")
    db = DatabaseManager()
    print(f"数据库路径: {db.db_path}")

    # 2. 添加设备信息
    print("\n[步骤2] 添加设备信息...")
    db.upsert_device(
        device_id='demo-device-001',
        name='Demo Android Device',
        platform='android',
        model='Pixel 6',
        os_version='Android 13'
    )
    print("已添加设备: demo-device-001")

    # 3. 添加应用信息
    print("\n[步骤3] 添加应用信息...")
    db.upsert_app('demo-device-001', 'com.demo.app', 'Demo Application')
    print("已添加应用: com.demo.app")

    # 4. 创建监控会话
    print("\n[步骤4] 创建监控会话...")
    session_id = db.create_session(
        device_id='demo-device-001',
        package_name='com.demo.app',
        sample_interval=1000,
        tags={
            'scenario': 'demo',
            'tester': 'AI Assistant',
            'version': '1.0.0'
        }
    )
    print(f"已创建会话: ID = {session_id}")

    # 5. 保存性能指标数据
    print("\n[步骤5] 保存性能指标数据...")
    import time
    import random

    # 模拟 10 秒的性能监控数据
    for i in range(10):
        metrics = {
            'cpu_app': random.uniform(10, 40),
            'cpu_system': random.uniform(5, 20),
            'memory_app_private': random.uniform(80, 150),
            'memory_pss': random.uniform(150, 250),
            'memory_vss': random.uniform(400, 600),
            'fps': random.uniform(50, 60),
            'fps_jank_count': random.randint(0, 5),
            'network_up_speed': random.uniform(0, 100),
            'network_down_speed': random.uniform(0, 500),
            'battery_level': random.uniform(70, 100),
            'battery_temp': random.uniform(30, 40),
            'device_temp': random.uniform(35, 45),
            'network_type': 'WIFI'
        }
        db.save_metrics(session_id, metrics)

    print(f"已保存 10 条性能指标样本")

    # 6. 生成告警
    print("\n[步骤6] 生成告警记录...")
    alerts = [
        {
            'alert_type': 'high_memory',
            'metric_name': 'memory_pss',
            'current_value': 280,
            'threshold_value': 250,
            'severity': 'warning',
            'description': '内存使用超过阈值'
        },
        {
            'alert_type': 'low_fps',
            'metric_name': 'fps',
            'current_value': 45,
            'threshold_value': 50,
            'severity': 'critical',
            'description': '帧率过低'
        }
    ]

    for alert in alerts:
        db.save_alert(session_id, alert)

    print(f"已生成 {len(alerts)} 条告警记录")

    # 7. 使用数据访问层查询数据
    print("\n[步骤7] 使用数据访问层查询数据...")

    metrics_repo = MetricsRepository(db)
    alert_repo = AlertRepository(db)
    session_repo = SessionRepository(db)

    # 获取 FPS 趋势
    fps_trend = metrics_repo.get_fps_trend(session_id)
    print(f"FPS 趋势数据点数: {len(fps_trend)}")

    # 获取统计数据
    stats = metrics_repo.get_statistics(session_id)
    print(f"\n统计数据:")
    if 'fps' in stats:
        print(f"  FPS 平均值: {stats['fps']['avg']:.2f}")
    if 'memory_pss' in stats:
        print(f"  内存平均值: {stats['memory_pss']['avg']:.2f} MB")
    if 'cpu_app' in stats:
        print(f"  CPU 平均值: {stats['cpu_app']['avg']:.2f}%")

    # 获取告警汇总
    alert_summary = alert_repo.get_alert_summary(session_id)
    print(f"\n告警汇总:")
    print(f"  告警总数: {alert_summary['total_count']}")
    print(f"  按类型: {alert_summary['by_type']}")
    print(f"  按严重程度: {alert_summary['by_severity']}")

    # 获取会话概览
    overview = session_repo.get_session_overview(session_id)
    print(f"\n会话概览:")
    print(f"  设备: {overview['session_info']['device_name']}")
    print(f"  应用: {overview['session_info']['package_name']}")
    print(f"  样本数: {overview['data_summary']['total_samples']}")

    # 8. 数据导出示例
    print("\n[步骤8] 数据导出...")

    exporter = DataExporter(db)

    # 导出为 JSON
    output_dir = os.path.join(project_root, 'exports')
    os.makedirs(output_dir, exist_ok=True)

    json_path = os.path.join(output_dir, 'demo_export.json')
    if exporter.export_to_json(session_id, json_path):
        print(f"JSON 导出成功: {json_path}")

    # 导出为 CSV
    csv_path = os.path.join(output_dir, 'demo_export.csv')
    if exporter.export_to_csv(session_id, csv_path):
        print(f"CSV 导出成功: {csv_path}")

    # 生成测试报告
    report_path = exporter.generate_report(session_id, output_dir)
    if report_path:
        print(f"测试报告生成成功: {report_path}")

    # 9. 配置模板管理
    print("\n[步骤9] 配置模板管理...")

    # 保存模板
    template_config = {
        'devices': ['demo-device-001'],
        'apps': ['com.demo.app'],
        'sample_interval': 1000,
        'thresholds': {
            'memory_pss': 250,
            'fps': 50,
            'cpu_app': 80
        }
    }

    db.save_template(
        name='演示模板',
        config=template_config,
        description='用于演示的配置模板'
    )
    print("已保存配置模板: '演示模板'")

    # 加载模板
    template = db.get_template('演示模板')
    print(f"模板配置: {template['config']}")

    # 10. 结束会话
    print("\n[步骤10] 结束监控会话...")
    db.end_session(session_id)
    print("会话已结束")

    # 11. 显示数据库统计
    print("\n[步骤11] 数据库统计...")
    stats = db.get_database_stats()
    print(f"设备数量: {stats['devices_count']}")
    print(f"应用数量: {stats['apps_count']}")
    print(f"会话数量: {stats['monitoring_sessions_count']}")
    print(f"指标记录数: {stats['performance_metrics_count']}")
    print(f"告警记录数: {stats['alerts_count']}")
    print(f"配置模板数: {stats['config_templates_count']}")
    print(f"数据库大小: {stats['db_size_mb']:.2f} MB")

    print("\n" + "=" * 70)
    print("示例演示完成！")
    print("=" * 70)


if __name__ == '__main__':
    main()
