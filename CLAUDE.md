# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Communication Language

**用户是中文使用者，请尽可能使用中文与用户交流。在代码开发过程中，注释应使用中文编写，专业术语可以使用英文。**

## Project Overview

**Insight-Eye** 是一个 Android 设备性能监控工具，提供 Python API 和 PyQt6 桌面 GUI 应用（赛博朋克霓虹风格）。

```
insight_eyes/
├── __main__.py           # 入口点: `python -m insight_eyes`
├── public/               # 核心性能监控库
│   ├── adb/              # ADB 封装
│   ├── android/          # Android 采集器
│   └── common.py         # 设备检测
└── desktop/              # PyQt6 桌面应用
    ├── main.py           # 应用入口
    ├── core/             # 设备管理、适配器、应用枚举
    ├── analytics/        # 数据分析、异常检测
    ├── data/             # 数据库、导出
    ├── ui/               # PyQt6 UI 组件、图表
    ├── config/           # 配置管理
    └── tools/            # 工具脚本
```

## 快速开始

### 启动应用
```bash
python -m insight_eyes
```

### 安装依赖
```bash
pip install -r insight_eyes/desktop/requirements.txt
```

### 外部依赖
- **ADB** (Android Debug Bridge) - Android 设备通信必需

## Architecture

```
┌─────────────────────────────────────┐
│         AndroidAPM (Facade)          │
│  collectCpu/Memory/Fps/Flow/Battery │
└────────────────┬────────────────────┘
                 │
                 ▼
    ┌────────────────────────┐
    │   Android 采集器        │
    │  (public/android/)      │
    ├────────────────────────┤
    │ CPUCollector           │
    │ MemoryCollector        │
    │ FPSMonitor             │
    │ NetworkCollector       │
    │ BatteryCollector       │
    └────────────────────────┘
                 │
                 ▼
    ┌────────────────────────┐
    │   ADB (adb/)           │
    └────────────────────────┘
```

## Key Classes

### AndroidAPM (`public/android/android_apm.py`)
```python
apm = AndroidAPM(package_name='com.example.app', device_id='device_id')
apm.start()
cpu = apm.collectCpu()      # {'appCpuRate': float, 'sysCpuRate': float}
memory = apm.collectMemory() # {'totalPass': float, 'nativePass': float, 'dalvikPass': float}
fps = apm.collectFps()       # {'fps': int, 'jank': int, 'bigJank': int}
flow = apm.collectFlow()     # {'upFlow': float, 'downFlow': float}
battery = apm.collectBattery() # {'level': int, 'temperature': float}
apm.stop()
```

### CPUCollector (`public/android/cpu_collector.py`)
- **精确算法**: 读取 `/proc/stat` 和 `/proc/[pid]/stat` 计算 delta（线程安全）
- **降级方案**: 解析 `top -n 1` 输出（支持多核 CPU、小米设备 ANSI 过滤）

### Devices (`public/common.py`)
```python
d = Devices()
devices = d.getDevices()  # ["Android emulator-5554"]
device_id = d.getIdbyDevice(device_str, Platform.Android)
```

### ADB (`public/adb/__init__.py`)
```python
from insight_eyes.public.adb import adb
result = adb.shell('dumpsys cpuinfo', device_id='device_id')
devices = adb.devices()
```

## Desktop Components

- **DeviceManager** - 设备扫描、监控、重连（心跳检测 + 指数退避）
- **DeviceAdapters** - Android 设备适配器
- **AppEnumerator** - 应用枚举
- **MetricsProcessor** - 原始数据处理
- **AnomalyDetector** - 异常检测

## Data Flow Pattern

1. **主要方法**: 尝试主要采集方式
2. **降级方案**: 失败时尝试替代解析
3. **默认值**: 全部失败返回 0/默认字典

## Thread Safety

- FPS 数据使用 `_fps_data_lock` (RLock)
- CPU 数据使用 `_cpu_data_lock` (Lock)
- Qt signals 确保线程安全通信
- 数据库使用线程本地连接

## Dependencies

```
PyQt6>=6.4.0          # GUI 框架
pyqtgraph>=0.13.0     # 实时图表
numpy>=1.23.0         # 数值计算
logzero>=1.7.0        # 日志
```

## Export Formats

支持 CSV、JSON、Excel、Markdown 数据导出。

## 更新日志

### 2025-01-21 (架构简化)
- 移除 iOS 监控支持
- 项目专注于 Android 平台

### 2025-01-19 (v2.0)
- 监控面板优化：曲线抗锯齿、悬停提示、动态卡片配置
- CPU 采集器重构：实现 /proc/stat delta 精确算法
- 新增测试报告面板

## UI Design

- **主题**: Cyberpunk Neon (赛博朋克霓虹)
- **主色**: #00d4ff (霓虹蓝)
- **样式**: `ui/styles.qss`
