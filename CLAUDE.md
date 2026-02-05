# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

**Insight-Eye** 是一个跨平台移动设备性能监控工具，支持 Android（无需 ROOT）和 iOS（无需越狱）设备，提供 Python API、PyQt6 桌面 GUI 和 FastAPI Web 服务。

### 架构设计

项目采用**四层架构**，从上到下依次为：

1. **表现层** (`desktop/` PyQt6 GUI, `web-frontend/` React)
2. **桌面层** (`desktop/core/`, `desktop/analytics/`, `desktop/data/`)
3. **核心层** (`core/` 桌面版和 Web 版共享)
4. **公共层** (`public/android/`, `public/ios/` 平台采集器)

### 关键架构原则

- **Data Flow Pattern**: 所有采集器遵循三层降级模式（主要方法 → 降级方案 → 默认值）
- **核心层共享**: `insight_eyes/core/` 提供桌面版和 Web 版共用的设备管理和数据模型
- **设备适配器模式**: 通过 `DeviceAdapterFactory` 创建 Android/iOS 适配器，统一接口
- **流式监听架构** (iOS): `SysmonStreamService` + `MetricsThrottle` 解决 sysmon 推送频率不稳定

## 开发命令

### 启动应用

```bash
# Web 后端 (FastAPI + uvicorn)
python -m insight_eyes
# 服务运行在 http://localhost:8001
# API 文档: http://localhost:8001/docs

# Web 前端开发服务器
cd insight_eyes/web-frontend
npm run dev
# 服务运行在 http://localhost:80 (见 vite.config.ts 配置)

# 前端构建
npm run build

# E2E 测试
npm run test:e2e
```

### 数据库初始化

```bash
# 初始化 SQLite 数据库
python -m insight_eyes.desktop.tools.init_db
```

## 核心模块说明

### 设备管理流程

```
DeviceManager.scan_devices()
  → Devices.getDevices() 获取设备列表
  → DeviceAdapterFactory.create_adapter() 创建适配器
  → adapter.connect() + adapter.get_device_info()
  → 返回 Device 对象列表
```

### iOS 监控流式架构

```
SysmonStreamService.start_monitoring()
  → pymobiledevice3 sysmontap 异步流
  → MetricsThrottle 频率控制层（确保稳定推送）
  → yield CPU/Memory/Battery/Energy 数据
```

**重要**: iOS 监控需要 `pymobiledevice3 >= 7.0.0`，设备必须信任电脑并开启开发者模式。

### Android 监控采集器

位于 `public/android/`，各采集器独立工作：

- `CPUCollector`: 支持 `/proc/stat` 精确算法和 `top` 降级方案
- `FPSMonitor`: 后台线程持续采集，支持小米设备 ANSI 过滤
- `DeviceProfile`: 自动检测厂商选择最佳采集策略

## 数据模型

核心模型定义在 `insight_eyes/core/models/`：

- **Device**: 设备信息 (device_id, name, type, status)
- **Session**: 监控会话 (id, device_id, app_package, status, start_time, end_time)
- **MetricsData**: 监控指标 (timestamp, cpu, memory, fps, network, battery)

## 线程安全

### 数据锁

| 数据类型 | 锁类型 | 位置 |
|---------|--------|------|
| FPS 数据 | `_fps_data_lock` (RLock) | FPSMonitor |
| CPU 数据 | `_cpu_data_lock` (Lock) | CPUCollector |

### Qt 线程安全

- 使用 Qt Signals 进行跨线程通信（`desktop/core/device_manager.py`）
- QRunnable 任务池并行采集（`desktop/analytics/metrics_batch_collector.py`）

## 错误处理约定

遵循 **Data Flow Pattern**:

```python
def collect_metric(self, device_id: str) -> dict:
    # 1. 尝试主要方法
    try:
        return self._primary_method(device_id)
    except SpecificException as e:
        logger.debug(f"主要方法失败: {e}")

    # 2. 尝试降级方案
    try:
        return self._fallback_method(device_id)
    except Exception as e:
        logger.warning(f"降级方案失败: {e}")

    # 3. 返回默认值
    return {'metric': 0}
```

**禁止**: 裸 `except:` 捕获，必须记录日志。

## iOS 监控特殊约定

### 降级方案

| 指标 | 主要方法 | 降级方案 |
|-----|---------|---------|
| CPU | sysmon | psutil + top |
| Memory | sysmon | diagnostics |
| Energy | sysmon | diagnostics |

### 超时设置

- sysmon 采集超时: **8 秒**
- 连接超时: **5 秒**

## Git 提交约定

```
<type>: <subject>

<body>
```

Type 类型:
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具

示例:
```
fix: 修复 iOS CPU 采集超时问题

增加 sysmon 采集超时时间至 8 秒，添加重试机制
```

## Web 前端开发

前端位于 `insight_eyes/web-frontend/`，使用:

- **React 18** + **TypeScript**
- **Vite** 构建工具
- **ECharts** 图表可视化
- **Ant Design** UI 组件
- **Zustand** 状态管理
- **TailwindCSS** 样式框架

### WebSocket 连接

实时数据通过 WebSocket 连接到 `ws://localhost:8001/api/sessions/{id}/stream`

## 相关文档

- 项目概述: `docs/project-overview.md`
- Android 监控: `docs/android-monitoring.md`
- iOS 监控: `docs/ios-monitoring.md`
- 开发工作流: `docs/dev-workflow.md`
