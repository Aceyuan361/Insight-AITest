# -*- coding: utf-8 -*-
"""
WebSocket 实时数据推送
"""

from fastapi import WebSocket, WebSocketDisconnect
from logzero import logger

from insight_aitest.platform.services.device_manager import DeviceManager


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}

    async def connect(self, session_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket 连接: session {session_id}")

    def disconnect(self, session_id: int):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket 断开: session {session_id}")

    async def send_data(self, message: dict, session_id: int):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(message)
            except Exception:
                self.disconnect(session_id)


manager = ConnectionManager()


async def monitoring_websocket(websocket: WebSocket, session_id: int):
    """监控数据实时推送"""
    await manager.connect(session_id, websocket)
    try:
        async for data in DeviceManager.stream_metrics(session_id):
            message = {"type": "metrics", "data": data.to_dict()}
            await manager.send_data(message, session_id)
    except WebSocketDisconnect:
        logger.info(f"WebSocket 断开: session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket 错误: {e}")
    finally:
        manager.disconnect(session_id)
