"""
UI工具模块初始化

注意：核心设备模型（Platform, DeviceStatus, DeviceInfo, AppInfo）从 core.models 导入
UI特定模型（CPUMetrics, ProcessedMetrics 等）从本地 models 导入
"""
from insight_eyes.desktop.core.models import (
    Platform,
    DeviceStatus,
    DeviceInfo,
    AppInfo
)
from .models import (
    AlertLevel,
    CPUMetrics,
    MemoryMetrics,
    FPSMetrics,
    NetworkMetrics,
    BatteryMetrics,
    GPUMetrics,
    ProcessedMetrics,
    AlertRecord,
    CollectionConfig,
    ScenarioMarker,
    MonitoringSession
)
from .card_configs import (
    MetricCardConfig,
    ALL_METRIC_CARDS,
    get_enabled_cards,
    get_card_config
)

__all__ = [
    # 核心模型（来自 core.models）
    'Platform',
    'DeviceStatus',
    'DeviceInfo',
    'AppInfo',
    # UI特定模型（本地 models）
    'AlertLevel',
    'CPUMetrics',
    'MemoryMetrics',
    'FPSMetrics',
    'NetworkMetrics',
    'BatteryMetrics',
    'GPUMetrics',
    'ProcessedMetrics',
    'AlertRecord',
    'CollectionConfig',
    'ScenarioMarker',
    'MonitoringSession',
    # 卡片配置
    'MetricCardConfig',
    'ALL_METRIC_CARDS',
    'get_enabled_cards',
    'get_card_config'
]
