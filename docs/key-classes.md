# 核心类和 API

**版本**: v1.0.1

本文档介绍 Insight-Eye 的核心类和 API。

## AndroidAPM

**位置**: `public/android/android_apm.py`

Android 性能监控主类。

### 使用示例

```python
from insight_eyes.public.android import AndroidAPM

apm = AndroidAPM(package_name='com.example.app', device_id='device_id')
apm.start()

# 采集各项指标
cpu = apm.collectCpu()      # {'appCpuRate': float, 'sysCpuRate': float}
memory = apm.collectMemory() # {'totalPass': float, 'nativePass': float, 'dalvikPass': float}
fps = apm.collectFps()       # {'fps': int, 'jank': int, 'bigJank': int}
flow = apm.collectFlow()     # {'upFlow': float, 'downFlow': float}
battery = apm.collectBattery() # {'level': int, 'temperature': float}

apm.stop()
```

---

## IOSAPM

**位置**: `public/ios/ios_apm.py`

iOS 性能监控主类。

### 使用示例

```python
from insight_eyes.public.ios import IOSAPM

apm = IOSAPM(bundle_name='com.example.app', device_id='ios_device_id')
apm.start()

# 采集各项指标
cpu = apm.collectCpu()      # {'cpu_app': float, 'cpu_system': float}
memory = apm.collectMemory() # {'used_mb': float, 'total_mb': float}
battery = apm.collectBattery() # {'level': int, 'temperature': float, 'is_charging': bool}
energy = apm.collectEnergy() # {'energy': float, 'cpu_energy': float, 'gpu_energy': float, 'network_energy': float}

apm.stop()
```

**注意**: iOS 监控采用流式监听架构，通过 sysmon 持续接收数据并按频率聚合。

---

## Devices

**位置**: `public/common.py`

设备检测和平台枚举。

### 使用示例

```python
from insight_eyes.public.common import Devices, Platform

d = Devices()
devices = d.getDevices()  # ["Android emulator-5554", "iPhone xxx"]

# 获取设备 ID
device_id = d.getIdbyDevice(device_str, Platform.Android)
device_id = d.getIdbyDevice(device_str, Platform.IOS)
```

---

## ADB

**位置**: `public/adb/__init__.py`

ADB 命令封装。

### 使用示例

```python
from insight_eyes.public.adb import adb

# 执行 shell 命令
result = adb.shell('dumpsys cpuinfo', device_id='device_id')

# 获取设备列表
devices = adb.devices()
```

---

## IOSDeviceAdapter

**位置**: `desktop/core/ios_device_adapter.py`

iOS 设备连接适配器，支持自动重连和健康检查。

### 特性

- 使用 pymobiledevice3 LockdownClient 连接
- 支持自动重连和健康检查
- 提供 collect_cpu、collect_memory 等便捷采集方法

### 异常类型

- `DeviceNotTrustedError` - 设备未信任
- `PMD3NotInstalledError` - pymobiledevice3 未安装
- `DeviceConnectionError` - 设备连接错误
- `ProcessNotFoundError` - 目标应用进程不存在

## SysmonStreamService

**位置**: `public/ios/sysmon_stream_service.py`

iOS 流式监听服务，持续接收 sysmon 数据并缓存。

### 特性

- 后台持续接收 sysmon 推送的数据（约 0.5-1 秒/次）
- 使用环形缓冲区保留最近 120 秒的原始数据
- 支持进程过滤，只累加目标进程数据
- 提供平滑处理，无数据时使用上次有效值

## MetricsThrottle

**位置**: `public/ios/metrics_throttle.py`

iOS 频率控制层，按设定频率聚合数据。

### 特性

- 按用户设定的采集频率（1-60 秒）聚合数据
- 支持多采集器共享同一数据源
- 提供数据缓存和平滑处理

---

## Desktop 组件

### DeviceManager
- 设备扫描、监控、重连（支持 Android 和 iOS）

### DeviceAdapters
- 设备适配器工厂（AndroidDeviceAdapter、IOSDeviceAdapter）

### AppEnumerator
- 应用枚举（Android ADB、iOS pymobiledevice3）

### IOSAppEnumerator
- iOS 应用专用枚举器
- 支持获取已安装应用列表
- 解析 Bundle ID 和应用名称

### MetricsProcessor
- 原始数据处理（平台无关）

### IOSSessionMonitor
- iOS 监控会话管理
- 协调各采集器的数据采集
- 处理会话开始和结束事件

### AnomalyDetector
- 异常检测
