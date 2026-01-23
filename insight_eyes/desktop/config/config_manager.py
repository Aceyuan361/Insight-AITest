# -*- coding: utf-8 -*-
"""
配置管理器
负责应用程序配置的加载、保存和管理
"""

import json
import os
import threading
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from logzero import logger
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QMessageBox

from ..ui.utils.models import CollectionConfig, AlertLevel


@dataclass
class UIConfig:
    """UI配置"""
    # 窗口配置
    window_width: int = 1600
    window_height: int = 1000
    window_maximized: bool = False

    # 面板布局
    splitter_sizes: list = field(default_factory=lambda: [280, 840, 280])

    # 最近使用的项目
    recent_devices: list = field(default_factory=list)  # 最近连接的设备ID列表
    recent_apps: list = field(default_factory=list)  # 最近监控的应用列表

    # 显示设置
    show_grid_lines: bool = True
    auto_scroll: bool = True
    theme: str = "dark"  # dark, light


@dataclass
class DeviceConfig:
    """设备配置"""
    # 自动连接设置
    auto_connect_last_device: bool = False
    last_connected_device: Optional[str] = None

    # 自动监控设置
    auto_monitor_last_app: bool = False
    last_monitored_app: Optional[str] = None

    # 刷新设置
    auto_refresh_interval: int = 5000  # 设备列表自动刷新间隔(ms)
    auto_refresh_enabled: bool = False


@dataclass
class AppConfig:
    """应用程序完整配置"""
    # 版本信息
    config_version: str = "1.0.0"
    last_modified: str = field(default_factory=lambda: datetime.now().isoformat())

    # 采集配置
    collection: CollectionConfig = field(default_factory=CollectionConfig)

    # 阈值配置（包含在collection中，但单独列出便于访问）
    fps_threshold: int = 30
    memory_threshold_mb: int = 500
    cpu_threshold_percent: float = 80.0
    battery_threshold_temp: float = 45.0

    # UI配置
    ui: UIConfig = field(default_factory=UIConfig)

    # 设备配置
    device: DeviceConfig = field(default_factory=DeviceConfig)

    # 数据导出配置
    export_format: str = "csv"  # csv, json, xlsx
    export_directory: str = ""

    # 告警配置
    alert_enabled: bool = True
    alert_sound_enabled: bool = False
    alert_popup_enabled: bool = True
    alert_min_level: str = AlertLevel.WARNING.value  # 最低告警级别

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'config_version': self.config_version,
            'last_modified': self.last_modified,
            'collection': asdict(self.collection),
            'fps_threshold': self.fps_threshold,
            'memory_threshold_mb': self.memory_threshold_mb,
            'cpu_threshold_percent': self.cpu_threshold_percent,
            'battery_threshold_temp': self.battery_threshold_temp,
            'ui': asdict(self.ui),
            'device': asdict(self.device),
            'export_format': self.export_format,
            'export_directory': self.export_directory,
            'alert_enabled': self.alert_enabled,
            'alert_sound_enabled': self.alert_sound_enabled,
            'alert_popup_enabled': self.alert_popup_enabled,
            'alert_min_level': self.alert_min_level
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AppConfig':
        """从字典创建配置对象（带向后兼容性）"""
        # 处理 collection 配置，添加向后兼容性
        collection_data = data.get('collection', {})

        # 向后兼容：旧的 enable_network 字段
        if 'enable_network' in collection_data and 'enable_network_up' not in collection_data:
            collection_data['enable_network_up'] = collection_data['enable_network']
            collection_data['enable_network_down'] = collection_data['enable_network']

        # 清理未知字段（避免 __init__ 错误）
        valid_collection_fields = {
            'interval_ms', 'enable_cpu', 'enable_memory', 'enable_fps',
            'enable_network_up', 'enable_network_down', 'enable_gpu',
            'fps_threshold', 'memory_threshold_mb', 'cpu_threshold_percent',
            'data_retention_days', 'max_samples_per_chart'
        }
        collection_data = {k: v for k, v in collection_data.items() if k in valid_collection_fields}

        collection = CollectionConfig(**collection_data)
        ui = UIConfig(**data.get('ui', {}))
        device = DeviceConfig(**data.get('device', {}))

        return cls(
            config_version=data.get('config_version', '1.0.0'),
            last_modified=data.get('last_modified', datetime.now().isoformat()),
            collection=collection,
            fps_threshold=data.get('fps_threshold', 30),
            memory_threshold_mb=data.get('memory_threshold_mb', 500),
            cpu_threshold_percent=data.get('cpu_threshold_percent', 80.0),
            battery_threshold_temp=data.get('battery_threshold_temp', 45.0),
            ui=ui,
            device=device,
            export_format=data.get('export_format', 'csv'),
            export_directory=data.get('export_directory', ''),
            alert_enabled=data.get('alert_enabled', True),
            alert_sound_enabled=data.get('alert_sound_enabled', False),
            alert_popup_enabled=data.get('alert_popup_enabled', True),
            alert_min_level=data.get('alert_min_level', AlertLevel.WARNING.value)
        )


class ConfigManager(QObject):
    """
    配置管理器
    负责配置的加载、保存和线程安全访问
    """

    # 信号定义
    config_loaded = pyqtSignal(object)  # 配置加载完成
    config_saved = pyqtSignal(object)  # 配置保存完成
    config_changed = pyqtSignal(str, object)  # 配置变更 (key, value)

    _instance = None  # 单例实例
    _lock = threading.Lock()  # 线程安全锁
    _initialized_instances = set()  # 跟踪已初始化的实例（Windows + PyQt6 兼容性）

    def __new__(cls):
        """实现单例模式（懒加载，仅在需要时创建）"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ConfigManager, cls).__new__(cls)
                    # 不在这里设置 _initialized，避免 Windows + PyQt6 的兼容性问题
                    # __init__ 会使用 _initialized_instances 来检查
        return cls._instance

    def __init__(self):
        """初始化配置管理器"""
        # 检查是否已经初始化（使用类级别集合避免访问实例属性）
        # 注意：在 Windows + PyQt6 环境下，不能在 super().__init__() 前访问实例属性
        if id(self) in ConfigManager._initialized_instances:
            return

        # 检查 QApplication 是否存在
        from PyQt6.QtWidgets import QApplication
        if QApplication.instance() is None:
            raise RuntimeError(
                "ConfigManager 必须在 QApplication 创建之后初始化。"
                "请确保先创建 QApplication 实例。"
            )

        super().__init__()

        # 标记为已初始化（必须在 super().__init__() 之后）
        ConfigManager._initialized_instances.add(id(self))
        self._initialized = True

        # 配置目录和文件路径
        self.config_dir = Path.home() / '.insight-eye'
        self.config_file = self.config_dir / 'config.json'

        # 当前配置
        self._config: Optional[AppConfig] = None

        # 确保配置目录存在
        self._ensure_config_dir()

    def _ensure_config_dir(self):
        """确保配置目录存在"""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"创建配置目录失败: {e}")

    def get_default_config(self) -> AppConfig:
        """
        获取默认配置

        Returns:
            AppConfig: 默认配置对象
        """
        return AppConfig()

    def load_config(self, emit_signal: bool = True) -> AppConfig:
        """
        从文件加载配置

        Args:
            emit_signal: 是否发射配置加载信号，默认为True。
                         在初始化时可以设为False以避免信号问题。

        Returns:
            AppConfig: 加载的配置对象，如果加载失败则返回默认配置
        """
        with self._lock:
            try:
                if self.config_file.exists():
                    with open(self.config_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    self._config = AppConfig.from_dict(data)
                    logger.debug(f"配置已从 {self.config_file} 加载")
                else:
                    logger.debug("配置文件不存在，使用默认配置")
                    self._config = self.get_default_config()
                    # 自动保存默认配置（不发射信号，不获取锁因为已经持有）
                    self._save_config_no_signal(acquire_lock=False)

            except json.JSONDecodeError as e:
                logger.error(f"配置文件JSON解析失败: {e}，使用默认配置")
                self._config = self.get_default_config()
            except (IOError, OSError) as e:
                logger.error(f"配置文件读取失败: {e}，使用默认配置")
                self._config = self.get_default_config()
            except Exception as e:
                logger.error(f"加载配置失败: {e}，使用默认配置")
                self._config = self.get_default_config()

        # 在锁外发射信号，避免死锁
        if emit_signal:
            try:
                self.config_loaded.emit(self._config)
            except Exception as e:
                print(f"发射配置加载信号失败: {e}")

        return self._config

    def _save_config_no_signal(self, acquire_lock: bool = True) -> bool:
        """
        保存配置但不发射信号（内部使用）

        Args:
            acquire_lock: 是否需要获取锁，默认为True。
                         如果已经持有锁，则设为False以避免死锁。

        Returns:
            bool: 是否保存成功
        """
        def _do_save():
            if self._config is None:
                self._config = self.get_default_config()

            self._config.last_modified = datetime.now().isoformat()
            self._ensure_config_dir()

            # 原子化写入：使用临时文件 + 原子重命名
            # 这样可以避免写入过程中崩溃导致配置文件损坏
            temp_file = self.config_file.parent / (self.config_file.name + '.tmp')
            try:
                # 先写入临时文件
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(self._config.to_dict(), f, indent=4, ensure_ascii=False)
                    # 确保数据写入磁盘
                    f.flush()
                    os.fsync(f.fileno())

                # 原子重命名（跨平台）
                os.replace(temp_file, self.config_file)

                logger.debug(f"配置已保存到 {self.config_file}")
                return True
            except Exception as e:
                # 清理临时文件
                if os.path.exists(temp_file):
                    try:
                        os.unlink(temp_file)
                    except:
                        pass
                raise e

        if acquire_lock:
            with self._lock:
                try:
                    return _do_save()
                except Exception as e:
                    print(f"保存配置失败: {e}")
                    return False
        else:
            try:
                return _do_save()
            except Exception as e:
                print(f"保存配置失败: {e}")
                return False

    def save_config(self, config: Optional[AppConfig] = None) -> bool:
        """
        保存配置到文件

        Args:
            config: 要保存的配置对象，如果为None则保存当前配置

        Returns:
            bool: 是否保存成功
        """
        config_to_save = None
        success = False

        with self._lock:
            try:
                # 确定要保存的配置
                if config is not None:
                    self._config = config
                elif self._config is None:
                    self._config = self.get_default_config()

                # 更新修改时间
                self._config.last_modified = datetime.now().isoformat()

                # 确保配置目录存在
                self._ensure_config_dir()

                # 使用原子化写入（内部方法）
                success = self._save_config_no_signal(acquire_lock=False)

                if success:
                    config_to_save = self._config

            except Exception as e:
                print(f"保存配置失败: {e}")
                return False

        # 在锁外发射信号，避免死锁
        if success and config_to_save is not None:
            try:
                self.config_saved.emit(config_to_save)
            except Exception as e:
                print(f"发射配置保存信号失败: {e}")

        return success

    def get_config(self) -> AppConfig:
        """
        获取当前配置

        Returns:
            AppConfig: 当前配置对象
        """
        with self._lock:
            if self._config is None:
                self._config = self.load_config()
            return self._config

    def update_config(self, **kwargs) -> bool:
        """
        更新配置项

        Args:
            **kwargs: 要更新的配置项键值对

        Returns:
            bool: 是否更新成功

        Examples:
            config_manager.update_config(fps_threshold=40, memory_threshold_mb=600)
        """
        with self._lock:
            try:
                if self._config is None:
                    self._config = self.load_config()

                # 更新配置项
                for key, value in kwargs.items():
                    # 类型转换：Path 对象转为字符串
                    from pathlib import Path
                    if isinstance(value, Path):
                        value = str(value)

                    if hasattr(self._config, key):
                        setattr(self._config, key, value)
                        self.config_changed.emit(key, value)
                    elif hasattr(self._config.collection, key):
                        setattr(self._config.collection, key, value)
                        self.config_changed.emit(f'collection.{key}', value)
                    elif hasattr(self._config.ui, key):
                        setattr(self._config.ui, key, value)
                        self.config_changed.emit(f'ui.{key}', value)
                    elif hasattr(self._config.device, key):
                        setattr(self._config.device, key, value)
                        self.config_changed.emit(f'device.{key}', value)

                # 保存配置
                return self.save_config()

            except Exception as e:
                print(f"更新配置失败: {e}")
                return False

    def update_collection_config(self, config: CollectionConfig) -> bool:
        """
        更新采集配置

        Args:
            config: 新的采集配置

        Returns:
            bool: 是否更新成功
        """
        with self._lock:
            try:
                if self._config is None:
                    self._config = self.load_config()

                self._config.collection = config
                self._config.fps_threshold = config.fps_threshold
                self._config.memory_threshold_mb = config.memory_threshold_mb
                self._config.cpu_threshold_percent = config.cpu_threshold_percent
                self._config.battery_threshold_temp = config.battery_threshold_temp

                return self.save_config()

            except Exception as e:
                print(f"更新采集配置失败: {e}")
                return False

    def reset_to_default(self) -> bool:
        """
        重置为默认配置

        Returns:
            bool: 是否重置成功
        """
        with self._lock:
            try:
                self._config = self.get_default_config()
                return self.save_config()

            except Exception as e:
                print(f"重置配置失败: {e}")
                return False

    def export_config(self, file_path: str) -> bool:
        """
        导出配置到指定文件

        Args:
            file_path: 导出文件路径

        Returns:
            bool: 是否导出成功
        """
        with self._lock:
            try:
                if self._config is None:
                    self._config = self.load_config()

                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self._config.to_dict(), f, indent=4, ensure_ascii=False)

                print(f"配置已导出到 {file_path}")
                return True

            except Exception as e:
                print(f"导出配置失败: {e}")
                return False

    def import_config(self, file_path: str) -> bool:
        """
        从指定文件导入配置

        Args:
            file_path: 导入文件路径

        Returns:
            bool: 是否导入成功
        """
        with self._lock:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                self._config = AppConfig.from_dict(data)
                return self.save_config()

            except Exception as e:
                print(f"导入配置失败: {e}")
                return False

    def get_config_file_path(self) -> str:
        """
        获取配置文件路径

        Returns:
            str: 配置文件的绝对路径
        """
        return str(self.config_file.absolute())

    def backup_config(self) -> Optional[str]:
        """
        备份当前配置

        Returns:
            Optional[str]: 备份文件路径，如果备份失败则返回None
        """
        with self._lock:
            try:
                if self._config is None:
                    self._config = self.load_config()

                # 生成备份文件名
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_file = self.config_dir / f'config_backup_{timestamp}.json'

                # 保存备份
                with open(backup_file, 'w', encoding='utf-8') as f:
                    json.dump(self._config.to_dict(), f, indent=4, ensure_ascii=False)

                print(f"配置已备份到 {backup_file}")
                return str(backup_file.absolute())

            except Exception as e:
                print(f"备份配置失败: {e}")
                return None


# 全局配置管理器实例
_config_manager_instance: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """
    获取全局配置管理器实例（单例）

    Returns:
        ConfigManager: 配置管理器实例
    """
    global _config_manager_instance
    if _config_manager_instance is None:
        _config_manager_instance = ConfigManager()
    return _config_manager_instance
