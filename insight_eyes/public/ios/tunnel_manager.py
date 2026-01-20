# -*- coding: utf-8 -*-
"""
iOS 隧道管理器
管理 pymobiledevice3 远程隧道连接

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License

Author: Aceyuan361
"""
import subprocess
import time
import threading
from typing import Optional, Tuple, Dict, Any
from logzero import logger


class IOSTunnelManager:
    """
    iOS 隧道管理器

    职责：
    1. 管理 pymobiledevice3 隧道进程
    2. 启动和停止隧道
    3. 获取隧道地址（host, port）
    4. 隧道健康检查
    5. 自动重连

    使用场景：
    - iOS 17+ 设备需要通过隧道访问 Instruments 服务
    - 有线连接设备需要建立远程隧道
    - 支持多个设备同时建立隧道

    支持版本：
    - iOS 17-26（需要 pymobiledevice3）
    """

    def __init__(self, udid: str):
        """
        初始化隧道管理器

        Args:
            udid: iOS 设备唯一标识符
        """
        self.udid = udid

        # 隧道进程
        self._tunnel_process: Optional[subprocess.Popen] = None

        # 隧道状态
        self._is_running = False
        self._remote_address: Optional[Tuple[str, int]] = None
        self._start_time: Optional[float] = None

        # 配置
        self._tunnel_timeout = 30  # 隧道启动超时（秒）
        self._health_check_interval = 10  # 健康检查间隔（秒）
        self._max_retry_attempts = 3  # 最大重试次数

        # 线程锁
        self._lock = threading.RLock()

        # 健康检查线程
        self._health_check_thread: Optional[threading.Thread] = None
        self._stop_health_check = threading.Event()

        logger.debug(f"[iOS隧道] 初始化隧道管理器: udid={udid}")

    def start_tunnel(self) -> bool:
        """
        启动远程隧道

        使用 pymobiledevice3 启动远程隧道：
        1. 执行 `pymobiledevice3 tunneld` 命令
        2. 解析输出获取远程地址
        3. 验证隧道连接

        Returns:
            bool: 是否启动成功
        """
        with self._lock:
            if self._is_running:
                logger.warning(f"[iOS隧道] 隧道已在运行: {self.udid}")
                return True

            try:
                # 检查 pymobiledevice3 是否安装
                if not self._check_pymobiledevice3():
                    logger.error("[iOS隧道] pymobiledevice3 未安装")
                    logger.error("[iOS隧道] 请安装: pip install pymobiledevice3")
                    return False

                logger.info(f"[iOS隧道] 正在启动隧道: {self.udid}")

                # 启动隧道进程
                self._tunnel_process = subprocess.Popen(
                    ['pymobiledevice3', 'tunneld', '--udid', self.udid],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                # 等待隧道启动并获取地址
                self._remote_address = self._wait_for_tunnel_address()

                if self._remote_address:
                    self._is_running = True
                    self._start_time = time.time()

                    # 启动健康检查线程
                    self._start_health_check()

                    logger.info(f"[iOS隧道] ✓ 隧道启动成功: {self._remote_address}")
                    return True
                else:
                    logger.error("[iOS隧道] ✗ 无法获取隧道地址")
                    self._stop_tunnel_process()
                    return False

            except (ImportError, ModuleNotFoundError) as e:
                logger.error(f"[iOS隧道] ✗ 依赖库缺失: {e}")
                logger.error("[iOS隧道] 请安装: pip install pymobiledevice3")
                return False
            except FileNotFoundError:
                logger.error("[iOS隧道] ✗ pymobiledevice3 命令未找到")
                logger.error("[iOS隧道] 请安装: pip install pymobiledevice3")
                return False
            except Exception as e:
                logger.error(f"[iOS隧道] ✗ 启动失败: {e}")
                self._stop_tunnel_process()
                return False

    def stop_tunnel(self):
        """
        停止远程隧道
        """
        with self._lock:
            logger.info(f"[iOS隧道] 正在停止隧道: {self.udid}")

            # 停止健康检查
            self._stop_health_check.set()
            if self._health_check_thread:
                self._health_check_thread.join(timeout=2)
                self._health_check_thread = None

            # 停止隧道进程
            self._stop_tunnel_process()

            # 清理状态
            self._is_running = False
            self._remote_address = None
            self._start_time = None
            self._stop_health_check.clear()

            logger.info(f"[iOS隧道] ✓ 隧道已停止: {self.udid}")

    def get_remote_address(self) -> Optional[Tuple[str, int]]:
        """
        获取远程隧道地址

        Returns:
            (host, port) 元组，如果隧道未运行返回 None
        """
        with self._lock:
            return self._remote_address

    def is_running(self) -> bool:
        """
        检查隧道是否运行中

        Returns:
            bool: 隧道是否运行
        """
        with self._lock:
            return self._is_running

    def is_alive(self) -> bool:
        """
        检查隧道是否存活

        检查项：
        1. 进程是否存在
        2. 隧道是否运行
        3. 进程是否正常（未崩溃）

        Returns:
            bool: 隧道是否存活
        """
        with self._lock:
            if not self._is_running:
                return False

            if not self._tunnel_process:
                return False

            # 检查进程状态
            return self._tunnel_process.poll() is None

    def _check_pymobiledevice3(self) -> bool:
        """
        检查 pymobiledevice3 是否安装

        Returns:
            bool: 是否安装
        """
        try:
            result = subprocess.run(
                ['pymobiledevice3', '--version'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _wait_for_tunnel_address(self, timeout: float = 30.0) -> Optional[Tuple[str, int]]:
        """
        等待隧道启动并获取远程地址

        pymobiledevice3 tunneld 输出示例：
        "Starting tunnel on 127.0.0.1:12345..."

        Args:
            timeout: 超时时间（秒）

        Returns:
            (host, port) 元组，失败返回 None
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            if not self._tunnel_process:
                return None

            # 检查进程是否已退出
            if self._tunnel_process.poll() is not None:
                # 进程已退出，读取错误输出
                stderr = self._tunnel_process.stderr.read() if self._tunnel_process.stderr else ""
                logger.error(f"[iOS隧道] 隧道进程意外退出: {stderr}")
                return None

            # 尝试从输出中解析地址
            try:
                # 非阻塞读取
                line = self._tunnel_process.stdout.readline()
                if line:
                    logger.debug(f"[iOS隧道] 隧道输出: {line.strip()}")

                    # 解析地址
                    address = self._parse_tunnel_address(line)
                    if address:
                        return address
            except:
                pass

            time.sleep(0.5)

        logger.error(f"[iOS隧道] 等待隧道地址超时 ({timeout}s)")
        return None

    def _parse_tunnel_address(self, line: str) -> Optional[Tuple[str, int]]:
        """
        解析隧道地址

        支持的格式：
        - "Starting tunnel on 127.0.0.1:12345..."
        - "Tunnel started: 127.0.0.1:12345"

        Args:
            line: 输出行

        Returns:
            (host, port) 元组，解析失败返回 None
        """
        import re

        # 尝试匹配 IP:PORT 格式
        pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{2,5})'
        match = re.search(pattern, line)

        if match:
            host = match.group(1)
            port = int(match.group(2))
            logger.debug(f"[iOS隧道] 解析到隧道地址: {host}:{port}")
            return (host, port)

        return None

    def _start_health_check(self):
        """
        启动健康检查线程

        定期检查隧道状态，如果断开则尝试重连
        """
        self._stop_health_check.clear()
        self._health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True
        )
        self._health_check_thread.start()
        logger.debug("[iOS隧道] ✓ 健康检查线程已启动")

    def _health_check_loop(self):
        """
        健康检查循环

        定期检查隧道状态，如果断开则尝试重连
        """
        while not self._stop_health_check.is_set():
            try:
                time.sleep(self._health_check_interval)

                if self._stop_health_check.is_set():
                    break

                # 检查隧道是否存活
                if not self.is_alive():
                    logger.warning(f"[iOS隧道] 隧道断开: {self.udid}")

                    # 尝试重连
                    if self._is_running:
                        logger.info("[iOS隧道] 尝试重新建立隧道...")
                        self._stop_tunnel_process()

                        if self.start_tunnel():
                            logger.info("[iOS隧道] ✓ 隧道重连成功")
                        else:
                            logger.error("[iOS隧道] ✗ 隧道重连失败")
                            self._is_running = False

            except Exception as e:
                logger.error(f"[iOS隧道] 健康检查异常: {e}")

    def _stop_tunnel_process(self):
        """
        停止隧道进程
        """
        if self._tunnel_process:
            try:
                self._tunnel_process.terminate()
                self._tunnel_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._tunnel_process.kill()
            except Exception as e:
                logger.warning(f"[iOS隧道] 停止进程失败: {e}")
            finally:
                self._tunnel_process = None

    def __enter__(self):
        """支持上下文管理器"""
        self.start_tunnel()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持上下文管理器"""
        self.stop_tunnel()

    def __del__(self):
        """析构函数，确保资源清理"""
        self.stop_tunnel()
