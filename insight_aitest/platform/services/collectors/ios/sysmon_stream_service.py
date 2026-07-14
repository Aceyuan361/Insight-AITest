# -*- coding: utf-8 -*-
"""
iOS Sysmon 流式监听服务 (pymobiledevice3 v9.x async API)

持续监听 iOS 设备的性能数据，并推送给频率控制层。

功能：
1. 在 IOSConnectionManager 的事件循环上运行 async DVT 流
2. 后台协程持续接收 Sysmontap 数据
3. 监控连接状态，发出连接丢失/恢复信号（Qt 信号跨线程安全）
4. 自动重连机制

pymobiledevice3 v9.x 变更：
- DvtSecureSocketProxyService → DvtProvider (async context manager)
- Sysmontap.__init__ → Sysmontap.create() (async factory)
- tap.iter_processes() → async generator
"""

import asyncio
import threading
import time
from typing import Optional, Dict
from logzero import logger

from PyQt6.QtCore import QObject, pyqtSignal

from .metrics_throttle import MetricsThrottle
from .connection_manager import IOSConnectionManager


class SysmonStreamService(QObject):
    """iOS Sysmon 流式监听服务

    使用 pymobiledevice3 v9.x async API 持续监听 iOS 设备的性能数据。
    数据通过 Throttle 层进行频率控制后，提供给 Collector 使用。

    流协程运行在 IOSConnectionManager 的 AsyncLoopThread 上，
    Qt 信号通过 loop.call_soon_threadsafe 跨线程安全发送。
    """

    # 信号定义
    connection_lost = pyqtSignal(str)  # 连接丢失，参数为错误消息
    connection_restored = pyqtSignal()  # 连接恢复
    data_received = pyqtSignal()  # 接收到数据（用于调试）

    # 单例管理
    _instance_lock = threading.Lock()
    _instances: Dict[str, "SysmonStreamService"] = {}

    def __init__(self, udid: Optional[str] = None):
        """初始化监听服务

        Args:
            udid: iOS 设备唯一标识符
        """
        super().__init__()

        self.udid = udid
        self._lock = threading.RLock()
        self._is_connected = False
        self._is_monitoring = False
        self._stream_task: Optional[asyncio.Future] = None
        self._throttle: Optional[MetricsThrottle] = None

        # 连接状态监控
        self._last_data_time = 0.0
        self._data_timeout_seconds = 10.0  # 10秒无数据视为超时

        logger.debug(f"SysmonStreamService 初始化: UDID={udid or '默认'}")

    @classmethod
    def get_instance(cls, udid: Optional[str] = None) -> "SysmonStreamService":
        """获取监听服务实例（单例模式）

        Args:
            udid: iOS 设备唯一标识符

        Returns:
            SysmonStreamService 实例
        """
        device_key = udid or "default"

        with cls._instance_lock:
            if device_key not in cls._instances:
                cls._instances[device_key] = cls(udid)
            return cls._instances[device_key]

    def connect(self) -> bool:
        """验证设备连接可用性（实际连接由 IOSConnectionManager 管理）

        Returns:
            bool: 是否连接成功
        """
        with self._lock:
            if self._is_connected:
                return True

            try:
                if not self.udid:
                    logger.warning("SysmonStreamService: 无 UDID，无法连接")
                    return False

                mgr = IOSConnectionManager.get_instance(self.udid)
                if not mgr.is_connected:
                    mgr.connect()

                self._is_connected = True
                logger.debug("✓ SysmonStreamService 连接就绪")
                return True

            except Exception as e:
                logger.error(f"✗ SysmonStreamService 连接失败: {type(e).__name__}: {e}")
                return False

    def set_throttle(self, throttle: MetricsThrottle):
        """设置频率控制层

        Args:
            throttle: MetricsThrottle 实例
        """
        with self._lock:
            self._throttle = throttle
            logger.debug("频率控制层已设置")

    def start_monitoring(self):
        """启动监听

        在 IOSConnectionManager 的事件循环上启动 async 流协程。
        """
        with self._lock:
            if self._is_monitoring:
                logger.warning("监听已在运行中")
                return

            if not self._is_connected:
                if not self.connect():
                    logger.error("无法启动监听：连接失败")
                    return

            self._is_monitoring = True

            # 在 ConnectionManager 的 AsyncLoopThread 上启动流协程
            mgr = IOSConnectionManager.get_instance(self.udid)
            self._stream_task = mgr.loop_thread.create_task(self._stream_coroutine())

            logger.info("✓ Sysmon 监听服务已启动")

    def stop_monitoring(self):
        """停止监听（非阻塞）

        取消 async 流协程。
        """
        with self._lock:
            if not self._is_monitoring:
                return

            self._is_monitoring = False

            # 取消流协程
            if self._stream_task is not None:
                try:
                    self._stream_task.cancel()
                except Exception:
                    pass
                self._stream_task = None

            logger.info("Sysmon 监听服务停止信号已发送")

    def disconnect(self):
        """断开连接"""
        self.stop_monitoring()

        with self._lock:
            self._is_connected = False
            self._last_data_time = 0.0
            logger.debug("SysmonStreamService 连接已断开")

    async def _stream_coroutine(self):
        """async 流协程：持续从 Sysmontap 接收数据。

        运行在 IOSConnectionManager 的 AsyncLoopThread 上。
        通过 loop.call_soon_threadsafe 安全发送 Qt 信号。
        """
        from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
        from pymobiledevice3.services.dvt.instruments.sysmontap import Sysmontap

        consecutive_failures = 0
        MAX_CONSECUTIVE_FAILURES = 3
        RETRY_DELAY_SECONDS = 2.0

        logger.debug("async 流协程已启动")

        while self._is_monitoring:
            try:
                mgr = IOSConnectionManager.get_instance(self.udid)
                lockdown = mgr.get_async_lockdown()

                async with DvtProvider(lockdown) as dvt:
                    tap = await Sysmontap.create(dvt)
                    async with tap:
                        # 连接成功，重置失败计数
                        consecutive_failures = 0
                        self._is_connected = True
                        self._last_data_time = time.time()

                        # 安全发送 Qt 信号
                        mgr.loop_thread.call_soon_threadsafe(self.connection_restored.emit)

                        logger.debug("✓ Sysmontap 流已建立")

                        # 持续接收数据
                        async for process_list in tap.iter_processes():
                            if not self._is_monitoring:
                                logger.debug("监听已停止，退出循环")
                                break

                            # 更新数据接收时间
                            self._last_data_time = time.time()

                            # 推送给 Throttle 层
                            if self._throttle and process_list:
                                self._throttle.on_raw_batch(process_list)
                                mgr.loop_thread.call_soon_threadsafe(self.data_received.emit)

            except asyncio.CancelledError:
                logger.info("async 流协程已取消")
                raise

            except Exception as e:
                consecutive_failures += 1
                error_str = str(e)

                # 检查是否是用户停止了监听
                if not self._is_monitoring:
                    logger.debug("监听已手动停止")
                    break

                logger.warning(
                    f"监听异常 (第{consecutive_failures}次): {type(e).__name__}: {error_str}"
                )

                # 连续失败达到阈值，判定为连接丢失
                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    self._is_connected = False

                    error_msg = (
                        f"设备连接中断\n\n"
                        f"错误信息: {error_str}\n\n"
                        f"可能原因:\n"
                        f"  • USB 线松动或断开\n"
                        f"  • 设备已锁屏\n"
                        f"  • 信任证书失效\n"
                        f"  • 设备重启\n\n"
                        f"请检查设备连接后重新开始监控"
                    )

                    mgr = IOSConnectionManager.get_instance(self.udid)
                    mgr.loop_thread.call_soon_threadsafe(self.connection_lost.emit, error_msg)
                    logger.error(f"✗ 连接丢失: {error_msg}")
                    break

                # 等待后重试
                logger.debug(f"等待 {RETRY_DELAY_SECONDS} 秒后重试...")
                await asyncio.sleep(RETRY_DELAY_SECONDS)

        logger.debug("async 流协程已退出")

    def is_connected(self) -> bool:
        """检查是否已连接"""
        with self._lock:
            return self._is_connected

    def is_monitoring(self) -> bool:
        """检查是否正在监听"""
        with self._lock:
            return self._is_monitoring

    def is_receiving_data(self) -> bool:
        """检查是否正在接收数据"""
        return time.time() - self._last_data_time < self._data_timeout_seconds

    @classmethod
    def shutdown_all(cls):
        """关闭所有实例的监听"""
        with cls._instance_lock:
            for instance in list(cls._instances.values()):
                instance.disconnect()
            cls._instances.clear()
            logger.debug("所有 SysmonStreamService 实例已关闭")

    def __del__(self):
        """析构函数，确保资源清理"""
        try:
            self.disconnect()
        except Exception:
            pass
