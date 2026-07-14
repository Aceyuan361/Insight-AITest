# iOS 监控专题

**版本**: v2.0.0 · **作者**: Aceyuan361

## 概述

iOS 监控是 Insight-AITest **性能监控模块（模块 B）** 的设备采集后端，通过 pymobiledevice3 与设备通信。受限于 iOS 系统 API 能力，部分指标采用降级方案或估算值。采集器位于平台共享服务层 `platform/services/collectors/ios/`。

## 支持的系统版本

- **最低版本**: iOS 11.0
- **最高版本**: iOS 16.x
- **不支持**: iOS 17+

## 技术栈

### 主要依赖
- **pymobiledevice3** >= 9.0.0 - iOS 设备通信（iOS 17+ 需 tunnel 支持）
- **sysmon** - 系统监控服务（DVT）
- **DiagnosticsService** - 诊断服务

### 设备要求
- 需要信任电脑
- 需要开启开发者模式

## 流式监听架构

iOS 监控采用流式监听架构，以解决 sysmon 数据推送频率不固定的问题：

```
iOS 设备 --[持续推送]--> SysmonStreamService --[按频率聚合]--> MetricsThrottle --> 采集器
```

**特点**：
- **持续接收**：后台持续接收 sysmon 推送的数据（约 0.5-1 秒/次）
- **频率控制**：按用户设定的采集频率（1-60 秒）聚合数据
- **数据缓存**：使用环形缓冲区保留最近 120 秒的原始数据
- **进程过滤**：只累加目标进程的数据，忽略其他 1000+ 系统进程
- **平滑处理**：无数据时使用上次有效值，避免曲线跳变

**关键组件**（位于 `platform/services/collectors/ios/`）：

| 组件 | 位置 | 职责 |
|-----|------|------|
| SysmonStreamService | `sysmon_stream_service.py` | 流式监听服务（持续接收 sysmon 数据） |
| MetricsThrottle | `metrics_throttle.py` | 频率控制层（按设定频率聚合） |
| SysmonService | `sysmon_service.py` | sysmon 服务封装 |

## 支持的指标

| 指标 | 主要方法 | 降级方案 | 精度 | 状态 |
|-----|---------|---------|------|------|
| CPU | sysmon process | psutil + top | 中 | ✅ 完整支持 |
| Memory | sysmon memory | diagnostics | 中 | ✅ 完整支持 |
| Energy | sysmon energy | diagnostics | 中 | ✅ 完整支持 |
| Battery | diagnostics | - | 高 | ✅ 完整支持 |
| FPS | 系统刷新率参考 | - | 低 | ⚠️ 参考值 |
| Network | 系统级统计 | - | 低 | ⚠️ 系统级 |
| GPU | - | - | - | ❌ 不支持（系统 API 限制） |

## 核心类

### IOSAPM
**位置**: `platform/services/collectors/ios/ios_apm.py`

iOS 性能采集主类：

```python
from insight_aitest.platform.services.collectors.ios import IOSAPM

apm = IOSAPM(bundle_name='com.example.app', device_id='ios_device_id')
apm.start()

cpu = apm.collectCpu()         # {'cpu_app': float, 'cpu_system': float}
memory = apm.collectMemory()   # {'used_mb': float, 'total_mb': float}
battery = apm.collectBattery() # {'level': int, 'temperature': float, 'is_charging': bool}
energy = apm.collectEnergy()   # {'energy': float, 'cpu_energy': float, 'gpu_energy': float, 'network_energy': float}

apm.stop()
```

### 各指标采集器

| 采集器 | 位置 | 主要方法 | 降级方案 |
|-------|------|---------|---------|
| CPUCollector | `collectors/ios/cpu_collector.py` | `pymobiledevice3 developer dvt sysmon process single` | psutil + top |
| MemoryCollector | `collectors/ios/memory_collector.py` | `sysmon memory` | `diagnostics memory` |
| EnergyCollector | `collectors/ios/energy_collector.py` | `sysmon energy` | `diagnostics energy` |
| BatteryCollector | `collectors/ios/battery_collector.py` | `pymobiledevice3 diagnostics` | - |

## 设备适配器

**位置**: `platform/services/device_adapters/ios_device_adapter.py`

iOS 设备连接适配器，支持自动重连、健康检查、连接状态管理。

### 异常类型

| 异常 | 说明 |
|-----|------|
| `DeviceNotTrustedError` | 设备未信任 |
| `PMD3NotInstalledError` | pymobiledevice3 未安装 |
| `DeviceConnectionError` | 设备连接错误 |

### 超时配置

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
在 iOS 设备上信任电脑，然后重新连接。

### 2. pymobiledevice3 未安装
```bash
pip install "pymobiledevice3>=9.0.0"
```

### 3. sysmon 采集失败
**可能原因**：设备未开启开发者模式、pymobiledevice3 版本不兼容、设备连接不稳定、目标应用未运行。

**解决**：检查开发者模式、升级 pymobiledevice3、确保目标应用正在运行，必要时使用降级方案。

### 4. CPU 数据异常低
**原因**：数据聚合时累加了所有系统进程而非目标进程。
**解决**：确保使用最新版本代码（已修复进程过滤逻辑）。

## 调试技巧

### 手动测试 sysmon
```bash
pymobiledevice3 developer dvt sysmon process single <device_id>
```

### 启用详细日志
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```
