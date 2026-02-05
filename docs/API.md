# Insight-Eye Web API 文档

## 基础信息

- **Base URL**: `http://localhost:8001`
- **API 版本**: v1.0.0
- **认证方式**: 无需认证（开发环境）
- **数据格式**: JSON
- **作者**: Aceyuan361

## 自动生成的 API 文档

启动后端服务后，可以通过以下地址查看完整的交互式 API 文档：

- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

## API 端点概览

### 设备管理

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/devices` | 获取所有设备列表 |
| GET | `/api/devices/{device_id}` | 获取指定设备信息 |
| POST | `/api/devices/{device_id}/connect` | 连接指定设备 |
| DELETE | `/api/devices/{device_id}` | 断开设备连接 |
| GET | `/api/devices/{device_id}/apps` | 获取设备应用列表 |
| POST | `/api/devices/refresh` | 刷新设备列表 |

### 监控会话

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/monitoring/start` | 开始监控 |
| POST | `/api/monitoring/stop` | 停止监控 |
| GET | `/api/monitoring/sessions` | 获取所有会话列表 |
| GET | `/api/monitoring/sessions/{session_id}` | 获取指定会话信息 |
| DELETE | `/api/monitoring/sessions/{session_id}` | 删除会话 |
| GET | `/api/monitoring/sessions/{session_id}/metrics` | 获取会话指标数据 |
| GET | `/api/monitoring/sessions/{session_id}/statistics` | 获取会话统计数据 |
| GET | `/api/monitoring/sessions/{session_id}/alerts` | 获取会话告警记录 |
| POST | `/api/monitoring/sessions/batch-delete` | 批量删除会话 |
| WS | `/ws/monitoring/{session_id}` | 实时数据流（WebSocket） |

### 健康检查

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/health` | 服务健康检查 |

## WebSocket 消息格式

### 实时数据流消息

```json
{
  "type": "metrics",
  "timestamp": "2025-02-05T12:34:56Z",
  "data": {
    "cpu": 45.2,
    "memory": 512.5,
    "fps": 60,
    "network_up": 1024,
    "network_down": 2048,
    "battery_level": 85,
    "battery_temp": 32.5
  }
}
```

### 告警消息

```json
{
  "type": "alert",
  "timestamp": "2025-02-05T12:34:56Z",
  "data": {
    "alert_id": "123",
    "metric_name": "cpu",
    "current_value": 85.5,
    "threshold_value": 80,
    "severity": "warning",
    "message": "CPU 使用率过高"
  }
}
```

### 错误消息

```json
{
  "type": "error",
  "timestamp": "2025-02-05T12:34:56Z",
  "data": {
    "code": "DEVICE_NOT_FOUND",
    "message": "设备未找到或已断开连接"
  }
}
```

## 错误码

| 错误码 | HTTP 状态 | 描述 |
|--------|----------|------|
| `INVALID_REQUEST` | 400 | 请求参数无效 |
| `UNAUTHORIZED` | 401 | 未授权（暂未使用） |
| `DEVICE_NOT_FOUND` | 404 | 设备未找到 |
| `SESSION_NOT_FOUND` | 404 | 会话未找到 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |

## 请求示例

### Python

```python
import requests

# 获取设备列表
response = requests.get("http://localhost:8000/api/devices")
devices = response.json()

# 创建监控会话
session_data = {
    "device_id": "emulator-5554",
    "app_package": "com.example.app"
}
response = requests.post("http://localhost:8000/api/sessions", json=session_data)
session = response.json()
```

### JavaScript

```javascript
// 获取设备列表
const response = await fetch('http://localhost:8000/api/devices');
const devices = await response.json();

// 创建监控会话
const sessionData = {
  device_id: 'emulator-5554',
  app_package: 'com.example.app'
};
const response = await fetch('http://localhost:8000/api/sessions', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(sessionData)
});
const session = await response.json();
```

### cURL

```bash
# 获取设备列表
curl -X GET http://localhost:8000/api/devices

# 创建监控会话
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"device_id":"emulator-5554","app_package":"com.example.app"}'
```

## WebSocket 连接示例

### JavaScript

```javascript
// 连接到实时数据流
const ws = new WebSocket('ws://localhost:8000/api/sessions/1/stream');

ws.onopen = () => {
  console.log('WebSocket 已连接');
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  if (message.type === 'metrics') {
    console.log('性能数据:', message.data);
  } else if (message.type === 'alert') {
    console.log('告警:', message.data);
  }
};

ws.onerror = (error) => {
  console.error('WebSocket 错误:', error);
};

ws.onclose = () => {
  console.log('WebSocket 已断开');
};
```

### Python

```python
import asyncio
import websockets

async def receive_metrics(session_id: int):
    uri = f"ws://localhost:8000/api/sessions/{session_id}/stream"

    async with websockets.connect(uri) as websocket:
        while True:
            message = await websocket.recv()
            data = json.loads(message)

            if data['type'] == 'metrics':
                print(f"性能数据: {data['data']}")
            elif data['type'] == 'alert':
                print(f"告警: {data['data']}")

# 运行
asyncio.run(receive_metrics(1))
```

## 数据模型

### Device（设备）

```json
{
  "device_id": "string",
  "name": "string",
  "platform": "android" | "ios",
  "status": "connected" | "disconnected" | "busy",
  "model": "string",
  "os_version": "string"
}
```

### Session（会话）

```json
{
  "session_id": "integer",
  "device_id": "string",
  "app_package": "string",
  "app_name": "string",
  "start_time": "string (ISO 8601)",
  "status": "running" | "stopped" | "error"
}
```

### MetricsData（性能数据）

```json
{
  "timestamp": "string (ISO 8601)",
  "cpu": "number",
  "memory": "number",
  "fps": "number",
  "network_up": "number",
  "network_down": "number",
  "battery_level": "number",
  "battery_temp": "number"
}
```

### AlertRule（告警规则）

```json
{
  "rule_id": "integer",
  "metric_name": "string",
  "operator": "gt" | "lt" | "eq",
  "threshold": "number",
  "severity": "info" | "warning" | "critical",
  "enabled": "boolean"
}
```

## 版本历史

- **v1.0.0** (2025-02-05): 初始版本
  - 设备管理 API
  - 监控会话 API
  - 实时数据流 WebSocket
  - 告警系统 API
