# -*- coding: utf-8 -*-
"""
设备管理数据模型
定义设备、应用等核心数据结构
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

# PyQt6 是可选依赖（仅桌面版需要）
try:
    from PyQt6.QtCore import QObject, pyqtSignal

    PYQT6_AVAILABLE = True
except ImportError:
    # Web 环境或未安装 PyQt6
    PYQT6_AVAILABLE = False

    # 创建占位符类以避免 ImportError
    class QObject:
        pass

    class pyqtSignal:
        def __init__(self, *args, **kwargs):
            pass


class Platform(Enum):
    """平台枚举"""

    ANDROID = "Android"
    IOS = "iOS"
    UNKNOWN = "Unknown"


class DeviceStatus(Enum):
    """设备状态枚举"""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    AUTHORIZING = "authorizing"  # 等待授权
    OFFLINE = "offline"
    UNAUTHORIZED = "unauthorized"
    RECONNECTING = "reconnecting"  # 重连中


class AppStatus(Enum):
    """应用状态枚举"""

    RUNNING = "running"
    STOPPED = "stopped"
    BACKGROUND = "background"


@dataclass
class AppInfo:
    """
    应用信息数据模型

    Attributes:
        package_name: 包名（Android）或Bundle ID（iOS）
        app_name: 应用显示名称
        pid: 进程ID（运行中的应用才有）
        is_running: 是否正在运行
        is_monitoring: 是否正在监控
        status: 应用状态
        uid: 用户ID（Android）
        version: 应用版本号
        memory_usage: 内存占用（MB）
        cpu_usage: CPU使用率
    """

    package_name: str
    app_name: str
    pid: Optional[int] = None
    is_running: bool = False
    is_monitoring: bool = False
    status: AppStatus = AppStatus.STOPPED
    uid: Optional[int] = None
    version: Optional[str] = None
    memory_usage: float = 0.0
    cpu_usage: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "package_name": self.package_name,
            "app_name": self.app_name,
            "pid": self.pid,
            "is_running": self.is_running,
            "is_monitoring": self.is_monitoring,
            "status": self.status.value,
            "uid": self.uid,
            "version": self.version,
            "memory_usage": self.memory_usage,
            "cpu_usage": self.cpu_usage,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppInfo":
        """从字典创建实例"""
        return cls(
            package_name=data.get("package_name", ""),
            app_name=data.get("app_name", ""),
            pid=data.get("pid"),
            is_running=data.get("is_running", False),
            is_monitoring=data.get("is_monitoring", False),
            status=AppStatus(data.get("status", AppStatus.STOPPED.value)),
            uid=data.get("uid"),
            version=data.get("version"),
            memory_usage=data.get("memory_usage", 0.0),
            cpu_usage=data.get("cpu_usage", 0.0),
        )


@dataclass
class DeviceInfo:
    """
    设备信息数据模型

    Attributes:
        device_id: 设备唯一标识符
        name: 设备名称
        platform: 平台类型
        model: 设备型号
        os_version: 操作系统版本
        battery_level: 电池电量百分比
        status: 设备连接状态
        apps: 设备上的应用列表
        last_update: 最后更新时间
        serial_number: 序列号
        manufacturer: 制造商
        network_type: 网络类型（4G/5G/Wi-Fi）
        temperature: 设备温度（摄氏度）
        is_monitoring: 是否正在监控
    """

    device_id: str
    name: str
    platform: Platform
    model: str
    os_version: str
    battery_level: int = 100
    status: DeviceStatus = DeviceStatus.CONNECTED
    apps: List[AppInfo] = field(default_factory=list)
    last_update: Optional[datetime] = None
    serial_number: Optional[str] = None
    manufacturer: Optional[str] = None
    network_type: str = "Unknown"
    temperature: float = 0.0
    is_monitoring: bool = False

    def __post_init__(self):
        """初始化后处理"""
        if self.last_update is None:
            self.last_update = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "device_id": self.device_id,
            "name": self.name,
            "platform": self.platform.value,
            "model": self.model,
            "os_version": self.os_version,
            "battery_level": self.battery_level,
            "status": self.status.value,
            "apps": [app.to_dict() for app in self.apps],
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "serial_number": self.serial_number,
            "manufacturer": self.manufacturer,
            "network_type": self.network_type,
            "temperature": self.temperature,
            "is_monitoring": self.is_monitoring,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeviceInfo":
        """从字典创建实例"""
        apps = [AppInfo.from_dict(app_data) for app_data in data.get("apps", [])]
        last_update = None
        if data.get("last_update"):
            try:
                last_update = datetime.fromisoformat(data["last_update"])
            except (ValueError, TypeError):
                pass

        return cls(
            device_id=data.get("device_id", ""),
            name=data.get("name", ""),
            platform=Platform(data.get("platform", Platform.UNKNOWN.value)),
            model=data.get("model", ""),
            os_version=data.get("os_version", ""),
            battery_level=data.get("battery_level", 100),
            status=DeviceStatus(data.get("status", DeviceStatus.DISCONNECTED.value)),
            apps=apps,
            last_update=last_update,
            serial_number=data.get("serial_number"),
            manufacturer=data.get("manufacturer"),
            network_type=data.get("network_type", "Unknown"),
            temperature=data.get("temperature", 0.0),
            is_monitoring=data.get("is_monitoring", False),
        )

    def get_running_apps(self) -> List[AppInfo]:
        """获取正在运行的应用列表"""
        return [app for app in self.apps if app.is_running]

    def find_app_by_package(self, package_name: str) -> Optional[AppInfo]:
        """根据包名查找应用"""
        for app in self.apps:
            if app.package_name == package_name:
                return app
        return None

    def update_app(self, app_info: AppInfo) -> bool:
        """
        更新应用信息

        Args:
            app_info: 应用信息

        Returns:
            bool: 是否成功更新
        """
        for i, app in enumerate(self.apps):
            if app.package_name == app_info.package_name:
                self.apps[i] = app_info
                self.last_update = datetime.now()
                return True
        return False

    def add_app(self, app_info: AppInfo) -> None:
        """添加应用到列表"""
        # 检查是否已存在
        existing = self.find_app_by_package(app_info.package_name)
        if existing:
            self.update_app(app_info)
        else:
            self.apps.append(app_info)
        self.last_update = datetime.now()

    def remove_app(self, package_name: str) -> bool:
        """
        从列表中移除应用

        Args:
            package_name: 包名

        Returns:
            bool: 是否成功移除
        """
        for i, app in enumerate(self.apps):
            if app.package_name == package_name:
                self.apps.pop(i)
                self.last_update = datetime.now()
                return True
        return False


@dataclass
class DeviceFilter:
    """
    设备过滤器

    Attributes:
        platform: 平台过滤（None表示不过滤）
        min_os_version: 最低系统版本（None表示不过滤）
        manufacturer: 制造商过滤（None表示不过滤）
        status: 状态过滤（None表示不过滤）
        search_text: 搜索文本（匹配设备名称或型号）
    """

    platform: Optional[Platform] = None
    min_os_version: Optional[str] = None
    manufacturer: Optional[str] = None
    status: Optional[DeviceStatus] = None
    search_text: Optional[str] = None

    def matches(self, device: DeviceInfo) -> bool:
        """
        检查设备是否匹配过滤器

        Args:
            device: 设备信息

        Returns:
            bool: 是否匹配
        """
        # 平台过滤
        if self.platform is not None and device.platform != self.platform:
            return False

        # 状态过滤
        if self.status is not None and device.status != self.status:
            return False

        # 制造商过滤
        if self.manufacturer is not None:
            if (
                device.manufacturer is None
                or self.manufacturer.lower() not in device.manufacturer.lower()
            ):
                return False

        # 系统版本过滤
        if self.min_os_version is not None:
            try:
                device_version = tuple(map(int, device.os_version.split(".")[:2]))
                filter_version = tuple(map(int, self.min_os_version.split(".")[:2]))
                if device_version < filter_version:
                    return False
            except (ValueError, AttributeError):
                return False

        # 文本搜索
        if self.search_text is not None and self.search_text.strip():
            search_lower = self.search_text.lower()
            name_match = device.name.lower().find(search_lower) != -1
            model_match = device.model.lower().find(search_lower) != -1
            if not (name_match or model_match):
                return False

        return True


@dataclass
class AppFilter:
    """
    应用过滤器

    Attributes:
        is_running: 是否只显示运行中的应用
        status: 状态过滤（None表示不过滤）
        search_text: 搜索文本（匹配应用名称或包名）
    """

    is_running: bool = False
    status: Optional[AppStatus] = None
    search_text: Optional[str] = None

    def matches(self, app: AppInfo) -> bool:
        """
        检查应用是否匹配过滤器

        Args:
            app: 应用信息

        Returns:
            bool: 是否匹配
        """
        # 运行状态过滤
        if self.is_running and not app.is_running:
            return False

        # 状态过滤
        if self.status is not None and app.status != self.status:
            return False

        # 文本搜索
        if self.search_text is not None and self.search_text.strip():
            search_lower = self.search_text.lower()
            name_match = app.app_name.lower().find(search_lower) != -1
            package_match = app.package_name.lower().find(search_lower) != -1
            if not (name_match or package_match):
                return False

        return True


@dataclass
class MonitoringConfig:
    """
    监控配置

    Attributes:
        sample_interval: 采样间隔（毫秒）
        enable_cpu: 是否启用CPU监控
        enable_memory: 是否启用内存监控
        enable_fps: 是否启用FPS监控
        enable_network: 是否启用网络监控
        enable_battery: 是否启用电池监控
        buffer_size: 环形缓冲区大小
    """

    sample_interval: int = 1000  # 默认1秒
    enable_cpu: bool = True
    enable_memory: bool = True
    enable_fps: bool = True
    enable_network: bool = True
    enable_battery: bool = True
    buffer_size: int = 1000  # 缓存最近1000条数据

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "sample_interval": self.sample_interval,
            "enable_cpu": self.enable_cpu,
            "enable_memory": self.enable_memory,
            "enable_fps": self.enable_fps,
            "enable_network": self.enable_network,
            "enable_battery": self.enable_battery,
            "buffer_size": self.buffer_size,
        }


@dataclass
class ReconnectConfig:
    """
    重连配置

    Attributes:
        enable_auto_reconnect: 是否启用自动重连
        max_retry_count: 最大重试次数（0表示无限重试）
        initial_retry_interval: 初始重试间隔（秒）
        max_retry_interval: 最大重试间隔（秒）
        retry_multiplier: 重试间隔倍数（指数退避）
        enable_heartbeat: 是否启用心跳检测
        heartbeat_interval: 心跳检测间隔（秒）
        heartbeat_timeout: 心跳超时时间（秒）
    """

    enable_auto_reconnect: bool = True
    max_retry_count: int = 10  # 默认最多重试10次
    initial_retry_interval: int = 1  # 初始1秒
    max_retry_interval: int = 60  # 最大60秒
    retry_multiplier: float = 2.0  # 每次间隔翻倍
    enable_heartbeat: bool = True
    heartbeat_interval: int = 5  # 每5秒检测一次
    heartbeat_timeout: int = 15  # 15秒无响应认为断开

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "enable_auto_reconnect": self.enable_auto_reconnect,
            "max_retry_count": self.max_retry_count,
            "initial_retry_interval": self.initial_retry_interval,
            "max_retry_interval": self.max_retry_interval,
            "retry_multiplier": self.retry_multiplier,
            "enable_heartbeat": self.enable_heartbeat,
            "heartbeat_interval": self.heartbeat_interval,
            "heartbeat_timeout": self.heartbeat_timeout,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReconnectConfig":
        """从字典创建实例"""
        return cls(
            enable_auto_reconnect=data.get("enable_auto_reconnect", True),
            max_retry_count=data.get("max_retry_count", 10),
            initial_retry_interval=data.get("initial_retry_interval", 1),
            max_retry_interval=data.get("max_retry_interval", 60),
            retry_multiplier=data.get("retry_multiplier", 2.0),
            enable_heartbeat=data.get("enable_heartbeat", True),
            heartbeat_interval=data.get("heartbeat_interval", 5),
            heartbeat_timeout=data.get("heartbeat_timeout", 15),
        )


@dataclass
class ReconnectState:
    """
    重连状态

    Attributes:
        device_id: 设备ID
        retry_count: 当前重试次数
        last_retry_time: 最后重试时间
        current_interval: 当前重试间隔
        is_reconnecting: 是否正在重连
        cancelled: 是否已取消重连
        error_message: 错误信息
    """

    device_id: str
    retry_count: int = 0
    last_retry_time: Optional[datetime] = None
    current_interval: int = 1
    is_reconnecting: bool = False
    cancelled: bool = False
    error_message: Optional[str] = None

    def __post_init__(self):
        """初始化后处理"""
        if self.last_retry_time is None:
            self.last_retry_time = datetime.now()

    def reset(self):
        """重置重连状态"""
        self.retry_count = 0
        self.last_retry_time = datetime.now()
        self.current_interval = 1
        self.is_reconnecting = False
        self.cancelled = False
        self.error_message = None

    def increment_retry(self, max_interval: int, multiplier: float):
        """
        增加重试次数并更新间隔

        Args:
            max_interval: 最大重试间隔
            multiplier: 间隔倍数
        """
        self.retry_count += 1
        self.last_retry_time = datetime.now()
        # 指数退避：current_interval = current_interval * multiplier
        self.current_interval = min(int(self.current_interval * multiplier), max_interval)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "device_id": self.device_id,
            "retry_count": self.retry_count,
            "last_retry_time": self.last_retry_time.isoformat() if self.last_retry_time else None,
            "current_interval": self.current_interval,
            "is_reconnecting": self.is_reconnecting,
            "cancelled": self.cancelled,
            "error_message": self.error_message,
        }


class DeviceChangeType(Enum):
    """设备变更类型"""

    ADDED = "added"
    REMOVED = "removed"
    UPDATED = "updated"


@dataclass
class DeviceChangeEvent:
    """
    设备变更事件

    Attributes:
        change_type: 变更类型
        device_info: 设备信息
        timestamp: 变更时间
    """

    change_type: DeviceChangeType
    device_info: DeviceInfo
    timestamp: datetime = field(default_factory=datetime.now)
