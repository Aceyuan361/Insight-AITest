# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Communication Language

**用户是中文使用者，请尽可能使用中文与用户交流。在代码开发过程中，注释应使用中文编写，专业术语可以使用英文。**

## Project Overview

**Insight-Eye** 是一个移动设备性能监控工具，支持 Android/iOS 应用程序的实时性能数据采集。提供 Python API 和 PyQt6 桌面 GUI 应用（赛博朋克霓虹风格）。

```
insight_eyes/
├── __main__.py           # 入口点: `python -m insight_eyes`
├── public/               # 核心性能监控库
│   ├── adb/              # ADB 封装，用于 Android 通信
│   ├── android/          # Android 平台采集器
│   ├── ios/              # iOS 平台采集器 (使用 tidevice)
│   └── common.py         # 设备检测 (Devices, Platform 枚举)
└── desktop/              # PyQt6 桌面应用
    ├── main.py           # 桌面应用入口
    ├── core/             # 设备管理、适配器、应用枚举
    ├── analytics/        # 数据分析、异常检测
    ├── data/             # 数据库、导出功能
    ├── ui/               # PyQt6 UI 组件、图表
    ├── config/           # 配置管理
    └── tools/            # 工具和调试脚本
```

## 运行应用

### 启动桌面应用
```bash
python -m insight_eyes
# 或
python insight_eyes/desktop/main.py
```

### 运行测试
```bash
# 运行所有测试
python -m pytest insight_eyes/desktop/tests/

# 运行特定测试
python insight_eyes/desktop/tests/test_all_fixes.py

# 验证修复
python insight_eyes/desktop/tests/test_all_fixes.py
```
- **必须执行**：每次bug修复完必须进行代码审查，审核通过后使用skills/testing-guide进行测试。

### 安装依赖
```bash
# 安装桌面应用依赖
pip install -r insight_eyes/desktop/requirements.txt

# 安装 iOS 支持 (可选)
pip install tidevice>=0.9.7
```

## Architecture

代码库采用**平台分离的采集器架构**：

```
┌─────────────────────────────────────────────────────┐
│           AndroidAPM / IOSAPM (Facade)              │
│  统一接口: collectCpu(), collectMemory(),           │
│           collectFps(), collectFlow(),              │
│           collectBattery(), collectGpu()            │
└──────────────────────────┬──────────────────────────┘
                           │
         ┌─────────────────┴─────────────────┐
         ▼                                   ▼
┌─────────────────────┐           ┌─────────────────────┐
│   Android 采集器     │           │    iOS 采集器       │
│ (public/android/)    │           │   (public/ios/)     │
├─────────────────────┤           ├─────────────────────┤
│ CPUCollector        │           │ CPUCollector        │
│ MemoryCollector     │           │ MemoryCollector     │
│ FPSMonitor          │           │ FPSCollector        │
│ NetworkCollector    │           │ NetworkCollector    │
│ BatteryCollector    │           │ BatteryCollector    │
└─────────────────────┘           └─────────────────────┘
         │                                   │
         ▼                                   ▼
┌─────────────────────┐           ┌─────────────────────┐
│   ADB (adb/)        │           │   tidevice (ext)    │
│   ADBHelper class   │           │   subprocess 调用   │
└─────────────────────┘           └─────────────────────┘
```

### 设计模式

- **Facade Pattern**: APM 类提供统一接口
- **Factory Pattern**: DeviceAdapterFactory, AppEnumeratorFactory
- **Adapter Pattern**: 平台特定的设备适配器
- **Observer Pattern**: Qt signals/slots 事件处理
- **Strategy Pattern**: DeviceProfile 根据设备选择最优采集策略

## Dependencies

### 核心运行时
```
PyQt6>=6.4.0          # GUI 框架
pyqtgraph>=0.13.0     # 实时图表
numpy>=1.23.0         # 数值计算
logzero>=1.7.0        # 日志
```

### 平台特定
```
tidevice>=0.9.7       # iOS 设备支持 (可选)
sqlite3               # 内置于 Python
```

### 外部工具
- **ADB** (Android Debug Bridge) - Android 设备通信必需
- **tidevice** - iOS 设备通信必需

## Key Classes and Interfaces

### APM Facades

**AndroidAPM** (`public/android/android_apm.py`):
```python
apm = AndroidAPM(package_name='com.example.app', device_id='device_id')
apm.start()
cpu = apm.collectCpu()  # {'appCpuRate': float, 'sysCpuRate': float}
memory = apm.collectMemory()  # {'totalPass': float, 'nativePass': float, 'dalvikPass': float}
fps = apm.collectFps()  # {'fps': int, 'jank': int, 'bigJank': int, 'ftime_avg': float, ...}
flow = apm.collectFlow()  # {'upFlow': float, 'downFlow': float}
battery = apm.collectBattery()  # {'level': int, 'temperature': float, 'current': float, ...}
gpu = apm.collectGpu()  # 返回 0 (未实现)
apm.stop()
```

**IOSAPM** (`public/ios/ios_apm.py`):
```python
apm = IOSAPM(bundleId='com.example.app', udid='device_udid')
# 与 AndroidAPM 相同的接口
```

### Platform Collectors

**CPUCollector** (`public/android/cpu_collector.py`):
```python
from insight_eyes.public.android.cpu_collector import CPUCollector

collector = CPUCollector('com.example.app', device_id='device_id')
cpu_data = collector.collect()

# CPU 采集策略（自动降级）:
# 1. 精确算法: 读取 /proc/stat 和 /proc/[pid]/stat 计算差值
#    - 优点: 准确反映实际 CPU 使用率
#    - 缺点: 需要两次采样，计算 delta
# 2. top 命令: 解析 top 输出获取瞬时 CPU
#    - 优点: 单次采样，快速响应
#    - 缺点: 数值波动大，可能不准确

# 返回值: {'appCpuRate': float, 'sysCpuRate': float}
# 失败返回: None
```

**内部方法（精确算法）**:
```python
# 线程安全的 CPU 数据获取
collector._get_app_cpu_time_from_proc(pid)  # 从 /proc/[pid]/stat 读取进程 CPU 时间
collector._get_cpu_data_atomic(package_name)  # 线程安全的 CPU 数据获取
collector._parse_cpu_from_proc_stat(proc_stat_content)  # 解析 stat 文件内容
```

### Device Detection

**Devices** (`public/common.py`):
```python
d = Devices()
devices = d.getDevices()  # ["Android emulator-5554", "iOS iPhone (udid)"]
device_id = d.getIdbyDevice(device_str, Platform.Android)
ios_packages = d.getPkgnameByiOS(udid)
```

### ADB Wrapper

**ADBHelper** (`public/adb/__init__.py`):
```python
from insight_eyes.public.adb import adb
result = adb.shell('dumpsys cpuinfo', device_id='device_id')
devices = adb.devices()
```

### Desktop Core Components

**DeviceManager** (`desktop/core/device_manager.py`):
- 设备扫描、监控、重连 (带心跳检测)
- 指数退避重连策略

**DeviceAdapters** (`desktop/core/device_adapters.py`):
- 平台特定的设备适配器 (Android/iOS)

**AppEnumerator** (`desktop/core/app_enumerator.py`):
- 应用程序枚举 (两个平台)

**MetricsProcessor** (`desktop/analytics/metrics_processor.py`):
- 原始数据处理、派生指标计算

**AnomalyDetector** (`desktop/analytics/anomaly_detector.py`):
- 性能异常检测、告警抑制

## Platform-Specific Notes

### Android Collectors
- **CPU**:
  - **精确算法（推荐）**: 读取 `/proc/[pid]/stat` 和 `/proc/stat` 计算 delta
    - 线程安全：使用 `_cpu_data_lock` 保护
    - 降级机制：失败时自动切换到 top 命令
  - **top 命令（降级）**: 解析 `top -n 1` 输出
    - 支持多核 CPU：自动除以核心数
    - 小米设备：启用 `cpu_ansi_filter=True` 过滤 ANSI 转义码
- **Memory**: 解析 `dumpsys meminfo` 输出 (Total RSS/PSS, Native/Dalvik heaps)
- **FPS**: 使用 `dumpsys SurfaceFlinger --latency`，复杂的卡顿检测
- **Network**: 读取 `/proc/uid_stat/{uid}/tcp_rcv` 和 `tcp_snd`
- **Battery**: 解析 `dumpsys battery` 输出

### iOS Collectors
- **CPU/Memory/FPS**: 使用 `tidevice perf --bundleid <bundle_id> --io`
- **Network**: 返回 0 (不支持)
- **Battery**: 返回默认值 (支持有限)
- **GPU**: 返回 0 (未实现)

## Data Flow Pattern

每个采集器遵循以下模式：
1. **主要方法**: 尝试主要采集方式
2. **降级方案**: 如果主要方法失败，尝试替代解析
3. **默认值**: 如果全部失败，返回 0/默认字典

返回值:
- 成功: `dict` 包含指标特定的键
- 失败: `None` 或包含 0 的默认字典

### CPU 采集流程 (Android)

**精确算法（优先）**:
1. 第一次采样: 读取 `/proc/stat`（总 CPU 时间）+ `/proc/[pid]/stat`（进程 CPU 时间）
2. 等待采集间隔（通常 1 秒）
3. 第二次采样: 再次读取相同文件
4. 计算差值: (进程 CPU delta) / (总 CPU delta) × 100% × CPU 核心数

**降级方案**:
- 如果 `/proc` 文件不可读，使用 `top -n 1` 命令
- 解析 top 输出中的 CPU 列
- 处理多核设备: CPU% ÷ 核心数 = 实际使用率

## FPS Monitoring (Android)

Android FPS 采集器 (`android/fps_collector.py`) 比较复杂:
- **SurfaceStatsCollector**: 从 SurfaceFlinger 线程安全地采集帧数据
- **FPSMonitor**: 管理采集器的包装器
- 使用 `threading.RLock()` 保证线程安全，超时 2 秒
- 计算常规 Jank (>166ms 帧时间) 和 BigJank (>100ms)
- 支持旧版 `page_flip` 方法（旧 Android 版本）

## Thread Safety

- FPS 数据使用 `_fps_data_lock` (RLock) 在 `fps_collector.py`
- Network 采集器维护 `last_data` 和 `last_time` 字典用于速率计算
- 调用 `network_collector.reset(package_name)` 清除存储的数据
- Qt signals 确保线程安全通信
- 数据库使用线程本地连接

## Known Limitations

1. **iOS 17+ 需要额外依赖** - py-ios-device 和 pymobiledevice3（可选，会自动降级到 tidevice）
2. **GPU 监控未实现** - 两个平台都不支持
3. **iOS 网络流量** - 支持有限（iOS 17+ 可通过 py-ios-device 获取）
4. **Android FPS** - 需要 stop() 获取数据 (设计限制)

## iOS Monitoring Enhancement (2025-01-20)

### 混合架构
自动根据 iOS 版本选择最佳采集方案：
- **iOS 15-16**: tidevice（标准方案）
- **iOS 17-26**: py-ios-device + pymobiledevice3（优化方案），失败时自动降级到 tidevice

### 新增组件
| 组件 | 文件 | 功能 |
|------|------|------|
| IOSDependencyChecker | `dependency_checker.py` | 检测 py-ios-device 和 pymobiledevice3 可用性 |
| PyIOSConnection | `pyios_connect.py` | 管理 Instruments 服务连接 |
| IOSDataNormalizer | `data_normalizer.py` | 统一数据格式（兼容 tidevice） |
| IOSTunnelManager | `tunnel_manager.py` | pymobiledevice3 隧道管理 |
| SysMontapCollector | `pyios_collectors/sysmontap.py` | CPU/Memory/Network 采集 |
| GraphicsCollector | `pyios_collectors/graphics.py` | FPS/GPU 采集 |
| EnergyCollector | `pyios_collectors/energy.py` | Battery 采集 |

### 安装完整支持
```bash
pip install py-ios-device pymobiledevice3
```

### 安全增强
- ✅ UDID 验证（防止命令注入）
- ✅ 线程安全（网络速率计算）
- ✅ 资源清理健壮性

### 文档
- 设计文档: `docs/plans/2025-01-20-ios-monitoring-upgrade-design.md`
- 实施报告: `docs/ios-monitoring-upgrade-implementation-report.md`

---

## 📚 Claude Code Skills

项目有 5 个专业 Skills（关键词自动触发）：

| Skill | 触发关键词 |
|-------|-----------|
| apm-collector-dev | create collector, APM collector, performance collector |
| insight-eye-coding-standards | code style, review code, format code |
| device-profile-guide | add device support, configure device profile |
| pyqt6-ui-patterns | create UI component, PyQt6 interface, add widget |
| testing-guide | write tests, create unit tests, test APM collector |

📖 详见：`docs/Skills创建总结.md`

## 🤖 AI Agent Team

6 位专业智能体（使用 `@agent_name` 调用）：

- `@senior_architect` - 架构设计、性能优化、并发编程
- `@android_expert` - ADB、FPS/CPU/Memory 监控、dumpsys
- `@ios_expert` - tidevice、iOS 性能监控限制
- `@ui_design_director` - PyQt6、赛博朋克风格、数据可视化
- `@code_reviewer` - PEP 8、线程安全、代码质量
- `@test_engineer` - 集成测试、性能测试、兼容性

### 使用方式
```
@android_expert 分析 FPS 采集问题         # 单个智能体
@android_expert,@test_engineer 编写测试    # 多智能体协作
@all 评审架构设计                          # 全团队
```

📖 详见：`.agents/README.md`

### 何时使用
- 简单任务 → Skills 自动加载
- 复杂任务/跨模块 → 使用 `@agent_name` 或 `@all`

---

## ⚠️ 已知陷阱与避坑指南

> 本章节记录项目开发中遇到的常见问题和解决方案，避免重复犯错。
> 格式：问题 → 原因 → 解决

### Android 采集

| 问题 | 原因 | 解决 |
|------|------|------|
| FPS 返回 0 | 活动名解析不完整 (如 `com.app/.ui.MainActivity`) | 使用完整包名+活动名 |
| CPU 解析失败 | 小米 top 输出含 ANSI 转义码 | 启用 `cpu_ansi_filter=True` |
| 网络采集权限 | /proc/uid_stat 需要 shell 包装 | 使用 `sh -c 'cat ...'` |
| **FPS 内存泄漏** | 队列无界增长导致 OOM | 使用 `queue.Queue(maxsize=100)` 有界队列 |
| **网络采集除零** | 高频采集时时间间隔接近 0 | 添加 `MIN_TIME_INTERVAL = 0.01s` 检查 |
| **设备缓存泄漏** | 断开设备后缓存未清理 | 实现 LRU 淘汰策略 (maxsize=100) |
| **CPU 数据不准确** | top 命令瞬时值波动大，无法反映真实 CPU 使用率 | 实现 `/proc/stat` delta 算法，读取进程累计 CPU 时间差值计算 |
| **CPU 采集竞态** | 多线程读取 /proc 文件系统时数据不一致 | 使用 `threading.Lock` 保护 `_last_cpu_data` 字典 |

### PyQt6 UI

| 问题 | 原因 | 解决 |
|------|------|------|
| 线程不安全 | 直接在工作线程更新 UI | 使用信号/槽 + @pyqtSlot |
| 内存泄漏 | 信号连接未断开 | 对象销毁时 `disconnect()` |
| 图表卡顿 | 更新频率过高 | 限制 ≤30fps，使用 QThreadPool |
| **线程清理失败** | 使用 `terminate()` 导致段错误 | 使用 `wait(5000)` + 断开所有信号 |
| **UI 冻结** | 数据库操作阻塞主线程 | 使用 `QThreadPool` 异步保存 |
| **UI 节流丢数据** | 节流时丢失 metrics 数据 | 补偿机制仅清除标志 |
| **信号断开异常** | disconnect 调用未连接的信号导致 TypeError | 在 `_connect_signal` 中验证连接结果，仅在成功时保存引用 |
| **ConfigManager 单例崩溃** | 多线程访问 QObject 单例导致竞争条件 | 使用本地配置对象，避免访问 ConfigManager |

### ADB & 安全

| 问题 | 原因 | 解决 |
|------|------|------|
| **命令注入** | 字符串拼接构建命令 | 使用参数列表 + 输入验证 |
| **Windows ADB 不兼容** | Windows 不支持 `sh -c` | 使用 `subprocess.run(shell=False, cmd_list)` |

### 数据持久化

| 问题 | 原因 | 解决 |
|------|------|------|
| **配置文件损坏** | 写入过程中崩溃 | 使用临时文件 + `os.replace()` 原子重命名 |
| **JSON 解析崩溃** | 配置文件格式错误 | 捕获 `JSONDecodeError` + 默认配置 |
| **数据库单例失效** | 不同 db_path 绕过检查 | 缓存首次创建的 db_path |

### 线程安全

| 问题 | 原因 | 解决 |
|------|------|------|
| **APM 实例竞态** | 双重检查锁定不完整 | 明确锁保护范围，完善文档 |
| **deque 线程不安全** | 并发访问导致数据损坏 | 使用 `threading.Lock` 保护操作 |
| **CPU 数据竞态** | 多线程访问 `_last_cpu_data` 导致数据不一致 | 使用 `threading.Lock` 保护 `_last_cpu_data` 字典读写 |

### 设备适配

| 问题 | 原因 | 解决 |
|------|------|------|
| 华为 FPS 不稳定 | gfxinfo 不可靠 | 使用 `surfaceflinger_latency` |
| 小米命令异常 | 窗口名含 `$` 需转义 | `fps_window_name_escape=True` |

---

## Desktop Application Structure

```
desktop/
├── main.py                  # 应用入口
├── requirements.txt         # Python 依赖
├── core/                    # 核心业务逻辑
│   ├── device_manager.py    # 设备管理器 (扫描、监控、重连)
│   ├── device_adapters.py   # 平台特定设备适配器
│   ├── app_enumerator.py    # 应用枚举
│   └── models.py            # 数据模型
├── analytics/               # 分析模块
│   ├── metrics_processor.py # 指标处理
│   ├── anomaly_detector.py  # 异常检测
│   ├── statistics.py        # 统计分析
│   ├── correlation_analyzer.py  # 关联分析
│   └── thresholds.py        # 阈值管理
├── data/                    # 数据持久化
│   ├── database.py          # SQLite 数据库
│   ├── repository.py        # 数据访问层
│   └── exporter.py          # 数据导出 (CSV/JSON/Excel/MD)
├── ui/                      # 用户界面
│   ├── main_window.py       # 主窗口
│   ├── panels/              # UI 面板
│   │   ├── monitor_panel_v2.py    # 监控面板 V2
│   │   ├── device_selection_panel.py  # 设备选择
│   │   └── config_panel.py    # 配置面板
│   ├── charts/              # 图表组件
│   │   └── trend_chart.py   # 实时趋势图
│   ├── widgets/             # 自定义控件
│   └── styles.qss           # 赛博朋克样式表
├── config/                  # 配置管理
│   └── config_manager.py    # 配置管理器
├── docs/                    # 文档
│   ├── architecture.md      # 架构文档
│   ├── api-reference.md     # API 参考
│   ├── database-design.md   # 数据库设计
│   └── user-guide.md        # 用户指南
└── tests/                   # 测试
    ├── test_all_fixes.py    # 修复验证测试
    ├── test_integration.py  # 集成测试
    └── test_device_manager.py  # 设备管理测试
```

## 数据库设计

使用 SQLite 存储监控数据：

- **devices**: 设备信息
- **applications**: 应用信息
- **monitoring_sessions**: 监控会话
- **metrics_samples**: 指标样本数据
- **alerts**: 告警记录

详见 `desktop/docs/database-design.md`

## UI Design System

- **主题**: Cyberpunk Neon (赛博朋克霓虹)
- **主色**: #00d4ff (霓虹蓝)
- **组件**: 霓虹卡片、渐变进度条、实时图表
- **样式文件**: `ui/styles.qss`, `ui/styles_improved.qss`

## Export Formats

支持多种数据导出格式：
- CSV
- JSON
- Excel (需要 openpyxl)
- Markdown

通过 `desktop/data/exporter.py` 实现

---

## 项目更新日志

### 2025-01-19 (功能增强 v2.0)

**监控面板优化:**
- 实现曲线抗锯齿和样条插值
- 增加数据悬停提示功能（垂直参考线 + 数据点高亮 + 浮动提示框）
- 支持动态卡片配置（CPU/内存/FPS/网络/电池/GPU）
- 自适应网格布局系统（1-4列，根据卡片数量自动调整）
- 数据点数量从 60 增加到 120，获得更细腻的曲线

**测试报告功能:**
- 新增独立测试报告面板（report_panel.py）
- 支持历史监控会话列表查看
- 详细数据展示和图表重现
- 监控结束处理动画

**配置管理:**
- 新增卡片配置模型 (ui/utils/card_configs.py)
- CollectionConfig 支持指标开关（set_metric_enabled）
- 配置面板新增指标选择器
- 配置变更实时生效

**技术改进:**
- NeonChartCard 新增悬停提示功能（_on_mouse_moved）
- MonitorPanelV2 实现动态卡片重建（_rebuild_cards）
- 新增测试文件：test_monitor_panel_enhancements.py
- 新增用户指南：monitor-panel-optimization-guide.md

### 2025-01-19 (CPU 采集器优化)

**功能增强:**
- Android CPU 采集器重构：实现 /proc/stat delta 精确算法
- 添加线程安全的 CPU 数据缓存机制
- 优化多核设备的 CPU 使用率计算

**Bug 修复:**
- 修复监控停止时信号断开异常
- 修复信号连接未验证导致的 TypeError
- 改进 _disconnect_collection_signals 异常处理

**技术改进:**
- CPUCollector 新增 _get_app_cpu_time_from_proc() 方法
- CPUCollector 新增 _get_cpu_data_atomic() 线程安全方法
- CPUCollector 新增 _parse_cpu_from_proc_stat() 解析方法
- MainWindow 改进信号连接验证逻辑

---

### 2025-01-19 (Bug 修复与用户体验优化)

**Bug 修复:**
- ✅ 修复电池/GPU复选框崩溃问题（ConfigManager 单例竞争条件）
- ✅ 优化批量删除会话功能（从多次弹窗优化为一次提示）

**功能增强:**
- ✅ 添加详细的 DEBUG 日志追踪功能
- ✅ CSV 导出增加格式化时间戳列
- ✅ 禁用图表鼠标缩放功能

**技术改进:**
- config_panel.py: 使用本地配置对象替代 ConfigManager 单例，避免多线程竞争条件
- monitor_panel_v2.py: refresh_cards 方法接收配置字典参数，简化调用链
- session_manager.py: delete_session 添加 emit_signal 参数控制信号发射
- report_panel.py: 新增 sessions_deleted 信号处理方法，优化批量删除体验

**测试结果:**
- 批量删除 12 个会话，只弹出 1 次结果窗口（之前会弹出 12 次）
- 批量删除 10 个会话，只弹出 1 次结果窗口（之前会弹出 10 次）
- 勾选电池/GPU 复选框不再崩溃，监控面板正确显示新增卡片
- 单个删除功能保持向后兼容，仍然正常工作
