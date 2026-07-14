# -*- coding: utf-8 -*-
"""
IOSConnectionManager — iOS 设备连接管理器（per-UDID 单例）

pymobiledevice3 >=9.x 中，iOS 17+ 设备无法直接通过 ``create_using_usbmux`` 连接，
必须先建立 CoreDevice tunnel，再通过 ``RemoteServiceDiscoveryService`` (RSD) 访问。

IOSConnectionManager 统一管理两种连接路径：

- **iOS <17**: ``create_using_usbmux(udid)`` → LockdownClient
- **iOS ≥17**: ``get_core_device_tunnel_services`` → ``start_tunnel`` → RSD

连接建立后，返回 ``SyncLockdownProxy`` 供同步代码使用。
对于需要原始 async 对象的场景（如 DVT 流式 sysmon），通过 ``get_async_lockdown()``
获取被包装的 ``LockdownServiceProvider``。

单例模式（per-UDID）：多个 collector 共享同一个连接，避免重复建立 tunnel。
"""

import asyncio
import threading
from typing import Optional, Any

from logzero import logger

from .async_loop import AsyncLoopThread
from .sync_proxy import SyncLockdownProxy

# 模块级导入（版本容忍，保证测试可 patch）
try:
    from pymobiledevice3 import usbmux as _usbmux_module
except ImportError:
    _usbmux_module = None

try:
    from pymobiledevice3.lockdown import create_using_usbmux as _create_using_usbmux
except ImportError:
    _create_using_usbmux = None

try:
    from pymobiledevice3.remote.tunnel_service import (
        start_tunnel as _start_tunnel,
        get_core_device_tunnel_services as _get_core_device_tunnel_services,
    )
except ImportError:
    _start_tunnel = None
    _get_core_device_tunnel_services = None

try:
    from pymobiledevice3.remote.remote_service_discovery import (
        RemoteServiceDiscoveryService as _RemoteServiceDiscoveryService,
    )
except ImportError:
    _RemoteServiceDiscoveryService = None

# 为测试暴露的名称（测试通过 patch 这些名称来 mock）
usbmux_list_devices = _usbmux_module.list_devices if _usbmux_module else None
create_using_usbmux = _create_using_usbmux
start_tunnel = _start_tunnel
get_core_device_tunnel_services = _get_core_device_tunnel_services
RemoteServiceDiscoveryService = _RemoteServiceDiscoveryService


class IOSConnectionManager:
    """iOS 设备连接管理器（per-UDID 单例）。

    自动检测 iOS 版本，选择 usbmux 或 tunnel 路径连接设备。
    对外提供同步接口（通过 SyncLockdownProxy）和 async 接口。
    """

    _instance_lock = threading.Lock()
    _instances: dict[str, "IOSConnectionManager"] = {}

    def __init__(self, udid: str) -> None:
        self.udid = udid
        self._loop_thread = AsyncLoopThread()

        # 连接状态
        self._lockdown: Optional[Any] = None  # 原始 async LockdownServiceProvider
        self._sync_proxy: Optional[SyncLockdownProxy] = None
        self._connected = False
        self._is_ios17_plus = False
        self._product_version: Optional[str] = None

        # tunnel 保活（仅 iOS 17+）
        self._tunnel_keeper_task: Optional[asyncio.Task] = None
        self._tunnel_rsd: Optional[Any] = None
        self._tunnel_ready = threading.Event()

        # 线程安全
        self._connect_lock = threading.Lock()

    @classmethod
    def get_instance(cls, udid: str) -> "IOSConnectionManager":
        """获取或创建 per-UDID 单例。"""
        with cls._instance_lock:
            if udid not in cls._instances:
                cls._instances[udid] = cls(udid)
            return cls._instances[udid]

    @classmethod
    def clear_instances(cls) -> None:
        """清除所有单例实例（测试用）。"""
        with cls._instance_lock:
            for mgr in cls._instances.values():
                try:
                    mgr.disconnect()
                except Exception:
                    pass
            cls._instances.clear()

    # ========== 版本检测 ==========

    @staticmethod
    def _parse_version(version_str: str) -> tuple[int, int, int]:
        """解析版本字符串为 (major, minor, patch)。"""
        parts = version_str.split(".")
        nums = []
        for p in parts[:3]:
            try:
                nums.append(int(p))
            except ValueError:
                nums.append(0)
        while len(nums) < 3:
            nums.append(0)
        return tuple(nums)  # type: ignore[return-value]

    @staticmethod
    def _check_ios17_plus(product_version: Optional[str]) -> bool:
        """判断 iOS 版本是否 >= 17.0。"""
        if not product_version:
            return False
        try:
            major = IOSConnectionManager._parse_version(product_version)[0]
            return major >= 17
        except (ValueError, IndexError):
            return False

    # ========== 连接 ==========

    def connect(self) -> bool:
        """连接设备（线程安全，自动检测版本选择路径）。

        Returns:
            bool: 是否连接成功
        """
        with self._connect_lock:
            if self._connected:
                return True

            # 启动事件循环线程
            if not self._loop_thread.is_running():
                self._loop_thread.start()

            # 通过事件循环执行 async 连接逻辑
            self._loop_thread.run_sync(self._connect_async())

            self._connected = True
            return True

    async def _connect_async(self) -> None:
        """异步连接逻辑：检测版本 → 选择路径。"""
        # Step 1: 确认设备存在
        if usbmux_list_devices is None:
            raise RuntimeError("pymobiledevice3 未安装")

        devices = await usbmux_list_devices()
        device_udids = [d.serial for d in devices]

        if self.udid not in device_udids:
            raise RuntimeError(f"设备未找到: {self.udid}")

        # Step 2: 通过 usbmux 获取版本号
        lockdown = await create_using_usbmux(self.udid)
        product_version = await lockdown.get_value(key="ProductVersion")
        self._product_version = product_version
        self._is_ios17_plus = self._check_ios17_plus(product_version)

        logger.info(
            f"iOS 设备 {self.udid}: version={product_version}, " f"ios17+={self._is_ios17_plus}"
        )

        if self._is_ios17_plus:
            # iOS 17+: 启动 tunnel，通过 RSD 连接
            # 先关闭临时的 usbmux lockdown
            try:
                await lockdown.close()
            except Exception:
                pass

            await self._start_tunnel_keeper()
            # tunnel keeper 会设置 self._tunnel_rsd
        else:
            # iOS <17: 直接使用 usbmux lockdown
            self._lockdown = lockdown

        # 创建同步代理
        async_lockdown = self._tunnel_rsd if self._is_ios17_plus else self._lockdown
        self._sync_proxy = SyncLockdownProxy(async_lockdown, self._loop_thread)

    async def _start_tunnel_keeper(self) -> None:
        """启动 tunnel keeper 后台协程（iOS 17+ 专用）。

        tunnel 必须在 ``async with start_tunnel(...)`` 块内保持存活，
        因此这个协程会一直阻塞直到 disconnect。
        """
        if get_core_device_tunnel_services is None:
            raise RuntimeError(
                "pymobiledevice3 版本不支持 tunnel（需要 >=9.0.0），" "无法连接 iOS 17+ 设备"
            )

        # 发现 tunnel 服务
        services = await get_core_device_tunnel_services(udid=self.udid)
        if not services:
            raise RuntimeError(
                f"未找到 iOS 17+ tunnel 服务: {self.udid}。"
                "请确保设备已信任电脑并启用 Developer Mode"
            )

        service = services[0]

        # tunnel keeper 作为后台 task 启动
        # 我们需要将 RSD 通过 event 传递出去
        self._tunnel_ready.clear()

        async def keeper():
            try:
                async with start_tunnel(service, protocol="tcp") as tunnel_result:
                    logger.info(
                        f"iOS 17+ tunnel 建立: {tunnel_result.address}:{tunnel_result.port}"
                    )
                    # 通过 tunnel 地址建立 RSD
                    rsd = RemoteServiceDiscoveryService((tunnel_result.address, tunnel_result.port))
                    await rsd.connect()
                    self._tunnel_rsd = rsd

                    # 通知主线程 tunnel 已就绪
                    self._tunnel_ready.set()

                    # 保活：等待直到被取消或连接关闭
                    await tunnel_result.client.wait_closed()
            except asyncio.CancelledError:
                logger.info("iOS 17+ tunnel keeper 已取消")
                raise
            except Exception as e:
                logger.error(f"iOS 17+ tunnel keeper 异常: {e}")
                self._tunnel_ready.set()  # 避免 connect 永久阻塞
                raise

        # 在事件循环上启动后台 task
        self._tunnel_keeper_task = self._loop_thread.create_task(keeper())

        # 等待 tunnel 就绪
        if not self._tunnel_ready.wait(timeout=30):
            raise RuntimeError("iOS 17+ tunnel 启动超时")

        if self._tunnel_rsd is None:
            raise RuntimeError("iOS 17+ tunnel 启动失败")

    def get_lockdown(self) -> SyncLockdownProxy:
        """获取同步 lockdown 代理。

        Returns:
            SyncLockdownProxy: 可像同步 lockdown 一样使用

        Raises:
            RuntimeError: 未连接
        """
        if self._sync_proxy is None:
            raise RuntimeError("设备未连接，请先调用 connect()")
        return self._sync_proxy

    def get_async_lockdown(self) -> Any:
        """获取原始 async LockdownServiceProvider。

        供需要在 async 上下文中直接使用的场景（如 DVT 流式 sysmon）。

        Returns:
            LockdownServiceProvider（UsbmuxLockdownClient 或 RemoteServiceDiscoveryService）

        Raises:
            RuntimeError: 未连接
        """
        if not self._connected:
            raise RuntimeError("设备未连接，请先调用 connect()")
        return self._tunnel_rsd if self._is_ios17_plus else self._lockdown

    def run_async(self, coro: Any, timeout: float = 60.0) -> Any:
        """在事件循环中执行协程，阻塞等待结果。

        供 collector 在同步上下文中调用 async API 使用。
        """
        return self._loop_thread.run_sync(coro, timeout=timeout)

    def disconnect(self) -> None:
        """断开连接，清理资源。"""
        with self._connect_lock:
            # 取消 tunnel keeper
            if self._tunnel_keeper_task is not None and self._loop_thread.is_running():
                try:
                    self._tunnel_keeper_task.cancel()
                except Exception:
                    pass
                self._tunnel_keeper_task = None

            # 关闭 RSD
            if self._tunnel_rsd is not None:
                try:
                    self._loop_thread.run_sync(self._tunnel_rsd.close(), timeout=5)
                except Exception:
                    pass
                self._tunnel_rsd = None

            # 关闭 usbmux lockdown
            if self._lockdown is not None:
                try:
                    self._loop_thread.run_sync(self._lockdown.close(), timeout=5)
                except Exception:
                    pass
                self._lockdown = None

            self._sync_proxy = None
            self._connected = False
            self._tunnel_ready.clear()

    # ========== 属性 ==========

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def is_ios17_plus(self) -> bool:
        return self._is_ios17_plus

    @property
    def product_version(self) -> Optional[str]:
        return self._product_version

    @property
    def loop_thread(self) -> AsyncLoopThread:
        """暴露事件循环线程供外部使用。"""
        return self._loop_thread
