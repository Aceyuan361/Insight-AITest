# 快速开始指南

## 1. 初始化数据库

```bash
# 进入项目目录
cd C:\Users\86132\Desktop\收纳盒\性能工具\insight_eye-1.0.0\insight_eye-1.0.0

# 初始化数据库并创建示例数据
python -m insight_eyes.desktop.data.init_db --sample-data
```

## 2. 在代码中使用

### 方法 1: 使用数据库管理器（推荐用于简单的数据存储）

```python
import sys
sys.path.insert(0, '.')

# 直接导入
from insight_eyes.desktop.data.database import DatabaseManager

# 初始化数据库
db = DatabaseManager()

# 添加设备
db.upsert_device('my-device', 'My Phone', 'android', 'Pixel 6', 'Android 13')

# 创建监控会话
session_id = db.create_session('my-device', 'com.example.app')

# 保存性能指标
db.save_metrics(session_id, {
    'cpu_app': 25.5,
    'memory_pss': 180.3,
    'fps': 58.0,
    'network_up_speed': 50.5,
    'network_down_speed': 200.3
})

# 查询数据
metrics = db.get_metrics(session_id)
print(f"查询到 {len(metrics)} 条记录")
```

### 方法 2: 使用数据访问层（推荐用于高级查询和统计）

```python
from insight_eyes.desktop.data.database import DatabaseManager
from insight_eyes.desktop.data.repository import MetricsRepository

# 初始化
db = DatabaseManager()
metrics_repo = MetricsRepository(db)

# 获取 FPS 趋势
fps_trend = metrics_repo.get_fps_trend(session_id)
for timestamp, fps in fps_trend:
    print(f"{timestamp}: {fps} fps")

# 获取统计数据
stats = metrics_repo.get_statistics(session_id)
print(f"FPS 平均值: {stats['fps']['avg']}")
print(f"内存平均值: {stats['memory_pss']['avg']} MB")
```

### 方法 3: 使用数据导出器

```python
from insight_eyes.desktop.data.database import DatabaseManager
from insight_eyes.desktop.data.exporter import DataExporter

# 初始化
db = DatabaseManager()
exporter = DataExporter(db)

# 导出为 Excel
exporter.export_to_excel(session_id, 'report.xlsx')

# 生成性能测试报告
exporter.generate_report(session_id, './reports/')
```

## 3. 运行测试

```bash
# 运行单元测试
python -m insight_eyes.desktop.data.test_database

# 运行性能测试
python insight_eyes/desktop/data/performance_test.py
```

## 4. 数据库维护

```python
from insight_eyes.desktop.data.database import DatabaseManager

db = DatabaseManager()

# 清理 7 天前的数据
stats = db.cleanup_old_data(retention_days=7)
print(f"删除了 {stats['metrics_deleted']} 条指标记录")

# 备份数据库
db.backup_database('backup.db')

# 查看数据库统计
stats = db.get_database_stats()
print(f"数据库大小: {stats['db_size_mb']} MB")
```

## 5. 配置模板使用

```python
from insight_eyes.desktop.data.database import DatabaseManager

db = DatabaseManager()

# 保存配置模板
config = {
    'devices': ['device-001', 'device-002'],
    'apps': ['com.example.app'],
    'sample_interval': 1000,
    'thresholds': {
        'memory_pss': 200,
        'fps': 50,
        'cpu_app': 80
    }
}

db.save_template('我的模板', config, description='测试配置')

# 加载模板
template = db.get_template('我的模板')
my_config = template['config']
```

## 常见使用场景

### 场景 1: 记录应用性能数据

```python
from insight_eyes.desktop.data.database import DatabaseManager

db = DatabaseManager()

# 1. 注册设备（首次使用）
db.upsert_device('phone-001', 'My Pixel', 'android', 'Pixel 6', 'Android 13')

# 2. 创建监控会话
session_id = db.create_session(
    'phone-001',
    'com.myapp',
    sample_interval=1000,
    tags={'scenario': '冷启动测试', 'version': '1.0.0'}
)

# 3. 在监控循环中保存数据
while monitoring:
    metrics = collect_performance_data()  # 你的数据采集逻辑
    db.save_metrics(session_id, metrics)

# 4. 结束监控
db.end_session(session_id)
```

### 场景 2: 生成性能测试报告

```python
from insight_eyes.desktop.data.database import DatabaseManager
from insight_eyes.desktop.data.exporter import DataExporter

db = DatabaseManager()
exporter = DataExporter(db)

# 为最近的会话生成报告
sessions = db.get_recent_sessions(limit=1)
if sessions:
    session_id = sessions[0]['id']
    report_path = exporter.generate_report(session_id, './reports/')
    print(f"报告已生成: {report_path}")
```

### 场景 3: 分析历史数据

```python
from insight_eyes.desktop.data.database import DatabaseManager
from insight_eyes.desktop.data.repository import MetricsRepository, AlertRepository
from datetime import datetime, timedelta

db = DatabaseManager()
metrics_repo = MetricsRepository(db)
alert_repo = AlertRepository(db)

# 获取昨天的所有会话
yesterday = datetime.now() - timedelta(days=1)
sessions = db.get_recent_sessions(limit=100)

for session in sessions:
    session_time = datetime.fromisoformat(session['start_time'])
    if session_time.date() == yesterday.date():
        # 获取统计数据
        stats = metrics_repo.get_statistics(session['id'])

        # 获取告警汇总
        alert_summary = alert_repo.get_alert_summary(session['id'])

        # 输出分析结果
        print(f"\n会话: {session['package_name']}")
        print(f"  FPS 平均: {stats['fps']['avg']:.2f}")
        print(f"  内存平均: {stats['memory_pss']['avg']:.2f} MB")
        print(f"  告警数: {alert_summary['total_count']}")
```

### 场景 4: 比较不同版本的性能

```python
from insight_eyes.desktop.data.database import DatabaseManager
from insight_eyes.desktop.data.repository import MetricsRepository

db = DatabaseManager()
metrics_repo = MetricsRepository(db)

# 假设有两个版本的会话ID
session_v1 = 1  # 版本 1.0
session_v2 = 2  # 版本 2.0

comparison = metrics_repo.compare_sessions([session_v1, session_v2])

for sid, data in comparison.items():
    stats = data['statistics']
    print(f"\n会话 {sid}:")
    print(f"  FPS: {stats['fps']['avg']:.2f}")
    print(f"  内存: {stats['memory_pss']['avg']:.2f} MB")
    print(f"  CPU: {stats['cpu_app']['avg']:.2f}%")
```

## 数据库文件位置

默认数据库文件存储在:
```
C:\Users\86132\Desktop\收纳盒\性能工具\insight_eye-1.0.0\insight_eye-1.0.0\insight_eyes\data\insight_eye.db
```

可以使用 DB Viewer 或 SQLite 命令行工具查看数据库内容。

## 下一步

- 查看完整的 API 文档: `README.md`
- 运行使用示例: `example_usage.py`
- 查看单元测试了解更多用法: `test_database.py`
