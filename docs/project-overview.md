# 项目概述

## Insight-Eye

**版本**: v1.0.3

**Insight-Eye** 是一个跨平台设备性能监控工具，支持 Android 和 iOS 平台，提供：
- Python API
- PyQt6 桌面 GUI 应用（赛博朋克霓虹风格）
- FastAPI Web 后端
- React Web 前端（与桌面版 1:1 对等）

## 项目结构

```
insight_eyes/
├── __main__.py           # 入口点: `python -m insight_eyes`
├── public/               # 核心性能监控库
│   ├── adb/              # ADB 封装
│   ├── android/          # Android 采集器
│   │   ├── android_apm.py      # Android APM 主类
│   │   ├── cpu_collector.py    # CPU 采集器
│   │   ├── memory_collector.py # 内存采集器
│   │   ├── fps_collector.py    # FPS 监控器
│   │   ├── network_collector.py # 网络流量采集器
│   │   └── battery_collector.py # 电池采集器
│   ├── ios/              # iOS 采集器
│   │   ├── ios_apm.py          # iOS APM 主类
│   │   ├── cpu_collector.py    # CPU 采集器（sysmon）
│   │   ├── memory_collector.py # 内存采集器（sysmon）
│   │   ├── battery_collector.py # 电池采集器
│   │   ├── energy_collector.py # 能耗采集器（sysmon）
│   │   ├── sysmon_service.py   # sysmon 服务封装
│   │   ├── sysmon_stream_service.py # 流式监听服务
│   │   ├── metrics_throttle.py # 频率控制层
│   │   └── exceptions.py       # iOS 专用异常
│   └── common.py         # 设备检测、平台枚举
├── desktop/              # PyQt6 桌面应用
│   ├── main.py           # 应用入口
│   ├── core/             # 设备管理、适配器、应用枚举
│   ├── analytics/        # 数据分析、异常检测
│   ├── data/             # 数据库、导出
│   ├── ui/               # PyQt6 UI 组件、图表
│   ├── config/           # 配置管理
│   └── tools/            # 工具脚本
├── web/                  # FastAPI Web 后端
│   ├── api/              # API 端点
│   │   ├── main.py       # FastAPI 主应用
│   │   ├── devices.py    # 设备管理 API
│   │   ├── monitoring.py # 监控控制 API
│   │   └── schemas.py    # Pydantic 数据模型
│   ├── websocket/        # WebSocket 处理
│   │   └── handler.py    # 实时数据推送
│   └── requirements.txt  # Web 依赖
└── web-frontend/         # React Web 前端
    ├── src/
    │   ├── components/   # React 组件
    │   │   ├── charts/   # ECharts 图表组件
    │   │   ├── layout/   # 布局组件
    │   │   ├── panels/   # 面板组件
    │   │   └── widgets/  # 小部件
    │   ├── config/       # 配置文件
    │   ├── services/     # API 服务
    │   ├── store/        # Zustand 状态管理
    │   ├── theme/        # 霓虹主题
    │   └── types/        # TypeScript 类型
    ├── package.json
    ├── vite.config.ts
    └── tailwind.config.js
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
    │  Fps/Flow/Battery     │             │  Battery/Energy     │
    └───────────┬───────────┘             └──────────┬───────────┘
                │                                     │
                ▼                                     ▼
    ┌───────────────────────┐             ┌──────────────────────┐
    │   Android 采集器       │             │    iOS 采集器        │
    │  (public/android/)     │             │   (public/ios/)      │
    ├───────────────────────┤             ├──────────────────────┤
    │ CPUCollector          │             │ SysmonStreamService  │
    │ MemoryCollector       │             │ (流式监听架构)       │
    │ FPSMonitor            │             │ ├─ MetricsThrottle   │
    │ NetworkCollector      │             │ ├─ CPUCollector      │
    │ BatteryCollector      │             │ ├─ MemoryCollector   │
    │                       │             │ ├─ BatteryCollector  │
    │                       │             │ └─ EnergyCollector   │
    └───────────┬───────────┘             └──────────────────────┘
                │                                     │
                ▼                                     ▼
    ┌───────────────────────┐             ┌──────────────────────┐
    │   ADB (adb/)          │             │ pymobiledevice3      │
    │   /proc, dumpsys      │             │ sysmon + diagnostics │
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
- **CPU** - 应用 CPU 使用率（通过 sysmon 流式监听）
- **Memory** - 已用内存、总内存（通过 sysmon）
- **Battery** - 电量、温度、充电状态
- **Energy** - 能耗数据（总能耗、CPU、GPU、网络）
- **FPS** - 帧率（计划中）
- **Network** - 网络流量（计划中）

**注意**：
- iOS 监控需要 pymobiledevice3 >= 7.0.0
- 设备需要信任电脑并开启开发者模式
- 采 用流式监听架构，解决 sysmon 数据推送频率不固定问题
- 部分功能受 pymobiledevice3 API 限制

## 导出格式

支持以下数据导出格式：
- CSV
- JSON
- Excel
- Markdown
