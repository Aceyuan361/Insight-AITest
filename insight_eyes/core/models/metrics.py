"""
监控指标数据模型
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class MetricType(Enum):
    """指标类型"""
    CPU = "cpu"
    MEMORY = "memory"
    FPS = "fps"
    NETWORK_UP = "network_up"
    NETWORK_DOWN = "network_down"
    BATTERY = "battery"
    GPU = "gpu"


@dataclass
class MetricsData:
    """监控指标数据"""
    timestamp: datetime
    cpu: Optional[float] = None  # 百分比
    memory: Optional[float] = None  # MB
    fps: Optional[float] = None
    network_up: Optional[float] = None  # KB/s
    network_down: Optional[float] = None  # KB/s
    battery: Optional[float] = None  # 百分比
    temperature: Optional[float] = None  # 摄氏度

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "cpu": self.cpu,
            "memory": self.memory,
            "fps": self.fps,
            "network_up": self.network_up,
            "network_down": self.network_down,
            "battery": self.battery,
            "temperature": self.temperature,
        }

    def get_metric(self, metric_type: MetricType) -> Optional[float]:
        """获取指定类型的指标值"""
        return getattr(self, metric_type.value, None)
