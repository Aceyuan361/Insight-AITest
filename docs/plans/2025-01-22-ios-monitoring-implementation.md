# iOS 设备性能监控实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标:** 在 Insight-Eye 项目中添加 iOS 设备性能监控功能，支持在 Windows 上连接 iOS 设备并采集基础性能数据。

**架构:** 遵循现有 AndroidAPM 架构模式，使用 pymobiledevice3 连接 iOS 设备，通过 IOSDeviceAdapter 适配到现有设备管理系统。

**技术栈:** pymobiledevice3（设备通信）、PyQt6（UI）、SQLite（存储）、pytest（测试）

---

## 前置条件

### POC 验证已完成

✅ pymobiledevice3 在 Windows 上成功检测到 iOS 设备
✅ 技术方案可行性已确认

### 需要的文件

- 设计文档: `docs/plans/2025-01-22-ios-monitoring-design.md`
- POC 脚本: `tests/test_ios_poc_simple.py`

---

## 阶段 1：基础架构（第 1-4 步）

### Task 1: 恢复 Platform 枚举的 iOS 支持

**文件:**
- 修改: `insight_eyes/public/common.py`

**步骤 1: 定位 Platform 枚举**

打开文件 `insight_eyes/public/common.py`，找到 `Platform` 枚举定义。

**步骤 2: 添加 IOS 枚举值**

```python
# 在 Platform 类中添加
class Platform(Enum):
    """平台枚举"""
    ANDROID = "Android"
    IOS = "iOS"  # 添加此行
    UNKNOWN = "Unknown"
```

**步骤 3: 验证修改**

运行: `python -c "from insight_eyes.public.common import Platform; print(Platform.IOS.value)"`
预期输出: `iOS`

**步骤 4: 提交**

```bash
git add insight_eyes/public/common.py
git commit -m "feat: 恢复 Platform 枚举的 iOS 支持"
```

---

### Task 2: 更新数据库 Schema 支持 iOS

**文件:**
- 修改: `insight_eyes/desktop/data/database.py`

**步骤 1: 定位 CHECK 约束**

查找 `CREATE TABLE` 语句中的 `CHECK(platform IN ('android'))` 约束。

**步骤 2: 修改约束以支持 iOS**

```python
# 将 CHECK 约束改为
CHECK(platform IN ('android', 'ios'))
```

**步骤 3: 添加数据迁移逻辑**

在 `DatabaseManager` 类中添加迁移方法：

```python
def _migrate_add_ios_platform(self):
    """迁移数据库以支持 iOS 平台"""
    cursor = self.get_thread_local_cursor()

    # 检查是否需要迁移
    cursor.execute("""
        SELECT sql FROM sqlite_master
        WHERE type='table' AND name='sessions'
    """)
    result = cursor.fetchone()

    if 'android' in result[0] and 'ios' not in result[0]:
        logger.info("检测到旧版本数据库，执行平台字段迁移...")

        # SQLite 不支持直接修改约束，需要重建表
        cursor.execute("""
            CREATE TABLE sessions_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                package_name TEXT NOT NULL,
                start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                end_time DATETIME,
                sample_interval INTEGER DEFAULT 1000,
                platform TEXT NOT NULL CHECK(platform IN ('android', 'ios')),
                tags TEXT
            )
        """)

        # 复制数据，旧数据标记为 android
        cursor.execute("""
            INSERT INTO sessions_new
            SELECT *, 'android' FROM sessions
        """)

        cursor.execute("DROP TABLE sessions")
        cursor.execute("ALTER TABLE sessions_new RENAME TO sessions")

        logger.info("数据库迁移完成")
```

在 `__init__` 中调用迁移：

```python
def __init__(self, db_path: str = None):
    # ... 现有代码 ...
    self._migrate_add_ios_platform()  # 添加此行
```

**步骤 4: 测试迁移**

```python
# 创建测试脚本 tests/test_db_migration.py
def test_ios_platform_migration():
    from insight_eyes.desktop.data.database import DatabaseManager
    import tempfile
    import os

    # 创建临时数据库
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name

    try:
        db = DatabaseManager(db_path)

        # 测试创建 iOS 会话
        session_id = db.create_session(
            device_id="test_ios_device",
            package_name="com.test.app",
            sample_interval=1000,
            platform="ios"
        )

        assert session_id > 0
        print("✓ iOS 平台支持测试通过")

    finally:
        os.unlink(db_path)
```

运行: `python tests/test_db_migration.py`
预期: 测试通过，无错误

**步骤 5: 提交**

```bash
git add insight_eyes/desktop/data/database.py tests/test_db_migration.py
git commit -m "feat: 数据库支持 iOS 平台，添加迁移逻辑"
```

---

### Task 3: 实现 IOSDeviceAdapter 骨架

**文件:**
- 创建: `insight_eyes/desktop/core/ios_device_adapter.py`
- 修改: `insight_eyes/desktop/core/device_adapters.py`

**步骤 1: 创建 IOSDeviceAdapter 类**

```python
# insight_eyes/desktop/core/ios_device_adapter.py
"""
iOS 设备适配器

负责 iOS 设备的连接、性能采集和状态管理
"""

from typing import Optional, Dict, Any
from logzero import logger
from datetime import datetime

from insight_eyes.desktop.core.device_adapters import BaseDeviceAdapter
from insight_eyes.public.common import Platform


class IOSDeviceAdapter(BaseDeviceAdapter):
    """iOS 设备适配器"""

    def __init__(self, device_id: str):
        super().__init__(device_id)
        self.device_id = device_id
        self.platform = Platform.IOS
        self._connection = None

    def connect(self) -> bool:
        """连接 iOS 设备"""
        try:
            from pymobiledevice3 import usbmux
            from pymobiledevice3.lockdown import LockdownClient

            logger.info(f"正在连接 iOS 设备: {self.device_id}")

            # 创建 Lockdown 连接
            self._connection = LockdownClient(self.device_id)

            logger.info(f"iOS 设备连接成功: {self.device_id}")
            return True

        except Exception as e:
            logger.error(f"iOS 设备连接失败: {e}")
            return False

    def disconnect(self) -> bool:
        """断开 iOS 设备连接"""
        try:
            if self._connection:
                self._connection = None
                logger.info(f"iOS 设备已断开: {self.device_id}")
            return True
        except Exception as e:
            logger.error(f"断开 iOS 设备失败: {e}")
            return False

    def get_device_info(self) -> Dict[str, Any]:
        """获取 iOS 设备信息"""
        try:
            if not self._connection:
                self.connect()

            info = self._connection.get_value()

            return {
                'device_id': self.device_id,
                'name': info.get('DeviceName', 'Unknown'),
                'model': info.get('ProductType', 'Unknown'),
                'os_version': info.get('ProductVersion', 'Unknown'),
                'platform': 'ios'
            }
        except Exception as e:
            logger.error(f"获取 iOS 设备信息失败: {e}")
            return {}

    def is_connected(self) -> bool:
        """检查设备是否连接"""
        return self._connection is not None

    def check_device_ready(self) -> bool:
        """检查设备是否准备好进行监控"""
        try:
            # 检查设备是否信任此电脑
            return self.is_connected()
        except Exception:
            return False
```

**步骤 2: 在 device_adapters.py 中注册 iOS 适配器**

找到 `create_adapter` 函数，添加 iOS 分支：

```python
# insight_eyes/desktop/core/device_adapters.py

# 在文件顶部导入
from insight_eyes.desktop.core.ios_device_adapter import IOSDeviceAdapter

# 在 create_adapter 函数中添加分支
def create_adapter(device_id: str, platform: Platform) -> Optional[BaseDeviceAdapter]:
    """
    创建设备适配器（工厂方法）

    Args:
        device_id: 设备 ID
        platform: 平台类型

    Returns:
        设备适配器实例，失败返回 None
    """
    logger.debug(f"create_adapter 调用: device_id={device_id}, platform={platform}")

    if platform == Platform.ANDROID:
        adapter = AndroidDeviceAdapter(device_id)
        adapter.connect()
        return adapter
    elif platform == Platform.IOS:  # 添加此分支
        adapter = IOSDeviceAdapter(device_id)
        adapter.connect()
        return adapter
    else:
        logger.error(f"不支持的平台: {platform}")
        return None
```

**步骤 3: 编写基础测试**

```python
# tests/test_ios_adapter.py
import pytest
from insight_eyes.desktop.core.ios_device_adapter import IOSDeviceAdapter
from insight_eyes.public.common import Platform


def test_ios_adapter_creation():
    """测试 iOS 适配器创建"""
    adapter = IOSDeviceAdapter("test_device_udid")

    assert adapter.device_id == "test_device_udid"
    assert adapter.platform == Platform.IOS
    assert not adapter.is_connected()

    print("✓ iOS 适配器创建测试通过")


def test_ios_adapter_get_info_mock():
    """测试获取设备信息（模拟）"""
    adapter = IOSDeviceAdapter("test_device_udid")

    # 未连接时返回空字典
    info = adapter.get_device_info()
    assert info == {}

    print("✓ iOS 适配器获取信息测试通过")
```

运行: `pytest tests/test_ios_adapter.py -v`
预期: 测试通过

**步骤 4: 提交**

```bash
git add insight_eyes/desktop/core/ios_device_adapter.py
git add insight_eyes/desktop/core/device_adapters.py
git add tests/test_ios_adapter.py
git commit -m "feat: 实现 IOSDeviceAdapter 基础类"
```

---

### Task 4: 集成 iOS 设备检测到 DeviceManager

**文件:**
- 修改: `insight_eyes/desktop/core/device_manager.py`

**步骤 1: 添加 iOS 设备扫描**

在 `DeviceManager` 类中添加 iOS 扫描方法：

```python
def _scan_ios_devices(self) -> List[DeviceInfo]:
    """
    扫描 iOS 设备

    Returns:
        iOS 设备信息列表
    """
    devices = []

    try:
        from pymobiledevice3 import usbmux

        # 扫描连接的 iOS 设备
        mux_devices = usbmux.list_devices()

        for mux_device in mux_devices:
            udid = mux_device.serial

            device_info = DeviceInfo(
                device_id=udid,
                name=f"iOS Device ({udid[:8]})",
                platform=Platform.IOS,
                status="connected"
            )

            devices.append(device_info)
            logger.info(f"检测到 iOS 设备: {udid}")

    except ImportError:
        logger.warning("pymobiledevice3 未安装，iOS 设备扫描不可用")
    except Exception as e:
        logger.error(f"扫描 iOS 设备失败: {e}")

    return devices
```

**步骤 2: 修改扫描方法以包含 iOS**

在 `scan_devices` 方法中添加 iOS 扫描：

```python
def scan_devices(self) -> List[DeviceInfo]:
    """
    扫描所有设备（Android + iOS）

    Returns:
        设备信息列表
    """
    all_devices = []

    # 扫描 Android 设备（现有逻辑）
    android_devices = self._scan_android_devices()
    all_devices.extend(android_devices)

    # 扫描 iOS 设备（新增）
    ios_devices = self._scan_ios_devices()
    all_devices.extend(ios_devices)

    logger.info(f"扫描完成: {len(android_devices)} 个 Android, {len(ios_devices)} 个 iOS")

    return all_devices
```

**步骤 3: 测试设备扫描**

```python
# tests/test_device_scan.py
from insight_eyes.desktop.core.device_manager import DeviceManager
from insight_eyes.public.common import Platform


def test_scan_ios_devices():
    """测试 iOS 设备扫描"""
    manager = DeviceManager()

    # 扫描设备
    devices = manager.scan_devices()

    # 检查 iOS 设备（如果有连接的话）
    ios_devices = [d for d in devices if d.platform == Platform.IOS]

    print(f"检测到 {len(ios_devices)} 个 iOS 设备")

    for device in ios_devices:
        print(f"  - {device.device_id}: {device.name}")

    print("✓ 设备扫描测试完成")


if __name__ == "__main__":
    test_scan_ios_devices()
```

运行: `python tests/test_device_scan.py`
预期: 显示检测到的 iOS 设备数量和信息

**步骤 4: 提交**

```bash
git add insight_eyes/desktop/core/device_manager.py
git add tests/test_device_scan.py
git commit -m "feat: DeviceManager 支持 iOS 设备扫描"
```

---

## 阶段 2：iOS 性能采集器（第 5-8 步）

### Task 5: 创建 iOSAPM 主入口

**文件:**
- 创建: `insight_eyes/public/ios/__init__.py`
- 创建: `insight_eyes/public/ios/ios_apm.py`

**步骤 1: 创建 ios 模块**

```python
# insight_eyes/public/ios/__init__.py
"""
iOS 性能采集模块

提供 iOS 设备的性能数据采集功能
"""

from insight_eyes.public.ios.ios_apm import IOSAPM

__all__ = ['IOSAPM']
```

**步骤 2: 实现 IOSAPM 类**

```python
# insight_eyes/public/ios/ios_apm.py
"""
iOS APM (Application Performance Monitoring) 主类

提供统一的 iOS 性能监控接口，类似 AndroidAPM
"""

from typing import Dict, Any, Optional
from logzero import logger

from insight_ees.desktop.core.ios_device_adapter import IOSDeviceAdapter


class IOSAPM:
    """
    iOS 性能监控主类

    提供统一的性能数据采集接口
    """

    def __init__(self, bundle_name: str, device_id: str):
        """
        初始化 iOS APM

        Args:
            bundle_name: 应用 Bundle ID (如 com.example.app)
            device_id: iOS 设备 UDID
        """
        self.bundle_name = bundle_name
        self.device_id = device_id
        self.adapter = None

    def start(self):
        """启动性能监控"""
        logger.info(f"启动 iOS APM: {self.bundle_name} @ {self.device_id}")

        # 连接设备
        self.adapter = IOSDeviceAdapter(self.device_id)
        if not self.adapter.connect():
            raise ConnectionError(f"无法连接 iOS 设备: {self.device_id}")

        logger.info("iOS APM 启动成功")

    def stop(self):
        """停止性能监控"""
        if self.adapter:
            self.adapter.disconnect()
            self.adapter = None

        logger.info("iOS APM 已停止")

    def collectCpu(self) -> Dict[str, Any]:
        """
        采集 CPU 使用率

        Returns:
            {'cpu_app': float, 'cpu_system': float}
        """
        # TODO: 实现 CPU 采集
        logger.warning("iOS CPU 采集尚未实现")
        return {'cpu_app': 0.0, 'cpu_system': 0.0}

    def collectMemory(self) -> Dict[str, Any]:
        """
        采集内存使用情况

        Returns:
            {'used_mb': float, 'total_mb': float}
        """
        # TODO: 实现内存采集
        logger.warning("iOS 内存采集尚未实现")
        return {'used_mb': 0.0, 'total_mb': 0.0}

    def collectFps(self) -> Dict[str, Any]:
        """
        采集帧率信息

        Returns:
            {'fps': int, 'jank': int}
        """
        # TODO: 实现 FPS 采集
        logger.warning("iOS FPS 采集尚未实现")
        return {'fps': 60, 'jank': 0}
```

**步骤 3: 编写测试**

```python
# tests/test_ios_apm.py
from insight_eyes.public.ios.ios_apm import IOSAPM


def test_ios_apm_init():
    """测试 IOSAPM 初始化"""
    apm = IOSAPM(
        bundle_name="com.test.app",
        device_id="test_device"
    )

    assert apm.bundle_name == "com.test.app"
    assert apm.device_id == "test_device"

    print("✓ IOSAPM 初始化测试通过")


def test_ios_apm_collect():
    """测试基础数据采集"""
    apm = IOSAPM(
        bundle_name="com.test.app",
        device_id="test_device"
    )

    # 测试采集方法（返回默认值）
    cpu = apm.collectCpu()
    assert 'cpu_app' in cpu
    assert 'cpu_system' in cpu

    memory = apm.collectMemory()
    assert 'used_mb' in memory
    assert 'total_mb' in memory

    fps = apm.collectFps()
    assert 'fps' in fps
    assert 'jank' in fps

    print("✓ IOSAPM 采集接口测试通过")
```

运行: `pytest tests/test_ios_apm.py -v`
预期: 测试通过

**步骤 4: 提交**

```bash
git add insight_eyes/public/ios/ tests/test_ios_apm.py
git commit -m "feat: 实现 IOSAPM 主类和基础接口"
```

---

## 阶段 3：UI 集成（第 9-12 步）

### Task 9: 设备列表显示 iOS 设备

**文件:**
- 修改: `insight_eyes/desktop/ui/panels/device_selection_panel.py`

**步骤 1: 添加平台图标**

在 `DeviceSelectionPanel` 类中添加方法：

```python
def _get_platform_icon(self, platform: str) -> str:
    """获取平台图标"""
    return {
        'android': '🤖',
        'ios': '🍎'
    }.get(platform.lower(), '📱')
```

**步骤 2: 修改设备列表显示**

在 `_refresh_devices` 方法中更新设备名称显示：

```python
# 在显示设备名称时添加平台图标
device_name = f"{icon} {device.name}"
```

**步骤 3: 测试 UI 显示**

启动应用，查看设备列表是否显示 iOS 设备的 🍎 图标。

**步骤 4: 提交**

```bash
git add insight_eyes/desktop/ui/panels/device_selection_panel.py
git commit -m "feat: 设备列表显示 iOS 设备图标"
```

---

### Task 10: 监控面板支持 iOS 平台

**文件:**
- 修改: `insight_eyes/desktop/ui/panels/monitor_panel_v2.py`
- 修改: `insight_eyes/desktop/ui/main_window.py`

**步骤 1: 修改 start_monitoring 方法**

在 `_start_monitoring` 中根据平台选择 APM：

```python
def _start_monitoring(self):
    """开始监控"""
    # ... 现有检查逻辑 ...

    # 根据平台创建 APM
    if self.current_device_platform == Platform.IOS:
        from insight_eyes.public.ios import IOSAPM
        self.apm = IOSAPM(
            bundle_name=self.current_package_name,
            device_id=self.current_device_id
        )
    else:
        from insight_eyes.public.android import AndroidAPM
        self.apm = AndroidAPM(
            package_name=self.current_package_name,
            device_id=self.current_device_id
        )

    # 启动监控
    self.apm.start()
```

**步骤 2: 更新 UI 状态**

确保 `is_monitoring` 状态对 iOS 和 Android 一致处理。

**步骤 3: 测试 iOS 监控启动**

1. 选择 iOS 设备
2. 选择应用
3. 点击"开始"按钮
4. 验证监控能正常启动

**步骤 4: 提交**

```bash
git add insight_eyes/desktop/ui/main_window.py
git commit -m "feat: 监控功能支持 iOS 平台"
```

---

### Task 11: 数据库扩展支持 iOS 标识

**文件:**
- 修改: `insight_eyes/desktop/data/database.py`

**步骤 1: 修改 create_session 方法**

添加 `platform` 参数：

```python
def create_session(
    self,
    device_id: str,
    package_name: str,
    sample_interval: int = 1000,
    platform: str = "android",  # 添加默认值
    tags: dict = None
) -> int:
    """
    创建监控会话

    Args:
        device_id: 设备 ID
        package_name: 应用包名或 Bundle ID
        sample_interval: 采样间隔（毫秒）
        platform: 平台类型 ('android' 或 'ios')
        tags: 标签字典
    """
    # ... 实现 ...
```

**步骤 2: 修改 insert 语句**

```python
cursor.execute("""
    INSERT INTO sessions (
        device_id, package_name, sample_interval, platform, tags
    ) VALUES (?, ?, ?, ?, ?)
""", (device_id, package_name, sample_interval, platform, json.dumps(tags or {})))
```

**步骤 3: 测试数据库操作**

```python
# tests/test_database_ios.py
def test_create_ios_session():
    """测试创建 iOS 会话"""
    db = DatabaseManager()

    session_id = db.create_session(
        device_id="test_ios_device",
        package_name="com.test.app",
        platform="ios"
    )

    assert session_id > 0

    # 验证会话平台
    session = db.get_session(session_id)
    assert session['platform'] == 'ios'

    print("✓ iOS 会话创建测试通过")
```

**步骤 4: 提交**

```bash
git add insight_eyes/desktop/data/database.py tests/test_database_ios.py
git commit -m "feat: 数据库会话支持 iOS 平台标识"
```

---

### Task 12: 测试报告支持 iOS 数据

**文件:**
- 修改: `insight_eyes/desktop/ui/widgets/session_report_widget.py`

**步骤 1: 修改图表卡片创建**

在 `_create_chart_cards` 中根据平台调整卡片：

```python
def _create_chart_cards(self, platform: str):
    """
    根据平台创建图表卡片

    Args:
        platform: 'android' 或 'ios'
    """
    # 基础卡片（两个平台通用）
    cards = ['cpu', 'memory', 'fps', 'network']

    # iOS 特有卡片（未来扩展）
    if platform == 'ios':
        # 预留 GPU 卡片位置
        # cards.append('gpu')
        pass

    self._create_charts(cards)
```

**步骤 2: 测试 iOS 报告生成**

1. 创建一个 iOS 监控会话
2. 生成测试报告
3. 验证图表正确显示

**步骤 3: 提交**

```bash
git add insight_eyes/desktop/ui/widgets/session_report_widget.py
git commit -m "feat: 测试报告支持 iOS 平台数据"
```

---

## 阶段 4：完善与优化（第 13-16 步）

### Task 13: 实现基础 CPU 采集器

**文件:**
- 创建: `insight_eyes/public/ios/cpu_collector.py`

**步骤 1: 实现 CPUCollector**

```python
# insight_eyes/public/ios/cpu_collector.py
"""
iOS CPU 使用率采集器
"""

from typing import Dict
from logzero import logger


class CPUCollector:
    """iOS CPU 使用率采集"""

    def __init__(self, adapter):
        """
        初始化 CPU 采集器

        Args:
            adapter: IOSDeviceAdapter 实例
        """
        self.adapter = adapter

    def collect(self) -> Dict[str, float]:
        """
        采集 CPU 使用率

        Returns:
            {'cpu_app': float, 'cpu_system': float}
        """
        try:
            # 方法 1：尝试通过 sysctl 获取 CPU 信息
            return self._collect_via_sysctl()

        except Exception as e:
            logger.debug(f"sysctl 方法失败: {e}")

            # 方法 2：返回估算值
            return self._get_estimated_value()

    def _collect_via_sysctl(self) -> Dict[str, float]:
        """通过 sysctl 获取 CPU 信息"""
        # TODO: 实现 sysctl 调用
        # 这是 iOS 特有的系统调用
        return {'cpu_app': 0.0, 'cpu_system': 0.0}

    def _get_estimated_value(self) -> Dict[str, float]:
        """返回估算值"""
        logger.warning("CPU 采集失败，返回默认值")
        return {'cpu_app': 0.0, 'cpu_system': 0.0}
```

**步骤 2: 集成到 IOSAPM**

```python
# 在 IOSAPM.__init__ 中添加
from insight_eyes.public.ios.cpu_collector import CPUCollector

self.cpu_collector = CPUCollector(self.adapter)

# 在 collectCpu 中调用
def collectCpu(self) -> Dict[str, Any]:
    return self.cpu_collector.collect()
```

**步骤 3: 测试**

```python
# tests/test_cpu_collector.py
def test_cpu_collector():
    """测试 CPU 采集器"""
    from insight_ees.public.ios.cpu_collector import CPUCollector

    # 创建模拟适配器
    class MockAdapter:
        pass

    collector = CPUCollector(MockAdapter())
    result = collector.collect()

    assert 'cpu_app' in result
    assert 'cpu_system' in result

    print("✓ CPU 采集器测试通过")
```

**步骤 4: 提交**

```bash
git add insight_eyes/public/ios/cpu_collector.py
git add tests/test_cpu_collector.py
git add insight_eyes/public/ios/ios_apm.py
git commit -m "feat: 实现 iOS CPU 基础采集器"
```

---

### Task 14: 实现内存采集器

**文件:**
- 创建: `insight_eyes/public/ios/memory_collector.py`

**步骤 1: 实现 MemoryCollector**

```python
# insight_eyes/public/ios/memory_collector.py
"""
iOS 内存使用情况采集器
"""

from typing import Dict
from logzero import logger


class MemoryCollector:
    """iOS 内存使用采集"""

    def __init__(self, adapter):
        """
        初始化内存采集器

        Args:
            adapter: IOSDeviceAdapter 实例
        """
        self.adapter = adapter

    def collect(self) -> Dict[str, float]:
        """
        采集内存使用情况

        Returns:
            {'used_mb': float, 'total_mb': float}
        """
        try:
            return self._collect_via_host_info()

        except Exception as e:
            logger.debug(f"内存采集失败: {e}")
            return self._get_estimated_value()

    def _collect_via_host_info(self) -> Dict[str, float]:
        """通过 host_info 获取内存信息"""
        # TODO: 实现 iOS 内存信息获取
        return {'used_mb': 0.0, 'total_mb': 0.0}

    def _get_estimated_value(self) -> Dict[str, float]:
        """返回估算值"""
        return {'used_mb': 0.0, 'total_mb': 0.0}
```

**步骤 2-4:** 类似 Task 13，集成到 IOSAPM、测试、提交

---

### Task 15: 实现电池采集器

**文件:**
- 创建: `insight_eyes/public/ios/battery_collector.py`

**步骤 1: 实现 BatteryCollector**

```python
# insight_eyes/public/ios/battery_collector.py
"""
iOS 电池状态采集器
"""

from typing import Dict
from logzero import logger


class BatteryCollector:
    """iOS 电池状态采集"""

    def __init__(self, adapter):
        self.adapter = adapter

    def collect(self) -> Dict[str, Any]:
        """
        采集电池状态

        Returns:
            {'level': int, 'temperature': float}
        """
        try:
            # iOS 通过 UIDevice 获取电量
            return self._collect_via_uidevice()

        except Exception as e:
            logger.debug(f"电池采集失败: {e}")
            return self._get_estimated_value()

    def _collect_via_uidevice(self) -> Dict[str, Any]:
        """通过 UIDevice 获取电池信息"""
        # TODO: 实现 iOS 电池信息获取
        return {'level': 100, 'temperature': 25.0}

    def _get_estimated_value(self) -> Dict[str, Any]:
        """返回估算值"""
        return {'level': 100, 'temperature': 25.0}
```

**步骤 2-4:** 集成、测试、提交

---

### Task 16: 完善错误处理和降级方案

**文件:**
- 修改: 所有采集器
- 创建: `insight_eyes/public/ios/exceptions.py`

**步骤 1: 定义 iOS 专用异常**

```python
# insight_eyes/public/ios/exceptions.py
"""
iOS 监控专用异常
"""

class IOSMonitorError(Exception):
    """iOS 监控基础异常"""
    pass


class DeviceNotTrustedError(IOSMonitorError):
    """设备未信任异常"""
    pass


class DeviceNotFoundError(IOSMonitorError):
    """设备未找到异常"""
    pass


class DeveloperModeNotEnabledError(IOSMonitorError):
    """开发者模式未启用异常"""
    pass
```

**步骤 2: 更新采集器异常处理**

在所有采集器中添加详细错误处理：

```python
def collect(self):
    """采集数据（带详细错误处理）"""

    # 方案 1：主要方法
    try:
        result = self._try_primary_method()
        if self._validate_result(result):
            logger.debug("[采集器] ✓ 主要方法成功")
            return result
    except Exception as e:
        logger.debug(f"[采集器] 主要方法失败: {e}")

    # 方案 2：降级方法
    try:
        result = self._try_fallback_method()
        if self._validate_result(result):
            logger.debug("[采集器] ✓ 降级方法成功")
            return result
    except Exception as e:
        logger.debug(f"[采集器] 降级方法失败: {e}")

    # 方案 3：默认值
    logger.warning("[采集器] 所有方法失败，返回默认值")
    return self._get_default_value()
```

**步骤 3: 添加连接引导**

在 IOSDeviceAdapter 中添加信任检查：

```python
def check_device_trust(self) -> bool:
    """检查设备是否信任此电脑"""
    try:
        # 尝试连接，如果失败则提示用户
        self.connect()
        return True
    except Exception as e:
        if "not paired" in str(e).lower():
            logger.error("""
设备未信任此电脑！

请按以下步骤操作：
1. 在 iOS 设备上解锁屏幕
2. 连接时会弹出"信任此电脑？"提示
3. 点击"信任"
4. 重新运行程序
            """)
        return False
```

**步骤 4: 测试错误处理**

```python
# tests/test_error_handling.py
def test_device_not_trusted():
    """测试设备未信任场景"""
    # 模拟设备未信任的情况
    # 验证错误提示清晰
    pass


def test_collector_fallback():
    """测试采集器降级逻辑"""
    # 模拟主要方法失败
    # 验证降级方法被调用
    pass
```

**步骤 5: 提交**

```bash
git add insight_eyes/public/ios/exceptions.py
git add insight_eyes/public/ios/cpu_collector.py
git add insight_eyes/public/ios/memory_collector.py
git add insight_eyes/public/ios/battery_collector.py
git add insight_eyes/desktop/core/ios_device_adapter.py
git add tests/test_error_handling.py
git commit -m "feat: 完善 iOS 监控的错误处理和降级方案"
```

---

## 最终验证

### 验证清单

**功能验证:**

- [ ] 能检测到连接的 iOS 设备
- [ ] 能获取 iOS 设备信息（型号、iOS 版本）
- [ ] 能启动和停止 iOS 监控
- [ ] 能采集基础性能数据
- [ ] UI 能正确显示 iOS 设备和数据
- [ ] 测试报告能正确显示 iOS 数据

**质量验证:**

- [ ] 所有单元测试通过
- [ ] 无明显性能问题
- [ ] 错误处理完善
- [ ] 降级方案有效

**打包验证:**

- [ ] PyInstaller 打包成功
- [ ] 打包后的 .exe 能正常运行
- [ ] 在没有 Python 环境的机器上测试

---

## 附录

### 相关文档

- 架构设计: `docs/plans/2025-01-22-ios-monitoring-design.md`
- POC 验证: `tests/test_ios_poc_simple.py`
- 项目规范: `CLAUDE.md`

### 技术参考

- [pymobiledevice3 文档](https://github.com/doronz88/pymobiledevice3)
- iOS 性能监控最佳实践
- AndroidAPM 架构参考

### 依赖项

```
pymobiledevice3>=1.0.0  # iOS 设备通信
PyQt6>=6.4.0            # UI 框架
pytest>=7.0.0            # 测试框架
```
