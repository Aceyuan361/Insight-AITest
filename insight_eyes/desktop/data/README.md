# 数据存储管理模块

## 概述

本模块为 Insight-Eye 性能监控工具提供轻量级的 SQLite 数据库存储解决方案，支持设备信息、应用信息、性能监控数据、异常告警记录的持久化存储，并提供丰富的数据查询、导出和报告生成功能。

## 目录结构

```
data/
├── __init__.py           # 模块初始化文件
├── database.py           # 数据库管理器（核心）
├── repository.py         # 数据访问层（高级查询接口）
├── exporter.py           # 数据导出器（多格式导出）
├── init_db.py            # 数据库初始化脚本
├── test_database.py      # 单元测试
└── README.md            # 本文档
```

## 核心功能

### 1. 数据库管理器 (DatabaseManager)

负责数据库的初始化、连接管理和基本 CRUD 操作。

**主要特性：**
- 线程安全的单例模式设计
- 自动创建表结构和索引
- 优化的 SQLite 性能配置（WAL 模式）
- 完整的数据事务支持

**基本用法：**

```python
from insight_eyes.desktop.data import DatabaseManager

# 初始化数据库（自动创建表结构）
db = DatabaseManager()  # 使用默认路径
# 或指定路径
db = DatabaseManager('/path/to/database.db')

# 设备管理
db.upsert_device(
    device_id='emulator-5554',
    name='Android Emulator',
    platform='android',
    model='Pixel 5',
    os_version='Android 13'
)

# 创建监控会话
session_id = db.create_session(
    device_id='emulator-5554',
    package_name='com.example.app',
    sample_interval=1000,
    tags={'scenario': 'performance_test'}
)

# 保存性能指标
db.save_metrics(session_id, {
    'cpu_app': 25.5,
    'memory_pss': 180.3,
    'fps': 58.0,
    'network_up_speed': 50.5,
    'network_down_speed': 200.3,
    'battery_level': 85.0
})

# 保存告警
db.save_alert(session_id, {
    'alert_type': 'high_memory',
    'metric_name': 'memory_pss',
    'current_value': 250.0,
    'threshold_value': 200.0,
    'severity': 'warning',
    'description': '内存使用超过阈值'
})

# 查询数据
metrics = db.get_metrics(session_id)
alerts = db.get_alerts(session_id=session_id)

# 结束会话
db.end_session(session_id)
```

### 2. 数据访问层 (Repository)

提供高级的数据查询和统计分析功能。

**包含三个 Repository 类：**

#### MetricsRepository - 性能指标查询

```python
from insight_eyes.desktop.data import MetricsRepository, DatabaseManager

db = DatabaseManager()
metrics_repo = MetricsRepository(db)

# 获取 FPS 趋势
fps_trend = metrics_repo.get_fps_trend(session_id)
# 返回: [(datetime, fps_value), ...]

# 获取内存趋势
memory_trend = metrics_repo.get_memory_trend(session_id)

# 获取统计数据
stats = metrics_repo.get_statistics(session_id)
# 返回: {
#   'fps': {'avg': 58.5, 'max': 60, 'min': 55, ...},
#   'cpu_app': {'avg': 25.3, 'max': 30, 'min': 20, ...},
#   'memory_pss': {'avg': 180.5, 'max': 200, 'min': 150, ...}
# }

# 获取聚合数据（按时间间隔）
aggregated = metrics_repo.get_aggregated_metrics(session_id, interval_seconds=60)

# 比较多个会话
comparison = metrics_repo.compare_sessions([session_id_1, session_id_2])
```

#### AlertRepository - 告警查询

```python
from insight_eyes.desktop.data import AlertRepository, DatabaseManager

db = DatabaseManager()
alert_repo = AlertRepository(db)

# 获取告警汇总
summary = alert_repo.get_alert_summary(session_id)
# 返回: {
#   'total_count': 10,
#   'by_type': {'high_memory': 5, 'low_fps': 3, ...},
#   'by_severity': {'warning': 7, 'critical': 3},
#   'unresolved_count': 2
# }

# 获取性能问题分析
issues = alert_repo.get_performance_issues(session_id)
# 返回: {
#   'critical_issues': [...],
#   'warnings': [...],
#   'recommendations': [...]
# }
```

#### SessionRepository - 会话查询

```python
from insight_eyes.desktop.data import SessionRepository, DatabaseManager

db = DatabaseManager()
session_repo = SessionRepository(db)

# 获取会话概览
overview = session_repo.get_session_overview(session_id)
# 返回: {
#   'session_info': {...},
#   'data_summary': {...}
# }

# 搜索会话
sessions = session_repo.search_sessions(
    device_id='emulator-5554',
    package_name='com.example.app',
    start_date=datetime(2024, 1, 1),
    tags={'scenario': 'test'}
)
```

### 3. 数据导出器 (DataExporter)

支持将监控数据导出为多种格式。

```python
from insight_eyes.desktop.data import DataExporter, DatabaseManager

db = DatabaseManager()
exporter = DataExporter(db)

# 导出为 CSV
exporter.export_to_csv(session_id, '/path/to/export.csv')

# 导出为 JSON
exporter.export_to_json(session_id, '/path/to/export.json')

# 导出为 Excel（多工作表）
exporter.export_to_excel(session_id, '/path/to/export.xlsx')

# 生成测试报告（Markdown 格式）
report_path = exporter.generate_report(session_id, '/path/to/output/')

# 批量导出
files = exporter.export_batch(
    session_ids=[1, 2, 3],
    output_dir='/path/to/exports/',
    format='excel'
)
```

**Excel 导出包含以下工作表：**
1. 会话概览 - 基本信息
2. 性能指标 - 原始数据
3. 统计数据 - 指标统计
4. 告警记录 - 所有告警
5. 趋势数据 - FPS 和内存趋势

### 4. 配置模板管理

保存和加载监控配置模板。

```python
# 保存模板
db.save_template(
    name='性能测试标准配置',
    config={
        'devices': ['emulator-5554', 'iphone-test-001'],
        'apps': ['com.example.app'],
        'sample_interval': 1000,
        'thresholds': {
            'memory_pss': 200,
            'fps': 50,
            'cpu_app': 80
        }
    },
    description='标准性能测试配置'
)

# 加载模板
template = db.get_template('性能测试标准配置')
config = template['config']

# 列出所有模板
all_templates = db.get_all_templates()

# 删除模板
db.delete_template('性能测试标准配置')
```

### 5. 数据维护

```python
# 清理过期数据（保留 7 天）
stats = db.cleanup_old_data(retention_days=7)
# 返回: {
#   'metrics_deleted': 1000,
#   'alerts_deleted': 50,
#   'sessions_deleted': 10
# }

# 备份数据库
success = db.backup_database('/path/to/backup.db')

# 获取数据库统计
stats = db.get_database_stats()
# 返回: {
#   'devices_count': 5,
#   'performance_metrics_count': 10000,
#   'db_size_mb': 2.5,
#   ...
# }
```

## 数据库表结构

### devices - 设备表

```sql
CREATE TABLE devices (
    device_id TEXT PRIMARY KEY,      -- 设备ID
    name TEXT NOT NULL,               -- 设备名称
    platform TEXT NOT NULL,           -- 平台 (android/ios)
    model TEXT,                       -- 设备型号
    os_version TEXT,                  -- 系统版本
    first_seen TIMESTAMP,             -- 首次发现时间
    last_seen TIMESTAMP               -- 最后发现时间
);
```

### apps - 应用表

```sql
CREATE TABLE apps (
    id INTEGER PRIMARY KEY,
    device_id TEXT NOT NULL,          -- 关联设备
    package_name TEXT NOT NULL,       -- 包名/Bundle ID
    app_name TEXT,                    -- 应用名称
    first_monitored TIMESTAMP         -- 首次监控时间
);
```

### monitoring_sessions - 监控会话表

```sql
CREATE TABLE monitoring_sessions (
    id INTEGER PRIMARY KEY,
    device_id TEXT NOT NULL,          -- 设备ID
    package_name TEXT NOT NULL,       -- 应用包名
    start_time TIMESTAMP,             -- 开始时间
    end_time TIMESTAMP,               -- 结束时间
    sample_interval INTEGER,          -- 采样间隔(ms)
    tags TEXT                         -- 场景标记(JSON)
);
```

### performance_metrics - 性能指标表

```sql
CREATE TABLE performance_metrics (
    id INTEGER PRIMARY KEY,
    session_id INTEGER NOT NULL,      -- 关联会话
    timestamp TIMESTAMP,              -- 采集时间
    -- App级指标
    cpu_app REAL,                     -- App CPU使用率(%)
    cpu_system REAL,                  -- 系统CPU使用率(%)
    memory_app_private REAL,          -- App私有内存(MB)
    memory_pss REAL,                  -- PSS内存(MB)
    memory_vss REAL,                  -- VSS内存(MB)
    fps REAL,                         -- 帧率
    fps_jank_count INTEGER,           -- 卡顿次数
    network_up_speed REAL,            -- 上行速度(KB/s)
    network_down_speed REAL,          -- 下行速度(KB/s)
    -- 设备级指标
    battery_level REAL,               -- 电池电量(%)
    battery_temp REAL,                -- 电池温度(°C)
    device_temp REAL,                 -- 设备温度(°C)
    network_type TEXT,                -- 网络类型
    -- iOS 特定指标
    energy REAL                       -- 能耗数据（iOS专用）
);
```

**iOS 特定字段说明：**
- `energy REAL` - 能耗数据，仅 iOS 设备提供，通过 sysmon 流式监听获取
- `cpu_app REAL` - 在 iOS 上表示应用 CPU 使用率，通过 sysmon 流式监听获取
- `memory_app_private REAL` - 在 iOS 上表示应用私有内存（Private Memory），通过 sysmon 流式监听获取

### alerts - 告警表

```sql
CREATE TABLE alerts (
    id INTEGER PRIMARY KEY,
    session_id INTEGER NOT NULL,      -- 关联会话
    timestamp TIMESTAMP,              -- 告警时间
    alert_type TEXT NOT NULL,         -- 告警类型
    metric_name TEXT,                 -- 指标名称
    current_value REAL,               -- 当前值
    threshold_value REAL,             -- 阈值
    severity TEXT,                    -- 严重程度
    description TEXT,                 -- 描述
    resolved BOOLEAN                  -- 是否已解决
);
```

### config_templates - 配置模板表

```sql
CREATE TABLE config_templates (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,        -- 模板名称
    config_json TEXT NOT NULL,        -- 配置JSON
    created_at TIMESTAMP,             -- 创建时间
    description TEXT                  -- 描述
);
```

## 初始化数据库

使用提供的初始化脚本创建数据库：

```bash
# 基本初始化
python -m insight_eyes.desktop.data.init_db

# 指定数据库路径
python -m insight_eyes.desktop.data.init_db --db-path /path/to/database.db

# 创建示例数据（用于测试）
python -m insight_eyes.desktop.data.init_db --sample-data
```

## 运行单元测试

```bash
# 运行所有测试
python -m insight_eyes.desktop.data.test_database

# 或使用 unittest
python -m unittest insight_eyes.desktop.data.test_database
```

## 性能优化

### 数据库优化配置

1. **WAL 模式** - 写前日志，提升并发性能
2. **批量插入** - 使用事务批量保存指标
3. **索引优化** - 为时间戳和会话ID创建索引
4. **连接池** - 线程本地连接，避免锁竞争

### 查询优化建议

```python
# 推荐：使用时间范围查询
metrics = db.get_metrics(session_id, start_time, end_time)

# 推荐：使用聚合数据减少数据量
aggregated = metrics_repo.get_aggregated_metrics(session_id, interval_seconds=60)

# 避免：查询全部数据后再过滤
all_metrics = db.get_metrics(session_id)  # 可能返回大量数据
filtered = [m for m in all_metrics if m['fps'] < 30]
```

## 数据导出格式对比

| 格式 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| CSV | 体积小，兼容性好 | 不支持多表，无结构 | 简单数据交换 |
| JSON | 结构化，支持嵌套 | 文件较大 | 程序间数据交换 |
| Excel | 多工作表，可读性强 | 需要 openpyxl | 人工查看分析 |
| Markdown | 报告格式清晰 | 不适合数据导入 | 测试报告生成 |

## 常见问题

### Q: 如何更改数据库存储位置？

A: 初始化时传入自定义路径：
```python
db = DatabaseManager('/custom/path/to/database.db')
```

### Q: 数据库文件太大怎么办？

A: 使用清理功能删除旧数据：
```python
stats = db.cleanup_old_data(retention_days=7)
```

### Q: 如何迁移数据库？

A: 使用备份功能：
```python
db.backup_database('/backup/path/database.db')
```

### Q: 支持多线程访问吗？

A: 支持。DatabaseManager 使用线程本地存储和 WAL 模式，确保线程安全。

### Q: Excel 导出失败？

A: 确保安装 openpyxl：
```bash
pip install openpyxl
```

## 依赖项

- Python 3.9+
- sqlite3 (Python 标准库)
- openpyxl (可选，用于 Excel 导出)

## 未来规划

- [ ] 支持更多数据库后端（PostgreSQL、MySQL）
- [ ] 数据压缩功能
- [ ] 实时数据流导出
- [ ] 自动备份策略
- [ ] 数据可视化集成

## 技术支持

如有问题或建议，请联系项目维护者。
