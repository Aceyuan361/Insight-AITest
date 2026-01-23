# Android 监控专题

**版本**: v1.0.1

## 概述

Android 监控通过 ADB (Android Debug Bridge) 与设备通信，提供精确的性能数据采集能力。

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

### AndroidAPM
**位置**: `public/android/android_apm.py`

```python
from insight_eyes.public.android import AndroidAPM

apm = AndroidAPM(package_name='com.example.app', device_id='device_id')
apm.start()

cpu = apm.collectCpu()      # {'appCpuRate': float, 'sysCpuRate': float}
memory = apm.collectMemory() # {'totalPass': float, 'nativePass': float, 'dalvikPass': float}
fps = apm.collectFps()       # {'fps': int, 'jank': int, 'bigJank': int}
flow = apm.collectFlow()     # {'upFlow': float, 'downFlow': float}
battery = apm.collectBattery() # {'level': int, 'temperature': float}

apm.stop()
```

### CPUCollector
**位置**: `public/android/cpu_collector.py`

#### 主要方法：/proc/stat + /proc/[pid]/stat
```python
# 读取系统 CPU 统计
with open('/proc/stat') as f:
    stats = f.readline()

# 读取进程 CPU 统计
with open(f'/proc/{pid}/stat') as f:
    proc_stat = f.readline()

# 计算 delta（线程安全）
cpu_rate = calculate_delta(prev_stats, curr_stats)
```

**优点**：
- 精确的 CPU 使用率计算
- 支持 delta 计算（消除绝对值误差）
- 线程安全

#### 降级方案：top -n 1
```python
# 解析 top 输出
result = adb.shell('top -n 1', device_id)
# 过滤 ANSI 转义码（小米设备）
# 解析 CPU 使用率
```

**优点**：
- 兼容性好（所有设备支持）
- 支持多核 CPU
- 支持小米设备 ANSI 过滤

### MemoryCollector
**位置**: `public/android/memory_collector.py`

#### 方法：dumpsys meminfo
```python
result = adb.shell(f'dumpsys meminfo {package_name}', device_id)
# 解析输出：
# - Total PSS: 总内存
# - Native PSS: Native 内存
# - Dalvik PSS: Dalvik 内存
```

### FPSMonitor
**位置**: `public/android/fps_monitor.py`

#### 方法：gfxinfo
```python
result = adb.shell(f'dumpsys gfxinfo {package_name}', device_id)
# 解析输出：
# - fps: 帧率
# - jank: 卡顿次数
# - big_jank: 大卡顿次数
```

### NetworkCollector
**位置**: `public/android/network_collector.py`

#### 方法：/proc/net/dev
```python
result = adb.shell('cat /proc/net/dev', device_id)
# 解析各接口的发送/接收字节数
# 计算 delta 得到流量
```

### BatteryCollector
**位置**: `public/android/battery_collector.py`

#### 方法：dumpsys battery
```python
result = adb.shell('dumpsys battery', device_id)
# 解析输出：
# - level: 电量百分比
# - temperature: 温度
```

## ADB 工具类

**位置**: `public/adb/__init__.py`

### 使用示例

```python
from insight_eyes.public.adb import adb

# 执行 shell 命令
result = adb.shell('dumpsys cpuinfo', device_id='device_id')

# 获取设备列表
devices = adb.devices()

# 推送文件
adb.push(local_path, remote_path, device_id)

# 拉取文件
adb.pull(remote_path, local_path, device_id)
```

## 线程安全

### 数据锁

| 数据类型 | 锁类型 | 用途 |
|---------|--------|------|
| FPS 数据 | `_fps_data_lock` (RLock) | 帧率数据保护 |
| CPU 数据 | `_cpu_data_lock` (Lock) | CPU 数据保护 |

### 示例

```python
class CPUCollector:
    def __init__(self):
        self._cpu_data_lock = Lock()
        self._prev_cpu_stats = None

    def collect_cpu(self, device_id: str) -> dict:
        with self._cpu_data_lock:
            # 读取当前统计
            curr_stats = self._read_proc_stat(device_id)

            # 计算 delta
            if self._prev_cpu_stats:
                cpu_rate = self._calculate_delta(
                    self._prev_cpu_stats,
                    curr_stats
                )

            # 保存当前统计
            self._prev_cpu_stats = curr_stats

        return {'cpu_rate': cpu_rate}
```

## 常见问题

### 1. ADB 未授权
**解决方案**：
1. 检查设备 USB 调试是否开启
2. 在设备上授权 ADB 调试
3. 重新连接设备

### 2. 小米设备 ANSI 转义码
**问题**：top 命令输出包含 ANSI 转义码

**解决方案**：
```python
import re

# 过滤 ANSI 转义码
ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
clean_output = ansi_escape.sub('', raw_output)
```

### 3. 多核 CPU 计算
**问题**：/proc/stat 返回所有 CPU 核心的统计

**解决方案**：
```python
# 计算平均 CPU 使用率
total_cpu = sum(cpu_cores) / len(cpu_cores)
```

### 4. 进程 ID 查找失败
**问题**：包名对应的进程 ID 不存在

**解决方案**：
```python
# 使用 pidof 命令
pid = adb.shell(f'pidof {package_name}', device_id)

# 或使用 ps 命令
pid = adb.shell(f'ps | grep {package_name}', device_id)
```

## 调试技巧

### 手动测试 ADB 命令
```bash
# 测试 CPU
adb shell cat /proc/stat
adb shell top -n 1

# 测试内存
adb shell dumpsys meminfo com.example.app

# 测试 FPS
adb shell dumpsys gfxinfo com.example.app

# 测试网络
adb shell cat /proc/net/dev

# 测试电量
adb shell dumpsys battery
```

### 检查 ADB 连接
```python
from insight_eyes.public.adb import adb

devices = adb.devices()
print(f"已连接设备: {devices}")
```

### 启用详细日志
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```
