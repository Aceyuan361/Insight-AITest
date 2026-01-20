# -*- coding: utf-8 -*-
"""
py-ios-device 采集器基类
提供数据采集的基础接口和通用功能

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License

Author: Aceyuan361
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from logzero import logger


class PyIOSCollectorBase(ABC):
    """
    py-ios-device 采集器基类

    职责：
    1. 定义采集器接口
    2. 提供通用数据解析方法
    3. 管理 Instruments 服务通信

    所有具体采集器都应该继承此类
    """

    def __init__(self, rpc_connection):
        """
        初始化采集器

        Args:
            rpc_connection: InstrumentServer RPC 连接对象
        """
        self._rpc = rpc_connection
        self._service_name = ""
        self._last_message = None

    @abstractmethod
    def configure(self) -> bool:
        """
        配置采集服务

        Returns:
            bool: 配置是否成功
        """
        pass

    @abstractmethod
    def start(self) -> bool:
        """
        启动采集服务

        Returns:
            bool: 启动是否成功
        """
        pass

    @abstractmethod
    def parse_message(self, message: Any) -> Optional[Dict[str, Any]]:
        """
        解析 Instruments 消息

        Args:
            message: 原始 DTX 消息

        Returns:
            dict: 解析后的数据
        """
        pass

    def receive_message(self, timeout: float = 2.0) -> Optional[Any]:
        """
        接收 Instruments 消息

        Args:
            timeout: 超时时间（秒）

        Returns:
            原始消息，失败返回 None
        """
        try:
            if not self._rpc:
                logger.warning(f"[{self._service_name}] RPC 连接不存在")
                return None

            message = self._rpc.receive_dtx_message(timeout=timeout)
            self._last_message = message
            return message

        except Exception as e:
            logger.error(f"[{self._service_name}] 接收消息失败: {e}")
            return None

    def call_service(self, method: str, *args) -> Any:
        """
        调用 Instruments 服务方法

        Args:
            method: 方法名
            *args: 方法参数

        Returns:
            方法返回值
        """
        try:
            if not self._rpc:
                logger.warning(f"[{self._service_name}] RPC 连接不存在")
                return None

            result = self._rpc.call(self._service_name, method, *args)
            return result

        except Exception as e:
            logger.error(f"[{self._service_name}] 调用服务方法失败: {method}: {e}")
            return None

    def validate_data(self, data: Dict[str, Any]) -> bool:
        """
        验证数据有效性

        Args:
            data: 待验证的数据

        Returns:
            bool: 数据是否有效
        """
        if not data:
            return False

        if not isinstance(data, dict):
            return False

        return True
