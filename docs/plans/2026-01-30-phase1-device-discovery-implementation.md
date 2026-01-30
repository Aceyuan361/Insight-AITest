# 第一阶段：设备发现与连接实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现完整的设备管理功能，支持 Android 和 iOS 设备的发现、连接、状态监控和应用枚举。

**Architecture:** 将桌面层的设备管理功能移植到核心层，通过 FastAPI 暴露 RESTful API，前端通过 HTTP 调用实现设备管理。

**Tech Stack:** FastAPI, ADB (Android), pymobiledevice3 (iOS), React/TypeScript

---

## 实施概览

### 主要任务
1. 扩展 `common.py` 支持 iOS 设备扫描
2. 移植设备扫描逻辑到核心层 `DeviceManager`
3. 扩展 Web API 支持设备连接/断开操作
4. 添加应用枚举功能
5. 前端集成真实设备管理 API

### 文件结构
```
insight_eyes/
├── public/
│   ├── common.py                    [修改] 添加 iOS 设备扫描
│   ├── android/
│   │   └── android_apm.py            [复用] Android 设备管理
│   └── ios/
│       └── ios_apm.py                [复用] iOS 设备管理
├── core/
│   ├── device_manager.py             [修改] 实现真实设备扫描
│   └── models/
│       └── device.py                 [修改] 扩展设备模型
└── web/
    ├── api/
    │   └── devices.py                [修改] 添加连接/断开/应用枚举 API
    └── frontend/
        └── src/
            ├── services/
            │   └── api.ts            [修改] 集成设备管理 API
            └── components/
                └── panels/
                    └── DeviceSelectionPanel.tsx  [修改] 使用真实 API
```

---

## Task 1: 扩展 common.py 支持 iOS 设备扫描

**Files:**
- Modify: `insight_eyes/public/common.py:20-80`

**Step 1: 添加 iOS 设备扫描方法**

在 `Devices` 类中添加 `_get_ios_devices` 方法。

```python
def _get_ios_devices(self):
    """获取 iOS 设备列表"""
    try:
        from pymobiledevice3.usbmux import list_devices

        devices = []
        ios_device_list = list_devices()

        for device in ios_device_list:
            device_id = str(device.serial)
            devices.append(f"iOS {device_id}")
            logger.debug(f"检测到 iOS 设备: {device_id}")

        return devices

    except ImportError:
        logger.debug("pymobiledevice3 未安装，跳过 iOS 设备扫描")
        return []
    except Exception as e:
        logger.error(f"获取 iOS 设备失败: {e}")
        return []
```

**Step 2: 更新 getDevices 方法**

```python
def getDevices(self):
    """获取所有连接的设备列表"""
    devices = []

    # 获取 Android 设备
    android_devices = self._get_android_devices()
    for device_id in android_devices:
        devices.append(f"Android {device_id}")

    # 获取 iOS 设备
    ios_devices = self._get_ios_devices()
    devices.extend(ios_devices)

    return devices
```

**Step 3: 更新 getIdbyDevice 方法支持 iOS**

```python
def getIdbyDevice(self, device_info_str, platform):
    """从设备信息字符串中提取设备 ID"""
    if platform == Platform.Android:
        if device_info_str.startswith("Android "):
            return device_info_str[8:].strip()
        return device_info_str
    elif platform == Platform.IOS:
        if device_info_str.startswith("iOS "):
            return device_info_str[4:].strip()
        return device_info_str
    return device_info_str
```

**Step 4: 运行测试验证**

```bash
cd .worktrees/phase1-device-discovery
python -c "from insight_eyes.public.common import Devices; d = Devices(); print(d.getDevices())"
```

预期输出：至少包含连接的设备列表（如果有 Android/iOS 设备连接）

**Step 5: 提交代码**

```bash
git add insight_eyes/public/common.py
git commit -m "feat: 添加 iOS 设备扫描支持到 common.py"
```

---

## Task 2: 实现核心层设备扫描逻辑

**Files:**
- Modify: `insight_eyes/core/device_manager.py:27-41`
- Reference: `insight_eyes/desktop/core/device_manager.py:123-149`

**Step 1: 移植 Android 设备扫描逻辑**

将桌面层的 Android 设备扫描逻辑移植到核心层 `DeviceManager.scan_devices()` 方法。

```python
@staticmethod
def scan_devices() -> List[Device]:
    """扫描可用设备"""
    from insight_eyes.public.common import Devices, Platform
    from insight_eyes.core.models.device import Device, DeviceType, DeviceStatus

    logger.info("扫描设备...")
    devices = []

    try:
        devices_detector = Devices()
        device_list = devices_detector.getDevices()

        for device_str in device_list:
            try:
                # 解析设备类型和ID
                if device_str.startswith("Android "):
                    device_id = device_str[8:].strip()
                    device_type = DeviceType.ANDROID
                    platform = Platform.ANDROID
                elif device_str.startswith("iOS "):
                    device_id = device_str[4:].strip()
                    device_type = DeviceType.IOS
                    platform = Platform.IOS
                else:
                    continue

                # 创建设备适配器并获取设备信息
                from insight_eyes.desktop.core.device_adapters import DeviceAdapterFactory

                adapter = DeviceAdapterFactory.create_adapter(device_id, platform)
                if not adapter:
                    logger.warning(f"无法为设备 {device_id} 创建适配器")
                    continue

                # 连接设备并获取信息
                if adapter.connect():
                    device_info = adapter.get_device_info()
                    if device_info:
                        # 转换为核心层 Device 模型
                        device = Device(
                            device_id=device_info.device_id,
                            name=device_info.name,
                            type=device_type,
                            status=DeviceStatus.ONLINE,
                            sdk_version=device_info.os_version,
                            model=device_info.model
                        )
                        devices.append(device)
                        logger.info(f"发现设备: {device.name} ({device.type.value})")

            except Exception as e:
                logger.error(f"处理设备失败 [{device_str}]: {e}")
                continue

    except Exception as e:
        logger.error(f"设备扫描异常: {e}")

    return devices
```

**Step 2: 运行测试验证**

```bash
cd .worktrees/phase1-device-discovery
python -c "from insight_eyes.core.device_manager import DeviceManager; devices = DeviceManager.scan_devices(); print(f'发现 {len(devices)} 个设备'); [print(f'- {d.name} ({d.type.value})') for d in devices]"
```

预期输出：显示检测到的设备数量和列表

**Step 3: 提交代码**

```bash
git add insight_eyes/core/device_manager.py
git commit -m "feat: 实现核心层真实设备扫描逻辑"
```

---

## Task 3: 扩展 Web API 支持设备连接/断开

**Files:**
- Modify: `insight_eyes/web/api/devices.py`
- Test: `tests/integration/test_device_api.py` (新建)

**Step 1: 添加设备连接 API**

```python
@router.post("/{device_id}/connect")
async def connect_device(device_id: str):
    """连接指定设备"""
    try:
        from insight_eyes.desktop.core.device_adapters import DeviceAdapterFactory
        from insight_eyes.core.models.device import DeviceType
        from insight_eyes.public.common import Platform

        # 获取设备列表以确定平台类型
        devices = DeviceManager.scan_devices()
        device = next((d for d in devices if d.device_id == device_id), None)

        if not device:
            raise HTTPException(status_code=404, detail="Device not found")

        # 转换 DeviceType 到 Platform
        platform = Platform.ANDROID if device.type == DeviceType.ANDROID else Platform.IOS

        # 创建适配器并连接
        adapter = DeviceAdapterFactory.create_adapter(device_id, platform)
        if not adapter:
            raise HTTPException(status_code=500, detail="Failed to create device adapter")

        if adapter.connect():
            logger.info(f"设备连接成功: {device_id}")
            return {"device_id": device_id, "status": "connected"}
        else:
            raise HTTPException(status_code=500, detail="Failed to connect to device")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"设备连接失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**Step 2: 添加设备断开 API**

```python
@router.delete("/{device_id}")
async def disconnect_device(device_id: str):
    """断开设备连接"""
    try:
        from insight_eyes.desktop.core.device_adapters import DeviceAdapterFactory
        from insight_eyes.core.models.device import DeviceType
        from insight_eyes.public.common import Platform

        # 获取设备列表以确定平台类型
        devices = DeviceManager.scan_devices()
        device = next((d for d in devices if d.device_id == device_id), None)

        if not device:
            raise HTTPException(status_code=404, detail="Device not found")

        # 转换 DeviceType 到 Platform
        platform = Platform.ANDROID if device.type == DeviceType.ANDROID else Platform.IOS

        # 创建适配器并断开
        adapter = DeviceAdapterFactory.create_adapter(device_id, platform)
        if adapter:
            adapter.disconnect()

        logger.info(f"设备已断开: {device_id}")
        return {"device_id": device_id, "status": "disconnected"}

    except Exception as e:
        logger.error(f"设备断开失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**Step 3: 刷新设备列表 API**

```python
@router.post("/refresh")
async def refresh_devices():
    """刷新设备列表（重新扫描）"""
    try:
        devices = DeviceManager.scan_devices()
        logger.info(f"刷新设备列表: 发现 {len(devices)} 个设备")
        return devices
    except Exception as e:
        logger.error(f"刷新设备列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**Step 4: 运行测试验证**

```bash
cd .worktrees/phase1-device-discovery/insight_eyes/web
# 启动后端服务（如果有）或直接测试
python -c "from api.devices import router; print('API routes loaded successfully')"
```

**Step 5: 提交代码**

```bash
git add insight_eyes/web/api/devices.py
git commit -m "feat: 添加设备连接/断开/刷新 API"
```

---

## Task 4: 添加应用枚举功能

**Files:**
- Modify: `insight_eyes/web/api/devices.py` (追加新端点)
- Reference: `insight_eyes/desktop/core/app_enumerator.py`

**Step 1: 添加获取应用列表 API**

```python
@router.get("/{device_id}/apps")
async def get_device_apps(device_id: str, include_system: bool = False):
    """获取设备应用列表"""
    try:
        from insight_eyes.desktop.core.app_enumerator import AppEnumeratorFactory
        from insight_eyes.core.models.device import DeviceType
        from insight_eyes.public.common import Platform

        # 获取设备列表以确定平台类型
        devices = DeviceManager.scan_devices()
        device = next((d for d in devices if d.device_id == device_id), None)

        if not device:
            raise HTTPException(status_code=404, detail="Device not found")

        # 转换 DeviceType 到 Platform
        platform = Platform.ANDROID if device.type == DeviceType.ANDROID else Platform.IOS

        # 创建枚举器并获取应用列表
        enumerator = AppEnumeratorFactory.create_enumerator(device_id, platform)
        if not enumerator:
            raise HTTPException(status_code=500, detail="Failed to create app enumerator")

        apps = enumerator.enumerate_apps(include_system_apps=include_system)

        # 获取运行中的应用
        try:
            running_apps = enumerator.get_running_apps()
            running_packages = {app.package_name for app in running_apps}

            # 更新应用运行状态
            for app in apps:
                if app.package_name in running_packages:
                    running_app = next((a for a in running_apps if a.package_name == app.package_name), None)
                    if running_app:
                        app.is_running = True
                        app.pid = running_app.pid
                        app.status = running_app.status
        except Exception as e:
            logger.warning(f"获取运行中的应用失败: {e}")

        # 转换为字典格式返回
        apps_data = [
            {
                "package_name": app.package_name,
                "name": app.name,
                "is_running": app.is_running,
                "pid": app.pid,
                "status": app.status.value if app.status else None
            }
            for app in apps
        ]

        logger.info(f"获取设备应用列表: {device_id}, 应用数量: {len(apps_data)}")
        return apps_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取应用列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**Step 2: 提交代码**

```bash
git add insight_eyes/web/api/devices.py
git commit -m "feat: 添加应用枚举 API"
```

---

## Task 5: 前端集成真实设备管理 API

**Files:**
- Modify: `insight_eyes/web-frontend/src/services/api.ts`
- Modify: `insight_eyes/web-frontend/src/components/panels/DeviceSelectionPanel.tsx`

**Step 1: 更新 API 服务**

在 `api.ts` 中添加设备管理 API 调用方法：

```typescript
// 设备管理 API
export const deviceApi = {
  // 获取设备列表
  getDevices: async (): Promise<Device[]> => {
    const response = await fetch(`${API_BASE}/api/devices`);
    if (!response.ok) throw new Error('Failed to fetch devices');
    return response.json();
  },

  // 刷新设备列表
  refreshDevices: async (): Promise<Device[]> => {
    const response = await fetch(`${API_BASE}/api/devices/refresh`, {
      method: 'POST',
    });
    if (!response.ok) throw new Error('Failed to refresh devices');
    return response.json();
  },

  // 连接设备
  connectDevice: async (deviceId: string): Promise<{ device_id: string; status: string }> => {
    const response = await fetch(`${API_BASE}/api/devices/${deviceId}/connect`, {
      method: 'POST',
    });
    if (!response.ok) throw new Error('Failed to connect device');
    return response.json();
  },

  // 断开设备
  disconnectDevice: async (deviceId: string): Promise<{ device_id: string; status: string }> => {
    const response = await fetch(`${API_BASE}/api/devices/${deviceId}`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error('Failed to disconnect device');
    return response.json();
  },

  // 获取设备应用列表
  getDeviceApps: async (deviceId: string, includeSystem = false): Promise<AppInfo[]> => {
    const response = await fetch(`${API_BASE}/api/devices/${deviceId}/apps?include_system=${includeSystem}`);
    if (!response.ok) throw new Error('Failed to fetch device apps');
    return response.json();
  },
};
```

**Step 2: 更新 DeviceSelectionPanel 组件**

移除 mock 数据注释，使用真实 API：

```typescript
export default function DeviceSelectionPanel() {
  const { devices, setDevices, selectedDevice, setSelectedDevice } = useMonitoringStore();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 加载设备列表
  const loadDevices = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const deviceList = await deviceApi.getDevices();
      setDevices(deviceList);
    } catch (err) {
      console.error('Failed to load devices:', err);
      setError('无法加载设备列表，请检查后端服务是否正常运行');
    } finally {
      setIsLoading(false);
    }
  };

  // 刷新设备列表
  const handleRefresh = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const deviceList = await deviceApi.refreshDevices();
      setDevices(deviceList);
    } catch (err) {
      console.error('Failed to refresh devices:', err);
      setError('刷新设备列表失败');
    } finally {
      setIsLoading(false);
    }
  };

  // 初始加载
  useEffect(() => {
    loadDevices();
  }, []);

  return (
    <div>
      {/* 组件内容保持不变，使用真实设备数据 */}
    </div>
  );
}
```

**Step 3: 构建前端验证**

```bash
cd .worktrees/phase1-device-discovery/insight_eyes/web-frontend
npm run build
```

**Step 4: 提交代码**

```bash
git add insight_eyes/web-frontend/src/services/api.ts
git add insight_eyes/web-frontend/src/components/panels/DeviceSelectionPanel.tsx
git commit -m "feat: 前端集成真实设备管理 API"
```

---

## 验收标准

完成所有任务后，应该满足以下标准：

1. **设备扫描**
   - [ ] 能够扫描并显示所有连接的 Android 设备
   - [ ] 能够扫描并显示所有连接的 iOS 设备
   - [ ] 设备信息包含：设备ID、名称、型号、系统版本

2. **设备连接/断开**
   - [ ] 能够连接指定设备
   - [ ] 能够断开设备连接
   - [ ] 连接状态实时更新

3. **应用枚举**
   - [ ] 能够枚举设备上的已安装应用
   - [ ] 能够识别运行中的应用
   - [ ] 应用列表包含：包名、应用名、运行状态、PID

4. **性能**
   - [ ] 设备扫描响应时间 < 2 秒
   - [ ] API 调用响应时间 < 500ms

5. **错误处理**
   - [ ] 设备未连接时显示友好提示
   - [ ] API 调用失败时显示错误信息

---

## 测试计划

### 单元测试
```bash
cd .worktrees/phase1-device-discovery
pytest tests/unit/test_device_manager.py -v
pytest tests/unit/test_common.py -v
```

### 集成测试
```bash
pytest tests/integration/test_device_api.py -v
```

### E2E 测试
```bash
cd .worktrees/phase1-device-discovery/insight_eyes/web-frontend
npx playwright test e2e/device-management.spec.ts
```

---

## 风险与注意事项

### 高风险项
1. **iOS 设备兼容性**
   - pymobiledevice3 版本兼容问题
   - iOS 设备需要信任开发者证书

2. **ADB 权限问题**
   - Linux/Mac 可能需要 sudo 权限
   - Windows 需要正确安装驱动

### 中风险项
1. **设备连接稳定性**
   - USB 连接可能不稳定
   - 需要实现重连机制

2. **性能问题**
   - 应用枚举可能较慢
   - 需要实现缓存机制

---

## 参考文档

- 桌面层设备管理器: `insight_eyes/desktop/core/device_manager.py:1-1535`
- 设备适配器: `insight_eyes/desktop/core/device_adapters.py:1-869`
- AndroidAPM: `insight_eyes/public/android/android_apm.py`
- IOSAPM: `insight_eyes/public/ios/ios_apm.py`
- 迁移计划: `docs/plans/2026-01-30-web-migration-plan.md:234-303`
