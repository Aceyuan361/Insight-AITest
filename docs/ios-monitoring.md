# iOS 监控专题

**版本**: v1.0.1

## 概述

iOS 监控受限于 pymobiledevice3 的 API 能力，部分指标需要使用降级方案或估算值。

## 技术栈

### 主要依赖
- **pymobiledevice3** >= 7.0.0 - iOS 设备通信
- **sysmon** - 系统监控服务（DVT）
- **DiagnosticsService** - 诊断服务

### 架构组件
1. **SysmonStreamService** - 流式监听服务（持续接收 sysmon 数据）
2. **MetricsThrottle** - 频率控制层（按设定频率聚合数据）
3. **数据采集器** - CPU/Memory/Energy/Battery 采集器

### 流式监听架构

iOS 监控采用流式监听架构，以解决 sysmon 数据推送频率不固定的问题：

```
iOS 设备 --[持续推送]--> SysmonStreamService --[按频率聚合]--> MetricsThrottle --> 采集器
```

**特点**：
- 持续接收：后台持续接收 sysmon 推送的数据（约 0.5-1 秒/次）
- 频率控制：按用户设定的采集频率（1-60 秒）聚合数据
- 数据缓存：使用环形缓冲区保留最近 120 秒的原始数据
- 进程过滤：只累加目标进程的数据，忽略其他 1000+ 系统进程
- 平滑处理：无数据时使用上次有效值，避免曲线跳变

**文件位置**：
- `public/ios/sysmon_stream_service.py` - 流式监听服务
- `public/ios/metrics_throttle.py` - 频率控制层

### 设备要求
- 需要信任电脑
- 需要开启开发者模式

## 支持的指标

| 指标 | 主要方法 | 降级方案 | 精度 | 状态 |
|-----|---------|---------|------|------|
| CPU | sysmon process | psutil + top | 中 | ✅ 完整支持 |
| Memory | sysmon memory | diagnostics | 中 | ✅ 完整支持 |
| Energy | sysmon energy | diagnostics | 中 | ✅ 完整支持 |
| Battery | diagnostics | - | 高 | ✅ 完整支持 |
| FPS | - | - | - | ⚠️ 计划中 |
| Network | - | - | - | ⚠️ 计划中 |
| GPU | - | - | - | ❌ 不支持（API 限制） |

## 核心类

### IOSAPM
**位置**: `public/ios/ios_apm.py`

```python
from insight_eyes.public.ios import IOSAPM

apm = IOSAPM(bundle_name='com.example.app', device_id='ios_device_id')
apm.start()

cpu = apm.collectCpu()      # {'cpu_app': float, 'cpu_system': float}
memory = apm.collectMemory() # {'used_mb': float, 'total_mb': float}
battery = apm.collectBattery() # {'level': int, 'temperature': float, 'is_charging': bool}
energy = apm.collectEnergy() # {'energy': float, 'cpu_energy': float, 'gpu_energy': float, 'network_energy': float}

apm.stop()
```

### CPUCollector
**位置**: `public/ios/cpu_collector.py`

#### 主要方法：sysmon process
- 使用 `pymobiledevice3 developer dvt sysmon process single`
- 解析进程 CPU 使用率

#### 降级方案：psutil + top
- 使用 psutil 获取系统 CPU
- 使用 top 命令解析应用 CPU

### MemoryCollector
**位置**: `public/ios/memory_collector.py`

#### 主要方法：sysmon memory
- 使用 `pymobiledevice3 developer dvt sysmon memory`
- 解析内存使用详情

#### 降级方案：diagnostics
- 使用 `pymobiledevice3 diagnostics memory`
- 获取总体内存信息

### EnergyCollector
**位置**: `public/ios/energy_collector.py`

#### 主要方法：sysmon energy
- 使用 `pymobiledevice3 developer dvt sysmon energy`
- 解析能耗数据

#### 降级方案：diagnostics
- 使用 `pymobiledevice3 diagnostics energy`
- 获取能耗信息

### BatteryCollector
**位置**: `public/ios/battery_collector.py`

- 使用 `pymobiledevice3 diagnostics`
- 获取电量、温度、充电状态

## iOSDeviceAdapter

**位置**: `desktop/core/ios_device_adapter.py`

iOS 设备连接适配器，支持：
- 自动重连
- 健康检查
- 连接状态管理

### 异常类型

| 异常 | 说明 |
|-----|------|
| `DeviceNotTrustedError` | 设备未信任 |
| `PMD3NotInstalledError` | pymobiledevice3 未安装 |
| `DeviceConnectionError` | 设备连接错误 |

## 超时配置

| 操作 | 超时时间 |
|-----|---------|
| sysmon 采集 | 8 秒 |
| 连接超时 | 5 秒 |

## iOS 监控限制说明

### API 限制
1. **GPU 监控**：iOS 系统不支持第三方应用访问 GPU 使用率，API 层面无相关接口
2. **FPS 监控**：需要私有 API 或越狱设备，官方 SDK 未提供相关接口
3. **网络流量**：sysmon 提供的网络数据粒度较粗，无法精确到应用级别

### 数据处理特性
1. **进程过滤**：iOS sysmon 返回 1000+ 系统进程的数据，采集器会过滤并只累加目标进程的数据
2. **平滑处理**：使用上次有效值缓存，避免无数据时出现 0 值跳变
3. **超时控制**：sysmon 采集操作默认超时时间为 8 秒

## 常见问题

### 1. 设备未信任
**解决方案**：
1. 在 iOS 设备上信任电脑
2. 重新连接设备

### 2. pymobiledevice3 未安装
**解决方案**：
```bash
pip install pymobiledevice3>=7.0.0
```

### 3. sysmon 采集失败
**可能原因**：
- 设备未开启开发者模式
- pymobiledevice3 版本不兼容
- 设备连接不稳定
- 目标应用未运行

**解决方案**：
- 检查开发者模式状态
- 升级 pymobiledevice3
- 确保目标应用正在运行
- 使用降级方案

### 4. Bundle ID 解析错误
**问题**：应用名提取时错误处理 `.com` 等后缀

**解决方案**：使用正确的 Bundle ID 解析逻辑，处理常见 TLD 后缀

### 5. CPU 数据异常低
**问题**：CPU 使用率显示为 0.35% 而非预期的 6-8%

**原因**：数据聚合时累加了所有系统进程而非目标进程

**解决方案**：确保使用最新版本的代码，已修复此问题

## 调试技巧

### 启用详细日志
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 手动测试 sysmon
```bash
pymobiledevice3 developer dvt sysmon process single <device_id>
```

### 检查设备连接
```python
from insight_eyes.desktop.core.ios_device_adapter import IOSDeviceAdapter
adapter = IOSDeviceAdapter(device_id)
print(adapter.is_connected())
```
