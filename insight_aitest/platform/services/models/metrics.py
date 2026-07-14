# -*- coding: utf-8 -*-
"""
监控指标数据模型
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any


class MetricType(Enum):
    """性能指标类型枚举

    定义支持的所有性能监控指标类型。
    """

    CPU = "cpu"
    MEMORY = "memory"
    FPS = "fps"
    NETWORK_UP = "network_up"
    NETWORK_DOWN = "network_down"
    BATTERY = "battery"
    GPU = "gpu"


@dataclass
class MetricsData:
    """性能监控指标数据模型

    记录单个时间点的设备性能指标。

    Attributes:
        timestamp: 数据采集时间戳
        cpu: CPU 使用率，单位为百分比（可选）
        memory: 内存使用量，单位为 MB（可选）
        fps: 帧率（可选）
        network_up: 上行网络速度，单位为 KB/s（可选）
        network_down: 下行网络速度，单位为 KB/s（可选）
        battery: 电池电量，单位为百分比（可选）
        temperature: 设备温度，单位为摄氏度（可选）
        is_alert: 是否为告警数据（可选）
        alert_data: 告警数据，当is_alert为True时包含告警信息（可选）
    """

    timestamp: datetime
    cpu: Optional[float] = None  # 百分比
    memory: Optional[float] = None  # MB
    fps: Optional[float] = None
    network_up: Optional[float] = None  # KB/s
    network_down: Optional[float] = None  # KB/s
    battery: Optional[float] = None  # 百分比
    temperature: Optional[float] = None  # 摄氏度
    is_alert: Optional[bool] = None  # 是否为告警
    alert_data: Optional[Dict[str, Any]] = None  # 告警数据

    def to_dict(self) -> Dict[str, Any]:
        """将指标数据对象转换为字典

        Returns:
            Dict[str, Any]: 包含所有指标字段的字典，时间戳转换为 ISO 格式字符串
        """
        result = {
            "timestamp": self.timestamp.isoformat(),
            "cpu": self.cpu,
            "memory": self.memory,
            "fps": self.fps,
            "network_up": self.network_up,
            "network_down": self.network_down,
            "battery": self.battery,
            "temperature": self.temperature,
        }
        # 如果是告警数据，添加告警字段
        if self.is_alert:
            result["is_alert"] = True
            result["alert_data"] = self.alert_data
        return result

    def get_metric(self, metric_type: MetricType) -> Optional[float]:
        """获取指定类型的指标值

        Args:
            metric_type: 要获取的指标类型

        Returns:
            Optional[float]: 指标值，如果不存在则返回 None
        """
        return getattr(self, metric_type.value, None)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MetricsData":
        """从字典创建指标数据对象

        Args:
            data: 包含指标数据的字典，timestamp 字段应为 ISO 格式字符串

        Returns:
            MetricsData: 新的指标数据对象实例
        """
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            cpu=data.get("cpu"),
            memory=data.get("memory"),
            fps=data.get("fps"),
            network_up=data.get("network_up"),
            network_down=data.get("network_down"),
            battery=data.get("battery"),
            temperature=data.get("temperature"),
        )
