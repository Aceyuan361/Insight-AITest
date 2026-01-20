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

        # 采集器缓存（优化：避免重复创建和配置）
        self._sysmontap_collector: Optional['SysMontapCollector'] = None
        self._graphics_collector: Optional['GraphicsCollector'] = None
        self._energy_collector: Optional['EnergyCollector'] = None
        self._current_bundle_id: Optional[str] = None

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

            except (ImportError, ModuleNotFoundError) as e:
                logger.error(f"[PyIOS连接] ✗ 依赖库缺失: {e}")
                logger.error("[PyIOS连接] 请安装: pip install py-ios-device pymobiledevice3")
                return False
            except (ConnectionError, OSError) as e:
                logger.error(f"[PyIOS连接] ✗ 网络连接失败: {e}")
                self._cleanup()
                return False
            except Exception as e:
                logger.error(f"[PyIOS连接] ✗ 连接失败（未知错误）: {type(e).__name__}: {e}")
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

    def _get_or_create_collectors(self, bundle_id: str) -> Tuple['SysMontapCollector', 'GraphicsCollector', 'EnergyCollector']:
        """
        获取或创建采集器（懒加载 + 单例模式）

        优化策略：
        1. 如果 Bundle ID 变更，停止旧采集器并创建新的
        2. 如果采集器已存在，直接复用（避免重复配置和启动）
        3. 仅在首次创建时配置和启动服务

        Args:
            bundle_id: 应用 Bundle ID

        Returns:
            (SysMontapCollector, GraphicsCollector, EnergyCollector) 元组
        """
        # 检查是否需要重新创建采集器
        if self._current_bundle_id != bundle_id:
            logger.debug(f"[PyIOS连接] Bundle ID 变更: {self._current_bundle_id} -> {bundle_id}")

            # 停止旧采集器
            if self._sysmontap_collector:
                try:
                    self._sysmontap_collector.stop()
                except Exception as e:
                    logger.warning(f"[PyIOS连接] 停止 SysMontap 采集器失败: {e}")
                self._sysmontap_collector = None

            if self._graphics_collector:
                try:
                    self._graphics_collector.stop()
                except Exception as e:
                    logger.warning(f"[PyIOS连接] 停止 Graphics 采集器失败: {e}")
                self._graphics_collector = None

            if self._energy_collector:
                try:
                    self._energy_collector.stop()
                except Exception as e:
                    logger.warning(f"[PyIOS连接] 停止 Energy 采集器失败: {e}")
                self._energy_collector = None

            # 创建新采集器
            from .pyios_collectors.sysmontap import SysMontapCollector
            from .pyios_collectors.graphics import GraphicsCollector
            from .pyios_collectors.energy import EnergyCollector

            self._sysmontap_collector = SysMontapCollector(self._rpc, bundle_id)
            self._graphics_collector = GraphicsCollector(self._rpc, bundle_id)
            self._energy_collector = EnergyCollector(self._rpc, bundle_id)

            # 配置并启动（仅一次）
            if self._sysmontap_collector.configure():
                self._sysmontap_collector.start()
            if self._graphics_collector.configure():
                self._graphics_collector.start()
            if self._energy_collector.configure():
                self._energy_collector.start()

            self._current_bundle_id = bundle_id
            logger.debug(f"[PyIOS连接] ✓ 采集器已创建并启动: {bundle_id}")

        return self._sysmontap_collector, self._graphics_collector, self._energy_collector

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
                if not self._ensure_connected():
                    return None

                # 使用缓存采集器（避免重复配置和启动）
                sysmontap, _, _ = self._get_or_create_collectors(bundle_id)

                # 采集数据
                cpu_data = sysmontap.collect_cpu()

                # 使用数据规范化器
                from .data_normalizer import IOSDataNormalizer
                normalized = IOSDataNormalizer.normalize_cpu(cpu_data)

                return normalized

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
                if not self._ensure_connected():
                    return None

                # 使用缓存采集器（避免重复配置和启动）
                sysmontap, _, _ = self._get_or_create_collectors(bundle_id)

                # 采集数据
                mem_data = sysmontap.collect_memory()

                # 使用数据规范化器
                from .data_normalizer import IOSDataNormalizer
                normalized = IOSDataNormalizer.normalize_memory(mem_data)

                return normalized

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
                if not self._ensure_connected():
                    return None

                # 使用缓存采集器（避免重复配置和启动）
                _, graphics, _ = self._get_or_create_collectors(bundle_id)

                # 采集数据
                fps_data = graphics.collect_fps()

                # 使用数据规范化器
                from .data_normalizer import IOSDataNormalizer
                normalized = IOSDataNormalizer.normalize_fps(fps_data)

                return normalized

            except Exception as e:
                logger.error(f"[PyIOS连接] FPS 采集失败: {e}")
                return None

    def collect_battery(self, bundle_id: str) -> Optional[Dict[str, Any]]:
        """
        采集 Battery 数据（单次调用接口）

        Args:
            bundle_id: 应用 Bundle ID

        Returns:
            dict: {
                'level': int,
                'temperature': float,
                'current': int,
                'voltage': float,
                'power': float,
                'status': str
            }
        """
        with self._lock:
            try:
                if not self._ensure_connected():
                    return None

                # 使用缓存采集器（避免重复配置和启动）
                _, _, energy = self._get_or_create_collectors(bundle_id)

                # 采集数据
                battery_data = energy.collect_battery()

                # 使用数据规范化器
                from .data_normalizer import IOSDataNormalizer
                normalized = IOSDataNormalizer.normalize_battery(battery_data)

                return normalized

            except Exception as e:
                logger.error(f"[PyIOS连接] Battery 采集失败: {e}")
                return None

    def collect_gpu(self, bundle_id: str) -> Optional[Dict[str, Any]]:
        """
        采集 GPU 数据（单次调用接口）

        Args:
            bundle_id: 应用 Bundle ID

        Returns:
            dict: {
                'gpu': int,
                'gpu_freq': int,
                'gpu_vendor': str,
                'gpu_model': str
            }
        """
        with self._lock:
            try:
                if not self._ensure_connected():
                    return None

                # 使用缓存采集器（避免重复配置和启动）
                _, graphics, _ = self._get_or_create_collectors(bundle_id)

                # 采集数据
                gpu_data = graphics.collect_gpu()

                # 使用数据规范化器
                from .data_normalizer import IOSDataNormalizer
                normalized = IOSDataNormalizer.normalize_gpu(gpu_data)

                return normalized

            except Exception as e:
                logger.error(f"[PyIOS连接] GPU 采集失败: {e}")
                return None

    def disconnect(self):
        """
        断开连接并清理资源
        """
        with self._lock:
            logger.info("[PyIOS连接] 正在断开连接...")

            # 停止所有采集器
            if self._sysmontap_collector:
                try:
                    self._sysmontap_collector.stop()
                    logger.debug("[PyIOS连接] ✓ SysMontap 采集器已停止")
                except Exception as e:
                    logger.warning(f"[PyIOS连接] 停止 SysMontap 采集器失败: {e}")
                self._sysmontap_collector = None

            if self._graphics_collector:
                try:
                    self._graphics_collector.stop()
                    logger.debug("[PyIOS连接] ✓ Graphics 采集器已停止")
                except Exception as e:
                    logger.warning(f"[PyIOS连接] 停止 Graphics 采集器失败: {e}")
                self._graphics_collector = None

            if self._energy_collector:
                try:
                    self._energy_collector.stop()
                    logger.debug("[PyIOS连接] ✓ Energy 采集器已停止")
                except Exception as e:
                    logger.warning(f"[PyIOS连接] 停止 Energy 采集器失败: {e}")
                self._energy_collector = None

            self._current_bundle_id = None

            # 清理连接资源
            self._cleanup()
            logger.info("[PyIOS连接] ✓ 连接已断开")

    def _cleanup(self):
        """
        清理连接资源（增强版）

        确保所有资源都被正确清理，即使部分清理失败：
        1. 停止 Instruments 服务（_rpc）
        2. 关闭远程锁定连接（_rsd）
        3. 重置连接状态

        每个资源使用独立的 try-except 块，确保单个失败不影响其他清理
        """
        # 清理 RPC (Instruments 服务)
        rpc_cleanup_error = None
        if self._rpc is not None:
            try:
                logger.debug("[PyIOS连接] 正在停止 RPC 服务...")
                self._rpc.stop()
            except Exception as e:
                rpc_cleanup_error = e
                logger.warning(f"[PyIOS连接] 停止 RPC 失败: {type(e).__name__}: {e}")
            finally:
                # 确保 RPC 引用被清空（即使 stop() 失败）
                self._rpc = None
                logger.debug("[PyIOS连接] RPC 引用已清空")

        # 清理 RSD (远程锁定连接)
        rsd_cleanup_error = None
        if self._rsd is not None:
            try:
                logger.debug("[PyIOS连接] 正在关闭 RSD 连接...")
                self._rsd.close()
            except Exception as e:
                rsd_cleanup_error = e
                logger.warning(f"[PyIOS连接] 关闭 RSD 失败: {type(e).__name__}: {e}")
            finally:
                # 确保 RSD 引用被清空（即使 close() 失败）
                self._rsd = None
                logger.debug("[PyIOS连接] RSD 引用已清空")

        # 重置连接状态
        self._is_connected = False

        # 记录清理摘要
        if rpc_cleanup_error or rsd_cleanup_error:
            logger.warning(
                f"[PyIOS连接] 资源清理完成（存在错误）: "
                f"RPC错误={rpc_cleanup_error is not None}, "
                f"RSD错误={rsd_cleanup_error is not None}"
            )
        else:
            logger.debug("[PyIOS连接] ✓ 资源清理完成")

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
