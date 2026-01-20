"""
阈值配置管理模块

本模块负责管理性能指标的告警阈值配置
支持动态修改和实时生效
"""

import json
import threading
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class FPSThresholds:
    """FPS检测阈值"""
    warning_fps: float = 30.0          # 警告阈值FPS
    critical_fps: float = 20.0         # 严重阈值FPS
    jank_consecutive_count: int = 3    # 连续卡顿帧数阈值
    jank_fps_threshold: float = 24.0   # 卡顿判定FPS阈值
    big_jank_frame_time_ms: float = 100.0  # 大卡顿帧时间阈值(ms)
    frame_time_warning_ms: float = 50.0    # 帧时间警告阈值


@dataclass
class MemoryThresholds:
    """内存检测阈值"""
    leak_growth_mb: float = 100.0      # 泄疑泄露判定增长量(MB/5min)
    leak_time_window_minutes: int = 5  # 内存泄露检测时间窗口(分钟)
    high_memory_mb: float = 500.0      # 高内存占用阈值(MB)
    monotonic_increase_samples: int = 10  # 单调递增采样点数
    growth_rate_warning_mb_per_min: float = 10.0  # 增长率警告阈值(MB/min)
    growth_rate_critical_mb_per_min: float = 20.0 # 增长率严重阈值(MB/min)


@dataclass
class CPUThresholds:
    """CPU检测阈值"""
    high_app_cpu_percent: float = 80.0    # 应用高CPU阈值(%)
    high_sys_cpu_percent: float = 90.0    # 系统高CPU阈值(%)
    sustained_cpu_percent: float = 60.0   # 持续高负载阈值(%)
    sustained_duration_seconds: int = 60  # 持续高负载持续时间(秒)
    moving_avg_window: int = 10           # 移动平均窗口大小


@dataclass
class NetworkThresholds:
    """网络检测阈值"""
    timeout_seconds: int = 5          # 网络超时阈值(秒)
    zero_upload_threshold: int = 3    # 零上行连续次数阈值
    speed_variance_threshold: float = 0.5  # 速度波动阈值


class ThresholdManager:
    """阈值管理器

    负责管理所有性能指标的告警阈值
    支持动态修改和持久化存储
    """

    # 默认阈值配置
    DEFAULT_THRESHOLDS = {
        'fps': FPSThresholds(),
        'memory': MemoryThresholds(),
        'cpu': CPUThresholds(),
        'network': NetworkThresholds()
    }

    def __init__(self, config_path: Optional[str] = None):
        """初始化阈值管理器

        Args:
            config_path: 配置文件路径，如果为None则不持久化
        """
        self._config_path = config_path
        self._lock = threading.RLock()

        # 初始化阈值
        self._fps = FPSThresholds()
        self._memory = MemoryThresholds()
        self._cpu = CPUThresholds()
        self._network = NetworkThresholds()

        # 从配置文件加载（如果存在）
        if config_path and Path(config_path).exists():
            self.load_from_file(config_path)

    @property
    def fps(self) -> FPSThresholds:
        """获取FPS阈值"""
        with self._lock:
            return self._fps

    @property
    def memory(self) -> MemoryThresholds:
        """获取内存阈值"""
        with self._lock:
            return self._memory

    @property
    def cpu(self) -> CPUThresholds:
        """获取CPU阈值"""
        with self._lock:
            return self._cpu

    @property
    def network(self) -> NetworkThresholds:
        """获取网络阈值"""
        with self._lock:
            return self._network

    def update_fps_thresholds(self, **kwargs):
        """更新FPS阈值

        Args:
            **kwargs: FPSThresholds的字段和值
        """
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self._fps, key):
                    setattr(self._fps, key, value)
            self._save_if_needed()

    def update_memory_thresholds(self, **kwargs):
        """更新内存阈值

        Args:
            **kwargs: MemoryThresholds的字段和值
        """
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self._memory, key):
                    setattr(self._memory, key, value)
            self._save_if_needed()

    def update_cpu_thresholds(self, **kwargs):
        """更新CPU阈值

        Args:
            **kwargs: CPUThresholds的字段和值
        """
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self._cpu, key):
                    setattr(self._cpu, key, value)
            self._save_if_needed()

    def update_network_thresholds(self, **kwargs):
        """更新网络阈值

        Args:
            **kwargs: NetworkThresholds的字段和值
        """
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self._network, key):
                    setattr(self._network, key, value)
            self._save_if_needed()

    def reset_to_defaults(self):
        """重置所有阈值为默认值"""
        with self._lock:
            self._fps = FPSThresholds()
            self._memory = MemoryThresholds()
            self._cpu = CPUThresholds()
            self._network = NetworkThresholds()
            self._save_if_needed()

    def to_dict(self) -> Dict[str, Any]:
        """将所有阈值转换为字典

        Returns:
            包含所有阈值的字典
        """
        with self._lock:
            return {
                'fps': asdict(self._fps),
                'memory': asdict(self._memory),
                'cpu': asdict(self._cpu),
                'network': asdict(self._network)
            }

    def load_from_dict(self, config: Dict[str, Any]):
        """从字典加载阈值配置

        Args:
            config: 包含阈值配置的字典
        """
        with self._lock:
            if 'fps' in config:
                self._fps = FPSThresholds(**config['fps'])
            if 'memory' in config:
                self._memory = MemoryThresholds(**config['memory'])
            if 'cpu' in config:
                self._cpu = CPUThresholds(**config['cpu'])
            if 'network' in config:
                self._network = NetworkThresholds(**config['network'])
            self._save_if_needed()

    def save_to_file(self, path: Optional[str] = None):
        """保存阈值配置到文件

        Args:
            path: 文件路径，如果为None则使用初始化时的路径
        """
        save_path = path or self._config_path
        if not save_path:
            raise ValueError("未指定配置文件路径")

        with self._lock:
            config = self.to_dict()
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

    def load_from_file(self, path: str):
        """从文件加载阈值配置

        Args:
            path: 配置文件路径
        """
        with open(path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        with self._lock:
            self.load_from_dict(config)

    def _save_if_needed(self):
        """如果配置了文件路径，则自动保存"""
        if self._config_path:
            try:
                self.save_to_file()
            except Exception:
                # 静默失败，避免影响主流程
                pass

    def get_all_thresholds(self) -> Dict[str, Any]:
        """获取所有阈值的副本（线程安全）"""
        with self._lock:
            return {
                'fps': asdict(self._fps),
                'memory': asdict(self._memory),
                'cpu': asdict(self._cpu),
                'network': asdict(self._network)
            }

    def validate_thresholds(self) -> bool:
        """验证阈值配置是否合理

        Returns:
            True如果阈值配置有效
        """
        with self._lock:
            try:
                # FPS阈值验证
                assert 0 < self._fps.critical_fps < self._fps.warning_fps <= 60
                assert self._fps.jank_consecutive_count >= 1
                assert self._fps.big_jank_frame_time_ms > 0

                # 内存阈值验证
                assert self._memory.leak_growth_mb > 0
                assert self._memory.leak_time_window_minutes > 0
                assert self._memory.high_memory_mb > 0
                assert self._memory.monotonic_increase_samples >= 3

                # CPU阈值验证
                assert 0 <= self._cpu.high_app_cpu_percent <= 100
                assert 0 <= self._cpu.high_sys_cpu_percent <= 100
                assert 0 <= self._cpu.sustained_cpu_percent <= 100
                assert self._cpu.sustained_duration_seconds > 0
                assert self._cpu.moving_avg_window >= 2

                # 网络阈值验证
                assert self._network.timeout_seconds > 0
                assert self._network.zero_upload_threshold >= 1

                return True
            except (AssertionError, TypeError):
                return False
