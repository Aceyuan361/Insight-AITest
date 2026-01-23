# Insight-Eye 架构设计文档

## 文档信息

| 项目 | 内容 |
|------|------|
| 文档名称 | Insight-Eye 架构设计文档 |
| 版本 | 1.0.1 |
| 更新日期 | 2025-01-23 |

## 1. 概述

### 1.1 项目简介

Insight-Eye 是一个移动设备性能监控工具，支持 Android 和 iOS 平台。它采用 PyQt6 构建桌面应用，提供实时性能监控、数据采集、异常检测、数据分析和可视化等功能。

### 1.2 设计目标

- **无侵入式监控**：无需 root/越狱，不修改应用代码
- **实时性**：低延迟采集和展示性能数据
- **可扩展性**：模块化设计，易于添加新功能
- **用户友好**：直观的 UI，简洁的操作流程
- **高性能**：支持多设备并行监控

### 1.3 技术栈

| 类别 | 技术 |
|------|------|
| GUI 框架 | PyQt6 |
| 图表库 | pyqtgraph |
| 数据库 | SQLite3 |
| Android 通信 | ADB (Android Debug Bridge) |
| iOS 通信 | pymobiledevice3 |
| 日志 | logzero |
| 数据处理 | NumPy |

## 2. 整体架构

### 2.1 分层架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     Presentation Layer (UI层)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ DevicePanel  │  │ MonitorPanel │  │ ConfigPanel  │         │
│  │  (设备列表)   │  │  (监控面板)   │  │  (配置面板)   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              ↓↑
┌─────────────────────────────────────────────────────────────────┐
│                     Business Logic Layer (业务逻辑层)            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ DeviceManager│  │ MetricsProc  │  │ AnomalyDetect│         │
│  │  (设备管理)   │  │  (指标处理)   │  │  (异常检测)   │         │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤         │
│  │AppEnumerator │  │  Statistics  │  │  Correlation │         │
│  │  (应用枚举)   │  │  (统计分析)   │  │  (关联分析)   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              ↓↑
┌─────────────────────────────────────────────────────────────────┐
│                     Data Access Layer (数据访问层)               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │DatabaseManager│  │  Repository │  │   Exporter   │         │
│  │  (数据库管理)  │  │  (数据访问)   │  │  (数据导出)   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              ↓↑
┌─────────────────────────────────────────────────────────────────┐
│                    Infrastructure Layer (基础设施层)              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │DeviceAdapter │  │  ConfigMgr   │  │   Logger     │         │
│  │  (设备适配)   │  │  (配置管理)   │  │  (日志记录)   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              ↓↑
┌─────────────────────────────────────────────────────────────────┐
│                     Device Layer (设备层)                        │
│  ┌──────────────┐                    ┌──────────────┐         │
│  │  ADB         │                    │pymobiledevice│         │
│  │  (Android)   │                    │    3 (iOS)   │         │
│  └──────────────┘                    └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 核心模块

| 模块 | 文件路径 | 职责 |
|------|----------|------|
| 设备管理 | `core/` | 设备连接、应用枚举、设备监控 |
| 数据采集 | `public/` | 性能指标采集（FPS/CPU/内存/网络/电池） |
| 数据处理 | `analytics/` | 指标处理、异常检测、统计分析 |
| 数据存储 | `data/` | 数据库管理、数据导出 |
| 用户界面 | `ui/` | 主窗口、面板、图表、控件 |
| 配置管理 | `config/` | 应用配置、UI配置 |

### 2.3 解耦设计

```
采集层 ←→ 传输层 ←→ 存储层 ←→ 展示层
   ↓         ↓         ↓         ↓
  ADB     信号槽    SQLite    PyQt6
tidevice   事件     数据库    图表
```

## 3. 模块划分

### 3.1 核心模块 (core/)

**文件结构**：
```
core/
├── models.py              # 数据模型（设备、应用、配置）
├── device_manager.py      # 设备管理器
├── device_adapters.py     # 设备适配器（Android/iOS）
├── app_enumerator.py      # 应用枚举器
├── __init__.py
└── example_usage.py       # 使用示例
```

**核心类**：

| 类名 | 职责 |
|------|------|
| `DeviceManager` | 设备扫描、监控、信号分发 |
| `AndroidDeviceAdapter` | Android 设备通信 |
| `IOSDeviceAdapter` | iOS 设备通信 |
| `AndroidAppEnumerator` | Android 应用枚举 |
| `IOSAppEnumerator` | iOS 应用枚举 |
| `DeviceInfo` | 设备信息数据模型 |
| `AppInfo` | 应用信息数据模型 |

**设计模式**：
- 工厂模式：`DeviceAdapterFactory`, `AppEnumeratorFactory`
- 适配器模式：统一不同平台的设备接口
- 观察者模式：Qt 信号槽机制

### 3.2 数据采集模块 (public/)

**文件结构**：
```
analytics/
├── ios_session_monitor.py  # iOS 会话监控
├── ios_serial_collector.py # iOS 串口数据采集
└── metrics_batch_collector.py # 批量指标采集器
```

**采集指标**：

| 指标 | Android 实现 | iOS 实现 |
|------|-------------|----------|
| CPU | `dumpsys cpuinfo` | `sysmon` 命令 |
| 内存 | `dumpsys meminfo` | `sysmon` 命令 |
| FPS | `SurfaceFlinger` | 暂不支持 |
| 网络 | `/proc/uid_stat` | `sysmon` 命令 |
| 电池 | `dumpsys battery` | `sysmon` 命令 |
| GPU | 未实现 | 暂不支持 |

**iOS 数据采集说明**：

iOS 使用 `pymobiledevice3` 库通过 `sysmon` 命令采集性能数据：

1. **CPU 采集**：通过 sysmon 获取应用和系统 CPU 使用率
2. **内存采集**：获取应用的内存占用（物理内存、虚拟内存）
3. **网络采集**：获取网络流量统计（上行/下行）
4. **电池采集**：获取电池电量和温度

**限制说明**：

- iOS 平台暂不支持 FPS 监控（系统限制）
- iOS 平台暂不支持 GPU 监控
- 数据采集超时时间设置为 8 秒（iOS 响应较慢）

### 3.3 分析模块 (analytics/)

**文件结构**：
```
analytics/
├── models.py              # 分析数据模型
├── metrics_processor.py   # 指标处理器
├── anomaly_detector.py    # 异常检测器
├── statistics_analyzer.py # 统计分析器
├── correlation_analyzer.py# 关联分析器
├── thresholds.py          # 阈值管理器
├── test_analytics.py      # 单元测试
├── example_usage.py       # 使用示例
└── __init__.py
```

**核心功能**：

| 组件 | 功能 |
|------|------|
| `MetricsProcessor` | 原始数据清洗、派生指标计算、趋势分析 |
| `AnomalyDetector` | FPS/内存/CPU/网络异常检测 |
| `StatisticsAnalyzer` | 会话摘要、分位数、稳定性评分 |
| `CorrelationAnalyzer` | 异常关联分析、优化建议 |
| `ThresholdManager` | 阈值管理、持久化 |

**异常检测规则**：

- FPS < 30 → 警告，FPS < 20 → 严重
- 内存 5 分钟增长 > 100MB → 疑似泄露
- CPU > 80% → 高 CPU 警告
- 网络中断 > 5秒 → 连接问题

### 3.4 数据模块 (data/)

**文件结构**：
```
data/
├── database.py            # 数据库管理器
├── repository.py          # 数据访问层
├── exporter.py            # 数据导出器
├── init_db.py             # 初始化脚本
├── test_database.py       # 单元测试
├── example_usage.py       # 使用示例
└── __init__.py
```

**数据库表**：

| 表名 | 用途 |
|------|------|
| `devices` | 设备信息 |
| `apps` | 应用信息 |
| `monitoring_sessions` | 监控会话 |
| `performance_metrics` | 性能指标 |
| `alerts` | 异常告警 |
| `config_templates` | 配置模板 |

**导出格式**：
- CSV（简单数据交换）
- JSON（程序间数据交换）
- Excel（多工作表，可读性强）
- Markdown（测试报告）

### 3.5 UI 模块 (ui/)

**文件结构**：
```
ui/
├── main_window.py         # 主窗口
├── styles.qss             # 赛博朋克霓虹样式表
├── panels/                # 面板组件
│   ├── device_panel.py    # 设备列表面板
│   ├── monitor_panel.py   # 监控面板
│   └── config_panel.py    # 配置面板
├── widgets/               # 自定义控件
│   └── metrics_gauge.py   # 指标仪表盘
├── charts/                # 图表组件
│   └── trend_chart.py     # 趋势图
└── utils/                 # 工具模块
    └── models.py          # UI 数据模型
```

**UI 组件**：

| 组件 | 职责 |
|------|------|
| `MainWindow` | 主窗口、菜单栏、工具栏、状态栏 |
| `DeviceListPanel` | 设备树形列表、搜索、勾选 |
| `MonitorPanel` | 指标仪表盘、趋势图表、场景标记 |
| `ConfigPanel` | 采集配置、阈值设置、告警记录 |
| `MetricsDashboard` | 圆形仪表盘容器 |
| `ChartsContainer` | 趋势图容器（FPS/内存/CPU/网络/电池） |

## 4. 交互流程

### 4.1 设备连接流程

```
用户启动应用
    ↓
MainWindow.__init__()
    ↓
DeviceManager.start_scanning()
    ↓
DeviceScannerThread.run()
    ↓
定期调用 ADB.devices() / tidevice.list()
    ↓
发现新设备 → 发送 device_discovered 信号
    ↓
DeviceListPanel 添加设备到树形列表
    ↓
用户选择应用 → 发送 app_selected 信号
    ↓
MainWindow.set_monitoring_target()
    ↓
MonitorPanel 设置监控目标
```

### 4.2 监控流程

```
用户点击"开始监控"（或按 F5）
    ↓
MainWindow._start_monitoring()
    ↓
1. 创建 DatabaseManager 会话
2. 初始化 MetricsProcessor
3. 初始化 AnomalyDetector
4. 启动定时器 update_timer
    ↓
定时器触发（默认 1 秒间隔）
    ↓
MainWindow._on_update_timer()
    ↓
1. 调用 APM 采集指标（CPU/内存/FPS/网络/电池）
2. MetricsProcessor.process_raw_data() 处理数据
3. AnomalyDetector.detect_all() 检测异常
4. DatabaseManager.save_metrics() 保存数据
    ↓
发送信号更新 UI
    ↓
MonitorPanel.update_metrics() 更新仪表盘和图表
    ↓
ConfigPanel 显示告警（如有）
```

### 4.3 数据导出流程

```
用户点击"导出数据"（或按 Ctrl+E）
    ↓
MainWindow._export_data()
    ↓
显示文件选择对话框
    ↓
用户选择导出格式和路径
    ↓
DataExporter.export_to_*()
    ↓
1. DatabaseManager 查询数据
2. Repository 计算统计数据
3. 格式化输出（CSV/JSON/Excel/Markdown）
    ↓
显示导出成功消息
```

## 5. 技术选型

### 5.1 PyQt6

**选择理由**：
- 官方 Qt6 Python 绑定，稳定可靠
- 丰富的 UI 组件和布局管理
- 强大的信号槽机制，便于模块解耦
- 跨平台支持（Windows/macOS/Linux）

**替代方案对比**：
| 框架 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| PyQt6 | 官方支持、功能完整 | 许可证复杂 | ✅ |
| PySide6 | LGPL 许可证 | 社区较小 | ❌ |
| Tkinter | 标准库 | UI 简陋、不现代 | ❌ |
| Electron Web 技术栈 | 现代化 | 资源占用大 | ❌ |

### 5.2 pyqtgraph

**选择理由**：
- 专为科学数据可视化设计
- 基于 NumPy，性能优异
- 内置实时更新支持
- 轻量级，依赖少

**替代方案对比**：
| 库 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| pyqtgraph | 高性能、实时更新 | 文档较少 | ✅ |
| Matplotlib | 功能强大、文档完善 | 性能较差 | ❌ |
| Plotly | 交互性强 | Web 技术、性能差 | ❌ |

### 5.3 SQLite

**选择理由**：
- 轻量级，无需独立数据库服务
- Python 标准库支持
- 单文件存储，便于备份
- 支持 WAL 模式，性能良好

**数据量估算**：
- 每次采样约 200 字节
- 1 秒采样间隔，1 小时约 720 KB
- 10 个设备同时监控，1 天约 173 MB
- 结论：SQLite 完全够用

### 5.4 ADB 与 pymobiledevice3

**ADB（Android）**：
- Google 官方工具
- 功能完整、稳定可靠
- 支持无线调试

**pymobiledevice3（iOS）**：
- Python 实现，无需 Mac 电脑
- 通过 sysmon 采集性能数据
- 需要信任设备和启用开发者模式
- 功能受 Apple 系统限制

## 6. 性能设计

### 6.1 线程模型

```
主线程（UI 线程）
├── DeviceScannerThread（设备扫描，5 秒间隔）
├── DeviceMonitorThread（设备监控，10 秒间隔）
└── QTimer（数据采集更新，1 秒间隔）

工作线程
├── ADB 命令执行（异步）
├── tidevice 命令执行（异步）
└── 数据库写入（事务批处理）
```

**线程安全**：
- 使用 `threading.RLock()` 保护共享资源
- Qt 信号槽确保线程间通信安全
- 线程本地数据库连接

### 6.2 数据流优化

```python
# 1. 环形缓冲区限制内存
buffer_size = 1000  # 只保留最近 1000 条数据

# 2. 批量写入数据库
with db.transaction():
    for metric in metrics_batch:
        db.save_metrics(metric)

# 3. 异步采集
def _on_update_timer():
    # 非阻塞采集
    metrics = self.apm.collect_all()
    # 信号槽更新 UI
    self.metrics_ready.emit(metrics)
```

### 6.3 UI 性能

**图表优化**：
- 使用 `pyqtgraph` 的 `setDownsampling()` 降低采样率
- 限制最大数据点数
- 只更新可见区域

**动画优化**：
- 使用缓动函数减少帧数
- 数值变化时才触发重绘
- 动画完成后立即停止定时器

## 7. 扩展性设计

### 7.1 添加新的平台支持

```python
# 1. 继承 BaseDeviceAdapter
class HarmonyOSDeviceAdapter(BaseDeviceAdapter):
    def connect(self):
        # 实现连接逻辑
        pass

# 2. 注册到工厂
DeviceAdapterFactory.register('harmonyos', HarmonyOSDeviceAdapter)
```

### 7.2 添加新的指标类型

```python
# 1. 定义数据模型
@dataclass
class GPUMetrics:
    gpu_usage: float
    gpu_memory: float

# 2. 实现采集器
class GPUCollector:
    def collect(self):
        # 采集 GPU 数据
        pass

# 3. 集成到 UI
class GPUTrendChart(TrendChartWidget):
    pass
```

### 7.3 添加新的异常检测规则

```python
# 1. 定义 AlertType
class AlertType(Enum):
    HIGH_GPU = "high_gpu"

# 2. 实现检测方法
def detect_gpu_anomaly(self, metrics):
    if metrics.gpu.gpu_usage > 90:
        return Alert(...)

# 3. 注册到 AnomalyDetector
self.detector.register_rule('gpu', self.detect_gpu_anomaly)
```

## 8. 安全设计

### 8.1 数据安全

- 本地存储，不上传云端
- 配置文件明文存储（便于调试）
- 敏感信息（设备序列号）脱敏处理

### 8.2 权限控制

- ADB 需要用户授权
- iOS 需要信任电脑
- 不访问用户隐私数据

### 8.3 输入验证

- 设备 ID 格式验证
- 端口范围验证
- 文件路径验证

## 9. 错误处理

### 9.1 错误码定义

| 错误码 | 含义 | 处理方式 |
|--------|------|----------|
| `E001` | 设备未连接 | 提示用户检查连接 |
| `E002` | ADB 未启动 | 自动启动 ADB |
| `E003` | 应用未运行 | 提示用户启动应用 |
| `E004` | 权限不足 | 提示开启调试模式 |
| `E005` | 数据库错误 | 重试或提示修复 |

### 9.2 异常处理策略

```python
# 1. 采集层异常
try:
    metrics = self.apm.collect_all()
except Exception as e:
    logger.error(f"采集失败: {e}")
    return None  # 返回默认值

# 2. 业务层异常
try:
    processed = self.processor.process_raw_data(metrics)
except ValueError as e:
    logger.warning(f"数据异常: {e}")
    # 跳过该数据点

# 3. UI 层异常
try:
    self.monitor_panel.update_metrics(processed)
except Exception as e:
    logger.error(f"UI 更新失败: {e}")
    # 不影响主流程
```

## 10. 部署架构

### 10.1 单机部署

```
Windows/macOS/Linux
├── Python 3.9+
├── ADB（Android）
├── tidevice（iOS）
└── Insight-Eye
```

### 10.2 配置目录

```
~/.insight_eye/
├── config/
│   ├── app_config.json
│   └── ui_config.json
├── data/
│   └── insight_eye.db
└── logs/
    └── app.log
```

## 11. 版本规划

### v1.0.1（当前版本）

- ✅ 支持 iOS 设备连接和监控
- ✅ 使用 pymobiledevice3 替代 tidevice
- ✅ iOS sysmon 数据采集（CPU/内存/网络/电池）
- ✅ iOS 应用枚举支持
- ✅ 改进数据处理和错误处理
- ✅ 所有 v1.0.0 功能

### v1.0.0

- ✅ 基础设备连接
- ✅ Android 性能指标采集
- ✅ 实时监控 UI
- ✅ 异常检测
- ✅ 数据导出

### v1.1.0（规划中）

- [ ] GPU 监控
- [ ] Wi-Fi 无线调试
- [ ] 多设备对比视图
- [ ] 自定义仪表盘

### v2.0.0（远期规划）

- [ ] Web 版本
- [ ] 云端数据存储
- [ ] AI 性能优化建议
- [ ] 自动化测试集成

---

**文档维护**：本文档应随项目演进同步更新，确保架构设计文档始终反映最新的系统架构。
