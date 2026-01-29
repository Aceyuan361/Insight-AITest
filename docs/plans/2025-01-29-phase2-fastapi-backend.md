# Phase 2: FastAPI 后端开发实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标：** 实现 Web 服务层，支持浏览器访问 Insight-Eye

**架构：** FastAPI + WebSocket + 核心层集成

**Tech Stack：** FastAPI, Uvicorn, WebSocket, Pydantic

**前置条件：**
- Phase 1 核心层重构已完成
- 核心层模块可用：DeviceManager, DatabaseManager, 数据模型
- 当前在 `.worktrees/1.0.3` 分支

---

## Task 1: 创建 Web 项目结构

**Files:**
- Create: `insight_eyes/web/__init__.py`
- Create: `insight_eyes/web/api/__init__.py`
- Create: `insight_eyes/web/api/main.py`
- Create: `insight_eyes/web/requirements.txt`
- Create: `insight_eyes/web/README.md`

**Step 1: 创建 Web 包结构**

```bash
cd .worktrees/1.0.3
mkdir -p insight_eyes/web/api
mkdir -p insight_eyes/web/websocket
```

**Step 2: 创建依赖文件**

```python
# insight_eyes/web/requirements.txt
# FastAPI Web 应用依赖

# Web 框架
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
python-multipart>=0.0.6

# WebSocket
websockets>=12.0

# 数据验证
pydantic>=2.5.0
pydantic-settings>=2.1.0

# CORS
python-json-logger>=2.9.0

# 核心层依赖
# insight-eyes.core 已在项目根目录
```

**Step 3: 创建 FastAPI 主应用**

```python
# insight_eyes/web/api/main.py
# -*- coding: utf-8 -*-
"""
FastAPI Web 应用主入口
提供 Insight-Eye 的 Web API 服务
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
from logzero import logger
import sys
import os

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from insight_eyes.core.device_manager import DeviceManager
from insight_eyes.core.database import DatabaseManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("FastAPI 应用启动")
    yield
    logger.info("FastAPI 应用关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title="Insight-Eye API",
    description="移动设备性能监控工具 Web API",
    version="1.0.3",
    lifespan=lifespan,
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """根路径，返回 API 信息"""
    return {
        "name": "Insight-Eye API",
        "version": "1.0.3",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy"}


# 启动命令：
# uvicorn insight_eyes.web.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Step 4: 安装依赖**

```bash
cd .worktrees/1.0.3
venv/Scripts/pip.exe install -r insight_eyes/web/requirements.txt
```

**Step 5: 测试启动**

```bash
cd .worktrees/1.0.3
venv/Scripts/uvicorn.exe insight_eyes.web.api.main:app --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000 验证 API 文档

**Step 6: 提交**

```bash
cd .worktrees/1.0.3
git add insight_eyes/web/
git commit -m "feat(web): 创建 FastAPI Web 应用框架

- 创建 FastAPI 主应用
- 配置 CORS 中间件
- 添加健康检查端点
- 添加 Web 依赖清单

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>"
```

---

## Task 2: 实现设备管理 API

**Files:**
- Create: `insight_eyes/web/api/devices.py`
- Modify: `insight_eyes/web/api/main.py`
- Test: 测试 API 端点

**Step 1: 创建设备管理 API**

```python
# insight_eyes/web/api/devices.py
# -*- coding: utf-8 -*-
"""
设备管理 API
提供设备扫描、查询等功能
"""
from fastapi import APIRouter, HTTPException
from logzero import logger

from insight_eyes.core.device_manager import DeviceManager
from insight_eyes.core.models.device import Device


router = APIRouter(prefix="/api/devices", tags=["devices"])


@router.get("")
async def list_devices():
    """扫描并列出可用设备

    Returns:
        List[Device]: 设备列表
    """
    try:
        devices = DeviceManager.scan_devices()
        logger.info(f"扫描到 {len(devices)} 个设备")
        return devices
    except Exception as e:
        logger.error(f"设备扫描失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{device_id}")
async def get_device(device_id: str):
    """获取指定设备信息

    Args:
        device_id: 设备ID

    Returns:
        Device: 设备信息
    """
    # TODO: 从扫描结果中查找指定设备
    # 当前简化实现
    devices = DeviceManager.scan_devices()
    for device in devices:
        if device.device_id == device_id:
            return device

    raise HTTPException(status_code=404, detail="Device not found")
```

**Step 2: 注册路由到主应用**

在 `main.py` 中添加：

```python
from insight_eyes.web.api.devices import router as devices_router

app.include_router(devices_router)
```

**Step 3: 测试 API**

```bash
# 启动服务
venv/Scripts/uvicorn.exe insight_eyes.web.api.main:app --reload --port 8000

# 在另一个终端测试
curl http://localhost:8000/api/devices
```

**Step 4: 提交**

```bash
cd .worktrees/1.0.3
git add insight_eyes/web/api/
git commit -m "feat(web): 实现设备管理 API

- 添加 /api/devices 端点
- 支持设备扫描和查询
- 集成到主应用路由

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>"
```

---

## Task 3: 实现监控控制 API

**Files:**
- Create: `insight_eyes/web/api/monitoring.py`
- Create: `insight_eyes/web/api/schemas.py`
- Modify: `insight_eyes/web/api/main.py`

**Step 1: 创建数据模型（Pydantic）**

```python
# insight_eyes/web/api/schemas.py
# -*- coding: utf-8 -*-
"""
API 数据模型（Pydantic）
定义请求和响应的数据结构
"""
from pydantic import BaseModel, Field
from typing import Optional


class StartMonitoringRequest(BaseModel):
    """开始监控请求"""
    device_id: str = Field(..., description="设备ID")
    app_package: str = Field(..., description="应用包名或Bundle ID")
    platform: str = Field(default="android", description="平台类型（android/ios）")


class SessionResponse(BaseModel):
    """会话响应"""
    id: int
    device_id: str
    app_package: str
    platform: str
    status: str
    start_time: str
    end_time: Optional[str] = None
    duration: Optional[int] = None


class StopMonitoringRequest(BaseModel):
    """停止监控请求"""
    session_id: int = Field(..., description="会话ID")
```

**Step 2: 创建监控控制 API**

```python
# insight_eyes/web/api/monitoring.py
# -*- coding: utf-8 -*-
"""
监控控制 API
提供监控会话的启动、停止等功能
"""
from fastapi import APIRouter, HTTPException
from logzero import logger

from insight_eyes.core.device_manager import DeviceManager
from insight_eyes.core.database import DatabaseManager
from insight_eyes.core.models.session import Session
from insight_eyes.web.api.schemas import StartMonitoringRequest, SessionResponse


router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.post("/start", response_model=SessionResponse)
async def start_monitoring(request: StartMonitoringRequest):
    """开始监控

    Args:
        request: 监控启动请求

    Returns:
        SessionResponse: 创建的会话信息
    """
    try:
        session = await DeviceManager.start_session(
            request.device_id,
            request.app_package
        )
        logger.info(f"启动监控会话: {session.id}")

        return SessionResponse(
            id=session.id,
            device_id=session.device_id,
            app_package=session.app_package,
            platform=getattr(session, 'platform', 'android'),
            status=session.status.value,
            start_time=session.start_time.isoformat(),
            end_time=session.end_time.isoformat() if session.end_time else None,
            duration=session.duration,
        )
    except Exception as e:
        logger.error(f"启动监控失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_monitoring(session_id: int):
    """停止监控

    Args:
        session_id: 会话ID

    Returns:
        停止确认信息
    """
    try:
        await DeviceManager.stop_session(session_id)
        logger.info(f"停止监控会话: {session_id}")

        return {"status": "stopped", "session_id": session_id}
    except Exception as e:
        logger.error(f"停止监控失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def list_sessions(limit: int = 100):
    """列出所有会话

    Args:
        limit: 返回数量限制

    Returns:
        会话列表
    """
    try:
        db = DatabaseManager()
        sessions = db.list_sessions(limit=limit)

        return [
            SessionResponse(
                id=s.id,
                device_id=s.device_id,
                app_package=s.app_package,
                platform=getattr(s, 'platform', 'android'),
                status=s.status.value,
                start_time=s.start_time.isoformat(),
                end_time=s.end_time.isoformat() if s.end_time else None,
                duration=s.duration,
            )
            for s in sessions
        ]
    except Exception as e:
        logger.error(f"获取会话列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}")
async def get_session(session_id: int):
    """获取会话详情

    Args:
        session_id: 会话ID

    Returns:
        SessionResponse: 会话详细信息
    """
    try:
        db = DatabaseManager()
        session = db.get_session(session_id)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        return SessionResponse(
            id=session.id,
            device_id=session.device_id,
            app_package=session.app_package,
            platform=getattr(session, 'platform', 'android'),
            status=session.status.value,
            start_time=session.start_time.isoformat(),
            end_time=session.end_time.isoformat() if session.end_time else None,
            duration=session.duration,
        )
    except Exception as e:
        logger.error(f"获取会话详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**Step 3: 注册路由**

在 `main.py` 中添加：

```python
from insight_eyes.web.api.monitoring import router as monitoring_router

app.include_router(monitoring_router)
```

**Step 4: 测试 API**

```bash
# 测试启动监控
curl -X POST http://localhost:8000/api/monitoring/start \
  -H "Content-Type: application/json" \
  -d '{"device_id":"test_device","app_package":"com.example.app"}'

# 测试列出会话
curl http://localhost:8000/api/monitoring/sessions
```

**Step 5: 提交**

```bash
cd .worktrees/1.0.3
git add insight_eyes/web/api/
git commit -m "feat(web): 实现监控控制 API

- 添加 /api/monitoring/start 端点
- 添加 /api/monitoring/stop 端点
- 添加 /api/monitoring/sessions 端点
- 添加 /api/monitoring/sessions/{id} 端点
- 创建 Pydantic 数据模型

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>"
```

---

## Task 4: 实现 WebSocket 实时数据推送

**Files:**
- Create: `insight_eyes/web/websocket/handler.py`
- Modify: `insight_eyes/web/api/main.py`

**Step 1: 创建 WebSocket 处理器**

```python
# insight_eyes/web/websocket/handler.py
# -*- coding: utf-8 -*-
"""
WebSocket 实时数据推送
将监控数据实时推送到前端
"""
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
from logzero import logger
import json
import asyncio

from insight_eyes.core.device_manager import DeviceManager
from insight_eyes.core.models.metrics import MetricsData


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active_connections: dict[int, WebSocket] = {}

    async def connect(self, session_id: int, websocket: WebSocket):
        """建立连接"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket 连接建立: session {session_id}")

    def disconnect(self, session_id: int):
        """断开连接"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket 连接断开: session {session_id}")

    async def send_personal_message(self, message: dict, session_id: int):
        """发送消息到指定会话"""
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(message)
            except Exception as e:
                logger.error(f"发送消息失败 (session {session_id}): {e}")
                self.disconnect(session_id)


# 全局连接管理器
manager = ConnectionManager()


async def monitoring_websocket(
    websocket: WebSocket,
    session_id: int
):
    """
    监控数据实时推送 WebSocket 端点

    Args:
        websocket: WebSocket 连接
        session_id: 会话ID
    """
    await manager.connect(session_id, websocket)

    try:
        # 流式推送监控数据
        async for data in DeviceManager.stream_metrics(session_id):
            # 转换为 JSON 可序列化格式
            message = {
                "type": "metrics",
                "data": data.to_dict()
            }
            await manager.send_personal_message(message, session_id)
    except WebSocketDisconnect:
        logger.info(f"WebSocket 断开连接: session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket 错误 (session {session_id}): {e}")
    finally:
        manager.disconnect(session_id)
```

**Step 2: 注册 WebSocket 路由**

在 `main.py` 中添加：

```python
from insight_eyes.web.websocket.handler import monitoring_websocket

app.websocket("/ws/monitoring/{session_id}")(monitoring_websocket)
```

**Step 3: 创建测试客户端**

创建 `tests/web/test_websocket.py`:

```python
# -*- coding: utf-8 -*-
"""
WebSocket 测试
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from insight_eyes.web.api.main import app


@pytest.mark.asyncio
async def test_websocket_connection():
    """测试 WebSocket 连接"""
    # TODO: 实现 WebSocket 测试
    pass
```

**Step 4: 测试 WebSocket**

手动测试：
1. 启动服务：`uvicorn insight_eyes.web.api.main:app --reload`
2. 使用 WebSocket 客户端连接：`ws://localhost:8000/ws/monitoring/1`

**Step 5: 提交**

```bash
cd .worktrees/1.0.3
git add insight_eyes/web/websocket/ tests/web/
git commit -m "feat(web): 实现 WebSocket 实时数据推送

- 创建 WebSocket 连接管理器
- 实现 /ws/monitoring/{session_id} 端点
- 支持实时推送监控数据到前端
- 添加 WebSocket 测试框架

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>"
```

---

## Task 5: API 测试与文档

**Files:**
- Create: `tests/web/test_api.py`
- Modify: `insight_eyes/web/api/main.py`

**Step 1: 创建 API 测试**

```python
# tests/web/test_api.py
# -*- coding: utf-8 -*-
"""
FastAPI 测试
"""
from fastapi.testclient import TestClient

from insight_eyes.web.api.main import app


client = TestClient(app)


def test_root_endpoint():
    """测试根路径"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Insight-Eye API"
    assert data["version"] == "1.0.3"


def test_health_check():
    """测试健康检查"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_list_devices():
    """测试设备列表"""
    response = client.get("/api/devices")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_start_monitoring():
    """测试开始监控"""
    response = client.post(
        "/api/monitoring/start",
        json={
            "device_id": "test_device",
            "app_package": "com.example.app"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["device_id"] == "test_device"


def test_list_sessions():
    """测试会话列表"""
    response = client.get("/api/monitoring/sessions")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

**Step 2: 运行测试**

```bash
cd .worktrees/1.0.3
pytest tests/web/ -v
```

**Step 3: 提交**

```bash
cd .worktrees/1.0.3
git add tests/web/
git commit -m "test(web): 添加 API 集成测试

- 测试所有 REST API 端点
- 验证请求和响应格式
- 所有测试通过

Co-Authored-By: Claude (glm-4.7) <noreply@anthropic.com>"
```

---

## Task 6: Phase 2 验收与总结

**Step 1: 运行完整测试**

```bash
cd .worktrees/1.0.3
pytest tests/web/ -v
```

**Step 2: 手动测试 Web 服务**

1. 启动服务：
```bash
venv/Scripts/uvicorn.exe insight_eyes.web.api.main:app --reload --host 0.0.0.0 --port 8000
```

2. 访问 API 文档：http://localhost:8000/docs

3. 测试端点：
- GET /health
- GET /api/devices
- POST /api/monitoring/start
- GET /api/monitoring/sessions

**Step 3: 确认验收标准**

- [ ] FastAPI 应用正常启动
- [ ] API 文档可访问
- [ ] 所有 REST API 端点正常工作
- [ ] WebSocket 端点可连接
- [ ] 测试全部通过
- [ ] 与核心层集成正常

**Step 4: 创建 Phase 2 完成标记**

```bash
cd .worktrees/1.0.3
echo "# Phase 2: FastAPI 后端开发 - 已完成

**完成日期**: 2025-01-29
**状态**: ✅ 完成

## 实现的功能

### Web 服务
- FastAPI 主应用
- CORS 中间件配置
- API 文档自动生成

### REST API
- /api/devices - 设备管理
- /api/monitoring/start - 开始监控
- /api/monitoring/stop - 停止监控
- /api/monitoring/sessions - 会话列表
- /api/monitoring/sessions/{id} - 会话详情

### WebSocket
- /ws/monitoring/{session_id} - 实时数据推送

## 下一步

Phase 3: React 前端开发
" > docs/plans/phase2-completed.md

git add docs/plans/phase2-completed.md
git commit -m "docs: 标记 Phase 2 完成"
```

---

## Phase 2 总结

### 完成的工作

1. ✅ 创建 FastAPI Web 应用框架
2. ✅ 实现设备管理 API
3. ✅ 实现监控控制 API
4. ✅ 实现 WebSocket 实时推送
5. ✅ 添加 API 测试

### 技术栈

- **Web 框架**: FastAPI 0.104+
- **ASGI 服务器**: Uvicorn
- **实时通信**: WebSocket
- **数据验证**: Pydantic
- **API 文档**: 自动生成（Swagger/OpenAPI）

### 下一步

继续 **Phase 3: React 前端开发**

参考文档：`docs/plans/2025-01-29-v1.0.3-web-cross-platform-design.md`

---

**计划版本**: 1.0
**创建日期**: 2025-01-29
**预计工时**: 2周（80小时）
