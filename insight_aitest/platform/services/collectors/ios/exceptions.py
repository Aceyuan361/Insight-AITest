# -*- coding: utf-8 -*-
"""
iOS 监控专用异常

定义 iOS 设备监控过程中可能出现的各种异常类型
"""

from typing import Optional


class IOSMonitorError(Exception):
    """iOS 监控基础异常"""

    def __init__(self, message: str, details: Optional[str] = None):
        """
        初始化异常

        Args:
            message: 错误消息
            details: 详细信息（可选）
        """
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self):
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


class DeviceNotTrustedError(IOSMonitorError):
    """设备未信任异常

    当 iOS 设备没有信任此电脑时抛出
    """

    def __init__(self, device_id: Optional[str] = None):
        message = "iOS 设备未信任此电脑"
        details = f"设备 ID: {device_id}" if device_id else None
        super().__init__(message, details)
        self.device_id = device_id

    def get_user_guide(self) -> str:
        """获取用户操作指南"""
        return """
设备未信任此电脑！

请按以下步骤操作：
1. 在 iOS 设备上解锁屏幕
2. 连接时会弹出"信任此电脑？"提示
3. 点击"信任"
4. 重新运行程序
        """.strip()


class DeviceNotFoundError(IOSMonitorError):
    """设备未找到异常

    当指定的 iOS 设备未连接时抛出
    """

    def __init__(self, device_id: Optional[str] = None):
        message = "iOS 设备未找到"
        details = f"设备 ID: {device_id}" if device_id else None
        super().__init__(message, details)
        self.device_id = device_id


class DeviceConnectionError(IOSMonitorError):
    """设备连接异常

    当无法连接到 iOS 设备时抛出
    """

    def __init__(self, device_id: str, reason: Optional[str] = None):
        message = "无法连接到 iOS 设备"
        details = f"设备 ID: {device_id}" + (f", 原因: {reason}" if reason else "")
        super().__init__(message, details)
        self.device_id = device_id
        self.reason = reason


class DeveloperModeNotEnabledError(IOSMonitorError):
    """开发者模式未启用异常

    当 iOS 设备未启用开发者模式时抛出
    """

    def __init__(self):
        super().__init__("iOS 设备未启用开发者模式")

    def get_user_guide(self) -> str:
        """获取用户操作指南"""
        return """
开发者模式未启用！

请按以下步骤操作：
1. 在 iOS 设备上打开：设置 > 隐私与安全 > 开发者模式
2. 启用开发者模式
3. 重启设备
4. 重新运行程序
        """.strip()


class ApplicationNotFoundError(IOSMonitorError):
    """应用未找到异常

    当指定的应用未在设备上运行时抛出
    """

    def __init__(self, bundle_id: str):
        message = "应用未找到或未运行"
        details = f"Bundle ID: {bundle_id}"
        super().__init__(message, details)
        self.bundle_id = bundle_id


class PMD3NotInstalledError(IOSMonitorError):
    """pymobiledevice3 未安装异常

    当 pymobiledevice3 库未安装时抛出
    """

    def __init__(self):
        super().__init__("pymobiledevice3 未安装")

    def get_install_command(self) -> str:
        """获取安装命令"""
        return "pip install pymobiledevice3"


class CollectionTimeoutError(IOSMonitorError):
    """采集超时异常

    当数据采集超时时抛出
    """

    def __init__(self, metric_name: str, timeout: float):
        message = f"{metric_name} 采集超时"
        details = f"指标: {metric_name}, 超时时间: {timeout}秒"
        super().__init__(message, details)
        self.metric_name = metric_name
        self.timeout = timeout


class InvalidBundleIdError(IOSMonitorError):
    """无效的 Bundle ID 异常

    当 Bundle ID 格式无效时抛出
    """

    def __init__(self, bundle_id: str):
        message = "无效的 Bundle ID 格式"
        details = f"Bundle ID: {bundle_id}"
        super().__init__(message, details)
        self.bundle_id = bundle_id


class ProcessNotFoundError(IOSMonitorError):
    """进程未找到异常

    当启动监控时，目标应用的进程不存在时抛出。

    这与 ApplicationNotFoundError 不同：
    - ApplicationNotFoundError: 运行时发现应用未运行
    - ProcessNotFoundError: 启动监控前检测到进程不存在
    """

    def __init__(self, bundle_id: str, device_id: str = None):
        message = "未找到目标应用进程"
        details = f"Bundle ID: {bundle_id}"
        if device_id:
            details += f"\n设备: {device_id}"
        super().__init__(message, details)
        self.bundle_id = bundle_id
        self.device_id = device_id

    def get_user_guide(self) -> str:
        """获取用户操作指南"""
        return f"""
未找到目标应用进程！

Bundle ID: {self.bundle_id}

请确认：
  ✓ 应用是否正在运行
  ✓ Bundle ID 是否正确
  ✓ 设备是否已信任电脑
  ✓ 是否已启用开发者模式

提示：在 iOS 设备上打开应用后，再开始监控。
        """.strip()
