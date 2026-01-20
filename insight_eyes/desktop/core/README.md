# 设备连接与App枚举筛选模块

## 模块概述

本模块提供完整的移动设备管理功能，支持Android和iOS设备的自动检测、连接、应用枚举和状态监控。

## 核心功能

### 1. 设备连接
- 支持USB数据线和Wi-Fi两种连接方式
- Android基于ADB接口
- iOS基于tidevice工具
- 自动识别已连接设备
- 展示设备详细信息（名称、型号、系统版本、电池电量等）

### 2. 设备与App枚举
- 枚举设备上所有已安装的应用
- 显示应用名称、包名/Bundle ID、进程ID、运行状态
- 支持按应用名称、包名搜索
- 快速定位目标应用

### 3. 设备状态监控
- 实时监控设备连接状态
- 自动检测设备断开
- 监控电池电量、温度、网络类型
- 支持多设备并行监控

### 4. 无侵入式设计
- 无需root/越狱
- 不修改App代码
- 不重启App
- 不影响设备正常运行

## 目录结构

```
insight_eyes/desktop/core/
├── __init__.py              # 模块初始化
├── models.py                # 数据模型定义
├── device_adapters.py       # 设备连接适配器
├── app_enumerator.py        # 应用枚举器
├── device_manager.py        # 设备管理器
└── README.md               # 本文档
```

## 快速开始

### 1. 基本使用

```python
from PyQt6.QtWidgets import QApplication
from insight_eyes.desktop.core import DeviceManager

# 创建应用实例
app = QApplication([])

# 创建设备管理器
manager = DeviceManager()

# 开始扫描设备
manager.start_scan()

# 连接信号
manager.device_discovered.connect(lambda device: print(f"发现设备: {device.name}"))
manager.device_lost.connect(lambda device_id: print(f"设备断开: {device_id}"))

# 运行事件循环
app.exec()
```

### 2. 获取设备列表

```python
# 获取所有设备
devices = manager.get_devices()

# 使用过滤器筛选设备
from insight_eyes.desktop.core import DeviceFilter, Platform

filter = DeviceFilter(
    platform=Platform.ANDROID,
    search_text="Samsung"
)

android_devices = manager.get_devices(filter)
```

### 3. 枚举应用

```python
# 获取设备上的所有应用
device_id = "emulator-5554"
apps = manager.get_device_apps(device_id)

# 使用过滤器筛选应用
from insight_eyes.desktop.core import AppFilter

app_filter = AppFilter(
    search_text="WeChat",
    running_only=True
)

filtered_apps = manager.get_device_apps(device_id, app_filter)
```

### 4. 监控设备

```python
# 开始监控设备
manager.monitor_device(device_id)

# 连接监控信号
manager.device_updated.connect(lambda device: print(f"设备状态更新: {device.battery_level}%"))
manager.app_list_updated.connect(lambda did, apps: print(f"应用列表更新: {len(apps)}个应用"))

# 停止监控
manager.stop_monitoring(device_id)
```

## 数据模型

### DeviceInfo - 设备信息

```python
from insight_eyes.desktop.core import DeviceInfo, Platform, DeviceStatus

device = DeviceInfo(
    device_id="emulator-5554",
    name="Android Emulator",
    platform=Platform.ANDROID,
    model="sdk_gphone64_x86_64",
    os_version="Android 11",
    battery_level=100,
    status=DeviceStatus.CONNECTED
)
```

### AppInfo - 应用信息

```python
from insight_eyes.desktop.core import AppInfo, AppStatus

app = AppInfo(
    package_name="com.example.app",
    app_name="Example App",
    pid=12345,
    is_running=True,
    status=AppStatus.RUNNING
)
```

### DeviceFilter - 设备过滤器

```python
from insight_eyes.desktop.core import DeviceFilter, Platform

# 只显示Android设备，搜索关键字为"Samsung"
filter = DeviceFilter(
    platform=Platform.ANDROID,
    search_text="Samsung",
    min_os_version="Android 10"
)
```

### AppFilter - 应用过滤器

```python
from insight_eyes.desktop.core import AppFilter

# 只显示运行中的应用，搜索关键字为"WeChat"
filter = AppFilter(
    running_only=True,
    search_text="WeChat"
)
```

## 高级用法

### 1. 直接使用设备适配器

```python
from insight_eyes.desktop.core import DeviceAdapterFactory, Platform

# 创建Android设备适配器
adapter = DeviceAdapterFactory.create_adapter(device_id, Platform.ANDROID)

# 连接设备
if adapter.connect():
    # 获取设备信息
    device_info = adapter.get_device_info()

    # 执行命令
    output = adapter.execute_command("ls /sdcard")

    # 启动应用
    adapter.start_app("com.example.app")

# 断开连接
adapter.disconnect()
```

### 2. 直接使用应用枚举器

```python
from insight_eyes.desktop.core import AppEnumeratorFactory, Platform

# 创建应用枚举器
enumerator = AppEnumeratorFactory.create_enumerator(device_id, Platform.ANDROID)

# 枚举所有应用
apps = enumerator.enumerate_apps(include_system_apps=False)

# 获取运行中的应用
running_apps = enumerator.get_running_apps()

# 获取特定应用信息
app_info = enumerator.get_app_info("com.example.app")
```

## 信号定义

### DeviceManager信号

- `device_discovered(DeviceInfo)` - 发现新设备
- `device_lost(str)` - 设备断开（设备ID）
- `device_updated(DeviceInfo)` - 设备信息更新
- `app_list_updated(str, list)` - 应用列表更新（设备ID, 应用列表）
- `monitoring_started(str)` - 监控开始（设备ID）
- `monitoring_stopped(str)` - 监控停止（设备ID）
- `error_occurred(str, str)` - 错误发生（设备ID, 错误信息）

## 依赖要求

### Python依赖
- PyQt6 >= 6.0.0
- logzero >= 1.7.0

### 系统工具
- **ADB** (Android Debug Bridge) - Android设备通信
- **tidevice** >= 0.9.7 - iOS设备通信

### 安装依赖

```bash
# 安装Python依赖
pip install PyQt6 logzero

# 安装tidevice（用于iOS设备）
pip install tidevice

# 确保ADB已安装并在PATH中
# Android Studio会自动安装ADB
```

## 平台支持

### Android
- 支持Android 8.0+
- 适配华为、小米、OPPO、vivo等品牌
- 支持USB和Wi-Fi连接

### iOS
- 支持iOS 12.0+
- 支持iPhone、iPad
- 需要信任计算机连接

## 测试

运行单元测试：

```bash
python -m insight_eyes.desktop.tests.test_device_manager
```

测试覆盖：
- 数据模型测试
- 设备过滤器测试
- 应用过滤器测试
- 设备适配器测试
- 应用枚举器测试
- 序列化测试

## 注意事项

1. **设备连接**
   - 首次连接Android设备需要开启USB调试
   - 首次连接iOS设备需要信任计算机

2. **权限要求**
   - 无需root/越狱
   - 部分功能需要用户授权

3. **性能考虑**
   - 建议监控间隔不低于5秒
   - 高频采集可能影响设备性能

4. **兼容性**
   - 不同品牌Android设备可能有差异
   - iOS设备功能受系统限制

## 故障排除

### 问题：无法检测到Android设备
- 检查USB调试是否开启
- 确认ADB驱动已安装
- 尝试重启ADB服务：`adb kill-server && adb start-server`

### 问题：无法检测到iOS设备
- 确认已安装tidevice
- 检查是否信任计算机
- 重启tidevice服务：`tidevice list`

### 问题：应用列表为空
- 检查设备权限
- 尝试包含系统应用：`enumerate_apps(include_system_apps=True)`

## 开发计划

- [ ] 支持更多设备信息（存储、传感器等）
- [ ] 优化设备扫描性能
- [ ] 添加设备连接历史记录
- [ ] 支持批量操作
- [ ] 添加设备分组功能

## 许可证

MIT License

## 作者

Aceyuan361

GitHub: https://github.com/Aceyuan361/Insight-Eye
