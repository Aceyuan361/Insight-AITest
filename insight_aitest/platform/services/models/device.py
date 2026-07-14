# -*- coding: utf-8 -*-
"""
设备数据模型

注意：此模块使用 DeviceType 枚举来区分设备类型（android/ios）。
这是核心层重构后的新命名，与桌面层的 Platform 枚举功能相同但命名更清晰。
在后续重构中，桌面层将统一使用核心层的 DeviceType。
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any


class DeviceType(Enum):
    """设备类型枚举

    定义支持的移动设备平台类型。
    """

    ANDROID = "android"
    IOS = "ios"


class DeviceStatus(Enum):
    """设备状态枚举

    定义设备可能的连接状态。
    """

    ONLINE = "online"
    OFFLINE = "offline"
    UNAUTHORIZED = "unauthorized"


@dataclass
class Device:
    """设备信息数据模型

    表示一个移动设备及其当前状态。

    Attributes:
        device_id: 设备唯一标识符（如 Android 的 serial number）
        name: 设备显示名称
        type: 设备类型（ANDROID 或 IOS）
        status: 设备当前连接状态
        sdk_version: 系统 SDK 版本号（可选）
        model: 设备型号（可选）
    """

    device_id: str
    name: str
    type: DeviceType
    status: DeviceStatus
    sdk_version: Optional[str] = None
    model: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """将设备对象转换为字典

        Returns:
            Dict[str, Any]: 包含设备所有字段的字典，枚举类型转换为字符串值
        """
        return {
            "device_id": self.device_id,
            "name": self.name,
            "type": self.type.value,
            "status": self.status.value,
            "sdk_version": self.sdk_version,
            "model": self.model,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Device":
        """从字典创建设备对象

        Args:
            data: 包含设备数据的字典，type 和 status 字段应为枚举值字符串

        Returns:
            Device: 新的设备对象实例
        """
        return cls(
            device_id=data["device_id"],
            name=data["name"],
            type=DeviceType(data["type"]),
            status=DeviceStatus(data["status"]),
            sdk_version=data.get("sdk_version"),
            model=data.get("model"),
        )
