# Android 监控专题

**版本**: v2.0.0 · **作者**: Aceyuan361

## 概述

Android 监控是 Insight-AITest **性能监控模块（模块 B）** 的设备采集后端，通过 ADB（Android Debug Bridge）与设备通信，提供精确的性能数据采集能力。采集器位于平台共享服务层 `platform/services/collectors/`，由性能模块的 WebSocket 处理器实时推送至前端。

## 技术栈

### 主要依赖
- **ADB** (Android Debug Bridge) - 设备通信
- **dumpsys** - 系统服务信息
- **/proc 文件系统** - 内核信息

### 设备要求
- USB 调试已开启
- 已授权 ADB 调试

## 支持的指标

| 指标 | 主要方法 | 降级方案 | 精度 | 状态 |
|-----|---------|---------|------|------|
| CPU | /proc/stat + /proc/[pid]/stat | top -n 1 | 高 | ✅ 完整支持 |
| Memory | dumpsys meminfo | - | 高 | ✅ 完整支持 |
| FPS | gfxinfo | - | 高 | ✅ 完整支持 |
| Network | /proc/net/dev | - | 高 | ✅ 完整支持 |
| Battery | dumpsys battery | - | 高 | ✅ 完整支持 |
| GPU | dumpsys gfxinfo | - | 中 | ⚠️ 需要 root 或特定设备支持 |

## 核心类

采集器代码位于 `insight_aitest/platform/services/collectors/android/`：

### AndroidAPM
**位置**: `platform/services/collectors/android/android_apm.py`

Android 性能采集主类，聚合各指标采集器：

```python
from insight_aitest.platform.services.collectors.android import AndroidAPM

apm = AndroidAPM(package_name='com.example.app', device_id='device_id')
apm.start()

cpu = apm.collectCpu()       # {'appCpuRate': float, 'sysCpuRate': float}
memory = apm.collectMemory() # {'totalPass': float, 'nativePass': float, 'dalvikPass': float}
fps = apm.collectFps()       # {'fps': int, 'jank': int, 'bigJank': int}
flow = apm.collectFlow()     # {'upFlow': float, 'downFlow': float}
battery = apm.collectBattery() # {'level': int, 'temperature': float}

apm.stop()
```

### 各指标采集器

| 采集器 | 位置 | 方法 |
|-------|------|------|
| CPUCollector | `collectors/android/cpu_collector.py` | `/proc/stat` + `/proc/[pid]/stat`，降级 `top -n 1`（含小米 ANSI 过滤） |
| MemoryCollector | `collectors/android/memory_collector.py` | `dumpsys meminfo`（Total/Native/Dalvik PSS） |
| FPSCollector | `collectors/android/fps_collector.py` | `dumpsys gfxinfo`（帧率/卡顿/大卡顿） |
| NetworkCollector | `collectors/android/network_collector.py` | `/proc/net/dev`（按接口 delta 计算流量） |
| BatteryCollector | `collectors/android/battery_collector.py` | `dumpsys battery`（电量/温度） |

### ADB 工具类

**位置**: `platform/services/collectors/adb/`

封装 ADB shell 命令执行、设备列表、文件推送/拉取等能力。

## 线程安全

| 数据类型 | 锁类型 | 用途 |
|---------|--------|------|
| FPS 数据 | `_fps_data_lock` (RLock) | 帧率数据保护 |
| CPU 数据 | `_cpu_data_lock` (Lock) | CPU 数据保护 |

CPU 采集采用 delta 计算：保存上次统计 → 读取当前统计 → 计算差值得到使用率，全程持锁保证线程安全。

## 常见问题

### 1. ADB 未授权
1. 检查设备 USB 调试是否开启
2. 在设备上授权 ADB 调试
3. 重新连接设备

### 2. 小米设备 ANSI 转义码
`top` 命令输出包含 ANSI 转义码，采集器会自动过滤：
```python
ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
clean_output = ansi_escape.sub('', raw_output)
```

### 3. 进程 ID 查找失败
```bash
adb shell pidof com.example.app
# 或
adb shell ps | grep com.example.app
```

## 调试技巧

### 手动测试 ADB 命令
```bash
adb shell cat /proc/stat              # CPU
adb shell dumpsys meminfo com.example.app  # 内存
adb shell dumpsys gfxinfo com.example.app  # FPS
adb shell cat /proc/net/dev           # 网络
adb shell dumpsys battery             # 电量
```

### 检查 ADB 连接
```python
from insight_aitest.platform.services.collectors.adb import adb
devices = adb.devices()
print(f"已连接设备: {devices}")
```
