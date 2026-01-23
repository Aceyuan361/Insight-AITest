# Insight-Eye 模块接口文档

## 文档信息

| 项目 | 内容 |
|------|------|
| 文档名称 | Insight-Eye 模块接口文档 |
| 版本 | 1.0.1 |
| 更新日期 | 2025-01-23 |

## 1. 核心模块接口 (core/)

### 1.1 DeviceManager

**模块路径**：`insight_eyes.desktop.core.device_manager`

**类名**：`DeviceManager`

**职责**：设备扫描、监控、应用枚举、信号分发

#### 主要方法

##### start_scanning()

启动设备扫描线程。

```python
def start_scanning(self, interval_seconds: int = 5) -> None
```

**参数**：
- `interval_seconds` (int): 扫描间隔，默认 5 秒

**返回值**：无

**示例**：
```python
device_manager = DeviceManager()
device_manager.start_scanning(interval_seconds=10)
```

##### stop_scanning()

停止设备扫描。

```python
def stop_scanning(self) -> None
```

**示例**：
```python
device_manager.stop_scanning()
```

##### monitor_device()

开始监控指定设备。

```python
def monitor_device(self, device_id: str, interval_seconds: int = 10) -> bool
```

**参数**：
- `device_id` (str): 设备 ID
- `interval_seconds` (int): 监控间隔，默认 10 秒

**返回值**：
- `bool`: 是否成功开始监控

**示例**：
```python
success = device_manager.monitor_device('emulator-5554', interval_seconds=5)
```

##### stop_monitoring()

停止监控指定设备。

```python
def stop_monitoring(self, device_id: str) -> None
```

**参数**：
- `device_id` (str): 设备 ID

**示例**：
```python
device_manager.stop_monitoring('emulator-5554')
```

##### get_device_apps()

获取设备上的应用列表。

```python
def get_device_apps(self, device_id: str, app_filter: Optional[AppFilter] = None) -> List[AppInfo]
```

**参数**：
- `device_id` (str): 设备 ID
- `app_filter` (AppFilter, 可选): 应用过滤器

**返回值**：
- `List[AppInfo]`: 应用信息列表

**示例**：
```python
# 获取所有应用
apps = device_manager.get_device_apps('emulator-5554')

# 只获取运行中的应用
from core.models import AppFilter
filter = AppFilter(is_running=True)
apps = device_manager.get_device_apps('emulator-5554', filter)
```

##### get_devices()

获取所有已连接的设备。

```python
def get_devices(self, device_filter: Optional[DeviceFilter] = None) -> List[DeviceInfo]
```

**参数**：
- `device_filter` (DeviceFilter, 可选): 设备过滤器

**返回值**：
- `List[DeviceInfo]`: 设备信息列表

**示例**：
```python
# 获取所有设备
devices = device_manager.get_devices()

# 只获取 Android 设备
from core.models import DeviceFilter, Platform
filter = DeviceFilter(platform=Platform.ANDROID)
devices = device_manager.get_devices(filter)
```

##### search_devices()

搜索设备。

```python
def search_devices(self, search_text: str) -> List[DeviceInfo]
```

**参数**：
- `search_text` (str): 搜索文本

**返回值**：
- `List[DeviceInfo]`: 匹配的设备列表

**示例**：
```python
devices = device_manager.search_devices('Pixel')
```

#### 信号定义

##### device_discovered

发现新设备时触发。

```python
device_discovered = pyqtSignal(DeviceInfo)
```

**示例**：
```python
device_manager.device_discovered.connect(lambda device: print(f"发现设备: {device.name}"))
```

##### device_lost

设备断开时触发。

```python
device_lost = pyqtSignal(str)  # device_id
```

##### device_updated

设备信息更新时触发。

```python
device_updated = pyqtSignal(DeviceInfo)
```

##### app_list_updated

应用列表更新时触发。

```python
app_list_updated = pyqtSignal(str, list)  # device_id, apps
```

##### error_occurred

发生错误时触发。

```python
error_occurred = pyqtSignal(str, str)  # error_type, message
```

### 1.2 DeviceAdapter

**模块路径**：`insight_eyes.desktop.core.device_adapters`

#### AndroidDeviceAdapter

**类名**：`AndroidDeviceAdapter`

**继承**：`BaseDeviceAdapter`

##### connect()

连接设备。

```python
def connect(self) -> bool
```

**返回值**：
- `bool`: 是否成功连接

##### disconnect()

断开设备。

```python
def disconnect() -> None
```

##### execute_command()

执行 ADB 命令。

```python
def execute_command(self, command: str, timeout: int = 30) -> Optional[str]
```

**参数**：
- `command` (str): ADB 命令
- `timeout` (int): 超时时间（秒），默认 30

**返回值**：
- `Optional[str]`: 命令输出，失败返回 None

**示例**：
```python
adapter = AndroidDeviceAdapter('emulator-5554')
result = adapter.execute_command('shell dumpsys battery')
```

##### install_app()

安装应用。

```python
def install_app(self, apk_path: str) -> bool
```

**参数**：
- `apk_path` (str): APK 文件路径

**返回值**：
- `bool`: 是否成功安装

##### uninstall_app()

卸载应用。

```python
def uninstall_app(self, package_name: str) -> bool
```

**参数**：
- `package_name` (str): 包名

**返回值**：
- `bool`: 是否成功卸载

##### start_app()

启动应用。

```python
def start_app(self, package_name: str, activity: str = None) -> bool
```

**参数**：
- `package_name` (str): 包名
- `activity` (str, 可选): Activity 名称

**返回值**：
- `bool`: 是否成功启动

##### stop_app()

停止应用。

```python
def stop_app(self, package_name: str) -> bool
```

**参数**：
- `package_name` (str): 包名

**返回值**：
- `bool`: 是否成功停止

##### get_battery_info()

获取电池信息。

```python
def get_battery_info(self) -> dict
```

**返回值**：
```python
{
    'level': int,        # 电量百分比
    'temperature': float, # 温度（摄氏度）
    'status': str,       # 状态：charging/discharging
    'health': str        # 健康状态
}
```

##### get_network_type()

获取网络类型。

```python
def get_network_type(self) -> str
```

**返回值**：
- `str`: 网络类型（WIFI/MOBILE/ETHERNET/UNKNOWN）

#### IOSDeviceAdapter

**模块路径**：`insight_eyes.desktop.core.ios_device_adapter`

**类名**：`IOSDeviceAdapter`

**继承**：`BaseDeviceAdapter`

**依赖**：pymobiledevice3 >= 7.0.0

**特点**：
- 使用 pymobiledevice3 与 iOS 设备通信
- 通过 sysmon 命令采集性能数据
- 支持自动重连（指数退避策略）
- 需要设备信任和开发者模式

##### connect()

连接 iOS 设备。

```python
def connect(self) -> bool
```

**返回值**：
- `bool`: 是否成功连接

**异常**：
- `DeviceNotTrustedError`: 设备未信任
- `DeveloperModeNotEnabledError`: 开发者模式未启用
- `PMD3NotInstalledError`: pymobiledevice3 未安装

##### collect_fps()

iOS 平台暂不支持 FPS 采集。

```python
def collect_fps(self, package_name: str) -> Optional[Dict[str, Any]]
```

**返回值**：
- `None`: iOS 平台不支持

##### collect_cpu()

采集 CPU 使用率。

```python
def collect_cpu(self, package_name: str) -> Optional[Dict[str, Any]]
```

**返回值**：
```python
{
    'cpu_app': float,      # 应用 CPU 使用率 (%)
    'cpu_system': float    # 系统 CPU 使用率 (%)
}
```

##### collect_memory()

采集内存使用。

```python
def collect_memory(self, bundle_id: str) -> Optional[Dict[str, Any]]
```

**参数**：
- `bundle_id` (str): 应用 Bundle ID

**返回值**：
```python
{
    'memory_app_private': float,  # 应用私有内存 (MB)
    'memory_pss': float,          # PSS 内存 (MB)
    'memory_vss': float           # VSS 内存 (MB)
}
```

##### collect_network()

采集网络流量。

```python
def collect_network(self, bundle_id: str) -> Optional[Dict[str, Any]]
```

**返回值**：
```python
{
    'network_up_speed': float,   # 上行速度 (KB/s)
    'network_down_speed': float  # 下行速度 (KB/s)
}
```

##### collect_battery()

采集电池信息。

```python
def collect_battery(self) -> Optional[Dict[str, Any]]
```

**返回值**：
```python
{
    'battery_level': float,  # 电池电量 (%)
    'battery_temp': float    # 电池温度 (°C)
}
```

### 1.3 AppEnumerator

**模块路径**：`insight_eyes.desktop.core.app_enumerator`

#### AndroidAppEnumerator

**类名**：`AndroidAppEnumerator`

##### enumerate_apps()

枚举所有应用。

```python
def enumerate_apps(self) -> List[AppInfo]
```

**返回值**：
- `List[AppInfo]`: 应用信息列表

##### get_running_apps()

获取运行中的应用。

```python
def get_running_apps(self) -> List[AppInfo]
```

**返回值**：
- `List[AppInfo]`: 运行中的应用列表

##### get_app_memory()

获取应用内存占用。

```python
def get_app_memory(self, package_name: str) -> dict
```

**参数**：
- `package_name` (str): 包名

**返回值**：
```python
{
    'pid': int,
    'total_mb': float,
    'native_mb': float,
    'dalvik_mb': float
}
```

## 2. 分析模块接口 (analytics/)

### 2.1 MetricsProcessor

**模块路径**：`insight_eyes.desktop.analytics.metrics_processor`

**类名**：`MetricsProcessor`

#### 主要方法

##### process_raw_data()

处理原始指标数据。

```python
def process_raw_data(self, raw_data: dict) -> ProcessedMetrics
```

**参数**：
- `raw_data` (dict): 原始数据，格式如下：
```python
{
    'fps': {
        'fps': int,
        'jank': int,
        'bigJank': int,
        'ftime_avg': float,
        'ftime_max': float
    },
    'memory': {
        'totalPass': float,  # KB
        'nativePass': float,
        'dalvikPass': float
    },
    'cpu': {
        'appCpuRate': float,  # %
        'sysCpuRate': float
    },
    'network': {
        'upFlow': float,      # KB/s
        'downFlow': float
    },
    'battery': {
        'level': int,         # %
        'temperature': float  # °C
    }
}
```

**返回值**：
- `ProcessedMetrics`: 处理后的指标对象

**示例**：
```python
from analytics import MetricsProcessor

processor = MetricsProcessor(
    session_id=1,
    device_id='emulator-5554',
    app_id='com.example.app',
    window_size=60
)

raw_data = {
    'fps': {'fps': 60, 'jank': 0, 'bigJank': 0},
    'memory': {'totalPass': 180000},
    'cpu': {'appCpuRate': 45.0}
}

metrics = processor.process_raw_data(raw_data)
print(f"FPS: {metrics.fps.fps}")
print(f"内存: {metrics.memory.total_mb}MB")
```

##### get_trend()

获取指标趋势。

```python
def get_trend(self, metric_name: str) -> str
```

**参数**：
- `metric_name` (str): 指标名称（fps/memory/cpu/network）

**返回值**：
- `str`: 趋势（increasing/decreasing/stable/volatile）

##### clear_history()

清空历史数据。

```python
def clear_history(self) -> None
```

#### 信号定义

##### metrics_ready

指标处理完成时触发。

```python
metrics_ready = pyqtSignal(ProcessedMetrics)
```

### 2.2 AnomalyDetector

**模块路径**：`insight_eyes.desktop.analytics.anomaly_detector`

**类名**：`AnomalyDetector`

#### 主要方法

##### detect_all()

检测所有异常。

```python
def detect_all(self, metrics: ProcessedMetrics) -> List[Alert]
```

**参数**：
- `metrics` (ProcessedMetrics): 处理后的指标

**返回值**：
- `List[Alert]`: 检测到的告警列表

**示例**：
```python
from analytics import AnomalyDetector

detector = AnomalyDetector(session_id=1)
alerts = detector.detect_all(metrics)

for alert in alerts:
    print(f"{alert.severity.value}: {alert.message}")
```

##### detect_fps_anomaly()

检测 FPS 异常。

```python
def detect_fps_anomaly(self, metrics: ProcessedMetrics) -> List[Alert]
```

##### detect_memory_anomaly()

检测内存异常。

```python
def detect_memory_anomaly(self, metrics: ProcessedMetrics) -> List[Alert]
```

##### detect_cpu_anomaly()

检测 CPU 异常。

```python
def detect_cpu_anomaly(self, metrics: ProcessedMetrics) -> List[Alert]
```

##### detect_network_anomaly()

检测网络异常。

```python
def detect_network_anomaly(self, metrics: ProcessedMetrics) -> List[Alert]
```

#### 信号定义

##### alert_triggered

检测到异常时触发。

```python
alert_triggered = pyqtSignal(Alert)
```

### 2.3 ThresholdManager

**模块路径**：`insight_eyes.desktop.analytics.thresholds`

**类名**：`ThresholdManager`

#### 主要方法

##### update_fps_thresholds()

更新 FPS 阈值。

```python
def update_fps_thresholds(self, warning_fps: float = None, critical_fps: float = None, **kwargs) -> None
```

**参数**：
- `warning_fps` (float): 警告阈值
- `critical_fps` (float): 严重阈值
- `**kwargs`: 其他阈值参数

**示例**：
```python
thresholds = ThresholdManager()
thresholds.update_fps_thresholds(
    warning_fps=30.0,
    critical_fps=20.0,
    big_jank_frame_time_ms=100.0
)
```

##### update_memory_thresholds()

更新内存阈值。

```python
def update_memory_thresholds(self, high_memory_mb: float = None, **kwargs) -> None
```

##### update_cpu_thresholds()

更新 CPU 阈值。

```python
def update_cpu_thresholds(self, high_cpu_percent: float = None, **kwargs) -> None
```

##### reset_to_defaults()

重置为默认阈值。

```python
def reset_to_defaults(self) -> None
```

##### save_to_file()

保存阈值到文件。

```python
def save_to_file(self, path: str) -> None
```

##### load_from_file()

从文件加载阈值。

```python
def load_from_file(self, path: str) -> None
```

## 3. 数据模块接口 (data/)

### 3.1 DatabaseManager

**模块路径**：`insight_eyes.desktop.data.database`

**类名**：`DatabaseManager`

**设计模式**：单例模式

#### 主要方法

##### upsert_device()

插入或更新设备信息。

```python
def upsert_device(self, device_id: str, name: str, platform: str, **kwargs) -> None
```

**参数**：
- `device_id` (str): 设备 ID
- `name` (str): 设备名称
- `platform` (str): 平台（android/ios）
- `**kwargs`: 其他设备信息

**示例**：
```python
db = DatabaseManager()
db.upsert_device(
    device_id='emulator-5554',
    name='Android Emulator',
    platform='android',
    model='Pixel 5',
    os_version='Android 13'
)
```

##### create_session()

创建监控会话。

```python
def create_session(self, device_id: str, package_name: str, sample_interval: int = 1000, tags: dict = None) -> int
```

**参数**：
- `device_id` (str): 设备 ID
- `package_name` (str): 应用包名
- `sample_interval` (int): 采样间隔（毫秒）
- `tags` (dict, 可选): 场景标记

**返回值**：
- `int`: 会话 ID

**示例**：
```python
session_id = db.create_session(
    device_id='emulator-5554',
    package_name='com.example.app',
    sample_interval=1000,
    tags={'scenario': 'performance_test'}
)
```

##### save_metrics()

保存性能指标。

```python
def save_metrics(self, session_id: int, metrics: dict) -> None
```

**参数**：
- `session_id` (int): 会话 ID
- `metrics` (dict): 指标数据

**示例**：
```python
db.save_metrics(session_id, {
    'cpu_app': 25.5,
    'memory_pss': 180.3,
    'fps': 58.0,
    'network_up_speed': 50.5,
    'network_down_speed': 200.3,
    'battery_level': 85.0
})
```

##### save_metrics_batch()

批量保存指标（性能优化）。

```python
def save_metrics_batch(self, metrics_list: List[dict]) -> None
```

**参数**：
- `metrics_list` (List[dict]): 指标列表

**示例**：
```python
batch = [
    {'session_id': 1, 'cpu_app': 25.5, 'fps': 58.0},
    {'session_id': 1, 'cpu_app': 26.0, 'fps': 59.0},
    # ...更多数据
]
db.save_metrics_batch(batch)
```

##### get_metrics()

查询指标数据。

```python
def get_metrics(self, session_id: int, start_time: datetime = None, end_time: datetime = None, limit: int = None) -> List[dict]
```

**参数**：
- `session_id` (int): 会话 ID
- `start_time` (datetime, 可选): 开始时间
- `end_time` (datetime, 可选): 结束时间
- `limit` (int, 可选): 返回数量限制

**返回值**：
- `List[dict]`: 指标列表

**示例**：
```python
# 获取会话所有数据
metrics = db.get_metrics(session_id)

# 获取最近 1 小时的数据
from datetime import datetime, timedelta
end = datetime.now()
start = end - timedelta(hours=1)
metrics = db.get_metrics(session_id, start, end)
```

##### save_alert()

保存告警。

```python
def save_alert(self, session_id: int, alert: dict) -> int
```

**参数**：
- `session_id` (int): 会话 ID
- `alert` (dict): 告警数据

**返回值**：
- `int`: 告警 ID

**示例**：
```python
alert_id = db.save_alert(session_id, {
    'alert_type': 'high_memory',
    'metric_name': 'memory_pss',
    'current_value': 250.0,
    'threshold_value': 200.0,
    'severity': 'warning',
    'description': '内存使用超过阈值'
})
```

##### get_alerts()

查询告警。

```python
def get_alerts(self, session_id: int = None, severity: str = None, resolved: bool = None) -> List[dict]
```

**参数**：
- `session_id` (int, 可选): 会话 ID
- `severity` (str, 可选): 严重程度（warning/critical）
- `resolved` (bool, 可选): 是否已解决

**返回值**：
- `List[dict]`: 告警列表

##### end_session()

结束会话。

```python
def end_session(self, session_id: int) -> None
```

**示例**：
```python
db.end_session(session_id)
```

##### cleanup_old_data()

清理过期数据。

```python
def cleanup_old_data(self, retention_days: int = 7) -> dict
```

**参数**：
- `retention_days` (int): 保留天数

**返回值**：
```python
{
    'metrics_deleted': int,
    'alerts_deleted': int,
    'sessions_deleted': int
}
```

### 3.2 MetricsRepository

**模块路径**：`insight_eyes.desktop.data.repository`

**类名**：`MetricsRepository`

#### 主要方法

##### get_fps_trend()

获取 FPS 趋势。

```python
def get_fps_trend(self, session_id: int) -> List[tuple]
```

**返回值**：
- `List[tuple]`: [(timestamp, fps_value), ...]

##### get_memory_trend()

获取内存趋势。

```python
def get_memory_trend(self, session_id: int) -> List[tuple]
```

##### get_statistics()

获取统计数据。

```python
def get_statistics(self, session_id: int) -> dict
```

**返回值**：
```python
{
    'fps': {
        'avg': float,
        'max': float,
        'min': float,
        'std': float,
        'p50': float,
        'p95': float,
        'p99': float
    },
    'cpu_app': { /* 同上 */ },
    'memory_pss': { /* 同上 */ }
    # ...
}
```

##### get_aggregated_metrics()

获取聚合数据。

```python
def get_aggregated_metrics(self, session_id: int, interval_seconds: int = 60) -> List[dict]
```

**参数**：
- `session_id` (int): 会话 ID
- `interval_seconds` (int): 聚合间隔（秒）

**返回值**：
- `List[dict]`: 聚合后的数据

### 3.3 DataExporter

**模块路径**：`insight_eyes.desktop.data.exporter`

**类名**：`DataExporter`

#### 主要方法

##### export_to_csv()

导出为 CSV。

```python
def export_to_csv(self, session_id: int, output_path: str) -> bool
```

**参数**：
- `session_id` (int): 会话 ID
- `output_path` (str): 输出文件路径

**返回值**：
- `bool`: 是否成功导出

**示例**：
```python
from data import DatabaseManager, DataExporter

db = DatabaseManager()
exporter = DataExporter(db)
exporter.export_to_csv(session_id, 'metrics.csv')
```

##### export_to_json()

导出为 JSON。

```python
def export_to_json(self, session_id: int, output_path: str) -> bool
```

##### export_to_excel()

导出为 Excel（多工作表）。

```python
def export_to_excel(self, session_id: int, output_path: str) -> bool
```

**工作表**：
1. 会话概览
2. 性能指标
3. 统计数据
4. 告警记录
5. 趋势数据

##### generate_report()

生成 Markdown 测试报告。

```python
def generate_report(self, session_id: int, output_dir: str) -> str
```

**参数**：
- `session_id` (int): 会话 ID
- `output_dir` (str): 输出目录

**返回值**：
- `str`: 报告文件路径

##### export_batch()

批量导出。

```python
def export_batch(self, session_ids: List[int], output_dir: str, format: str = 'excel') -> List[str]
```

**参数**：
- `session_ids` (List[int]): 会话 ID 列表
- `output_dir` (str): 输出目录
- `format` (str): 导出格式（csv/json/excel）

**返回值**：
- `List[str]`: 导出的文件路径列表

## 4. 配置模块接口 (config/)

### 4.1 ConfigManager

**模块路径**：`insight_eyes.desktop.config.config_manager`

**函数**：`get_config_manager()`

**返回值**：`ConfigManager` 单例实例

#### 主要方法

##### get_app_config()

获取应用配置。

```python
def get_app_config(self) -> AppConfig
```

**返回值**：
```python
AppConfig(
    data_dir=str,              # 数据目录
    log_level=str,             # 日志级别
    log_dir=str,               # 日志目录
    db_path=str,               # 数据库路径
    auto_save_interval=int,    # 自动保存间隔（秒）
    retention_days=int         # 数据保留天数
)
```

##### get_ui_config()

获取 UI 配置。

```python
def get_ui_config(self) -> UIConfig
```

**返回值**：
```python
UIConfig(
    theme=str,                 # 主题
    sample_interval=int,       # 默认采样间隔（毫秒）
    chart_points=int,          # 图表最大数据点数
    enable_animations=bool,    # 是否启用动画
    window_width=int,          # 窗口宽度
    window_height=int          # 窗口高度
)
```

##### save_app_config()

保存应用配置。

```python
def save_app_config(self, config: AppConfig) -> None
```

##### save_ui_config()

保存 UI 配置。

```python
def save_ui_config(self, config: UIConfig) -> None
```

##### reset_to_defaults()

重置为默认配置。

```python
def reset_to_defaults(self) -> None
```

## 5. 错误码定义

### 5.1 设备连接错误

| 错误码 | 常量名 | 含义 |
|--------|--------|------|
| `E001` | `DEVICE_NOT_FOUND` | 设备未找到 |
| `E002` | `DEVICE_UNAUTHORIZED` | 设备未授权 |
| `E003` | `DEVICE_OFFLINE` | 设备离线 |
| `E004` | `ADB_NOT_FOUND` | ADB 未安装 |
| `E005` | `PMD3_NOT_FOUND` | pymobiledevice3 未安装 |
| `E006` | `DEVICE_NOT_TRUSTED` | iOS 设备未信任电脑 |
| `E007` | `DEVELOPER_MODE_DISABLED` | iOS 开发者模式未启用 |

### 5.2 采集错误

| 错误码 | 常量名 | 含义 |
|--------|--------|------|
| `E101` | `APP_NOT_RUNNING` | 应用未运行 |
| `E102` | `PERMISSION_DENIED` | 权限不足 |
| `E103` | `COLLECTION_TIMEOUT` | 采集超时 |
| `E104` | `INVALID_DATA` | 数据格式错误 |

### 5.3 数据库错误

| 错误码 | 常量名 | 含义 |
|--------|--------|------|
| `E201` | `DB_LOCKED` | 数据库被锁定 |
| `E202` | `DB_CORRUPTED` | 数据库损坏 |
| `E203` | `SESSION_NOT_FOUND` | 会话不存在 |
| `E204` | `DISK_FULL` | 磁盘空间不足 |

### 5.4 UI 错误

| 错误码 | 常量名 | 含义 |
|--------|--------|------|
| `E301` | `INVALID_CONFIG` | 配置无效 |
| `E302` | `EXPORT_FAILED` | 导出失败 |
| `E303` | `IMPORT_FAILED` | 导入失败 |

## 6. 事件与信号

### 6.1 设备事件

| 事件名 | 参数 | 触发时机 |
|--------|------|----------|
| `device_discovered` | `DeviceInfo` | 发现新设备 |
| `device_lost` | `device_id: str` | 设备断开 |
| `device_updated` | `DeviceInfo` | 设备信息更新 |
| `app_list_updated` | `device_id, apps` | 应用列表更新 |

### 6.2 监控事件

| 事件名 | 参数 | 触发时机 |
|--------|------|----------|
| `monitoring_started` | - | 开始监控 |
| `monitoring_stopped` | - | 停止监控 |
| `monitoring_paused` | - | 暂停监控 |
| `metrics_updated` | `ProcessedMetrics` | 指标更新 |
| `alert_triggered` | `Alert` | 检测到异常 |

### 6.3 UI 事件

| 事件名 | 参数 | 触发时机 |
|--------|------|----------|
| `device_selected` | `device_id: str` | 选择设备 |
| `app_selected` | `device_id, package_name` | 选择应用 |
| `monitor_toggled` | `device_id, package_name, enabled` | 切换监控状态 |
| `scenario_marked` | `scenario_name: str` | 标记场景 |
| `config_changed` | `config: dict` | 配置变更 |

## 7. 使用示例

### 7.1 完整监控流程

```python
from PyQt6.QtWidgets import QApplication
from desktop.ui.main_window import MainWindow
import sys

app = QApplication(sys.argv)
window = MainWindow()
window.show()

# 连接信号
window.device_manager.device_discovered.connect(
    lambda device: print(f"发现设备: {device.name}")
)

window.monitor_panel.metrics_updated.connect(
    lambda metrics: print(f"FPS: {metrics.fps.fps}")
)

sys.exit(app.exec())
```

### 7.2 自定义分析

```python
from desktop.analytics import MetricsProcessor, AnomalyDetector, ThresholdManager
from desktop.data import DatabaseManager

# 初始化
db = DatabaseManager()
thresholds = ThresholdManager()
thresholds.update_fps_thresholds(warning_fps=25.0, critical_fps=15.0)

processor = MetricsProcessor(session_id=1, device_id='xxx', app_id='com.app')
detector = AnomalyDetector(session_id=1, threshold_manager=thresholds)

# 处理数据
raw_data = {...}  # 从 APM 获取
metrics = processor.process_raw_data(raw_data)
alerts = detector.detect_all(metrics)

# 保存到数据库
session_id = db.create_session('device_id', 'com.app')
db.save_metrics(session_id, metrics.to_dict())
for alert in alerts:
    db.save_alert(session_id, alert.to_dict())
```

### 7.3 数据导出

```python
from desktop.data import DatabaseManager, DataExporter

db = DatabaseManager()
exporter = DataExporter(db)

# 导出单个会话
exporter.export_to_excel(session_id=1, 'output/session1.xlsx')

# 批量导出
files = exporter.export_batch(
    session_ids=[1, 2, 3],
    output_dir='output/',
    format='json'
)

# 生成报告
report_path = exporter.generate_report(session_id=1, 'output/')
print(f"报告已生成: {report_path}")
```

---

**文档维护**：本文档应随代码变更同步更新，确保接口文档的准确性。
