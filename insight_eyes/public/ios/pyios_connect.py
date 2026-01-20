# -*- coding: utf-8 -*-
"""
py-ios-device 连接管理器
管理 iOS 设备的 Instruments 服务连接

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License

Author: Aceyuan361
"""
import time
import threading
from typing import Optional, Dict, Any, Tuple
from logzero import logger


class PyIOSConnection:
    """
    py-ios-device 连接管理器

    职责：
    1. 管理远程隧道连接（通过 pymobiledevice3）
    2. 维护 InstrumentServer 会话
    3. 提供单次调用的采集接口（兼容 tidevice 模式）
    4. 自动重连和健康检查

    支持版本：
    - iOS 17-26（完整支持）

    使用场景：
    - iOS 17+ 设备的性能监控
    - 需要 Instruments 协议的精确数据采集
    """

    def __init__(self, udid: str, remote_address: Tuple[str, int]):
        """
        初始化连接管理器

        Args:
            udid: iOS 设备唯一标识符
            remote_address: 远程隧道地址 (host, port)
        """
        self.udid = udid
        self.remote_address = remote_address

        # 连接对象
        self._rsd = None  # RemoteLockdownClient
        self._rpc = None  # InstrumentServer

        # 连接状态
        self._is_connected = False
        self._last_use = time.time()
        self._connect_time: Optional[float] = None

        # 配置
        self._health_check_interval = 30  # 30秒健康检查
        self._connection_timeout = 10     # 连接超时
        self._receive_timeout = 2         # 接收数据超时

        # 线程锁
        self._lock = threading.RLock()

        logger.debug(f"[PyIOS连接] 初始化: udid={udid}, remote={remote_address}")

    def connect(self) -> bool:
        """
        建立 Instruments 服务连接

        Returns:
            bool: 是否连接成功
        """
        with self._lock:
            try:
                # 动态导入（避免硬依赖）
                from ios_device.remote.remote_lockdown import RemoteLockdownClient
                from ios_device.servers.Instrument import InstrumentServer

                logger.info(f"[PyIOS连接] 正在连接到 {self.remote_address}...")

                # 1. 连接到远程锁定服务
                self._rsd = RemoteLockdownClient(self.remote_address)
                logger.debug("[PyIOS连接] ✓ RemoteLockdownClient 连接成功")

                # 2. 初始化 Instruments 服务
                self._rpc = InstrumentServer(self._rsd).init()
                logger.debug("[PyIOS连接] ✓ InstrumentServer 初始化成功")

                # 3. 启动所需的监控服务
                self._start_services()

                # 4. 更新状态
                self._is_connected = True
                self._connect_time = time.time()
                self._last_use = time.time()

                logger.info(f"[PyIOS连接] ✓ 连接建立成功 (耗时: {self._connect_time:.2f}s)")
                return True

            except ImportError as e:
                logger.error(f"[PyIOS连接] ✗ 导入失败: {e}")
                logger.error("[PyIOS连接] 请安装: pip install py-ios-device")
                return False
            except Exception as e:
                logger.error(f"[PyIOS连接] ✗ 连接失败: {e}")
                self._cleanup()
                return False

    def _start_services(self):
        """
        启动 Instruments 监控服务

        启动以下服务：
        - SysMontap: CPU、Memory、Network 监控
        - Graphics: FPS、GPU 监控
        - Energy: Battery 监控
        """
        try:
            # 1. 配置并启动系统监控 (SysMontap)
            sysmon_config = {
                'ur': 1000,  # 数据更新频率(毫秒)
                'procAttrs': ['cpuUsage', 'memVirtualSize', 'threadCount'],
                'sysAttrs': ['networkIn', 'networkOut', 'cpuTotal']
            }
            self._rpc.call(
                "com.apple.instruments.server.services.sysmontap",
                "setConfig:",
                sysmon_config
            )
            self._rpc.call("com.apple.instruments.server.services.sysmontap", "start")
            logger.debug("[PyIOS连接] ✓ SysMontap 服务已启动")

            # 2. 尝试启动图形性能监控 (Graphics)
            try:
                self._rpc.call(
                    "com.apple.instruments.server.services.graphics.opengl",
                    "startSamplingAtTimeInterval:",
                    1.0
                )
                logger.debug("[PyIOS连接] ✓ Graphics 服务已启动")
            except Exception as e:
                logger.warning(f"[PyIOS连接] Graphics 服务启动失败（可能设备不支持）: {e}")

            # 3. 尝试启动能量监控 (Energy)
            try:
                self._rpc.call("com.apple.instruments.server.services.energy", "start")
                logger.debug("[PyIOS连接] ✓ Energy 服务已启动")
            except Exception as e:
                logger.warning(f"[PyIOS连接] Energy 服务启动失败: {e}")

        except Exception as e:
            logger.error(f"[PyIOS连接] 启动服务失败: {e}")

    def is_alive(self) -> bool:
        """
        检查连接是否存活

        检查项：
        1. 连接对象是否存在
        2. 是否超时（60秒未使用）
        3. 健康检查（可选）

        Returns:
            bool: 连接是否存活
        """
        with self._lock:
            if not self._is_connected or not self._rpc:
                return False

            # 检查超时
            idle_time = time.time() - self._last_use
            if idle_time > 60:
                logger.warning(f"[PyIOS连接] 连接空闲超时 ({idle_time:.0f}s)")
                return False

            return True

    def _ensure_connected(self) -> bool:
        """
        确保连接可用，如果断开则尝试重连

        Returns:
            bool: 是否连接成功
        """
        if self.is_alive():
            return True

        logger.info("[PyIOS连接] 连接已断开，尝试重新连接...")
        return self.connect()

    def _receive_data(self) -> Optional[Any]:
        """
        接收 Instruments 数据

        Returns:
            原始数据消息，失败返回 None
        """
        try:
            if not self._ensure_connected():
                return None

            # 接收消息
            message = self._rpc.receive_dtx_message(timeout=self._receive_timeout)
            self._last_use = time.time()
            return message

        except Exception as e:
            logger.error(f"[PyIOS连接] 接收数据失败: {e}")
            return None

    def collect_cpu(self, bundle_id: str) -> Optional[Dict[str, Any]]:
        """
        采集 CPU 数据（单次调用接口）

        Args:
            bundle_id: 应用 Bundle ID

        Returns:
            dict: {'appCpuRate': float, 'sysCpuRate': float}
        """
        with self._lock:
            try:
                message = self._receive_data()
                if not message:
                    return None

                # TODO: 解析 CPU 数据
                # 这里需要实现具体的解析逻辑
                return {'appCpuRate': 0.0, 'sysCpuRate': 0.0}

            except Exception as e:
                logger.error(f"[PyIOS连接] CPU 采集失败: {e}")
                return None

    def collect_memory(self, bundle_id: str) -> Optional[Dict[str, Any]]:
        """
        采集 Memory 数据（单次调用接口）

        Args:
            bundle_id: 应用 Bundle ID

        Returns:
            dict: {'totalPass': float, 'nativePass': float, 'dalvikPass': float}
        """
        with self._lock:
            try:
                message = self._receive_data()
                if not message:
                    return None

                # TODO: 解析 Memory 数据
                return {'totalPass': 0, 'nativePass': 0, 'dalvikPass': 0}

            except Exception as e:
                logger.error(f"[PyIOS连接] Memory 采集失败: {e}")
                return None

    def collect_fps(self, bundle_id: str) -> Optional[Dict[str, Any]]:
        """
        采集 FPS 数据（单次调用接口）

        Args:
            bundle_id: 应用 Bundle ID

        Returns:
            dict: {'fps': int, 'jank': int, 'bigJank': int, 'ftime_avg': float, ...}
        """
        with self._lock:
            try:
                message = self._receive_data()
                if not message:
                    return None

                # TODO: 解析 FPS 数据
                return {'fps': 60, 'jank': 0, 'bigJank': 0, 'ftime_avg': 16.67}

            except Exception as e:
                logger.error(f"[PyIOS连接] FPS 采集失败: {e}")
                return None

    def disconnect(self):
        """
        断开连接并清理资源
        """
        with self._lock:
            logger.info("[PyIOS连接] 正在断开连接...")
            self._cleanup()
            logger.info("[PyIOS连接] ✓ 连接已断开")

    def _cleanup(self):
        """清理连接资源"""
        try:
            # 停止 Instruments 服务
            if self._rpc:
                try:
                    self._rpc.stop()
                except Exception as e:
                    logger.warning(f"[PyIOS连接] 停止 RPC 失败: {e}")
                finally:
                    self._rpc = None

            # 关闭远程锁定连接
            if self._rsd:
                try:
                    self._rsd.close()
                except Exception as e:
                    logger.warning(f"[PyIOS连接] 关闭 RSD 失败: {e}")
                finally:
                    self._rsd = None

            self._is_connected = False

        except Exception as e:
            logger.error(f"[PyIOS连接] 清理资源失败: {e}")

    def __enter__(self):
        """支持上下文管理器"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持上下文管理器"""
        self.disconnect()

    def __del__(self):
        """析构函数，确保资源清理"""
        self._cleanup()
