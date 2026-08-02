# iOS 监控专题

**版本**: v2.1.0 · **作者**: Aceyuan361

## 概述

iOS 监控是 Insight-AITest **性能监控模块（模块 B）** 的设备采集后端，通过 pymobiledevice3 与设备通信。受限于 iOS 系统 API 能力，部分指标采用降级方案或估算值。采集器位于平台共享服务层 `platform/services/collectors/ios/`。

## 支持的系统版本

- **最低版本**: iOS 11.0
- **iOS 17+**: 通过 CoreDevice tunnel（userspace）支持，无需 root/管理员
- **iOS 26**: 需 pymobiledevice3 >= 10.3.0（v10.2.0 起 iOS 26 CoreDevice 协议适配，v10.2.1 起 Windows DTX 超时修复）

> 注：iOS 17+ 设备无法直接通过 usbmux 访问开发者服务，必须先建立 CoreDevice tunnel，再通过 RemoteServiceDiscoveryService (RSD) 访问。本项目使用 pymobiledevice3 v10.x 的 `UserspaceRsdTunnel`（纯 Python 网络栈，跨平台、无需 root/管理员）建立该 tunnel。
>
> **重要**：iOS 17+/26 上 DVT 服务（`com.apple.instruments.dtservicehub`，sysmon/进程列表/CPU/内存监控都依赖它）只有在挂载 **Personalized Developer Disk Image (DDI)** 后才会出现在 RSD 上。而挂载 personalized DDI 又要求设备先启用 **Developer Mode**。因此完整依赖链为：`Developer Mode → 挂载 personalized DDI → dtservicehub 可用 → DVT 监控可用`。项目会在连接后自动尝试挂载 DDI；若未开启 Developer Mode 则会提示用户。

## 技术栈

### 主要依赖
- **pymobiledevice3** >= 10.3.0 - iOS 设备通信（iOS 17+/26 需 v10.2+ 的 CoreDevice tunnel 支持）
- **sysmon** - 系统监控服务（DVT）
- **DiagnosticsService** - 诊断服务

### 设备要求
- 需要信任电脑
- 需要开启开发者模式（iOS 16+ 在「设置 → 隐私与安全性 → 开发者模式」开启）

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
| CPU | sysmon process（按核心数归一化） | psutil + top | 中 | ✅ 完整支持 |
| Memory | sysmon memory | diagnostics | 中 | ✅ 完整支持 |
| Energy | sysmon energy | diagnostics | 中 | ✅ 完整支持 |
| Battery | diagnostics | - | 高 | ✅ 完整支持 |
| FPS | DVT Graphics 服务（CoreAnimationFramesPerSecond） | - | 高 | ✅ 完整支持 |
| Network | pcapd（iOS <17）；iOS 17+/26 RSD 不支持 | - | - | ⚠️ iOS 17+/26 不可用 |
| GPU | - | - | - | ❌ 暂不支持（数据可获取但管线未接通） |

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
1. **GPU 监控**：DVT Graphics 服务可获取 GPU 利用率（Device/Renderer/Tiler Utilization %），但当前数据管线（MetricsData/前端）尚未接通 GPU 字段，暂不展示。
2. **FPS 监控**：已通过 DVT Graphics 服务的 `CoreAnimationFramesPerSecond` 实现真实帧率采集（系统级 Core Animation 合成帧率，与 PerfDog/Xcode 同源）。fps=0 表示当前无前台渲染（锁屏/静止画面）。Jank 检测基于 ~1Hz 采样的帧率突降启发式。
3. **网络流量**：iOS <17 可通过 pcapd 采集；iOS 17+/26 上 pcapd 的 RSD 服务被系统拒绝（StartServiceError），暂不可用。sysmon 提供的网络数据粒度较粗。

### 数据处理特性
1. **进程过滤**：iOS sysmon 返回 1000+ 系统进程的数据，采集器会过滤并只累加目标进程的数据
2. **平滑处理**：使用上次有效值缓存，避免无数据时出现 0 值跳变
3. **超时控制**：sysmon 采集操作默认超时时间为 8 秒

## 常见问题

### 1. 设备未信任
在 iOS 设备上信任电脑，然后重新连接。

### 2. pymobiledevice3 未安装或版本过低
```bash
pip install "pymobiledevice3>=10.3.0"
```

> ⚠️ iOS 17+ / iOS 26 设备必须使用 v10.3.0+。9.x 版本的 `get_core_device_tunnel_services` 在 iOS 26 上会返回空列表，报「未找到 iOS 17+ tunnel 服务」。

### 3. 「未找到 iOS 17+ tunnel 服务」错误（iOS 26）
**根因**：pymobiledevice3 版本过低（< 10.2.0），无法与 iOS 26 改动后的 CoreDevice 协议握手。

**解决**：
1. 升级：`pip install -U "pymobiledevice3>=10.3.0"`
2. 确认设备已信任电脑、已开启 Developer Mode
3. 重启应用重试

### 3.1. `No such service: com.apple.instruments.dtservicehub` 错误（iOS 17+/26）
**根因**：tunnel 已建立，但 RSD 上没有 DVT 服务。iOS 17+/26 的 DVT 服务（sysmon、进程列表、CPU/内存监控都依赖的 `com.apple.instruments.dtservicehub`）只有在挂载 **Personalized DDI** 后才会出现，而挂载 DDI 要求先启用 **Developer Mode**。

**完整依赖链**：`Developer Mode 开启 → 可挂载 personalized DDI → dtservicehub 出现 → DVT 监控可用`

**解决**：
1. 在设备上「设置 → 隐私与安全性 → 开发者模式」开启 Developer Mode（首次需重启设备并在重启后再次确认开启）
2. 重启应用，连接设备（项目会自动挂载 DDI）
3. 若仍失败，可手动验证 Developer Mode 状态：
   ```bash
   pymobiledevice3 developer dvt sysmon process single <udid> --rsd <tunnel_host> <tunnel_port>
   ```

### 3.2. 设置里找不到「开发者模式」开关（iOS 16+）
**根因**：iOS 16+ 默认**隐藏** Developer Mode 开关，只有设备被「用于开发」（pairing）后才会显示。通常需要连 Mac + Xcode 才能触发，但本项目可直接通过 AMFI 服务让它显示，**无需 Mac/Xcode**。

> 关键：iOS 17+/26 上 `com.apple.amfi.lockdown` 服务只能通过 **usbmux** 访问（RSD tunnel 上没有 amfi）。连接时若检测到 Developer Mode 未启用，项目会自动通过 usbmux 路径发送 reveal 动作。

**解决**：
1. 连接设备（即使首次失败，项目也会自动尝试 reveal）
2. 去 iPhone「设置 → 隐私与安全性」，**滑到最底部**应出现「开发者模式」
3. 若仍看不到：重新插拔 USB → 再次连接设备（会再次发送 reveal）
4. 出现后：打开开关 → 重启 → 在弹窗中点「Turn On」→ 重新运行程序

也可手动触发 reveal（无需 GUI）：
```python
from insight_aitest.platform.services.collectors.ios.devdisk_helper import DevDiskHelper
DevDiskHelper.reveal_developer_mode("你的设备UDID")
```

### 4. sysmon 采集失败
**可能原因**：设备未开启开发者模式、pymobiledevice3 版本不兼容、设备连接不稳定、目标应用未运行。

**解决**：检查开发者模式、升级 pymobiledevice3、确保目标应用正在运行，必要时使用降级方案。

### 5. CPU 数据异常低
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
