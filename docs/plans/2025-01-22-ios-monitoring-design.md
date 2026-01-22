# iOS 设备性能监控架构设计

**日期**: 2025-01-22
**作者**: Claude + Aceyuan361
**状态**: 技术验证通过，准备实施

## 概述

本文档描述如何在 Insight-Eye 项目中添加 iOS 设备性能监控功能。项目目前仅支持 Android 设备监控。POC 验证表明，使用 pymobiledevice3 在 Windows 上连接 iOS 设备可行。

## 目标

1. 支持连接 iOS 设备并采集性能数据
2. 保持与现有 Android 监控架构的一致性
3. 在 Windows 平台上打包分发
4. 提供基础性能监控：CPU、内存、FPS、网络、电池

## 技术方案

### 核心依赖

- **pymobiledevice3**: iOS 设备通信（已验证可用）
- **PyQt6**: UI 框架（现有）
- **SQLite**: 数据存储（现有）

### 架构设计

```
insight_eyes/
├── public/
│   ├── ios/                    # iOS 采集器（新增）
│   │   ├── __init__.py
│   │   ├── ios_apm.py          # 主入口
│   │   ├── cpu_collector.py
│   │   ├── memory_collector.py
│   │   ├── fps_collector.py
│   │   ├── network_collector.py
│   │   └── battery_collector.py
│   └── common.py               # 添加 Platform.IOS
│
└── desktop/
    ├── core/
    │   ├── models.py           # 恢复 Platform.IOS 枚举
    │   ├── ios_device_adapter.py  # iOS 设备适配器（新增）
    │   └── device_adapters.py  # 添加 iOS 分支
    │
    └── data/
        └── database.py         # 移除 platform CHECK 约束
```

### 数据流

```
用户连接 iOS 设备
    ↓
DeviceManager 检测设备（USBMUX）
    ↓
IOSDeviceAdapter 连接设备
    ↓
iOSAPM 启动性能采集
    ↓
采集器收集数据（CPU、内存、FPS 等）
    ↓
数据存入数据库（platform='ios'）
    ↓
UI 实时显示曲线
```

## 实施计划

### 阶段 1：基础框架（2 周）

**任务清单**

1. 恢复 Platform 枚举中的 IOS 选项
2. 移除数据库的 platform CHECK 约束
3. 实现 IOSDeviceAdapter 类
4. 实现基础采集器（CPU、内存、电池）
5. 设备列表支持 iOS 设备显示

**验收标准**

- 能检测到连接的 iOS 设备
- 能获取设备信息（型号、iOS 版本）
- 能采集基础性能数据

### 阶段 2：UI 集成（1 周）

**任务清单**

1. 监控面板适配 iOS 平台
2. 数据库扩展支持 iOS 标识
3. 测试报告支持 iOS 数据

**验收标准**

- UI 能同时显示 Android 和 iOS 设备
- 能启动和停止 iOS 监控
- 测试报告能导出 iOS 数据

### 阶段 3：完善优化（1 周）

**任务清单**

1. FPS 采集（Core Animation）
2. 网络监控适配
3. 异常检测适配
4. 错误处理和降级方案

**验收标准**

- 所有基础指标正常工作
- 降级方案有效
- PyInstaller 打包成功

## 技术决策

### 为什么选择 pymobiledevice3

1. **POC 验证通过**: 在 Windows 上成功检测到 iOS 设备
2. **活跃维护**: 支持 iOS 17+ 版本
3. **纯 Python**: 易于打包和分发

### 为什么不使用 GPU 监控（MVP）

1. **技术限制**: 系统级 GPU 使用率需要私有 API
2. **开发成本**: 实现复杂度高
3. **用户价值**: 基础指标已能满足大部分需求

后续可作为高级功能添加。

## 风险与缓解

### 风险 1：iOS 设备信任流程

**问题**: 首次连接需要用户在设备上信任电脑

**缓解**:
- 在 UI 中添加清晰的引导提示
- 检测信任状态并给出明确指示

### 风险 2：Windows 打包复杂度

**问题**: pymobiledevice3 依赖 C 库

**缓解**:
- 使用 PyInstaller 隐藏导入
- 测试打包后的功能完整性

### 风险 3：API 变化

**问题**: pymobiledevice3 API 可能更新

**缓解**:
- 使用稳定版本（pinned version）
- 添加抽象层隔离 API 变化

## 成功标准

1. 在 Windows 上能检测并连接 iOS 设备
2. 能采集基础性能数据（误差 <10%）
3. UI 能正常显示 iOS 监控数据
4. 打包后的 .exe 能在没有 Python 环境的机器上运行

## 参考资料

- [pymobiledevice3 文档](https://github.com/doronz88/pymobiledevice3)
- 现有 AndroidAPM 架构: `insight_eyes/public/android/android_apm.py`
- 设备适配器接口: `insight_eyes/desktop/core/device_adapters.py`
