"""
数据库存储性能测试
测试大量数据下的查询和导出性能
"""
import sys
import os
import time
import tempfile
import shutil

# 添加项目根目录到路径
current_dir = os.path.dirname(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.insert(0, project_root)

# 直接导入模块
from insight_eyes.desktop.data.database import DatabaseManager
from insight_eyes.desktop.data.repository import MetricsRepository
from insight_eyes.desktop.data.exporter import DataExporter


def test_insert_performance(db, session_id, num_records=1000):
    """测试插入性能"""
    print(f"\n[插入性能测试] 插入 {num_records} 条记录...")

    import random

    start_time = time.time()

    # 批量插入
    for i in range(num_records):
        metrics = {
            'cpu_app': random.uniform(5, 80),
            'cpu_system': random.uniform(2, 30),
            'memory_app_private': random.uniform(50, 300),
            'memory_pss': random.uniform(100, 500),
            'memory_vss': random.uniform(300, 800),
            'fps': random.uniform(30, 60),
            'fps_jank_count': random.randint(0, 20),
            'network_up_speed': random.uniform(0, 200),
            'network_down_speed': random.uniform(0, 1000),
            'battery_level': random.uniform(10, 100),
            'battery_temp': random.uniform(25, 45),
            'device_temp': random.uniform(30, 50),
            'network_type': random.choice(['WIFI', '4G', '5G'])
        }
        db.save_metrics(session_id, metrics)

    elapsed_time = time.time() - start_time

    print(f"  完成！耗时: {elapsed_time:.2f} 秒")
    print(f"  平均速度: {num_records / elapsed_time:.2f} 条/秒")
    print(f"  平均耗时: {elapsed_time / num_records * 1000:.2f} 毫秒/条")

    return elapsed_time


def test_query_performance(db, session_id):
    """测试查询性能"""
    print("\n[查询性能测试]")

    metrics_repo = MetricsRepository(db)

    # 测试 1: 全量查询
    print("  测试1: 全量查询所有指标...")
    start_time = time.time()
    metrics = db.get_metrics(session_id)
    elapsed_time = time.time() - start_time
    print(f"    查询 {len(metrics)} 条记录，耗时: {elapsed_time:.3f} 秒")

    # 测试 2: 时间范围查询
    print("  测试2: 时间范围查询...")
    from datetime import datetime, timedelta
    start_time = time.time()
    end_time = datetime.now()
    start_datetime = end_time - timedelta(hours=1)
    metrics = db.get_metrics(session_id, start_datetime, end_time)
    elapsed_time = time.time() - start_time
    print(f"    查询 {len(metrics)} 条记录，耗时: {elapsed_time:.3f} 秒")

    # 测试 3: 趋势数据查询
    print("  测试3: FPS 趋势查询...")
    start_time = time.time()
    fps_trend = metrics_repo.get_fps_trend(session_id)
    elapsed_time = time.time() - start_time
    print(f"    查询 {len(fps_trend)} 条FPS记录，耗时: {elapsed_time:.3f} 秒")

    # 测试 4: 统计数据计算
    print("  测试4: 统计数据计算...")
    start_time = time.time()
    stats = metrics_repo.get_statistics(session_id)
    elapsed_time = time.time() - start_time
    print(f"    计算统计数据，耗时: {elapsed_time:.3f} 秒")
    print(f"    统计项数量: {len(stats)}")

    # 测试 5: 聚合数据查询
    print("  测试5: 聚合数据查询(60秒间隔)...")
    start_time = time.time()
    aggregated = metrics_repo.get_aggregated_metrics(session_id, interval_seconds=60)
    elapsed_time = time.time() - start_time
    print(f"    查询 {len(aggregated)} 个聚合数据点，耗时: {elapsed_time:.3f} 秒")


def test_export_performance(db, session_id, temp_dir):
    """测试导出性能"""
    print("\n[导出性能测试]")

    exporter = DataExporter(db)

    # 测试 CSV 导出
    print("  测试1: CSV 导出...")
    csv_path = os.path.join(temp_dir, 'perf_test.csv')
    start_time = time.time()
    result = exporter.export_to_csv(session_id, csv_path)
    elapsed_time = time.time() - start_time

    if result:
        file_size = os.path.getsize(csv_path) / 1024  # KB
        print(f"    导出成功！耗时: {elapsed_time:.2f} 秒")
        print(f"    文件大小: {file_size:.2f} KB")
    else:
        print(f"    导出失败")

    # 测试 JSON 导出
    print("  测试2: JSON 导出...")
    json_path = os.path.join(temp_dir, 'perf_test.json')
    start_time = time.time()
    result = exporter.export_to_json(session_id, json_path)
    elapsed_time = time.time() - start_time

    if result:
        file_size = os.path.getsize(json_path) / 1024  # KB
        print(f"    导出成功！耗时: {elapsed_time:.2f} 秒")
        print(f"    文件大小: {file_size:.2f} KB")
    else:
        print(f"    导出失败")

    # 测试报告生成
    print("  测试3: 性能报告生成...")
    start_time = time.time()
    report_path = exporter.generate_report(session_id, temp_dir)
    elapsed_time = time.time() - start_time

    if report_path:
        file_size = os.path.getsize(report_path) / 1024  # KB
        print(f"    报告生成成功！耗时: {elapsed_time:.2f} 秒")
        print(f"    文件大小: {file_size:.2f} KB")
    else:
        print(f"    报告生成失败")


def main():
    """主函数"""
    print("=" * 70)
    print("Insight-Eye 数据库存储性能测试")
    print("=" * 70)

    # 创建临时数据库
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = temp_db.name
    temp_db.close()

    # 重置单例
    DatabaseManager._instance = None

    # 初始化数据库
    print(f"\n初始化临时数据库: {db_path}")
    db = DatabaseManager(db_path)

    # 创建测试数据
    print("\n准备测试环境...")
    db.upsert_device('perf-test-device', 'Performance Test Device', 'android', 'Pixel 6', 'Android 13')
    session_id = db.create_session('perf-test-device', 'com.perf.test', sample_interval=1000)
    print(f"测试会话ID: {session_id}")

    # 创建临时导出目录
    temp_dir = tempfile.mkdtemp()

    try:
        # 1. 插入性能测试
        test_insert_performance(db, session_id, num_records=1000)

        # 2. 查询性能测试
        test_query_performance(db, session_id)

        # 3. 导出性能测试
        test_export_performance(db, session_id, temp_dir)

        # 4. 数据库统计
        print("\n[数据库统计]")
        stats = db.get_database_stats()
        print(f"  总指标记录数: {stats['performance_metrics_count']}")
        print(f"  数据库大小: {stats['db_size_mb']:.2f} MB")
        print(f"  平均每条记录: {stats['db_size_bytes'] / stats['performance_metrics_count']:.2f} 字节")

        print("\n" + "=" * 70)
        print("性能测试完成！")
        print("=" * 70)

        # 性能评级
        print("\n[性能评级]")
        insert_time = test_insert_performance(db, session_id, num_records=100)

        if insert_time < 0.5:
            print("  插入性能: 优秀 ( > 200 条/秒)")
        elif insert_time < 1.0:
            print("  插入性能: 良好 ( > 100 条/秒)")
        else:
            print("  插入性能: 一般")

    finally:
        # 清理临时文件
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        except:
            pass


if __name__ == '__main__':
    main()
