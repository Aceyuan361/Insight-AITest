"""
数据模型类
定义UI组件使用的各类数据结构

注意：核心设备模型（Platform, DeviceInfo, AppInfo）已统一使用 core.models
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Literal
from enum import Enum

# 从 core.models 导入核心设备模型
from insight_eyes.desktop.core.models import Platform, DeviceInfo, AppInfo


class AlertLevel(Enum):
    """告警级别枚举"""
    INFO = "信息"
    WARNING = "警告"
    ERROR = "错误"
    CRITICAL = "严重"


@dataclass
class CPUMetrics:
    """CPU指标"""
    app_cpu_rate: float = 0.0   # 应用CPU使用率
    sys_cpu_rate: float = 0.0   # 系统CPU使用率


@dataclass
class MemoryMetrics:
    """内存指标"""
    total_mb: float = 0.0       # 总内存占用(MB)
    native_mb: float = 0.0      # Native堆内存(MB)
    dalvik_mb: float = 0.0      # Dalvik堆内存(MB)
    total_percent: float = 0.0  # 占总内存百分比


@dataclass
class FPSMetrics:
    """FPS指标"""
    fps: int = 0                # 当前FPS
    jank: int = 0               # 卡顿次数
    big_jank: int = 0           # 严重卡顿次数
    frame_time_avg: float = 0.0 # 平均帧时间(ms)


@dataclass
class NetworkMetrics:
    """网络流量指标"""
    upload_kb: float = 0.0      # 上行流量(KB)
    download_kb: float = 0.0    # 下行流量(KB)
    upload_rate_kbs: float = 0.0 # 上行速率(KB/s)
    download_rate_kbs: float = 0.0 # 下行速率(KB/s)


@dataclass
class BatteryMetrics:
    """电池指标"""
    level: int = 100            # 电量百分比
    temperature: float = 0.0    # 温度(℃)
    current_ma: float = 0.0     # 电流(mA)
    voltage: float = 0.0        # 电压(V)


@dataclass
class GPUMetrics:
    """GPU指标"""
    usage_percent: float = 0.0  # GPU使用率


@dataclass
class ProcessedMetrics:
    """处理后的完整监控指标"""
    timestamp: datetime = field(default_factory=datetime.now)
    device_id: str = ""
    package_name: str = ""

    # 各类指标
    cpu: CPUMetrics = field(default_factory=CPUMetrics)
    memory: MemoryMetrics = field(default_factory=MemoryMetrics)
    fps: FPSMetrics = field(default_factory=FPSMetrics)
    network: NetworkMetrics = field(default_factory=NetworkMetrics)
    battery: BatteryMetrics = field(default_factory=BatteryMetrics)
    gpu: GPUMetrics = field(default_factory=GPUMetrics)

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'device_id': self.device_id,
            'package_name': self.package_name,
            'cpu': {
                'app_cpu_rate': self.cpu.app_cpu_rate,
                'sys_cpu_rate': self.cpu.sys_cpu_rate
            },
            'memory': {
                'total_mb': self.memory.total_mb,
                'native_mb': self.memory.native_mb,
                'dalvik_mb': self.memory.dalvik_mb,
                'total_percent': self.memory.total_percent
            },
            'fps': {
                'fps': self.fps.fps,
                'jank': self.fps.jank,
                'big_jank': self.fps.big_jank,
                'frame_time_avg': self.fps.frame_time_avg
            },
            'network': {
                'upload_kb': self.network.upload_kb,
                'download_kb': self.network.download_kb,
                'upload_rate_kbs': self.network.upload_rate_kbs,
                'download_rate_kbs': self.network.download_rate_kbs
            },
            'battery': {
                'level': self.battery.level,
                'temperature': self.battery.temperature,
                'current_ma': self.battery.current_ma,
                'voltage': self.battery.voltage
            },
            'gpu': {
                'usage_percent': self.gpu.usage_percent
            }
        }


@dataclass
class AlertRecord:
    """告警记录"""
    id: str = ""                # 告警ID
    timestamp: datetime = field(default_factory=datetime.now)
    level: AlertLevel = AlertLevel.INFO
    device_id: str = ""         # 关联设备
    package_name: str = ""      # 关联应用
    metric_type: str = ""       # 指标类型 (CPU/内存/FPS等)
    message: str = ""           # 告警消息
    current_value: float = 0.0  # 当前值
    threshold: float = 0.0      # 阈值

    def __post_init__(self):
        """生成告警ID"""
        if not self.id:
            self.id = f"{self.device_id}_{self.metric_type}_{self.timestamp.strftime('%Y%m%d%H%M%S%f')}"


@dataclass
class CollectionConfig:
    """采集配置"""
    # 采集间隔 (毫秒)
    interval_ms: int = 1000

    # 监控指标开关
    enable_cpu: bool = True
    enable_memory: bool = True
    enable_fps: bool = True
    enable_network_up: bool = True      # 网络上行
    enable_network_down: bool = True    # 网络下行
    enable_gpu: bool = False            # 默认禁用

    # 阈值设置
    fps_threshold: int = 30             # FPS低于此值告警
    memory_threshold_mb: int = 500      # 内存超过此值告警(MB)
    cpu_threshold_percent: float = 80.0 # CPU超过此值告警(%)

    # 数据保留设置
    data_retention_days: int = 7        # 数据保留天数
    max_samples_per_chart: int = 1000   # 单图表最大数据点数

    def get_enabled_metrics(self) -> List[str]:
        """获取启用的指标ID列表"""
        metrics = []
        if self.enable_cpu:
            metrics.append('cpu')
        if self.enable_memory:
            metrics.append('memory')
        if self.enable_fps:
            metrics.append('fps')
        if self.enable_network_up:
            metrics.append('network_up')
        if self.enable_network_down:
            metrics.append('network_down')
        if self.enable_gpu:
            metrics.append('gpu')
        return metrics

    def set_metric_enabled(self, metric_id: str, enabled: bool):
        """
        设置指标启用状态

        Args:
            metric_id: 指标ID ('cpu', 'memory', 'fps', 'network_up', 'network_down', 'gpu')
            enabled: 是否启用
        """
        attr_map = {
            'cpu': 'enable_cpu',
            'memory': 'enable_memory',
            'fps': 'enable_fps',
            'network_up': 'enable_network_up',
            'network_down': 'enable_network_down',
            'gpu': 'enable_gpu'
        }

        if metric_id in attr_map:
            setattr(self, attr_map[metric_id], enabled)
        else:
            raise ValueError(f"未知的指标ID: {metric_id}")


@dataclass
class ScenarioMarker:
    """场景标记"""
    timestamp: datetime = field(default_factory=datetime.now)
    name: str = ""              # 场景名称
    description: str = ""       # 场景描述
    device_id: str = ""         # 关联设备
    package_name: str = ""      # 关联应用
    tags: List[str] = field(default_factory=list)  # 标签


@dataclass
class MonitoringSession:
    """监控会话"""
    session_id: str = ""        # 会话ID
    device_id: str = ""         # 设备ID
    package_name: str = ""      # 应用包名
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    status: Literal["running", "paused", "stopped"] = "running"
    metrics_count: int = 0      # 已采集指标数
    alert_count: int = 0        # 告警数

    def __post_init__(self):
        """生成会话ID"""
        if not self.session_id:
            self.session_id = f"session_{self.device_id}_{self.start_time.strftime('%Y%m%d%H%M%S')}"

    @property
    def duration(self) -> float:
        """获取持续时间(秒)"""
        end = self.end_time if self.end_time else datetime.now()
        return (end - self.start_time).total_seconds()
