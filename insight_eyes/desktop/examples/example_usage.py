"""
性能指标处理与异常检测模块使用示例

本示例演示如何使用analytics模块进行性能监控

注意：本示例使用 Android 平台的数据格式
- appCpuRate: Android 底层返回的字段名
- 桌面层会将其转换为 cpu_app

iOS 平台请参考 IOSAPM 的用法示例
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from insight_eyes.desktop.analytics import (
    MetricsProcessor,
    AnomalyDetector,
    StatisticsAnalyzer,
    CorrelationAnalyzer,
    ThresholdManager
)


def generate_mock_data(fps_value=45.0, memory_mb=200.0, cpu_percent=50.0):
    """生成模拟的原始数据"""
    return {
        'fps': {
            'fps': fps_value,
            'jank': 0 if fps_value > 30 else 2,
            'bigJank': 0 if fps_value > 24 else 1,
            'ftime_avg': 1000.0 / fps_value if fps_value > 0 else 0,
            'ftime_max': 1000.0 / fps_value * 1.5 if fps_value > 0 else 0
        },
        'memory': {
            'totalPass': memory_mb * 1024,
            'nativePass': memory_mb * 512,
            'dalvikPass': memory_mb * 256
        },
        'cpu': {
            'appCpuRate': cpu_percent,
            'sysCpuRate': cpu_percent * 0.6
        },
        'network': {
            'upFlow': 100.0 if cpu_percent < 80 else 0.0,
            'downFlow': 500.0
        }
    }


def main():
    """主函数"""
    print("=" * 60)
    print("性能指标处理与异常检测模块 - 使用示例")
    print("=" * 60)

    # 1. 初始化组件
    print("\n[1] 初始化组件...")

    thresholds = ThresholdManager()
    processor = MetricsProcessor(
        session_id=1,
        device_id='emulator-5554',
        app_id='com.example.app',
        window_size=60,
        threshold_manager=thresholds
    )
    detector = AnomalyDetector(session_id=1, threshold_manager=thresholds)
    stats_analyzer = StatisticsAnalyzer(session_id=1)
    correlation_analyzer = CorrelationAnalyzer(session_id=1)

    print("✓ 组件初始化完成")

    # 2. 自定义阈值
    print("\n[2] 自定义告警阈值...")
    thresholds.update_fps_thresholds(warning_fps=25.0, critical_fps=15.0)
    thresholds.update_memory_thresholds(high_memory_mb=400.0)
    print(f"✓ FPS警告阈值: {thresholds.fps.warning_fps}")
    print(f"✓ FPS严重阈值: {thresholds.fps.critical_fps}")
    print(f"✓ 内存告警阈值: {thresholds.memory.high_memory_mb}MB")

    # 3. 模拟正常数据
    print("\n[3] 处理正常性能数据...")
    for i in range(10):
        raw_data = generate_mock_data(fps_value=55.0, memory_mb=180.0, cpu_percent=35.0)
        metrics = processor.process_raw_data(raw_data)

        if metrics:
            stats_analyzer.add_metrics(metrics)
            correlation_analyzer.add_metrics(metrics)

            alerts = detector.detect_all(metrics)

    print(f"✓ 处理了10个正常数据点")
    print(f"  - 平均FPS: {metrics.fps.fps if metrics.fps else 0:.1f}")
    print(f"  - 内存: {metrics.memory.total_mb if metrics.memory else 0:.1f}MB")
    print(f"  - CPU: {metrics.cpu.app_cpu_percent if metrics.cpu else 0:.1f}%")
    print(f"  - 告警数: {len(metrics.alerts)}")

    # 4. 模拟低FPS场景
    print("\n[4] 模拟低FPS场景...")
    low_fps_data = generate_mock_data(fps_value=22.0, memory_mb=200.0, cpu_percent=65.0)
    low_fps_metrics = processor.process_raw_data(low_fps_data)

    if low_fps_metrics:
        stats_analyzer.add_metrics(low_fps_metrics)
        correlation_analyzer.add_metrics(low_fps_metrics)

        alerts = detector.detect_all(low_fps_metrics)

        print(f"✓ 检测到 {len(alerts)} 个告警:")
        for alert in alerts:
            print(f"  - [{alert.severity.value.upper()}] {alert.message}")

    # 5. 模拟内存泄露场景
    print("\n[5] 模拟内存泄露场景...")
    for i in range(10):
        memory_mb = 200.0 + i * 15.0  # 每次增长15MB
        leak_data = generate_mock_data(fps_value=50.0, memory_mb=memory_mb, cpu_percent=40.0)
        leak_metrics = processor.process_raw_data(leak_data)

        if leak_metrics:
            stats_analyzer.add_metrics(leak_metrics)
            correlation_analyzer.add_metrics(leak_metrics)

            alerts = detector.detect_all(leak_metrics)

            # 检查是否有泄露告警
            leak_alerts = [a for a in alerts if 'leak' in a.alert_type.value.lower()]
            if leak_alerts:
                print(f"✓ 采样点 {i+1}: 检测到内存泄露告警!")
                for alert in leak_alerts:
                    print(f"  - [{alert.severity.value.upper()}] {alert.message}")

    # 6. 模拟高CPU场景
    print("\n[6] 模拟高CPU场景...")
    high_cpu_data = generate_mock_data(fps_value=35.0, memory_mb=250.0, cpu_percent=88.0)
    high_cpu_metrics = processor.process_raw_data(high_cpu_data)

    if high_cpu_metrics:
        stats_analyzer.add_metrics(high_cpu_metrics)
        correlation_analyzer.add_metrics(high_cpu_metrics)

        alerts = detector.detect_all(high_cpu_metrics)

        print(f"✓ 检测到 {len(alerts)} 个告警:")
        for alert in alerts:
            print(f"  - [{alert.severity.value.upper()}] {alert.message}")

    # 7. 生成统计摘要
    print("\n[7] 生成性能统计摘要...")
    summary = stats_analyzer.calculate_session_summary()

    if summary:
        print("✓ 会话摘要:")
        print(f"  - 平均FPS: {summary.avg_fps:.1f}")
        print(f"  - 最低FPS: {summary.min_fps:.1f}")
        print(f"  - FPS P95: {summary.fps_p95:.1f}")
        print(f"  - 卡顿次数: {summary.jank_count}")
        print(f"  - 大卡顿次数: {summary.big_jank_count}")
        print(f"  - 平均内存: {summary.avg_memory_mb:.1f}MB")
        print(f"  - 峰值内存: {summary.peak_memory_mb:.1f}MB")
        print(f"  - 内存增长: {summary.memory_leaked_mb:+.1f}MB")
        print(f"  - 平均CPU: {summary.avg_cpu_percent:.1f}%")
        print(f"  - 峰值CPU: {summary.peak_cpu_percent:.1f}%")
        print(f"  - 告警总数: {summary.alert_count}")
        print(f"    - 严重: {summary.critical_count}")
        print(f"    - 警告: {summary.warning_count}")

    # 8. 计算稳定性评分
    print("\n[8] 计算稳定性评分...")
    scores = stats_analyzer.calculate_stability_score()

    print("✓ 稳定性评分:")
    print(f"  - FPS稳定性: {scores['fps_stability']:.1f}/100")
    print(f"  - 内存稳定性: {scores['memory_stability']:.1f}/100")
    print(f"  - CPU稳定性: {scores['cpu_stability']:.1f}/100")
    print(f"  - 总体稳定性: {scores['overall_stability']:.1f}/100")

    # 9. 关联分析（使用低FPS告警）
    if low_fps_metrics and low_fps_metrics.alerts:
        print("\n[9] 异常关联分析...")
        alert = low_fps_metrics.alerts[0]
        report = correlation_analyzer.generate_anomaly_report(alert)

        print(f"✓ 告警类型: {report['alert_info']['type']}")
        print(f"✓ 告警消息: {report['alert_info']['message']}")

        if 'metrics_at_alert_time' in report.get('context', {}):
            context_metrics = report['context']['metrics_at_alert_time']
            print("✓ 告警时的指标状态:")
            if 'fps' in context_metrics:
                print(f"  - FPS: {context_metrics['fps']['fps']:.1f}")
                print(f"  - 卡顿: {context_metrics['fps']['jank_count']}")
            if 'cpu' in context_metrics:
                print(f"  - CPU: {context_metrics['cpu']['app_cpu_percent']:.1f}%")

        if report.get('recommendations'):
            print("✓ 优化建议:")
            for rec in report['recommendations']:
                print(f"  - [{rec['priority']}] {rec['action']}")

    # 10. 导出数据
    print("\n[10] 导出数据...")
    json_data = stats_analyzer.export_metrics(format='json')
    print(f"✓ 导出JSON数据: {len(json_data)} 字符")

    print("\n" + "=" * 60)
    print("示例运行完成!")
    print("=" * 60)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
