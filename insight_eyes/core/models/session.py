# -*- coding: utf-8 -*-
"""
会话数据模型
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any


class SessionStatus(Enum):
    """会话状态枚举

    定义监控会话可能的状态。
    """
    CREATED = "created"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class Session:
    """监控会话数据模型

    表示一次完整的性能监控会话，记录设备、应用、时间等信息。

    Attributes:
        id: 会话唯一标识符
        device_id: 设备唯一标识符
        app_package: 被监控应用的包名
        platform: 平台类型 ('android' 或 'ios')
        status: 会话当前状态
        start_time: 会话开始时间
        end_time: 会话结束时间（可选）
        duration: 会话持续时间，单位为秒（可选）
    """
    id: int
    device_id: str
    app_package: str
    platform: str
    status: SessionStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[int] = None  # 秒

    def to_dict(self) -> Dict[str, Any]:
        """将会话对象转换为字典

        Returns:
            Dict[str, Any]: 包含会话所有字段的字典，时间字段转换为 ISO 格式字符串
        """
        return {
            "id": self.id,
            "device_id": self.device_id,
            "app_package": self.app_package,
            "platform": self.platform,
            "status": self.status.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        """从字典创建会话对象

        Args:
            data: 包含会话数据的字典，时间字段应为 ISO 格式字符串

        Returns:
            Session: 新的会话对象实例
        """
        return cls(
            id=data["id"],
            device_id=data["device_id"],
            app_package=data["app_package"],
            platform=data.get("platform", "android"),
            status=SessionStatus(data["status"]),
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            duration=data.get("duration"),
        )
