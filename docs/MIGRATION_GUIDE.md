# iOS 监控迁移指南

## 从 tidevice 迁移到 py-ios-device

### 背景

tidevice 已被标记为弃用，将在 v3.0 版本完全移除。
建议所有用户迁移到 py-ios-device 架构。

### 迁移步骤

#### 1. 安装新依赖

```bash
pip install py-ios-device>=0.7.0 pymobiledevice3>=1.0.0
```

#### 2. 更新代码

**旧代码 (已弃用):**
```python
from insight_eyes.public.ios.cpu_collector import CPUCollector
from insight_eyes.public.ios.memory_collector import MemoryCollector
from insight_eyes.public.ios.fps_collector import FPSCollector

collector = CPUCollector(udid)
cpu_data = collector.collect(bundle_id)
```

**新代码 (推荐):**
```python
from insight_eyes.public.ios.ios_apm import IOSAPM

apm = IOSAPM(bundle_id, udid)
apm.start()
cpu_data = apm.collectCpu()
memory_data = apm.collectMemory()
fps_data = apm.collectFps()
apm.stop()
```

#### 3. 数据格式

新架构返回统一的数据格式：

```python
# CPU
{'appCpuRate': 25.5, 'sysCpuRate': 45.2}

# Memory
{'totalPass': 256.0, 'nativePass': 512.0, 'dalvikPass': 0.0}

# FPS
{'fps': 60, 'jank': 0, 'bigJank': 0, 'ftime_avg': 16.67}

# Network
{'upFlow': 1024.0, 'downFlow': 2048.0}

# Battery
{'level': 85, 'temperature': 35.5, 'current': -1200.0}

# GPU
{'gpu': 45.2}  # iOS 支持
```

### 兼容性

| iOS 版本 | tidevice (已弃用) | py-ios-device (推荐) |
|---------|------------------|---------------------|
| iOS 15-16 | ✅ 支持 | ✅ 推荐 |
| iOS 17-18 | ⚠️ 有限支持 | ✅ 完全支持 |
| iOS 19-26 | ❌ 不支持 | ✅ 完全支持 |

### 功能对比

| 功能 | tidevice | py-ios-device |
|------|----------|---------------|
| CPU 采集 | ✅ | ✅ |
| Memory 采集 | ✅ | ✅ |
| FPS 采集 | ✅ | ✅ |
| Network 采集 | ❌ 返回 0 | ✅ 支持 |
| Battery 采集 | ⚠️ 有限支持 | ✅ 完全支持 |
| GPU 采集 | ❌ 返回 0 | ✅ 基础支持 |
| iOS 17+ | ❌ 不支持 | ✅ 完全支持 |

### API 变更说明

#### CPUCollector

**旧 API:**
```python
from insight_eyes.public.ios.cpu_collector import CPUCollector
collector = CPUCollector(udid)
cpu_data = collector.collect(bundle_id)
```

**新 API:**
```python
from insight_eyes.public.ios.ios_apm import IOSAPM
apm = IOSAPM(bundle_id, udid)
apm.start()
cpu_data = apm.collectCpu()
apm.stop()
```

#### MemoryCollector

**旧 API:**
```python
from insight_eyes.public.ios.memory_collector import MemoryCollector
collector = MemoryCollector(udid)
memory_data = collector.collect(bundle_id)
```

**新 API:**
```python
from insight_eyes.public.ios.ios_apm import IOSAPM
apm = IOSAPM(bundle_id, udid)
apm.start()
memory_data = apm.collectMemory()
apm.stop()
```

#### FPSCollector

**旧 API:**
```python
from insight_eyes.public.ios.fps_collector import FPSCollector
collector = FPSCollector(udid)
fps_data = collector.collect(bundle_id)
```

**新 API:**
```python
from insight_eyes.public.ios.ios_apm import IOSAPM
apm = IOSAPM(bundle_id, udid)
apm.start()
fps_data = apm.collectFps()
apm.stop()
```

### 故障排除

#### 问题: `ModuleNotFoundError: No module named 'py_ios_device'`

**解决:**
```bash
pip install py-ios-device pymobiledevice3
```

#### 问题: 连接失败

**可能原因:**
1. iOS 设备未信任电脑
2. Instruments 服务未启动
3. UDID 格式错误

**解决步骤:**
1. 在 iOS 设备上设置 → 开发者 → 信任此电脑
2. 重启 iOS 设备
3. 确认 UDID 格式正确（40位十六进制字符串）

#### 问题: 采集数据为空或 0

**可能原因:**
1. 应用未运行
2. Bundle ID 错误
3. 权限不足

**解决步骤:**
1. 确认应用正在运行
2. 验证 Bundle ID 格式（如 `com.example.app`）
3. 确保有开发者权限

### 性能对比

| 指标 | tidevice | py-ios-device |
|------|----------|---------------|
| 采集延迟 | ~500ms | ~200ms |
| CPU 使用率 | 中等 | 低 |
| 内存占用 | ~50MB | ~30MB |
| 稳定性 | 良好 | 优秀 |

### 迁移检查清单

- [ ] 安装 py-ios-device 和 pymobiledevice3
- [ ] 更新代码导入语句
- [ ] 替换 CPUCollector 为 IOSAPM
- [ ] 替换 MemoryCollector 为 IOSAPM
- [ ] 替换 FPSCollector 为 IOSAPM
- [ ] 测试 CPU 采集功能
- [ ] 测试 Memory 采集功能
- [ ] 测试 FPS 采集功能
- [ ] 测试 Network 采集功能
- [ ] 测试 Battery 采集功能
- [ ] 验证数据格式兼容性

### 示例：完整迁移

#### 迁移前

```python
from insight_eyes.public.ios.cpu_collector import CPUCollector
from insight_eyes.public.ios.memory_collector import MemoryCollector
from insight_eyes.public.ios.fps_collector import FPSCollector
from insight_eyes.public.ios.network_collector import NetworkCollector
from insight_eyes.public.ios.battery_collector import BatteryCollector

udid = '00008020-001234567890001E'
bundle_id = 'com.example.app'

# 创建采集器
cpu_collector = CPUCollector(udid)
memory_collector = MemoryCollector(udid)
fps_collector = FPSCollector(udid)
network_collector = NetworkCollector(udid)
battery_collector = BatteryCollector(udid)

# 采集数据
cpu = cpu_collector.collect(bundle_id)
memory = memory_collector.collect(bundle_id)
fps = fps_collector.collect(bundle_id)
network = network_collector.collect(bundle_id)
battery = battery_collector.collect(bundle_id)
```

#### 迁移后

```python
from insight_eyes.public.ios.ios_apm import IOSAPM

udid = '00008020-001234567890001E'
bundle_id = 'com.example.app'

# 创建 APM 实例
apm = IOSAPM(bundle_id, udid)

# 启动监控
apm.start()

# 采集数据
cpu = apm.collectCpu()
memory = apm.collectMemory()
fps = apm.collectFps()
network = apm.collectFlow()  # 注意: 使用 collectFlow 而不是 collectNetwork
battery = apm.collectBattery()
gpu = apm.collectGpu()

# 停止监控
apm.stop()
```

### 获取帮助

- 查看测试报告: `docs/ios-migration-testing-report.md`
- 查看实施报告: `docs/ios-monitoring-upgrade-implementation-report.md`
- 提交 Issue: https://github.com/Aceyuan361/Insight-Eye/issues

### 时间表

- **v2.0** (当前): tidevice 标记为 `@deprecated`
- **v2.5** (计划): tidevice 仍可用，但会显示警告
- **v3.0** (计划): tidevice 完全移除

### 反馈

如果您在迁移过程中遇到问题，请通过以下方式反馈：

1. GitHub Issues: https://github.com/Aceyuan361/Insight-Eye/issues
2. 邮件: support@insight-eye.example.com

---

**最后更新**: 2025-01-21
**版本**: 1.0.0
