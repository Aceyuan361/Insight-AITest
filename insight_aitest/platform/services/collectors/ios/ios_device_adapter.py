# -*- coding: utf-8 -*-
"""
iOS设备适配器 - 用于IOSAPM的简化版本

通过 IOSConnectionManager 管理连接（兼容 iOS 17+ tunnel）。
不直接调用 create_using_usbmux()，避免重复建立连接。
"""

from logzero import logger

from .connection_manager import IOSConnectionManager


class IOSDeviceAdapter:
    """iOS设备适配器（简化版，IOSAPM 内部使用）"""

    def __init__(self, device_id: str):
        self.device_id = device_id
        self._mgr: IOSConnectionManager | None = None

    def connect(self) -> bool:
        """连接到iOS设备（通过 IOSConnectionManager）"""
        try:
            self._mgr = IOSConnectionManager.get_instance(self.device_id)
            if not self._mgr.is_connected:
                self._mgr.connect()
            logger.info(f"iOS设备已连接: {self.device_id}")
            return True
        except Exception as e:
            logger.error(f"iOS设备连接失败: {e}")
            return False

    def disconnect(self):
        """断开设备连接（共享连接，仅清理本地引用）"""
        self._mgr = None
        logger.debug(f"iOS设备适配器引用已释放: {self.device_id}")
