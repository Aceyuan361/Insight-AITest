# -*- coding: utf-8 -*-
"""
iOS设备适配器 - 用于IOSAPM的简化版本

注意：这是Web版本的简化实现，仅用于IOSAPM内部使用。
不依赖desktop模块，直接使用pymobiledevice3。
"""

from logzero import logger


class IOSDeviceAdapter:
    """iOS设备适配器（简化版）"""

    def __init__(self, device_id: str):
        self.device_id = device_id
        self._lockdown = None

    def connect(self) -> bool:
        """连接到iOS设备"""
        try:
            from pymobiledevice3.lockdown import create_using_usbmux

            self._lockdown = create_using_usbmux(self.device_id)
            logger.info(f"iOS设备已连接: {self.device_id}")
            return True

        except Exception as e:
            logger.error(f"iOS设备连接失败: {e}")
            return False

    def disconnect(self):
        """断开设备连接"""
        if self._lockdown:
            try:
                self._lockdown.close()
                logger.debug(f"iOS设备已断开: {self.device_id}")
            except Exception as e:
                logger.debug(f"断开连接时出错: {e}")
            finally:
                self._lockdown = None
