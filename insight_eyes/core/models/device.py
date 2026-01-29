"""
设备数据模型
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


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
