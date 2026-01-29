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
    assert "docs" in data


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


def test_list_sessions_with_limit():
    """测试会话列表带限制"""
    response = client.get("/api/monitoring/sessions?limit=10")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_nonexistent_session():
    """测试获取不存在的会话"""
    response = client.get("/api/monitoring/sessions/99999")
    assert response.status_code == 404


def test_get_device_not_found():
    """测试获取不存在的设备"""
    response = client.get("/api/devices/nonexistent_device")
    assert response.status_code == 404
