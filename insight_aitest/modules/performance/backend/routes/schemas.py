# -*- coding: utf-8 -*-
"""
API 数据模型
"""

from pydantic import BaseModel, Field
from typing import Optional


class AlertThresholds(BaseModel):
    """告警阈值配置"""

    fps: float = Field(default=30, ge=10, le=60, description="FPS阈值")
    memory: float = Field(default=500, ge=100, description="内存阈值(MB)")
    cpu: float = Field(default=80, ge=0, le=100, description="CPU阈值(%)")
    temperature: float = Field(default=45, ge=0, description="电池温度阈值(°C)")


class StartMonitoringRequest(BaseModel):
    device_id: str = Field(..., description="设备ID")
    app_package: str = Field(..., description="应用包名")
    platform: str = Field(default="android", description="平台类型")
    sampling_interval: int = Field(default=1000, description="采样间隔(毫秒) 1000/3000/5000/10000")
    alert_thresholds: Optional[AlertThresholds] = Field(default=None, description="告警阈值配置")
    project_id: Optional[int] = Field(default=None, description="项目ID（归属项目）")


class StopMonitoringRequest(BaseModel):
    session_id: int = Field(..., description="会话ID")


class SessionResponse(BaseModel):
    id: int
    device_id: str
    app_package: str
    app_name: Optional[str] = None
    platform: str
    status: str
    start_time: str
    end_time: Optional[str] = None
    duration: Optional[int] = None
    project_id: Optional[int] = None
