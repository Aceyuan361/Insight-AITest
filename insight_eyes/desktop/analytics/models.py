"""
性能指标数据模型定义

本模块定义了性能监控系统中使用的所有数据结构和类型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class AlertSeverity(str, Enum):
    """告警严重程度"""
    WARNING = "warning"      # 警告
    CRITICAL = "critical"    # 严重
    INFO = "info"           # 信息


class AlertType(str, Enum):
    """告警类型"""
    # FPS相关
    LOW_FPS = "low_fps"                    # 低帧率
    FPS_JANK = "fps_jank"                  # 卡顿
    FPS_BIG_JANK = "fps_big_jank"          # 大卡顿
    FPS_FLUCTUATION = "fps_fluctuation"    # 帧率波动

    # 内存相关
    MEMORY_LEAK = "memory_leak"            # 内存泄露
    HIGH_MEMORY = "high_memory"            # 高内存占用
    MEMORY_GROWTH = "memory_growth"        # 内存持续增长

    # CPU相关
    HIGH_CPU = "high_cpu"                  # 高CPU占用
    CPU_SUSTAINED = "cpu_sustained"        # CPU持续高负载

    # 网络相关
    NETWORK_ABNORMAL = "network_abnormal"  # 网络异常
    UPLOAD_ERROR = "upload_error"          # 上传异常
    NETWORK_TIMEOUT = "network_timeout"    # 网络超时


class TrendType(str, Enum):
    """趋势类型"""
    STABLE = "stable"          # 稳定
    INCREASING = "increasing"  # 上升
    DECREASING = "decreasing"  # 下降
    FLUCTUATING = "fluctuating"  # 波动


@dataclass
class Alert:
    """告警数据结构"""
    alert_type: AlertType          # 告警类型
    severity: AlertSeverity        # 严重程度
    metric_name: str               # 指标名称
    current_value: float           # 当前值
    threshold: float               # 阈值
    message: str                   # 告警消息
    timestamp: datetime            # 发生时间
    session_id: int                # 会话ID
    device_id: str = ""            # 设备ID
    app_id: str = ""               # 应用ID
    context: Dict[str, Any] = field(default_factory=dict)  # 额外上下文信息

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'alert_type': self.alert_type.value,
            'severity': self.severity.value,
            'metric_name': self.metric_name,
            'current_value': self.current_value,
            'threshold': self.threshold,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'session_id': self.session_id,
            'device_id': self.device_id,
            'app_id': self.app_id,
            'context': self.context
        }


@dataclass
class FPSMetrics:
    """FPS指标数据"""
    fps: float                    # 当前FPS
    jank_count: int              # 卡顿次数
    big_jank_count: int          # 大卡顿次数
    frame_time_avg: float        # 平均帧时间(ms)
    frame_time_max: float        # 最大帧时间(ms)
    trend: TrendType             # FPS趋势
    timestamp: datetime          # 采集时间


@dataclass
class MemoryMetrics:
    """内存指标数据"""
    total_mb: float              # 总内存(MB)
    native_mb: float             # Native堆内存(MB)
    dalvik_mb: float             # Dalvik堆内存(MB)
    growth_rate_mb_per_min: float # 内存增长率(MB/min)
    trend: TrendType             # 内存趋势
    timestamp: datetime          # 采集时间


@dataclass
class CPUMetrics:
    """CPU指标数据"""
    app_cpu_percent: float       # 应用CPU占用率(%)
    sys_cpu_percent: float       # 系统CPU占用率(%)
    moving_avg: float            # 移动平均值
    thread_count: int = 0        # 线程数
    timestamp: datetime = None   # 采集时间


@dataclass
class NetworkMetrics:
    """网络指标数据"""
    upload_speed_kb_s: float     # 上行速度(KB/s)
    download_speed_kb_s: float   # 下行速度(KB/s)
    total_sent_mb: float         # 总发送量(MB)
    total_received_mb: float     # 总接收量(MB)
    timestamp: datetime          # 采集时间


@dataclass
class BatteryMetrics:
    """电池指标数据"""
    level: int                   # 电量百分比 (0-100)
    temperature: float           # 温度 (°C)
    current: float               # 电流 (mA)
    voltage: float               # 电压 (V)
    power: float                 # 功率 (W)
    status: str                  # 充电状态 (charging/discharging/full/not charging/unknown)
    capacity: int = None         # 电池容量 (mAh) - 可选字段
    timestamp: datetime = None   # 采集时间


@dataclass
class ProcessedMetrics:
    """处理后的综合指标数据"""
    session_id: int              # 会话ID
    timestamp: datetime          # 处理时间
    device_id: str               # 设备ID
    app_id: str                  # 应用ID

    # 各项指标
    fps: Optional[FPSMetrics] = None
    memory: Optional[MemoryMetrics] = None
    cpu: Optional[CPUMetrics] = None
    network: Optional[NetworkMetrics] = None
    battery: Optional[BatteryMetrics] = None  # 电池指标

    # 告警列表
    alerts: List[Alert] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            'session_id': self.session_id,
            'timestamp': self.timestamp.isoformat(),
            'device_id': self.device_id,
            'app_id': self.app_id,
            'alerts': [alert.to_dict() for alert in self.alerts]
        }

        if self.fps:
            result['fps'] = {
                'fps': self.fps.fps,
                'jank_count': self.fps.jank_count,
                'big_jank_count': self.fps.big_jank_count,
                'frame_time_avg': self.fps.frame_time_avg,
                'frame_time_max': self.fps.frame_time_max,
                'trend': self.fps.trend.value,
                'timestamp': self.fps.timestamp.isoformat()
            }

        if self.memory:
            result['memory'] = {
                'total_mb': self.memory.total_mb,
                'native_mb': self.memory.native_mb,
                'dalvik_mb': self.memory.dalvik_mb,
                'growth_rate_mb_per_min': self.memory.growth_rate_mb_per_min,
                'trend': self.memory.trend.value,
                'timestamp': self.memory.timestamp.isoformat()
            }

        if self.cpu:
            result['cpu'] = {
                'app_cpu_percent': self.cpu.app_cpu_percent,
                'sys_cpu_percent': self.cpu.sys_cpu_percent,
                'moving_avg': self.cpu.moving_avg,
                'thread_count': self.cpu.thread_count,
                'timestamp': self.cpu.timestamp.isoformat() if self.cpu.timestamp else None
            }

        if self.network:
            result['network'] = {
                'upload_speed_kb_s': self.network.upload_speed_kb_s,
                'download_speed_kb_s': self.network.download_speed_kb_s,
                'total_sent_mb': self.network.total_sent_mb,
                'total_received_mb': self.network.total_received_mb,
                'timestamp': self.network.timestamp.isoformat()
            }

        if self.battery:
            result['battery'] = {
                'level': self.battery.level,
                'temperature': self.battery.temperature,
                'current': self.battery.current,
                'voltage': self.battery.voltage,
                'power': self.battery.power,
                'status': self.battery.status,
                'capacity': self.battery.capacity,
                'timestamp': self.battery.timestamp.isoformat() if self.battery.timestamp else None
            }

        return result


@dataclass
class SessionSummary:
    """会话摘要统计数据"""
    session_id: int              # 会话ID
    start_time: datetime         # 开始时间
    end_time: datetime           # 结束时间
    duration_seconds: float      # 持续时间(秒)

    # FPS统计
    avg_fps: float               # 平均FPS
    min_fps: float               # 最低FPS
    max_fps: float               # 最高FPS
    fps_p95: float               # FPS 95分位数
    fps_std: float               # FPS标准差
    jank_count: int              # 卡顿次数
    big_jank_count: int          # 大卡顿次数

    # 内存统计
    avg_memory_mb: float         # 平均内存(MB)
    peak_memory_mb: float        # 峰值内存(MB)
    memory_leaked_mb: float      # 泄露内存(MB)

    # CPU统计
    avg_cpu_percent: float       # 平均CPU占用率(%)
    peak_cpu_percent: float      # 峰值CPU占用率(%)

    # 网络统计
    total_data_sent_mb: float    # 总发送数据(MB)
    total_data_received_mb: float # 总接收数据(MB)

    # 告警统计
    alert_count: int             # 告警总数
    critical_count: int          # 严重告警数
    warning_count: int           # 警告告警数

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'session_id': self.session_id,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'duration_seconds': self.duration_seconds,
            'avg_fps': self.avg_fps,
            'min_fps': self.min_fps,
            'max_fps': self.max_fps,
            'fps_p95': self.fps_p95,
            'fps_std': self.fps_std,
            'jank_count': self.jank_count,
            'big_jank_count': self.big_jank_count,
            'avg_memory_mb': self.avg_memory_mb,
            'peak_memory_mb': self.peak_memory_mb,
            'memory_leaked_mb': self.memory_leaked_mb,
            'avg_cpu_percent': self.avg_cpu_percent,
            'peak_cpu_percent': self.peak_cpu_percent,
            'total_data_sent_mb': self.total_data_sent_mb,
            'total_data_received_mb': self.total_data_received_mb,
            'alert_count': self.alert_count,
            'critical_count': self.critical_count,
            'warning_count': self.warning_count
        }
