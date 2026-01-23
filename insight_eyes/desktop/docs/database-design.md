# Insight-Eye 数据库设计文档

## 文档信息

| 项目 | 内容 |
|------|------|
| 文档名称 | Insight-Eye 数据库设计文档 |
| 版本 | 1.0.1 |
| 更新日期 | 2025-01-23 |
| 数据库 | SQLite 3 |

## 1. 数据库概述

### 1.1 设计目标

- **轻量级**：使用 SQLite，无需独立数据库服务
- **高性能**：优化索引和查询，支持高频写入
- **可扩展**：预留扩展字段，便于未来功能添加
- **易维护**：清晰的表结构和命名规范

### 1.2 数据库位置

**默认路径**：
```
~/.insight_eye/data/insight_eye.db
```

**Windows**：
```
C:\Users\<用户名>\.insight_eye\data\insight_eye.db
```

**macOS/Linux**：
```
~/.insight_eye/data/insight_eye.db
```

### 1.3 性能配置

```sql
-- 写前日志模式（提升并发性能）
PRAGMA journal_mode=WAL;

-- 平衡模式（性能与安全）
PRAGMA synchronous=NORMAL;

-- 增加缓存
PRAGMA cache_size=10000;

-- 临时表在内存中
PRAGMA temp_store=MEMORY;

-- 外键约束开启
PRAGMA foreign_keys=ON;
```

## 2. 表结构设计

### 2.1 devices - 设备表

**用途**：存储已连接的设备信息

#### 表结构

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| device_id | TEXT | PRIMARY KEY | 设备唯一标识符 |
| name | TEXT | NOT NULL | 设备名称 |
| platform | TEXT | NOT NULL, CHECK | 平台（android/ios） |
| model | TEXT | | 设备型号 |
| os_version | TEXT | | 操作系统版本 |
| manufacturer | TEXT | | 制造商 |
| serial_number | TEXT | | 序列号 |
| first_seen | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 首次发现时间 |
| last_seen | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 最后发现时间 |

#### SQL 定义

```sql
CREATE TABLE IF NOT EXISTS devices (
    device_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    platform TEXT NOT NULL CHECK(platform IN ('android', 'ios')),
    model TEXT,
    os_version TEXT,
    manufacturer TEXT,
    serial_number TEXT,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 索引

```sql
CREATE INDEX IF NOT EXISTS idx_devices_platform
ON devices(platform);

CREATE INDEX IF NOT EXISTS idx_devices_last_seen
ON devices(last_seen DESC);
```

#### 示例数据

| device_id | name | platform | model | os_version |
|-----------|------|----------|-------|------------|
| emulator-5554 | Android Emulator | android | Pixel 5 | Android 13 |
| abc123def456 | iPhone 15 Pro | ios | iPhone16,1 | iOS 17.0 |

#### 查询示例

```sql
-- 获取所有 Android 设备
SELECT * FROM devices WHERE platform = 'android';

-- 获取最近连接的设备
SELECT * FROM devices ORDER BY last_seen DESC LIMIT 10;

-- 获取设备详情
SELECT * FROM devices WHERE device_id = 'emulator-5554';
```

### 2.2 apps - 应用表

**用途**：存储设备上的应用信息

#### 表结构

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 自增主键 |
| device_id | TEXT | NOT NULL, FOREIGN KEY | 关联设备 |
| package_name | TEXT | NOT NULL | 包名/Bundle ID |
| app_name | TEXT | | 应用名称 |
| version | TEXT | | 应用版本号 |
| first_monitored | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 首次监控时间 |
| last_monitored | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 最后监控时间 |

#### SQL 定义

```sql
CREATE TABLE IF NOT EXISTS apps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    package_name TEXT NOT NULL,
    app_name TEXT,
    version TEXT,
    first_monitored TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_monitored TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(device_id, package_name),
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
);
```

#### 索引

```sql
CREATE INDEX IF NOT EXISTS idx_apps_device
ON apps(device_id);

CREATE INDEX IF NOT EXISTS idx_apps_package
ON apps(package_name);

CREATE INDEX IF NOT EXISTS idx_apps_last_monitored
ON apps(last_monitored DESC);
```

#### 示例数据

| device_id | package_name | app_name | version |
|-----------|--------------|----------|---------|
| emulator-5554 | com.example.app | Example App | 1.0.0 |
| abc123def456 | com.apple.mobilesafari | Safari | 17.0 |

#### 查询示例

```sql
-- 获取设备上的所有应用
SELECT * FROM apps WHERE device_id = 'emulator-5554';

-- 获取特定应用
SELECT * FROM apps
WHERE device_id = 'emulator-5554'
AND package_name = 'com.example.app';

-- 统计设备上的应用数量
SELECT device_id, COUNT(*) as app_count
FROM apps
GROUP BY device_id;
```

### 2.3 monitoring_sessions - 监控会话表

**用途**：记录每次监控会话的基本信息

#### 表结构

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 会话 ID |
| device_id | TEXT | NOT NULL, FOREIGN KEY | 设备 ID |
| package_name | TEXT | NOT NULL | 应用包名 |
| start_time | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 开始时间 |
| end_time | TIMESTAMP | | 结束时间 |
| sample_interval | INTEGER | DEFAULT 1000 | 采样间隔（毫秒） |
| tags | TEXT | | 场景标记（JSON） |
| duration_seconds | INTEGER | | 监控时长（秒） |
| metrics_count | INTEGER | DEFAULT 0 | 指标数据条数 |

#### SQL 定义

```sql
CREATE TABLE IF NOT EXISTS monitoring_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    package_name TEXT NOT NULL,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    sample_interval INTEGER DEFAULT 1000,
    tags TEXT,
    duration_seconds INTEGER,
    metrics_count INTEGER DEFAULT 0,
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
);
```

#### 索引

```sql
CREATE INDEX IF NOT EXISTS idx_sessions_device
ON monitoring_sessions(device_id);

CREATE INDEX IF NOT EXISTS idx_sessions_package
ON monitoring_sessions(package_name);

CREATE INDEX IF NOT EXISTS idx_sessions_start_time
ON monitoring_sessions(start_time DESC);

CREATE INDEX IF NOT EXISTS idx_sessions_end_time
ON monitoring_sessions(end_time);
```

#### 示例数据

| id | device_id | package_name | start_time | end_time | sample_interval | tags |
|----|-----------|--------------|------------|----------|-----------------|------|
| 1 | emulator-5554 | com.example.app | 2025-01-13 10:00:00 | 2025-01-13 10:10:00 | 1000 | {"scenario": "启动测试"} |
| 2 | emulator-5554 | com.example.app | 2025-01-13 10:15:00 | NULL | 1000 | {"scenario": "滑动测试"} |

#### 查询示例

```sql
-- 获取最近的监控会话
SELECT * FROM monitoring_sessions
ORDER BY start_time DESC
LIMIT 10;

-- 获取特定设备的会话
SELECT * FROM monitoring_sessions
WHERE device_id = 'emulator-5554'
AND package_name = 'com.example.app';

-- 获取正在进行的会话（end_time 为 NULL）
SELECT * FROM monitoring_sessions
WHERE end_time IS NULL;

-- 统计监控时长
SELECT
    device_id,
    package_name,
    SUM(duration_seconds) as total_duration
FROM monitoring_sessions
GROUP BY device_id, package_name;
```

### 2.4 performance_metrics - 性能指标表

**用途**：存储采集到的性能指标数据

#### 表结构

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 自增主键 |
| session_id | INTEGER | NOT NULL, FOREIGN KEY | 关联会话 |
| timestamp | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 采集时间 |
| cpu_app | REAL | | 应用 CPU 使用率（%） |
| cpu_system | REAL | | 系统 CPU 使用率（%） |
| memory_app_private | REAL | | 应用私有内存（MB） |
| memory_pss | REAL | | PSS 内存（MB） |
| memory_vss | REAL | | VSS 内存（MB） |
| fps | REAL | | 帧率 |
| fps_jank_count | INTEGER | | 卡顿次数 |
| network_up_speed | REAL | | 上行速度（KB/s） |
| network_down_speed | REAL | | 下行速度（KB/s） |
| battery_level | REAL | | 电池电量（%） |
| battery_temp | REAL | | 电池温度（°C） |
| device_temp | REAL | | 设备温度（°C） |
| network_type | TEXT | | 网络类型 |

#### SQL 定义

```sql
CREATE TABLE IF NOT EXISTS performance_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- App 级指标
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
);
```

#### 索引

```sql
-- 会话和时间复合索引（最常用）
CREATE INDEX IF NOT EXISTS idx_metrics_session_time
ON performance_metrics(session_id, timestamp);

-- 时间索引（用于时间范围查询）
CREATE INDEX IF NOT EXISTS idx_metrics_timestamp
ON performance_metrics(timestamp);

-- FPS 索引（用于性能分析）
CREATE INDEX IF NOT EXISTS idx_metrics_fps
ON performance_metrics(fps);

-- 内存索引
CREATE INDEX IF NOT EXISTS idx_metrics_memory
ON performance_metrics(memory_pss);
```

#### 示例数据

| session_id | timestamp | cpu_app | memory_pss | fps | network_up_speed | battery_level |
|------------|-----------|---------|------------|-----|------------------|---------------|
| 1 | 2025-01-13 10:00:01 | 25.5 | 180.3 | 58.0 | 50.5 | 85.0 |
| 1 | 2025-01-13 10:00:02 | 26.0 | 182.1 | 60.0 | 55.2 | 85.0 |
| 1 | 2025-01-13 10:00:03 | 24.8 | 181.5 | 59.0 | 48.0 | 85.0 |

#### 查询示例

```sql
-- 获取会话的所有指标
SELECT * FROM performance_metrics
WHERE session_id = 1
ORDER BY timestamp;

-- 获取最近 1 分钟的指标
SELECT * FROM performance_metrics
WHERE session_id = 1
AND timestamp >= datetime('now', '-1 minute')
ORDER BY timestamp;

-- 计算 FPS 平均值
SELECT
    AVG(fps) as avg_fps,
    MIN(fps) as min_fps,
    MAX(fps) as max_fps
FROM performance_metrics
WHERE session_id = 1;

-- 查找低 FPS 时刻
SELECT timestamp, fps
FROM performance_metrics
WHERE session_id = 1
AND fps < 30
ORDER BY timestamp;

-- 计算内存增长率
SELECT
    timestamp,
    memory_pss,
    LAG(memory_pss) OVER (ORDER BY timestamp) as prev_memory,
    memory_pss - LAG(memory_pss) OVER (ORDER BY timestamp) as growth
FROM performance_metrics
WHERE session_id = 1;
```

### 2.5 alerts - 异常告警表

**用途**：记录检测到的性能异常

#### 表结构

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 自增主键 |
| session_id | INTEGER | NOT NULL, FOREIGN KEY | 关联会话 |
| timestamp | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 告警时间 |
| alert_type | TEXT | NOT NULL | 告警类型 |
| metric_name | TEXT | | 指标名称 |
| current_value | REAL | | 当前值 |
| threshold_value | REAL | | 阈值 |
| severity | TEXT | CHECK | 严重程度（warning/critical） |
| description | TEXT | | 描述 |
| resolved | BOOLEAN | DEFAULT 0 | 是否已解决 |
| resolved_at | TIMESTAMP | | 解决时间 |

#### SQL 定义

```sql
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
    resolved_at TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES monitoring_sessions(id) ON DELETE CASCADE
);
```

#### 索引

```sql
CREATE INDEX IF NOT EXISTS idx_alerts_session
ON alerts(session_id);

CREATE INDEX IF NOT EXISTS idx_alerts_timestamp
ON alerts(timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_alerts_severity
ON alerts(severity);

CREATE INDEX IF NOT EXISTS idx_alerts_resolved
ON alerts(resolved);
```

#### 示例数据

| session_id | alert_type | metric_name | current_value | threshold_value | severity | description | resolved |
|------------|------------|-------------|---------------|-----------------|----------|-------------|----------|
| 1 | low_fps | fps | 25.0 | 30.0 | warning | 低帧率警告 | 0 |
| 1 | high_memory | memory_pss | 520.0 | 500.0 | critical | 高内存告警 | 0 |
| 1 | cpu_spike | cpu_app | 85.0 | 80.0 | warning | CPU 使用率过高 | 1 |

#### 查询示例

```sql
-- 获取会话的所有告警
SELECT * FROM alerts
WHERE session_id = 1
ORDER BY timestamp;

-- 获取未解决的严重告警
SELECT * FROM alerts
WHERE severity = 'critical'
AND resolved = 0
ORDER BY timestamp;

-- 统计告警类型
SELECT
    alert_type,
    severity,
    COUNT(*) as count
FROM alerts
WHERE session_id = 1
GROUP BY alert_type, severity;

-- 获取特定时间段内的告警
SELECT * FROM alerts
WHERE timestamp BETWEEN '2025-01-13 10:00:00' AND '2025-01-13 10:10:00'
ORDER BY timestamp;
```

### 2.6 config_templates - 配置模板表

**用途**：存储用户自定义的配置模板

#### 表结构

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 自增主键 |
| name | TEXT | UNIQUE NOT NULL | 模板名称 |
| config_json | TEXT | NOT NULL | 配置 JSON |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新时间 |
| description | TEXT | | 描述 |

#### SQL 定义

```sql
CREATE TABLE IF NOT EXISTS config_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    config_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);
```

#### 索引

```sql
CREATE INDEX IF NOT EXISTS idx_templates_name
ON config_templates(name);
```

#### 示例数据

| name | config_json | description |
|------|-------------|-------------|
| 性能测试标准配置 | {"sample_interval": 1000, "thresholds": {...}} | 标准性能测试配置 |
| 低频监控配置 | {"sample_interval": 5000, "thresholds": {...}} | 低频长时间监控 |

#### 查询示例

```sql
-- 获取所有模板
SELECT * FROM config_templates
ORDER BY created_at DESC;

-- 获取特定模板
SELECT * FROM config_templates
WHERE name = '性能测试标准配置';

-- 搜索模板
SELECT * FROM config_templates
WHERE name LIKE '%性能%';
```

## 3. 表关系图

```
┌─────────────┐
│   devices   │
│  (设备表)    │
└──────┬──────┘
       │ 1
       │
       │ N
┌──────▼──────────┐     ┌──────────────────┐
│      apps       │     │monitoring_sessions│
│    (应用表)      │     │   (监控会话表)     │
└─────────────────┘     └────────┬─────────┘
                                 │ 1
                                 │
                                 │ N
                        ┌────────▼──────────┐
                        │performance_metrics│
                        │  (性能指标表)      │
                        └───────────────────┘
                                 │ 1
                                 │
                                 │ N
                        ┌────────▼─────┐
                        │   alerts     │
                        │  (告警表)     │
                        └──────────────┘

┌──────────────────┐
│config_templates  │
│ (配置模板表)      │
└──────────────────┘
```

## 4. 数据字典

### 4.1 平台枚举

| 值 | 说明 |
|----|------|
| android | Android 平台 |
| ios | iOS 平台 |

### 4.2 告警类型枚举

| 值 | 说明 |
|----|------|
| low_fps | 低帧率 |
| high_memory | 高内存 |
| memory_leak | 内存泄露 |
| high_cpu | 高 CPU |
| cpu_spike | CPU 尖峰 |
| network_error | 网络错误 |
| battery_low | 低电量 |
| temperature_high | 温度过高 |

### 4.3 严重程度枚举

| 值 | 说明 |
|----|------|
| warning | 警告 |
| critical | 严重 |

### 4.4 网络类型枚举

| 值 | 说明 |
|----|------|
| WIFI | Wi-Fi 网络 |
| MOBILE | 移动网络 |
| ETHERNET | 以太网 |
| UNKNOWN | 未知 |

## 5. 常用查询

### 5.1 统计查询

#### 会话统计

```sql
-- 获取会话概览
SELECT
    s.id,
    s.device_id,
    s.package_name,
    s.start_time,
    s.end_time,
    s.duration_seconds,
    COUNT(m.id) as metrics_count,
    COUNT(a.id) as alerts_count
FROM monitoring_sessions s
LEFT JOIN performance_metrics m ON s.id = m.session_id
LEFT JOIN alerts a ON s.id = a.session_id
GROUP BY s.id
ORDER BY s.start_time DESC;
```

#### 指标统计

```sql
-- 计算 FPS 统计
SELECT
    session_id,
    COUNT(*) as sample_count,
    AVG(fps) as avg_fps,
    MIN(fps) as min_fps,
    MAX(fps) as max_fps,
    (
        SELECT fps FROM performance_metrics p2
        WHERE p2.session_id = p1.session_id
        ORDER BY fps
        LIMIT 1 OFFSET (SELECT COUNT(*) FROM performance_metrics WHERE session_id = p1.session_id) / 2
    ) as median_fps
FROM performance_metrics p1
WHERE session_id = 1 AND fps IS NOT NULL;
```

#### 告警统计

```sql
-- 告警汇总
SELECT
    alert_type,
    severity,
    COUNT(*) as count,
    COUNT(CASE WHEN resolved = 0 THEN 1 END) as unresolved_count
FROM alerts
WHERE session_id = 1
GROUP BY alert_type, severity;
```

### 5.2 性能分析查询

#### FPS 波动分析

```sql
-- 计算 FPS 标准差
SELECT
    session_id,
    AVG(fps) as avg_fps,
    (
        SELECT SQRT(AVG((fps - sub.avg) * (fps - sub.avg)))
        FROM performance_metrics, (SELECT AVG(fps) as avg FROM performance_metrics WHERE session_id = 1) as sub
        WHERE session_id = 1
    ) as std_dev
FROM performance_metrics
WHERE session_id = 1
GROUP BY session_id;
```

#### 内存泄露检测

```sql
-- 检测内存持续增长
SELECT
    timestamp,
    memory_pss,
    memory_pss - LAG(memory_pss, 10) OVER (ORDER BY timestamp) as growth_10_samples
FROM performance_metrics
WHERE session_id = 1
AND memory_pss IS NOT NULL
ORDER BY timestamp;
```

#### 卡顿分析

```sql
-- 统计卡顿次数和分布
SELECT
    DATE_FORMAT(timestamp, '%H:%i') as time_bucket,
    SUM(fps_jank_count) as total_jank,
    COUNT(*) as sample_count
FROM performance_metrics
WHERE session_id = 1
AND fps_jank_count > 0
GROUP BY time_bucket
ORDER BY timestamp;
```

### 5.3 数据维护查询

#### 清理过期数据

```sql
-- 删除 7 天前的数据
DELETE FROM performance_metrics
WHERE timestamp < datetime('now', '-7 days');

DELETE FROM alerts
WHERE timestamp < datetime('now', '-7 days');

DELETE FROM monitoring_sessions
WHERE start_time < datetime('now', '-7 days');
```

#### 数据库统计

```sql
-- 获取数据库大小
SELECT
    name,
    (page_count * page_size) / 1024.0 / 1024.0 as size_mb
FROM pragma_page_count(), pragma_page_size(), database_list
WHERE name = 'main';

-- 获取各表记录数
SELECT
    'devices' as table_name,
    COUNT(*) as row_count
FROM devices
UNION ALL
SELECT 'apps', COUNT(*) FROM apps
UNION ALL
SELECT 'monitoring_sessions', COUNT(*) FROM monitoring_sessions
UNION ALL
SELECT 'performance_metrics', COUNT(*) FROM performance_metrics
UNION ALL
SELECT 'alerts', COUNT(*) FROM alerts;
```

## 6. 数据备份与恢复

### 6.1 备份

#### SQL 备份

```bash
# 使用 SQLite 命令行工具
sqlite3 insight_eye.db ".backup backup_$(date +%Y%m%d).db"
```

#### Python 备份

```python
import shutil
from datetime import datetime

backup_path = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
shutil.copy2('insight_eye.db', backup_path)
```

### 6.2 恢复

```bash
# 停止应用
# 恢复数据库
cp backup_20250113.db insight_eye.db
# 重启应用
```

## 7. 性能优化建议

### 7.1 批量插入

```python
# 使用事务批量插入
with db.transaction():
    for metric in metrics_batch:
        db.save_metrics(session_id, metric)
```

### 7.2 定期清理

```python
# 每周清理一次过期数据
import schedule
from datetime import timedelta

def cleanup():
    stats = db.cleanup_old_data(retention_days=7)
    logger.info(f"清理完成: {stats}")

schedule.every().week.do(cleanup)
```

### 7.3 索引维护

```sql
-- 重建索引（每月一次）
REINDEX;

-- 分析表统计信息
ANALYZE;

-- 清空数据库
VACUUM;
```

## 8. 迁移与升级

### 8.1 版本控制

```sql
-- 创建版本表
CREATE TABLE IF NOT EXISTS db_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- 插入当前版本
INSERT INTO db_version (version, description) VALUES (1, 'Initial schema');
```

### 8.2 迁移脚本示例

```sql
-- 添加新字段
ALTER TABLE performance_metrics ADD COLUMN gpu_usage REAL;

-- 创建新表
CREATE TABLE IF NOT EXISTS custom_metrics (...);

-- 更新版本
INSERT INTO db_version (version, description) VALUES (2, 'Add GPU metrics');
```

---

**文档维护**：数据库结构变更时，应及时更新本文档。
