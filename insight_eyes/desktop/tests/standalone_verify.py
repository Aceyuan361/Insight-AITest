# -*- coding: utf-8 -*-
"""
Insight-Eye 独立集成验证脚本
直接导入模块文件，避免包级别的依赖

Author: Standalone Verification Script
Date: 2025-01-13
"""

import sys
import os

# 直接添加模块路径
desktop_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, desktop_path)

# 导入核心模块（直接导入文件，避免包导入）
import importlib.util

# 动态导入 models
models_path = os.path.join(desktop_path, 'core', 'models.py')
spec_models = importlib.util.spec_from_file_location("models", models_path)
models = importlib.util.module_from_spec(spec_models)
spec_models.loader.exec_module(models)

# 动态导入 database
database_path = os.path.join(desktop_path, 'data', 'database.py')
spec_database = importlib.util.spec_from_file_location("database", database_path)
database = importlib.util.module_from_spec(spec_database)
spec_database.loader.exec_module(database)

# 获取类引用
DeviceInfo = models.DeviceInfo
AppInfo = models.AppInfo
Platform = models.Platform
DeviceStatus = models.DeviceStatus
AppStatus = models.AppStatus
DeviceFilter = models.DeviceFilter
AppFilter = models.AppFilter
DatabaseManager = database.DatabaseManager

from datetime import datetime


def print_section(title):
    """打印分节标题"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)


def test_data_models():
    """测试数据模型"""
    print_section("测试1: 数据模型")

    try:
        # 创建设备信息
        device = DeviceInfo(
            device_id="test_device_001",
            name="Test Android Device",
            platform=Platform.ANDROID,
            model="Pixel 5",
            os_version="11.0",
            battery_level=85,
            status=DeviceStatus.CONNECTED
        )

        # 创建应用信息
        app = AppInfo(
            package_name="com.test.app",
            app_name="Test Application",
            is_running=True,
            status=AppStatus.RUNNING,
            pid=12345,
            uid=10001
        )

        # 添加应用到设备
        device.add_app(app)

        # 验证数据
        assert device.device_id == "test_device_001"
        assert device.platform == Platform.ANDROID
        assert len(device.apps) == 1
        assert device.find_app_by_package("com.test.app") is not None

        # 测试过滤
        running_apps = device.get_running_apps()
        assert len(running_apps) == 1

        print("✓ 数据模型创建成功")
        print(f"  设备: {device.name} ({device.platform.value})")
        print(f"  应用: {app.app_name} - {app.status.value}")
        return True

    except Exception as e:
        print(f"✗ 数据模型测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_integration():
    """测试数据库集成"""
    print_section("测试2: 数据库集成")

    try:
        # 使用内存数据库
        db = DatabaseManager(db_path=":memory:")

        # 测试设备CRUD
        print("\n[设备管理]")
        rowcount = db.upsert_device(
            device_id="android_001",
            name="Android Phone",
            platform="android",
            model="Pixel 5",
            os_version="11.0"
        )
        assert rowcount > 0
        print("  ✓ 设备插入成功")

        device = db.get_device("android_001")
        assert device is not None
        assert device['name'] == "Android Phone"
        print(f"  ✓ 设备查询成功: {device['name']}")

        # 测试应用管理
        print("\n[应用管理]")
        app_id = db.upsert_app(
            device_id="android_001",
            package_name="com.test.app",
            app_name="Test App"
        )
        assert app_id > 0
        print("  ✓ 应用插入成功")

        apps = db.get_apps_by_device("android_001")
        assert len(apps) > 0
        print(f"  ✓ 查询到 {len(apps)} 个应用")

        # 测试监控会话
        print("\n[监控会话]")
        session_id = db.create_session(
            device_id="android_001",
            package_name="com.test.app",
            sample_interval=1000,
            tags={"scenario": "verification_test"}
        )
        assert session_id > 0
        print(f"  ✓ 创建会话: ID={session_id}")

        session = db.get_session(session_id)
        assert session is not None
        assert session['device_id'] == "android_001"
        print(f"  ✓ 会话查询成功: {session['package_name']}")

        # 测试指标存储
        print("\n[指标存储]")
        for i in range(5):
            metrics = {
                'cpu_app': 30.0 + i * 5,
                'cpu_system': 15.0,
                'memory_app_private': 150.0 + i * 10,
                'memory_pss': 200.0,
                'memory_vss': 300.0,
                'fps': 60.0 - i,
                'fps_jank_count': i,
                'network_up_speed': 100.0,
                'network_down_speed': 500.0,
                'battery_level': 85,
                'battery_temp': 35.0,
                'device_temp': 36.0,
                'network_type': 'WIFI'
            }
            metric_id = db.save_metrics(session_id, metrics)
            assert metric_id > 0

        print("  ✓ 保存 5 条指标记录")

        # 查询指标
        retrieved_metrics = db.get_metrics(session_id)
        assert len(retrieved_metrics) == 5
        print(f"  ✓ 查询到 {len(retrieved_metrics)} 条指标")

        # 测试告警
        print("\n[告警管理]")
        alert = {
            'alert_type': 'high_cpu',
            'metric_name': 'cpu_app',
            'current_value': 95.0,
            'threshold_value': 80.0,
            'severity': 'critical',
            'description': 'CPU使用率过高'
        }
        alert_id = db.save_alert(session_id, alert)
        assert alert_id > 0
        print(f"  ✓ 保存告警: {alert['alert_type']}")

        alerts = db.get_alerts(session_id=session_id)
        assert len(alerts) > 0
        print(f"  ✓ 查询到 {len(alerts)} 条告警")

        # 结束会话
        db.end_session(session_id)
        session = db.get_session(session_id)
        assert session['end_time'] is not None
        print("  ✓ 会话已结束")

        # 获取统计信息
        stats = db.get_database_stats()
        print(f"\n[数据库统计]")
        print(f"  设备数: {stats['devices_count']}")
        print(f"  应用数: {stats['apps_count']}")
        print(f"  会话数: {stats['monitoring_sessions_count']}")
        print(f"  指标数: {stats['performance_metrics_count']}")
        print(f"  告警数: {stats['alerts_count']}")

        db.close()
        print("\n✓ 数据库集成测试通过")
        return True

    except Exception as e:
        print(f"\n✗ 数据库集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_filter_functionality():
    """测试过滤功能"""
    print_section("测试3: 过滤功能")

    try:
        # 创建测试设备
        devices = [
            DeviceInfo(
                device_id="android_1",
                name="Pixel 5",
                platform=Platform.ANDROID,
                model="Pixel 5",
                os_version="11.0",
                status=DeviceStatus.CONNECTED
            ),
            DeviceInfo(
                device_id="android_2",
                name="Samsung Galaxy",
                platform=Platform.ANDROID,
                model="Galaxy S21",
                os_version="10.0",
                status=DeviceStatus.OFFLINE
            ),
            DeviceInfo(
                device_id="ios_1",
                name="iPhone 12",
                platform=Platform.IOS,
                model="iPhone 12",
                os_version="14.0",
                status=DeviceStatus.CONNECTED
            )
        ]

        # 添加应用到设备
        for device in devices:
            app1 = AppInfo(
                package_name=f"com.{device.device_id}.app1",
                app_name="Running App",
                is_running=True,
                status=AppStatus.RUNNING
            )
            app2 = AppInfo(
                package_name=f"com.{device.device_id}.app2",
                app_name="Stopped App",
                is_running=False,
                status=AppStatus.STOPPED
            )
            device.add_app(app1)
            device.add_app(app2)

        print("\n[设备过滤]")

        # 平台过滤
        android_filter = DeviceFilter(platform=Platform.ANDROID)
        android_devices = [d for d in devices if android_filter.matches(d)]
        assert len(android_devices) == 2
        print(f"  ✓ 平台过滤 (Android): {len(android_devices)} 个设备")

        # 状态过滤
        online_filter = DeviceFilter(status=DeviceStatus.CONNECTED)
        online_devices = [d for d in devices if online_filter.matches(d)]
        assert len(online_devices) == 2
        print(f"  ✓ 状态过滤 (在线): {len(online_devices)} 个设备")

        # 文本搜索
        search_filter = DeviceFilter(search_text="iPhone")
        search_results = [d for d in devices if search_filter.matches(d)]
        assert len(search_results) == 1
        print(f"  ✓ 文本搜索 ('iPhone'): {len(search_results)} 个设备")

        print("\n[应用过滤]")

        # 运行状态过滤
        running_filter = AppFilter(is_running=True)
        test_device = devices[0]
        running_apps = [a for a in test_device.apps if running_filter.matches(a)]
        assert len(running_apps) == 1
        print(f"  ✓ 运行状态过滤: {len(running_apps)} 个应用")

        # 文本搜索
        search_filter = AppFilter(search_text="Stopped")
        search_results = [a for a in test_device.apps if search_filter.matches(a)]
        assert len(search_results) == 1
        print(f"  ✓ 文本搜索 ('Stopped'): {len(search_results)} 个应用")

        print("\n✓ 过滤功能测试通过")
        return True

    except Exception as e:
        print(f"\n✗ 过滤功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_flow():
    """测试数据流"""
    print_section("测试4: 端到端数据流")

    try:
        db = DatabaseManager(db_path=":memory:")

        # 步骤1: 设备连接
        print("\n[步骤1] 设备连接")
        device = DeviceInfo(
            device_id="flow_test_device",
            name="Flow Test Device",
            platform=Platform.ANDROID,
            model="Test Model",
            os_version="10.0",
            status=DeviceStatus.CONNECTED
        )
        app = AppInfo(
            package_name="com.flow.test",
            app_name="Flow Test App",
            is_running=True
        )
        device.add_app(app)

        db.upsert_device(
            device_id=device.device_id,
            name=device.name,
            platform=device.platform.value.lower(),
            model=device.model,
            os_version=device.os_version
        )
        print(f"  ✓ 设备已连接: {device.name}")

        # 步骤2: 应用发现
        print("\n[步骤2] 应用发现")
        db.upsert_app(
            device_id=device.device_id,
            package_name=app.package_name,
            app_name=app.app_name
        )
        print(f"  ✓ 应用已发现: {app.app_name}")

        # 步骤3: 创建监控会话
        print("\n[步骤3] 创建监控会话")
        session_id = db.create_session(
            device_id=device.device_id,
            package_name=app.package_name,
            sample_interval=1000
        )
        print(f"  ✓ 会话已创建: ID={session_id}")

        # 步骤4: 数据采集和存储
        print("\n[步骤4] 数据采集")
        sample_count = 10
        for i in range(sample_count):
            metrics = {
                'cpu_app': 30.0 + i * 2,
                'cpu_system': 15.0,
                'memory_app_private': 150.0 + i * 5,
                'memory_pss': 200.0,
                'memory_vss': 300.0,
                'fps': 60.0,
                'fps_jank_count': i % 3,
                'network_up_speed': 100.0 + i * 10,
                'network_down_speed': 500.0 + i * 20,
                'battery_level': 85 - i * 0.5,
                'battery_temp': 35.0,
                'device_temp': 36.0,
                'network_type': 'WIFI'
            }
            db.save_metrics(session_id, metrics)

        print(f"  ✓ 已采集 {sample_count} 个样本")

        # 步骤5: 数据查询和验证
        print("\n[步骤5] 数据查询")
        retrieved = db.get_metrics(session_id)
        assert len(retrieved) == sample_count

        # 验证数据趋势
        first_cpu = retrieved[0]['cpu_app']
        last_cpu = retrieved[-1]['cpu_app']
        assert last_cpu > first_cpu  # CPU使用率上升
        print(f"  ✓ 数据验证通过: CPU从{first_cpu}%上升到{last_cpu}%")

        # 步骤6: 告警触发
        print("\n[步骤6] 告警触发")
        high_memory_alert = {
            'alert_type': 'high_memory',
            'metric_name': 'memory_app_private',
            'current_value': 200.0,
            'threshold_value': 180.0,
            'severity': 'warning',
            'description': '内存使用超过阈值'
        }
        db.save_alert(session_id, high_memory_alert)
        alerts = db.get_alerts(session_id=session_id)
        assert len(alerts) > 0
        print(f"  ✓ 触发了 {len(alerts)} 个告警")

        # 步骤7: 数据导出
        print("\n[步骤7] 数据导出")
        recent_sessions = db.get_recent_sessions(limit=10)
        assert len(recent_sessions) > 0
        print(f"  ✓ 导出成功: 找到{len(recent_sessions)}个会话")

        # 步骤8: 结束监控
        print("\n[步骤8] 结束监控")
        db.end_session(session_id)
        session = db.get_session(session_id)
        assert session['end_time'] is not None
        duration = (session['end_time'] - session['start_time']).total_seconds()
        print(f"  ✓ 监控已结束，持续时间: {duration:.1f}秒")

        db.close()
        print("\n✓ 端到端数据流测试通过")
        return True

    except Exception as e:
        print(f"\n✗ 端到端数据流测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_concurrent_sessions():
    """测试并发会话"""
    print_section("测试5: 并发会话管理")

    try:
        db = DatabaseManager(db_path=":memory:")

        # 创建多个设备和会话
        device_count = 3
        session_ids = []

        print(f"\n[创建 {device_count} 个并发会话]")
        for i in range(device_count):
            device_id = f"concurrent_device_{i}"
            package_name = f"com.app{i}"

            # 插入设备
            db.upsert_device(
                device_id=device_id,
                name=f"Device {i}",
                platform="android",
                model=f"Model {i}",
                os_version="10.0"
            )

            # 插入应用
            db.upsert_app(
                device_id=device_id,
                package_name=package_name,
                app_name=f"App {i}"
            )

            # 创建会话
            session_id = db.create_session(
                device_id=device_id,
                package_name=package_name,
                sample_interval=1000
            )
            session_ids.append(session_id)

            # 为每个会话添加指标
            for j in range(5):
                metrics = {
                    'cpu_app': 30.0 + j,
                    'fps': 60.0,
                    'memory_app_private': 150.0
                }
                db.save_metrics(session_id, metrics)

        print(f"  ✓ 创建了 {len(session_ids)} 个会话")

        # 查询所有会话
        all_sessions = db.get_recent_sessions(limit=10)
        assert len(all_sessions) == device_count
        print(f"  ✓ 查询到 {len(all_sessions)} 个会话")

        # 验证每个会话的数据
        print("\n[验证各会话数据]")
        for session_id in session_ids:
            metrics = db.get_metrics(session_id)
            assert len(metrics) == 5
            print(f"  ✓ 会话 {session_id}: {len(metrics)} 条指标")

        db.close()
        print("\n✓ 并发会话管理测试通过")
        return True

    except Exception as e:
        print(f"\n✗ 并发会话管理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_test_report(results):
    """生成测试报告"""
    print_section("集成测试报告")

    total_tests = len(results)
    passed_tests = sum(1 for r in results.values() if r)
    failed_tests = total_tests - passed_tests

    print(f"\n总测试数: {total_tests}")
    print(f"通过: {passed_tests}")
    print(f"失败: {failed_tests}")
    print(f"通过率: {passed_tests/total_tests*100:.1f}%")

    print("\n详细结果:")
    for test_name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {test_name}: {status}")

    if failed_tests == 0:
        print("\n" + "="*60)
        print("  所有集成测试通过! ✓")
        print("="*60)
    else:
        print("\n" + "="*60)
        print(f"  有 {failed_tests} 个测试失败，需要修复")
        print("="*60)

    return failed_tests == 0


def main():
    """主函数"""
    print("\n" + "="*60)
    print("  Insight-Eye 集成验证测试")
    print("  日期:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*60)

    # 运行所有测试
    results = {}

    results["数据模型"] = test_data_models()
    results["数据库集成"] = test_database_integration()
    results["过滤功能"] = test_filter_functionality()
    results["端到端数据流"] = test_data_flow()
    results["并发会话管理"] = test_concurrent_sessions()

    # 生成报告
    success = generate_test_report(results)

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
