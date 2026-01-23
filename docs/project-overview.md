# 项目概述

## Insight-Eye

**Insight-Eye** 是一个跨平台设备性能监控工具，支持 Android 和 iOS 平台，提供 Python API 和 PyQt6 桌面 GUI 应用（赛博朋克霓虹风格）。

## 项目结构

```
insight_eyes/
├── __main__.py           # 入口点: `python -m insight_eyes`
├── public/               # 核心性能监控库
│   ├── adb/              # ADB 封装
│   ├── android/          # Android 采集器
│   ├── ios/              # iOS 采集器
│   └── common.py         # 设备检测、平台枚举
└── desktop/              # PyQt6 桌面应用
    ├── main.py           # 应用入口
    ├── core/             # 设备管理、适配器、应用枚举
    ├── analytics/        # 数据分析、异常检测
    ├── data/             # 数据库、导出
    ├── ui/               # PyQt6 UI 组件、图表
    ├── config/           # 配置管理
    └── tools/            # 工具脚本
```

## 系统架构

```
                    ┌─────────────────────────────────┐
                    │     DeviceManager (Platform)      │
                    │   Android | iOS                  │
                    └──────────────┬───────────────────┘
                                   │
              ┌────────────────────┴────────────────────┐
              │                                         │
              ▼                                         ▼
    ┌───────────────────────┐             ┌──────────────────────┐
    │    AndroidAPM         │             │     IOSAPM          │
    │  collectCpu/Memory/   │             │  collectCpu/Memory/ │
    │  Fps/Flow/Battery     │             │  Battery (降级方案) │
    └───────────┬───────────┘             └──────────┬───────────┘
                │                                     │
                ▼                                     ▼
    ┌───────────────────────┐             ┌──────────────────────┐
    │   Android 采集器       │             │    iOS 采集器        │
    │  (public/android/)     │             │   (public/ios/)      │
    ├───────────────────────┤             ├──────────────────────┤
    │ CPUCollector          │             │ CPUCollector (降级)  │
    │ MemoryCollector       │             │ MemoryCollector     │
    │ FPSMonitor            │             │ BatteryCollector    │
    │ NetworkCollector      │             │ (DiagnosticsService)│
    │ BatteryCollector      │             └──────────────────────┘
    └───────────┬───────────┘                         │
                │                                     │
                ▼                                     ▼
    ┌───────────────────────┐             ┌──────────────────────┐
    │   ADB (adb/)          │             │ pymobiledevice3      │
    └───────────────────────┘             └──────────────────────┘
```

## 支持的监控指标

### Android 平台
- **CPU** - 应用和系统 CPU 使用率
- **Memory** - 总内存、Native 内存、Dalvik 内存
- **FPS** - 帧率、卡顿次数、大卡顿次数
- **Network** - 上行/下行流量
- **Battery** - 电量、温度

### iOS 平台
- **CPU** - 应用 CPU 使用率（降级方案）
- **Memory** - 已用内存、总内存（部分降级）
- **Battery** - 电量、温度、充电状态
- **Energy** - 能耗数据（通过 sysmon）

## 导出格式

支持以下数据导出格式：
- CSV
- JSON
- Excel
- Markdown
