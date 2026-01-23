# 核心类和 API

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
cpu = apm.collectCpu()      # {'cpu_app': float, 'cpu_system': float} (降级方案)
memory = apm.collectMemory() # {'used_mb': float, 'total_mb': float} (部分降级)
battery = apm.collectBattery() # {'level': int, 'temperature': float, 'is_charging': bool}

apm.stop()
```

**注意**: iOS 监控受 pymobiledevice3 限制，部分功能使用降级方案或估算值。

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

### 异常类型

- `DeviceNotTrustedError` - 设备未信任
- `PMD3NotInstalledError` - pymobiledevice3 未安装
- `DeviceConnectionError` - 设备连接错误

---

## Desktop 组件

### DeviceManager
- 设备扫描、监控、重连（支持 Android 和 iOS）

### DeviceAdapters
- 设备适配器工厂（AndroidDeviceAdapter、IOSDeviceAdapter）

### AppEnumerator
- 应用枚举（Android ADB、iOS pymobiledevice3）

### MetricsProcessor
- 原始数据处理（平台无关）

### AnomalyDetector
- 异常检测
