# 性能指标处理与异常检测模块

## 模块概述

本模块是 Insight-Eye 性能监控工具的核心分析引擎，负责处理采集到的原始性能数据，检测异常，生成报告，并辅助定位性能问题。

## 核心功能

### 1. 指标数据处理 (MetricsProcessor)

**功能**：
- 接收并清洗原始指标数据
- 计算派生指标（内存增长率、移动平均等）
- 维护滑动窗口用于趋势分析
- 检测数据趋势（上升/下降/波动）

**主要方法**：
```python
processor.process_raw_data(raw_data: dict) -> ProcessedMetrics
```

**处理的数据类型**：
- FPS指标：帧率、卡顿次数、帧时间
- 内存指标：总内存、Native堆、Dalvik堆、增长率
- CPU指标：应用占用率、系统占用率、移动平均
- 网络指标：上行/下行速度、累计流量

### 2. 异常检测 (AnomalyDetector)

**检测规则**：

#### FPS卡顿检测
- 实时FPS < 30 → 警告
- 实时FPS < 20 → 严重
- 帧时间 > 100ms → 大卡顿
- 连续卡顿 → 告警

#### 内存泄露检测
- 5分钟内增长 > 100MB 且无回落 → 疑似泄露
- 10个采样点单调递增 → 泄露风险
- 内存超过500MB → 高内存告警

#### CPU异常检测
- App CPU > 80% → 高CPU警告
- 系统 CPU > 90% → 系统负载过高
- CPU持续 > 60% 超过1分钟 → 性能问题

#### 网络异常检测
- 上行速度为0但下行>0 → 可能上传异常
- 网络中断 > 5秒 → 连接问题

**主要方法**：
```python
detector.detect_all(metrics: ProcessedMetrics) -> List[Alert]
detector.detect_fps_anomaly(metrics) -> List[Alert]
detector.detect_memory_anomaly(metrics) -> List[Alert]
detector.detect_cpu_anomaly(metrics) -> List[Alert]
detector.detect_network_anomaly(metrics) -> List[Alert]
```

### 3. 统计分析 (StatisticsAnalyzer)

**功能**：
- 计算监控会话摘要
- 计算分位数（P95等）
- 对比多个会话性能
- 检测性能退化
- 计算稳定性评分

**主要方法**：
```python
analyzer.calculate_session_summary() -> SessionSummary
analyzer.calculate_percentile(metric_name, percentile) -> float
analyzer.compare_sessions(session_ids, other_summaries) -> dict
analyzer.calculate_stability_score() -> dict
analyzer.detect_performance_degradation() -> List[dict]
```

### 4. 异常关联分析 (CorrelationAnalyzer)

**功能**：
- 分析异常发生时的多维度数据
- 关联FPS与资源使用（CPU、内存）
- 关联内存与使用情况
- 生成异常详情报告
- 提供优化建议

**主要方法**：
```python
analyzer.analyze_alert_context(alert) -> dict
analyzer.correlate_fps_with_resources(alert) -> dict
analyzer.correlate_memory_with_usage(alert) -> dict
analyzer.generate_anomaly_report(alert) -> dict
analyzer.analyze_session_patterns() -> dict
```

### 5. 阈值管理 (ThresholdManager)

**功能**：
- 管理所有指标的告警阈值
- 支持动态修改并实时生效
- 支持持久化存储
- 阈值验证

**主要方法**：
```python
thresholds.update_fps_thresholds(**kwargs)
thresholds.update_memory_thresholds(**kwargs)
thresholds.update_cpu_thresholds(**kwargs)
thresholds.reset_to_defaults()
thresholds.save_to_file(path)
thresholds.load_from_file(path)
```

## 使用示例

### 基础使用

```python
from insight_eyes.desktop.analytics import (
    MetricsProcessor,
    AnomalyDetector,
    ThresholdManager
)

# 1. 初始化
thresholds = ThresholdManager()
processor = MetricsProcessor(
    session_id=1,
    device_id='emulator-5554',
    app_id='com.example.app',
    window_size=60,
    threshold_manager=thresholds
)
detector = AnomalyDetector(session_id=1, threshold_manager=thresholds)

# 2. 处理原始数据
raw_data = {
    'fps': {
        'fps': 45.0,
        'jank': 2,
        'bigJank': 1,
        'ftime_avg': 22.0,
        'ftime_max': 150.0
    },
    'memory': {
        'totalPass': 204800,
        'nativePass': 102400,
        'dalvikPass': 51200
    },
    'cpu': {
        'appCpuRate': 65.5,
        'sysCpuRate': 45.2
    },
    'network': {
        'upFlow': 100.0,
        'downFlow': 500.0
    }
}

metrics = processor.process_raw_data(raw_data)

# 3. 执行异常检测
alerts = detector.detect_all(metrics)

# 4. 处理告警
for alert in alerts:
    print(f"{alert.severity.value}: {alert.message}")
```

### 自定义阈值

```python
thresholds = ThresholdManager()

# 自定义FPS阈值
thresholds.update_fps_thresholds(
    warning_fps=25.0,
    critical_fps=15.0,
    big_jank_frame_time_ms=120.0
)

# 自定义内存阈值
thresholds.update_memory_thresholds(
    leak_growth_mb=150.0,
    high_memory_mb=600.0,
    growth_rate_warning_mb_per_min=15.0
)

# 保存到文件
thresholds.save_to_file('custom_thresholds.json')
```

### 统计分析

```python
from insight_eyes.desktop.analytics import StatisticsAnalyzer

analyzer = StatisticsAnalyzer(session_id=1)

# 添加多个数据点
for raw_data in data_stream:
    metrics = processor.process_raw_data(raw_data)
    analyzer.add_metrics(metrics)

# 生成摘要
summary = analyzer.calculate_session_summary()
print(f"平均FPS: {summary.avg_fps:.1f}")
print(f"峰值内存: {summary.peak_memory_mb:.1f}MB")
print(f"卡顿次数: {summary.jank_count}")

# 计算P95
fps_p95 = analyzer.calculate_percentile('fps', 95)
print(f"FPS P95: {fps_p95:.1f}")

# 稳定性评分
scores = analyzer.calculate_stability_score()
print(f"FPS稳定性: {scores['fps_stability']:.1f}/100")

# 检测性能退化
degradations = analyzer.detect_performance_degradation()
for deg in degradations:
    print(f"{deg['metric']}性能下降{deg['degradation_percent']:.1f}%")
```

### 关联分析

```python
from insight_eyes.desktop.analytics import CorrelationAnalyzer

analyzer = CorrelationAnalyzer(session_id=1)

# 收集数据
for raw_data in data_stream:
    metrics = processor.process_raw_data(raw_data)
    analyzer.add_metrics(metrics)

# 检测到异常后
if alerts:
    alert = alerts[0]

    # 生成详细报告
    report = analyzer.generate_anomaly_report(alert)

    print("告警信息:", report['alert_info']['message'])
    print("上下文:", report['context']['metrics_at_alert_time'])
    print("关联分析:", report['correlation'])
    print("优化建议:", report['recommendations'])
```

### 信号连接（PyQt6）

```python
from PyQt6.QtCore import QObject

class MonitorWidget(QObject):
    def __init__(self):
        super().__init__()

        # 初始化组件
        self.processor = MetricsProcessor(...)
        self.detector = AnomalyDetector(...)

        # 连接信号
        self.processor.metrics_ready.connect(self.on_metrics_ready)
        self.detector.alert_triggered.connect(self.on_alert_triggered)

    def on_metrics_ready(self, metrics):
        """处理后的指标就绪"""
        # 更新UI显示
        self.update_fps_chart(metrics.fps)
        self.update_memory_chart(metrics.memory)

    def on_alert_triggered(self, alert):
        """检测到告警"""
        # 显示告警（无弹窗）
        self.show_alert_in_list(alert)

        # 严重告警高亮显示
        if alert.severity == AlertSeverity.CRITICAL:
            self.highlight_alert(alert)
```

## 数据格式

### ProcessedMetrics

```python
ProcessedMetrics(
    session_id=1,
    timestamp=datetime.now(),
    device_id='device_id',
    app_id='com.example.app',

    fps=FPSMetrics(
        fps=45.0,
        jank_count=2,
        big_jank_count=1,
        frame_time_avg=22.0,
        frame_time_max=150.0,
        trend='stable',
        timestamp=datetime.now()
    ),

    memory=MemoryMetrics(
        total_mb=200.0,
        native_mb=100.0,
        dalvik_mb=50.0,
        growth_rate_mb_per_min=5.5,
        trend='increasing',
        timestamp=datetime.now()
    ),

    cpu=CPUMetrics(
        app_cpu_percent=65.5,
        sys_cpu_percent=45.2,
        moving_avg=62.3,
        timestamp=datetime.now()
    ),

    network=NetworkMetrics(
        upload_speed_kb_s=100.0,
        download_speed_kb_s=500.0,
        total_sent_mb=10.5,
        total_received_mb=52.3,
        timestamp=datetime.now()
    ),

    alerts=[Alert(...)]
)
```

### Alert

```python
Alert(
    alert_type=AlertType.LOW_FPS,
    severity=AlertSeverity.WARNING,
    metric_name='FPS',
    current_value=25.0,
    threshold=30.0,
    message='低帧率警告: 当前FPS 25.0 < 阈值 30.0',
    timestamp=datetime.now(),
    session_id=1,
    device_id='device_id',
    app_id='com.example.app',
    context={
        'jank_count': 3,
        'trend': 'declining'
    }
)
```

### SessionSummary

```python
SessionSummary(
    session_id=1,
    start_time=datetime(...),
    end_time=datetime(...),
    duration_seconds=300.0,

    avg_fps=52.3,
    min_fps=25.0,
    max_fps=60.0,
    fps_p95=58.0,
    fps_std=8.5,
    jank_count=15,
    big_jank_count=3,

    avg_memory_mb=185.5,
    peak_memory_mb=250.0,
    memory_leaked_mb=20.0,

    avg_cpu_percent=45.2,
    peak_cpu_percent=85.0,

    total_data_sent_mb=12.5,
    total_data_received_mb=85.3,

    alert_count=25,
    critical_count=5,
    warning_count=20
)
```

## 性能特性

- **无延迟检测**：与采集频率同步，实时处理每个数据点
- **低内存占用**：使用滑动窗口，自动丢弃旧数据
- **线程安全**：关键操作使用锁保护
- **可配置**：所有阈值可动态修改
- **可扩展**：易于添加新的检测规则

## 注意事项

1. **数据清洗**：异常值会被自动过滤（如负数FPS、超大内存值）
2. **趋势检测**：需要至少3个数据点才能计算趋势
3. **内存泄露检测**：需要至少10个采样点才能检测单调增长
4. **时间同步**：确保所有时间戳使用同一时区
5. **资源管理**：长时间监控后应调用 `clear_history()` 释放内存

## 测试

运行单元测试：

```bash
python -m insight_eyes.desktop.analytics.test_analytics
```

测试覆盖：
- 阈值管理功能
- 指标数据处理
- 异常检测准确率
- 统计分析功能
- 关联分析功能

## 扩展开发

### 添加新的检测规则

1. 在 `AlertType` 中添加新类型
2. 在 `AnomalyDetector` 中实现检测方法
3. 在 `ThresholdManager` 中添加相关阈值
4. 更新单元测试

### 添加新的派生指标

1. 在对应 `Metrics` 类中添加字段
2. 在 `MetricsProcessor` 中实现计算逻辑
3. 更新 `SessionSummary` 统计

### 添加新的关联分析

1. 在 `CorrelationAnalyzer` 中添加关联方法
2. 实现分析逻辑
3. 生成优化建议

## 版本历史

- v1.0.0 (2025-01-13)
  - 初始版本
  - 实现基础指标处理
  - 实现FPS/内存/CPU/网络异常检测
  - 实现统计分析和关联分析
  - 添加阈值管理和配置
