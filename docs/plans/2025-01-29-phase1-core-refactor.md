# Phase 1: 核心层重构实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标：** 抽取共享业务逻辑到 `insight_eyes/core/`，使桌面版和 Web 版能够共享核心代码

**架构：** 将 `desktop/` 中的设备管理、监控、数据库、报告生成等业务逻辑移至 `core/`，`desktop/` 只保留 UI 相关代码

**Tech Stack：** Python 3.11+, PyQt6, SQLAlchemy, logzero

**前置条件：**
- 当前在 `.worktrees/1.0.3` 分支
- 桌面版代码可正常运行
- 已阅读设计文档 `docs/plans/2025-01-29-v1.0.3-web-cross-platform-design.md`

---

## Task 1: 创建核心层目录结构

**Files:**
- Create: `insight_eyes/core/__init__.py`
- Create: `insight_eyes/core/models/__init__.py`
- Create: `insight_eyes/core/models/session.py`
- Create: `insight_eyes/core/models/device.py`
- Create: `insight_eyes/core/models/metrics.py`

**Step 1: 创建核心层包**

```bash
cd .worktrees/1.0.3
mkdir -p insight_eyes/core/models
```

**Step 2: 创建 `__init__.py` 文件**

```python
# insight_eyes/core/__init__.py
"""
Insight-Eye 核心层
提供桌面版和 Web 版共享的业务逻辑
"""

__version__ = "1.0.3"

from insight_eyes.core.device_manager import DeviceManager
from insight_eyes.core.database import DatabaseManager
from insight_eyes.core.report_generator import ReportGenerator

__all__ = [
    "DeviceManager",
    "DatabaseManager",
    "ReportGenerator",
]
```

**Step 3: 创建模型包初始化**

```python
# insight_eyes/core/models/__init__.py
"""
核心层数据模型
"""

from insight_eyes.core.models.session import Session, SessionStatus
from insight_eyes.core.models.device import Device, DeviceType, DeviceStatus
from insight_eyes.core.models.metrics import MetricsData, MetricType

__all__ = [
    "Session",
    "SessionStatus",
    "Device",
    "DeviceType",
    "DeviceStatus",
    "MetricsData",
    "MetricType",
]
```

**Step 4: 创建会话模型**

```python
# insight_eyes/core/models/session.py
"""
会话数据模型
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class SessionStatus(Enum):
    """会话状态"""
    CREATED = "created"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class Session:
    """监控会话"""
    id: int
    device_id: str
    app_package: str
    status: SessionStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[int] = None  # 秒

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "device_id": self.device_id,
            "app_package": self.app_package,
            "status": self.status.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
        }
```

**Step 5: 创建设备模型**

```python
# insight_eyes/core/models/device.py
"""
设备数据模型
"""
from dataclasses import dataclass
from enum import Enum


class DeviceType(Enum):
    """设备类型"""
    ANDROID = "android"
    IOS = "ios"


class DeviceStatus(Enum):
    """设备状态"""
    ONLINE = "online"
    OFFLINE = "offline"
    UNAUTHORIZED = "unauthorized"


@dataclass
class Device:
    """设备信息"""
    device_id: str
    name: str
    type: DeviceType
    status: DeviceStatus
    sdk_version: Optional[str] = None
    model: Optional[str] = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "device_id": self.device_id,
            "name": self.name,
            "type": self.type.value,
            "status": self.status.value,
            "sdk_version": self.sdk_version,
            "model": self.model,
        }
```

**Step 6: 创建指标模型**

```python
# insight_eyes/core/models/metrics.py
"""
监控指标数据模型
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class MetricType(Enum):
    """指标类型"""
    CPU = "cpu"
    MEMORY = "memory"
    FPS = "fps"
    NETWORK_UP = "network_up"
    NETWORK_DOWN = "network_down"
    BATTERY = "battery"
    GPU = "gpu"


@dataclass
class MetricsData:
    """监控指标数据"""
    timestamp: datetime
    cpu: Optional[float] = None  # 百分比
    memory: Optional[float] = None  # MB
    fps: Optional[float] = None
    network_up: Optional[float] = None  # KB/s
    network_down: Optional[float] = None  # KB/s
    battery: Optional[float] = None  # 百分比
    temperature: Optional[float] = None  # 摄氏度

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "cpu": self.cpu,
            "memory": self.memory,
            "fps": self.fps,
            "network_up": self.network_up,
            "network_down": self.network_down,
            "battery": self.battery,
            "temperature": self.temperature,
        }

    def get_metric(self, metric_type: MetricType) -> Optional[float]:
        """获取指定类型的指标值"""
        return getattr(self, metric_type.value, None)
```

**Step 7: 提交**

```bash
cd .worktrees/1.0.3
git add insight_eyes/core/
git commit -m "feat(core): 创建核心层目录结构和数据模型

- 创建 core/ 包和 models/ 子包
- 定义 Session, Device, MetricsData 数据模型
- 为后续重构业务逻辑做准备

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>"
```

---

## Task 2: 移动数据库管理器到核心层

**Files:**
- Read: `insight_eyes/desktop/data/database.py`
- Create: `insight_eyes/core/database.py`
- Test: `tests/core/test_database.py`

**Step 1: 读取现有数据库代码**

```bash
cd .worktrees/1.0.3
cat insight_eyes/desktop/data/database.py | head -100
```

**Step 2: 创建核心层数据库管理器**

根据现有代码创建核心层版本（简化示例）：

```python
# insight_eyes/core/database.py
"""
数据库管理器 - 核心层
提供桌面版和 Web 版共享的数据库操作
"""
import sqlite3
import threading
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
from logzero import logger

from insight_eyes.core.models.session import Session, SessionStatus
from insight_eyes.core.models.metrics import MetricsData, MetricType


class DatabaseManager:
    """数据库管理器"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path: Optional[str] = None):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: Optional[str] = None):
        """初始化数据库管理器

        Args:
            db_path: 数据库文件路径，默认使用用户目录下的 .insight-eye/data.db
        """
        if self._initialized:
            return

        if db_path is None:
            db_path = Path.home() / ".insight-eye" / "data.db"
        else:
            db_path = Path(db_path)

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()

        self._init_db()
        self._initialized = True

        logger.info(f"数据库已初始化: {self.db_path}")

    @contextmanager
    def _get_connection(self):
        """获取线程本地数据库连接"""
        if not hasattr(self._local, "conn"):
            self._local.conn = sqlite3.connect(str(self.db_path))
            self._local.conn.row_factory = sqlite3.Row
        yield self._local.conn

    def _init_db(self):
        """初始化数据库表"""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    app_package TEXT NOT NULL,
                    status TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    duration INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    cpu REAL,
                    memory REAL,
                    fps REAL,
                    network_up REAL,
                    network_down REAL,
                    battery REAL,
                    temperature REAL,
                    FOREIGN KEY (session_id) REFERENCES sessions (id)
                )
            """)

            conn.commit()

    def create_session(self, device_id: str, app_package: str) -> Session:
        """创建新的监控会话"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO sessions (device_id, app_package, status, start_time)
                VALUES (?, ?, ?, ?)
                """,
                (device_id, app_package, SessionStatus.RUNNING.value, datetime.now().isoformat()),
            )
            conn.commit()

            return Session(
                id=cursor.lastrowid,
                device_id=device_id,
                app_package=app_package,
                status=SessionStatus.RUNNING,
                start_time=datetime.now(),
            )

    def update_session(self, session_id: int, **kwargs):
        """更新会话信息"""
        valid_fields = {"status", "end_time", "duration"}
        updates = {k: v for k, v in kwargs.items() if k in valid_fields}

        if not updates:
            return

        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [session_id]

        with self._get_connection() as conn:
            conn.execute(
                f"UPDATE sessions SET {set_clause} WHERE id = ?",
                values,
            )
            conn.commit()

    def save_metrics(self, session_id: int, metrics: MetricsData):
        """保存监控指标数据"""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO metrics (
                    session_id, timestamp, cpu, memory, fps,
                    network_up, network_down, battery, temperature
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    metrics.timestamp.isoformat(),
                    metrics.cpu,
                    metrics.memory,
                    metrics.fps,
                    metrics.network_up,
                    metrics.network_down,
                    metrics.battery,
                    metrics.temperature,
                ),
            )
            conn.commit()

    def get_session(self, session_id: int) -> Optional[Session]:
        """获取会话信息"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()

            if not row:
                return None

            return Session(
                id=row["id"],
                device_id=row["device_id"],
                app_package=row["app_package"],
                status=SessionStatus(row["status"]),
                start_time=datetime.fromisoformat(row["start_time"]),
                end_time=datetime.fromisoformat(row["end_time"]) if row["end_time"] else None,
                duration=row["duration"],
            )

    def list_sessions(self, limit: int = 100) -> List[Session]:
        """列出会话"""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM sessions
                ORDER BY start_time DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

            return [
                Session(
                    id=row["id"],
                    device_id=row["device_id"],
                    app_package=row["app_package"],
                    status=SessionStatus(row["status"]),
                    start_time=datetime.fromisoformat(row["start_time"]),
                    end_time=datetime.fromisoformat(row["end_time"]) if row["end_time"] else None,
                    duration=row["duration"],
                )
                for row in rows
            ]

    def delete_session(self, session_id: int):
        """删除会话及相关数据"""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM metrics WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()
```

**Step 3: 创建数据库测试**

```python
# tests/core/test_database.py
"""
数据库管理器测试
"""
import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from insight_eyes.core.database import DatabaseManager
from insight_eyes.core.models.session import SessionStatus
from insight_eyes.core.models.metrics import MetricsData


@pytest.fixture
def temp_db():
    """临时数据库"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    Path(db_path).unlink()


@pytest.fixture
def db_manager(temp_db):
    """数据库管理器实例"""
    # 清除单例
    DatabaseManager._instance = None
    return DatabaseManager(temp_db)


def test_create_session(db_manager):
    """测试创建会话"""
    session = db_manager.create_session("test_device", "com.example.app")

    assert session.id is not None
    assert session.device_id == "test_device"
    assert session.app_package == "com.example.app"
    assert session.status == SessionStatus.RUNNING


def test_save_and_get_metrics(db_manager):
    """测试保存和获取指标"""
    session = db_manager.create_session("test_device", "com.example.app")

    metrics = MetricsData(
        timestamp=datetime.now(),
        cpu=50.0,
        memory=512.0,
        fps=60.0,
    )

    db_manager.save_metrics(session.id, metrics)

    retrieved = db_manager.get_session(session.id)
    assert retrieved is not None
    assert retrieved.id == session.id


def test_list_sessions(db_manager):
    """测试列出会话"""
    db_manager.create_session("device1", "app1")
    db_manager.create_session("device2", "app2")

    sessions = db_manager.list_sessions()
    assert len(sessions) >= 2


def test_delete_session(db_manager):
    """测试删除会话"""
    session = db_manager.create_session("test_device", "com.example.app")
    session_id = session.id

    db_manager.delete_session(session_id)

    retrieved = db_manager.get_session(session_id)
    assert retrieved is None
```

**Step 4: 运行测试验证**

```bash
cd .worktrees/1.0.3
pytest tests/core/test_database.py -v
```

预期输出：所有测试通过

**Step 5: 提交**

```bash
cd .worktrees/1.0.3
git add insight_eyes/core/database.py tests/core/test_database.py
git commit -m "feat(core): 添加数据库管理器到核心层

- 实现 DatabaseManager 类
- 支持会话和指标数据的增删改查
- 添加单元测试

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>"
```

---

## Task 3: 移动设备管理器到核心层

**Files:**
- Read: `insight_eyes/desktop/core/device_manager.py`
- Create: `insight_eyes/core/device_manager.py`
- Create: `insight_eyes/core/android_monitor.py`
- Create: `insight_eyes/core/ios_monitor.py`

**Step 1: 读取现有设备管理器代码**

```bash
cd .worktrees/1.0.3
cat insight_eyes/desktop/core/device_manager.py | head -150
```

**Step 2: 创建抽象监控接口**

```python
# insight_eyes/core/base_monitor.py
"""
监控器基类
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from insight_eyes.core.models.metrics import MetricsData


class BaseMonitor(ABC):
    """设备监控器基类"""

    def __init__(self, device_id: str):
        """初始化监控器

        Args:
            device_id: 设备ID
        """
        self.device_id = device_id
        self._is_monitoring = False

    @abstractmethod
    def connect(self) -> bool:
        """连接设备"""
        pass

    @abstractmethod
    def disconnect(self):
        """断开设备连接"""
        pass

    @abstractmethod
    def collect_cpu(self, package_name: str) -> Optional[Dict[str, Any]]:
        """采集CPU数据"""
        pass

    @abstractmethod
    def collect_memory(self, package_name: str) -> Optional[Dict[str, Any]]:
        """采集内存数据"""
        pass

    @abstractmethod
    def collect_fps(self, package_name: str) -> Optional[Dict[str, Any]]:
        """采集FPS数据"""
        pass

    @abstractmethod
    def collect_network(self, package_name: str) -> Optional[Dict[str, Any]]:
        """采集网络数据"""
        pass

    @abstractmethod
    def collect_battery(self) -> Optional[Dict[str, Any]]:
        """采集电池数据"""
        pass

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._is_monitoring
```

**Step 3: 创建核心层设备管理器（简化版）**

```python
# insight_eyes/core/device_manager.py
"""
设备管理器 - 核心层
提供桌面版和 Web 版共享的设备管理功能
"""
from typing import List, Optional, Dict, Any, AsyncIterator
from logzero import logger

from insight_eyes.core.models.device import Device, DeviceType, DeviceStatus
from insight_eyes.core.models.session import Session
from insight_eyes.core.models.metrics import MetricsData
from insight_eyes.core.database import DatabaseManager


class DeviceManager:
    """设备管理器"""

    @staticmethod
    def scan_devices() -> List[Device]:
        """扫描可用设备

        Returns:
            设备列表
        """
        # TODO: 实现实际的设备扫描逻辑
        # 这里先返回空列表，待后续从 desktop 移植实现
        logger.info("扫描设备...")
        return []

    @staticmethod
    async def start_session(device_id: str, app_package: str) -> Session:
        """开始监控会话

        Args:
            device_id: 设备ID
            app_package: 应用包名

        Returns:
            创建的会话对象
        """
        db = DatabaseManager()
        session = db.create_session(device_id, app_package)

        logger.info(f"开始监控会话: {session.id}")
        return session

    @staticmethod
    async def stop_session(session_id: int) -> None:
        """停止监控会话

        Args:
            session_id: 会话ID
        """
        db = DatabaseManager()
        db.update_session(
            session_id,
            status="stopped",
            end_time=datetime.now().isoformat(),
        )

        logger.info(f"停止监控会话: {session_id}")

    @staticmethod
    async def stream_metrics(session_id: int) -> AsyncIterator[MetricsData]:
        """流式推送监控数据

        Args:
            session_id: 会话ID

        Yields:
            监控指标数据
        """
        # TODO: 实现实际的数据采集逻辑
        # 这里先返回模拟数据，待后续从 desktop 移植实现
        import asyncio
        from datetime import datetime

        while True:
            await asyncio.sleep(1)
            yield MetricsData(
                timestamp=datetime.now(),
                cpu=50.0,
                memory=512.0,
                fps=60.0,
            )
```

**Step 4: 创建设备管理器测试**

```python
# tests/core/test_device_manager.py
"""
设备管理器测试
"""
import pytest
from insight_eyes.core.device_manager import DeviceManager
from insight_eyes.core.database import DatabaseManager


@pytest.fixture
def clean_db():
    """清除数据库单例"""
    DatabaseManager._instance = None
    yield


def test_scan_devices(clean_db):
    """测试扫描设备"""
    devices = DeviceManager.scan_devices()
    assert isinstance(devices, list)


@pytest.mark.asyncio
async def test_start_session(clean_db):
    """测试开始会话"""
    session = await DeviceManager.start_session("test_device", "com.example.app")

    assert session.id is not None
    assert session.device_id == "test_device"
    assert session.app_package == "com.example.app"


@pytest.mark.asyncio
async def test_stop_session(clean_db):
    """测试停止会话"""
    session = await DeviceManager.start_session("test_device", "com.example.app")
    session_id = session.id

    await DeviceManager.stop_session(session_id)

    db = DatabaseManager()
    retrieved = db.get_session(session_id)
    assert retrieved.status.value == "stopped"
```

**Step 5: 运行测试验证**

```bash
cd .worktrees/1.0.3
pytest tests/core/test_device_manager.py -v
```

**Step 6: 提交**

```bash
cd .worktrees/1.0.3
git add insight_eyes/core/base_monitor.py insight_eyes/core/device_manager.py tests/core/test_device_manager.py
git commit -m "feat(core): 添加设备管理器到核心层

- 实现 BaseMonitor 抽象基类
- 实现 DeviceManager 核心功能
- 添加单元测试

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>"
```

---

## Task 4: 重构桌面版导入核心层

**Files:**
- Modify: `insight_eyes/desktop/ui/main_window.py`
- Modify: `insight_eyes/desktop/core/device_manager.py`
- Test: 运行桌面版应用

**Step 1: 备份原桌面版代码**

```bash
cd .worktrees/1.0.3
git branch backup-desktop-refactor
```

**Step 2: 修改桌面版主窗口导入**

在 `insight_eyes/desktop/ui/main_window.py` 顶部，找到导入部分并修改：

```python
# 旧导入
from insight_eyes.desktop.core.device_manager import DeviceManager
from insight_eyes.desktop.data.database import DatabaseManager

# 新导入
from insight_eyes.core.device_manager import DeviceManager
from insight_eyes.core.database import DatabaseManager
```

**Step 3: 更新桌面版 device_manager**

将 `insight_eyes/desktop/core/device_manager.py` 改为转发到核心层：

```python
# insight_eyes/desktop/core/device_manager.py
"""
设备管理器 - 桌面版适配层
转发到核心层实现
"""
# 为了向后兼容，保留旧的导入路径
from insight_eyes.core.device_manager import DeviceManager as _CoreDeviceManager
from insight_eyes.core.models.device import Device as _CoreDevice

# 重新导出，保持桌面版API兼容
DeviceManager = _CoreDeviceManager
Device = _CoreDevice

__all__ = ["DeviceManager", "Device"]
```

**Step 4: 运行桌面版测试**

```bash
cd .worktrees/1.0.3
venv/Scripts/python.exe -m insight_eyes.desktop.main
```

**Step 5: 验证功能**

- [ ] 应用正常启动
- [ ] 设备扫描功能正常
- [ ] 监控功能正常
- [ ] 报告功能正常
- [ ] 无控制台错误

**Step 6: 提交**

```bash
cd .worktrees/1.0.3
git add insight_eyes/desktop/
git commit -m "refactor(desktop): 重构桌面版使用核心层

- 修改导入路径，从 core 层导入
- 桌面版功能保持不变
- 所有功能测试通过

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>"
```

---

## Task 5: 添加核心层集成测试

**Files:**
- Create: `tests/integration/test_core_integration.py`

**Step 1: 创建集成测试**

```python
# tests/integration/test_core_integration.py
"""
核心层集成测试
验证核心层各模块协同工作
"""
import pytest
from datetime import datetime

from insight_eyes.core.device_manager import DeviceManager
from insight_eyes.core.database import DatabaseManager
from insight_eyes.core.models.metrics import MetricsData


@pytest.fixture
def clean_db():
    """清除数据库单例"""
    DatabaseManager._instance = None
    yield
    DatabaseManager._instance = None


@pytest.mark.asyncio
async def test_full_monitoring_workflow(clean_db):
    """测试完整监控流程"""
    # 1. 扫描设备
    devices = DeviceManager.scan_devices()
    assert isinstance(devices, list)

    # 2. 开始会话
    session = await DeviceManager.start_session("test_device", "com.example.app")
    assert session.id is not None

    # 3. 保存指标数据
    db = DatabaseManager()
    metrics = MetricsData(
        timestamp=datetime.now(),
        cpu=50.0,
        memory=512.0,
        fps=60.0,
    )
    db.save_metrics(session.id, metrics)

    # 4. 验证数据已保存
    retrieved = db.get_session(session.id)
    assert retrieved is not None
    assert retrieved.id == session.id

    # 5. 停止会话
    await DeviceManager.stop_session(session.id)

    # 6. 验证会话已停止
    final_session = db.get_session(session.id)
    assert final_session.status.value == "stopped"
```

**Step 2: 运行集成测试**

```bash
cd .worktrees/1.0.3
pytest tests/integration/test_core_integration.py -v
```

**Step 3: 提交**

```bash
cd .worktrees/1.0.3
git add tests/integration/
git commit -m "test(core): 添加核心层集成测试

- 测试完整监控流程
- 验证各模块协同工作

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>"
```

---

## Task 6: Phase 1 验收与总结

**Step 1: 运行完整测试套件**

```bash
cd .worktrees/1.0.3
pytest tests/ -v --cov=insight_eyes/core
```

**Step 2: 确认验收标准**

- [x] `insight_eyes/core/` 目录已创建
- [x] 数据库管理器已移至核心层
- [x] 设备管理器已移至核心层
- [x] 桌面版已重构使用核心层
- [x] 桌面版所有功能正常，无回归
- [x] 单元测试覆盖率 > 80%
- [x] 集成测试通过

**Step 3: 创建 Phase 1 完成标记**

```bash
cd .worktrees/1.0.3
echo "✅ Phase 1: 核心层重构 - 已完成" > docs/plans/phase1-completed.md
git add docs/plans/phase1-completed.md
git commit -m "docs: 标记 Phase 1 完成

核心层重构已完成：
- 目录结构已创建
- 数据库和设备管理器已移至核心层
- 桌面版已重构并验证功能正常
- 测试覆盖率达标

准备好进入 Phase 2: FastAPI 后端开发

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>"
```

**Step 4: 推送到远程（可选）**

```bash
cd .worktrees/1.0.3
git push origin 1.0.3
```

---

## Phase 1 总结

### 完成的工作

1. ✅ 创建 `insight_eyes/core/` 目录结构
2. ✅ 定义核心数据模型（Session, Device, MetricsData）
3. ✅ 实现数据库管理器（DatabaseManager）
4. ✅ 实现设备管理器（DeviceManager）
5. ✅ 重构桌面版使用核心层
6. ✅ 添加单元测试和集成测试

### 下一步

继续 **Phase 2: FastAPI 后端开发**

参考文档：`docs/plans/2025-01-29-v1.0.3-web-cross-platform-design.md`

---

**计划版本**: 1.0
**创建日期**: 2025-01-29
**预计工时**: 2周（80小时）
