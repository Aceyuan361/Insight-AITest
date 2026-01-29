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
