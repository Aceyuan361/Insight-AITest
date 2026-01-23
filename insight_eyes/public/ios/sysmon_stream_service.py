# -*- coding: utf-8 -*-
"""
iOS Sysmon 流式监听服务

持续监听 iOS 设备的性能数据，并推送给频率控制层。

功能：
1. 保持持久的 DVT 连接
2. 后台线程持续接收 Sysmontap 数据
3. 监控连接状态，发出连接丢失/恢复信号
4. 自动重连机制

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License
"""

import socket
import threading
import time
from typing import Optional, Dict
from logzero import logger

from PyQt6.QtCore import QObject, pyqtSignal

from .metrics_throttle import MetricsThrottle


class SysmonStreamService(QObject):
    """iOS Sysmon 流式监听服务

    使用 pymobiledevice3 Python API 持续监听 iOS 设备的性能数据。
    数据通过 Throttle 层进行频率控制后，提供给 Collector 使用。
    """

    # 信号定义
    connection_lost = pyqtSignal(str)  # 连接丢失，参数为错误消息
    connection_restored = pyqtSignal()  # 连接恢复
    data_received = pyqtSignal()  # 接收到数据（用于调试）

    # 单例管理
    _instance_lock = threading.Lock()
    _instances: Dict[str, 'SysmonStreamService'] = {}

    def __init__(self, udid: Optional[str] = None):
        """初始化监听服务

        Args:
            udid: iOS 设备唯一标识符
        """
        super().__init__()

        self.udid = udid
        self._lock = threading.RLock()
        self._dvt = None
        self._is_connected = False
        self._is_monitoring = False
        self._stream_thread = None
        self._throttle: Optional[MetricsThrottle] = None

        # 连接状态监控
        self._last_data_time = 0.0
        self._data_timeout_seconds = 10.0  # 10秒无数据视为超时

        logger.debug(f"SysmonStreamService 初始化: UDID={udid or '默认'}")

    @classmethod
    def get_instance(cls, udid: Optional[str] = None) -> 'SysmonStreamService':
        """获取监听服务实例（单例模式）

        Args:
            udid: iOS 设备唯一标识符

        Returns:
            SysmonStreamService 实例
        """
        device_key = udid or 'default'

        with cls._instance_lock:
            if device_key not in cls._instances:
                cls._instances[device_key] = cls(udid)
            return cls._instances[device_key]

    def connect(self) -> bool:
        """建立到设备的 DVT 连接

        Returns:
            bool: 是否连接成功
        """
        with self._lock:
            if self._is_connected:
                return True

            try:
                from pymobiledevice3.lockdown import create_using_usbmux
                from pymobiledevice3.services.dvt.dvt_secure_socket_proxy import DvtSecureSocketProxyService

                logger.debug("===== SysmonStreamService: 建立 DVT 连接 =====")
                logger.debug(f"设备 UDID: {self.udid or '默认'}")

                # 创建 lockdown 连接
                if self.udid:
                    lockdown = create_using_usbmux(self.udid)
                else:
                    lockdown = create_using_usbmux()

                # 创建 DVT 服务
                self._dvt = DvtSecureSocketProxyService(lockdown)
                self._dvt.perform_handshake()

                self._is_connected = True
                logger.debug("✓ DVT 连接建立成功")

                return True

            except ImportError as e:
                logger.error(f"✗ 导入 pymobiledevice3 失败: {e}")
                return False
            except Exception as e:
                logger.error(f"✗ 建立 DVT 连接失败: {type(e).__name__}: {e}")
                self._cleanup()
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

        在后台线程中持续接收 Sysmontap 数据。
        """
        with self._lock:
            if self._is_monitoring:
                logger.warning("监听已在运行中")
                return

            if not self._is_connected:
                if not self.connect():
                    logger.error("无法启动监听：DVT 连接失败")
                    return

            self._is_monitoring = True
            self._stream_thread = threading.Thread(
                target=self._stream_loop,
                daemon=True,
                name=f"SysmonStream-{self.udid or 'default'}"
            )
            self._stream_thread.start()
            logger.info("✓ Sysmon 监听服务已启动")

    def stop_monitoring(self):
        """停止监听（非阻塞，立即返回）

        设置标志位让监听循环自动退出，不等待线程结束。
        线程会在下一个循环检查时自动退出。
        """
        with self._lock:
            if not self._is_monitoring:
                return

            # 设置标志位，让监听循环自动退出
            self._is_monitoring = False

            # 不等待线程结束，直接返回
            # 线程会在下一个循环检查 _is_monitoring 时自动退出
            logger.info("Sysmon 监听服务停止信号已发送")

    def disconnect(self):
        """断开连接"""
        self.stop_monitoring()

        with self._lock:
            self._cleanup()
            logger.debug("SysmonStreamService 连接已断开")

    def _cleanup(self):
        """清理资源"""
        try:
            if self._dvt:
                self._dvt.close()
                self._dvt = None
        except Exception as e:
            logger.debug(f"清理资源时出错: {e}")
        finally:
            self._is_connected = False
            self._last_data_time = 0.0

    def _stream_loop(self):
        """后台监听循环

        持续从 Sysmontap 接收数据，并推送给 Throttle 层。
        包含自动重连机制和连接状态监控。
        """
        consecutive_failures = 0
        MAX_CONSECUTIVE_FAILURES = 3
        RETRY_DELAY_SECONDS = 2.0

        logger.debug("监听循环已启动")

        while self._is_monitoring:
            try:
                from pymobiledevice3.services.dvt.instruments.sysmontap import Sysmontap

                # 设置 socket 超时避免无限阻塞
                old_timeout = socket.getdefaulttimeout()
                socket.setdefaulttimeout(5.0)

                try:
                    with Sysmontap(self._dvt) as tap:
                        # 连接成功，重置失败计数
                        consecutive_failures = 0
                        self._is_connected = True
                        self._last_data_time = time.time()

                        # 发出连接恢复信号
                        self.connection_restored.emit()

                        logger.debug("✓ Sysmontap 流已建立")

                        # 持续接收数据
                        for process_list in tap.iter_processes():
                            if not self._is_monitoring:
                                logger.debug("监听已停止，退出循环")
                                break

                            # 更新数据接收时间
                            self._last_data_time = time.time()

                            # 推送给 Throttle 层
                            if self._throttle and process_list:
                                self._throttle.on_raw_batch(process_list)
                                self.data_received.emit()

                finally:
                    socket.setdefaulttimeout(old_timeout)

            except (ConnectionError, OSError, socket.error) as e:
                consecutive_failures += 1
                error_str = str(e)

                # 检查是否是用户停止了监听
                if not self._is_monitoring:
                    logger.debug("监听已手动停止")
                    break

                logger.warning(f"监听异常 (第{consecutive_failures}次): {type(e).__name__}: {error_str}")

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
                    self.connection_lost.emit(error_msg)
                    logger.error(f"✗ 连接丢失: {error_msg}")
                    break

                # 等待后重试
                logger.debug(f"等待 {RETRY_DELAY_SECONDS} 秒后重试...")
                time.sleep(RETRY_DELAY_SECONDS)

            except Exception as e:
                logger.error(f"未预期的错误: {type(e).__name__}: {e}")
                consecutive_failures += 1

                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    self._is_connected = False
                    break

                time.sleep(RETRY_DELAY_SECONDS)

        logger.debug("监听循环已退出")

    def is_connected(self) -> bool:
        """检查是否已连接

        Returns:
            bool: 是否已连接到设备
        """
        with self._lock:
            return self._is_connected

    def is_monitoring(self) -> bool:
        """检查是否正在监听

        Returns:
            bool: 是否正在监听
        """
        with self._lock:
            return self._is_monitoring

    def is_receiving_data(self) -> bool:
        """检查是否正在接收数据

        Returns:
            bool: 最近 10 秒内是否有数据接收
        """
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
        self.disconnect()
