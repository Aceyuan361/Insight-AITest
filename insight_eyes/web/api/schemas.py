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


class SessionResponse(BaseModel):
    id: int
    device_id: str
    app_package: str
    platform: str
    status: str
    start_time: str
    end_time: Optional[str] = None
    duration: Optional[int] = None
