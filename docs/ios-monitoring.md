# iOS 监控专题

## 概述

iOS 监控受限于 pymobiledevice3 的 API 能力，部分指标需要使用降级方案或估算值。

## 技术栈

### 主要依赖
- **pymobiledevice3** >= 7.0.0 - iOS 设备通信
- **sysmon** - 系统监控服务（DVT）
- **DiagnosticsService** - 诊断服务

### 设备要求
- 需要信任电脑
- 需要开启开发者模式

## 支持的指标

| 指标 | 主要方法 | 降级方案 | 精度 |
|-----|---------|---------|------|
| CPU | sysmon process | psutil + top | 中 |
| Memory | sysmon memory | diagnostics | 中 |
| Energy | sysmon energy | diagnostics | 中 |
| Battery | diagnostics | - | 高 |

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

**解决方案**：
- 检查开发者模式状态
- 升级 pymobiledevice3
- 使用降级方案

### 4. Bundle ID 解析错误
**问题**：应用名提取时错误处理 `.com` 等后缀

**解决方案**：使用正确的 Bundle ID 解析逻辑，处理常见 TLD 后缀

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
