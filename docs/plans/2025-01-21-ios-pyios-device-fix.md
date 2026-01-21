# iOS py-ios-device 全面支持修复计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复 iOS 15-26 设备全面使用 py-ios-device 架构，移除 tidevice 依赖

**Architecture:**
- 修改 `PyIOSConnection` 支持直接连接（iOS 15-16）和隧道连接（iOS 17+）
- 设置 `adapter.platform` 属性供平台检测
- `IOSAPM` 统一使用 py-ios-device，移除 tidevice 降级逻辑

**Tech Stack:** py-ios-device, pymobiledevice3, iOS 15-26

---

## 问题分析

**当前问题:**
1. `DeviceAdapterFactory` 创建 adapter 时未设置 `platform` 属性
2. `PyIOSConnection.__init__` 硬编码要求 `remote_address` 参数（仅 iOS 17+ 需要）
3. `main_window.py` 平台检测失败：`hasattr(adapter, 'platform') = False`
4. iOS 设备被误识别为 Android，采集数据全为 0

**解决方案:**
1. ✅ 在 `DeviceAdapterFactory` 中设置 `adapter.platform` 属性（已完成）
2. 修改 `PyIOSConnection` 让 `remote_address` 为可选参数（None = 直接连接）
3. 修改 `IOSAPM._ensure_connection()` 传递 `remote_address=None`（iOS 15-16）

---

## Task 1: 修改 PyIOSConnection 支持直接连接

**Files:**
- Modify: `insight_eyes/public/ios/pyios_connect.py:36-70`

**Step 1: 修改 __init__ 方法签名**

```python
def __init__(self, udid: str, remote_address: Optional[Tuple[str, int]] = None):
    """
    初始化连接管理器

    Args:
        udid: iOS 设备唯一标识符
        remote_address: 远程隧道地址 (host, port) 或 None
                        - iOS 15-16: 有线连接，直接连接设备（None）
                        - iOS 17-26: 无线/USB连接，需要隧道 ((host, port))
    """
    self.udid = udid
    self.remote_address = remote_address

    # ... 其余代码保持不变
```

**Step 2: 修改 connect() 方法支持直接连接**

找到 `connect()` 方法中的远程锁定服务连接部分（第 87-89 行）：

```python
# 原代码:
self._rsd = RemoteLockdownClient(self.remote_address)

# 修改为:
if self.remote_address:
    # iOS 17+: 通过 pymobiledevice3 隧道连接
    self._rsd = RemoteLockdownClient(self.remote_address)
    logger.debug(f"[PyIOS连接] 使用隧道连接: {self.remote_address}")
else:
    # iOS 15-16: 直接连接（有线连接）
    self._rsd = RemoteLockdownClient()
    logger.debug("[PyIOS连接] 使用直接连接（本地设备）")
```

**Step 3: 运行导入测试验证**

```bash
python -c "from insight_eyes.public.ios.pyios_connect import PyIOSConnection; print('✓ 导入成功')"
```

Expected: `✓ 导入成功`

**Step 4: 提交修改**

```bash
git add insight_eyes/public/ios/pyios_connect.py
git commit -m "feat: PyIOSConnection 支持直接连接

- remote_address 参数改为可选（默认 None）
- iOS 15-16 有线连接：remote_address=None，直接连接
- iOS 17-26 隧道连接：remote_address=(host, port)"
```

---

## Task 2: 修改 IOSAPM 使用直接连接

**Files:**
- Modify: `insight_eyes/public/ios/ios_apm.py:67-85`

**Step 1: 修改 _ensure_connection() 方法**

找到 `_ensure_connection()` 方法（第 67-85 行）：

```python
def _ensure_connection(self) -> bool:
    """
    确保连接已建立

    对于 iOS 15-16 使用直接连接（remote_address=None）
    对于 iOS 17-26 使用隧道连接（需要 IOSTunnelManager）

    Returns:
        bool: 连接是否可用
    """
    if self._connection is None:
        try:
            from insight_eyes.public.ios.pyios_connect import PyIOSConnection

            # iOS 15-16 有线连接：直接连接（不需要隧道）
            # iOS 17-26 无线/USB：需要通过 pymobiledevice3 建立隧道
            self._connection = PyIOSConnection(self.udid, remote_address=None)

            if not self._connection.connect():
                logger.error("[IOSAPM] 连接失败")
                return False
        except Exception as e:
            logger.error(f"[IOSAPM] 连接异常: {e}")
            return False

    return self._connection.is_connected()
```

**Step 2: 验证修改**

```bash
python -c "
from insight_eyes.public.ios.ios_apm import IOSAPM
apm = IOSAPM('com.test.app', '00008030-001D29A62EEA802E')
print('✓ IOSAPM 初始化成功')
print(f'✓ UDID: {apm.udid}')
"
```

Expected:
```
✓ IOSAPM 初始化成功
✓ UDID: 00008030-001D29A62EEA802E
```

**Step 3: 提交修改**

```bash
git add insight_eyes/public/ios/ios_apm.py
git commit -m "feat: IOSAPM 使用直接连接（iOS 15-16）

- _ensure_connection() 传递 remote_address=None
- 移除 pymobiledevice3 隧道依赖（iOS 15-16）
- 支持有线 USB 连接的设备"
```

---

## Task 3: 验证 platform 属性设置

**Files:**
- Verify: `insight_eyes/desktop/core/device_adapters.py:1893-1895`

**Step 1: 确认 DeviceAdapterFactory 设置了 platform 属性**

检查 `device_adapters.py` 第 1893-1895 行：

```python
# 设置 platform 属性，供 main_window.py 检测平台类型
adapter.platform = platform
return adapter
```

**Step 2: 运行平台检测测试**

```bash
python -c "
from insight_eyes.public.common import Platform
from insight_eyes.desktop.core.device_adapters import DeviceAdapterFactory

# 创建 iOS adapter
adapter = DeviceAdapterFactory.create_adapter('00008030-001D29A62EEA802E', Platform.iOS)
print(f'✓ Adapter created: {type(adapter).__name__}')
print(f'✓ Has platform: {hasattr(adapter, \"platform\")}')
print(f'✓ Platform value: {adapter.platform}')
print(f'✓ Platform is iOS: {adapter.platform == Platform.iOS}')
"
```

Expected:
```
✓ Adapter created: IOSDeviceAdapter
✓ Has platform: True
✓ Platform value: Platform.iOS
✓ Platform is iOS: True
```

**Step 3: 如果测试通过，提交 device_adapters.py 修改**

```bash
git add insight_eyes/desktop/core/device_adapters.py
git commit -m "fix: 设置 adapter.platform 属性供平台检测

- DeviceAdapterFactory 创建 adapter 后设置 platform 属性
- 修复 main_window.py 平台检测失败问题
- 确保 iOS/Android 设备正确识别"
```

---

## Task 4: 端到端测试

**Step 1: 重启桌面应用**

```bash
python -m insight_eyes
```

**Step 2: 验证日志输出**

检查日志是否包含：
```
[DEBUG] hasattr(adapter, 'platform') = True
[DEBUG] adapter.platform = Platform.iOS
[DEBUG] is_ios = True
===== 开始 iOS 串行指标采集 =====
```

**Expected:**
- ✅ `hasattr(adapter, 'platform') = True`
- ✅ `is_ios = True`
- ✅ 启动 iOS 采集而非 Android 采集
- ✅ PyIOSConnection 使用直接连接
- ✅ 采集到正确的 CPU/Memory/FPS 数据

**Step 3: 验证数据采集**

在应用中选择设备和应用，开始监控后检查：
- CPU > 0%
- Memory > 0MB
- FPS > 0
- Battery > 0%

**Step 4: 提交测试结果**

```bash
git add .
git commit -m "test: 验证 iOS py-ios-device 直接连接修复

- iOS 16.3.1 设备成功使用 py-ios-device
- 平台检测正确识别 iOS 设备
- 采集数据正常（CPU/Memory/FPS > 0）
- 无需 tidevice 降级方案"
```

---

## 验证清单

### 功能验证

- [ ] Task 1: PyiOSConnection 支持直接连接
- [ ] Task 2: IOSAPM 使用直接连接
- [ ] Task 3: platform 属性正确设置
- [ ] Task 4: 端到端测试通过

### iOS 版本兼容性

- [ ] iOS 15.x: 直接连接，py-ios-device ✅
- [ ] iOS 16.x: 直接连接，py-ios-device ✅
- [ ] iOS 17.x: 隧道连接（可选），py-ios-device ✅
- [ ] iOS 18.x: 隧道连接（可选），py-ios-device ✅

### 代码质量

- [ ] 无 tidevice 相关代码残留
- [ ] 所有导入路径使用 py-ios-device
- [ ] 日志清晰标注连接方式（直接/隧道）

---

## 预期结果

**修复前:**
```
[DEBUG] hasattr(adapter, 'platform') = False
[DEBUG] is_ios = False
===== 开始 Android 并行指标采集 =====
[IOSAPM] 连接异常: PyIOSConnection.__init__() missing 1 required positional argument: 'remote_address'
采集结果: CPU=0%, Memory=0MB, FPS=0
```

**修复后:**
```
[DEBUG] hasattr(adapter, 'platform') = True
[DEBUG] adapter.platform = Platform.iOS
[DEBUG] is_ios = True
===== 开始 iOS 串行指标采集 =====
[PyIOS连接] 使用直接连接（本地设备）
[PyIOS连接] ✓ 连接建立成功
采集结果: CPU=15%, Memory=250MB, FPS=60
```

---

## 故障排除

### 如果 PyIOSConnection 连接失败

**问题:** `RemoteLockdownClient() 不支持无参数初始化

**解决方案:** 检查 py-ios-device 版本
```bash
pip show py-ios-device
# 需要 >= 0.7.0
```

### 如果 platform 属性未生效

**问题:** `hasattr(adapter, 'platform')` 仍然返回 False

**解决方案:** 确保 device_adapters.py 修改已保存并重启应用

### 如果采集数据仍为 0

**问题:** py-ios-device 连接成功但采集失败

**解决方案:**
1. 检查 Bundle ID 是否正确
2. 检查应用是否在前台运行
3. 查看 `[IOSAPM]` 日志排查具体错误

---

**执行选项:**

1. **Subagent-Driven (this session)** - 我逐任务实现，每步审查
2. **Parallel Session (separate)** - 新会话批量执行

**Which approach?**
