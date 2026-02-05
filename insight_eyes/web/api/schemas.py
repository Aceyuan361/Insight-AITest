# -*- coding: utf-8 -*-
"""
API 数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional


class StartMonitoringRequest(BaseModel):
    device_id: str = Field(..., description="设备ID")
    app_package: str = Field(..., description="应用包名")
    platform: str = Field(default="android", description="平台类型")
    sampling_interval: int = Field(default=1000, description="采样间隔(毫秒) 1000/3000/5000/10000")


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
