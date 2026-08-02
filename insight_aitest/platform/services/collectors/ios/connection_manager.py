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
import re
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

# pymobiledevice3 v10.x：userspace tunnel（纯 Python 网络栈，跨平台、无需 root/管理员）
# 直接 yield 一个已连接的 RemoteServiceDiscoveryService，是连接 iOS 17+/26 的推荐方式。
try:
    from pymobiledevice3.remote.userspace_tunnel import (
        UserspaceRsdTunnel as _UserspaceRsdTunnel,
    )
except ImportError:
    _UserspaceRsdTunnel = None

# 为测试暴露的名称（测试通过 patch 这些名称来 mock）
usbmux_list_devices = _usbmux_module.list_devices if _usbmux_module else None
create_using_usbmux = _create_using_usbmux
start_tunnel = _start_tunnel
get_core_device_tunnel_services = _get_core_device_tunnel_services
RemoteServiceDiscoveryService = _RemoteServiceDiscoveryService
UserspaceRsdTunnel = _UserspaceRsdTunnel


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
        """解析版本字符串为 (major, minor, patch)。

        容忍 beta/RC 版本可能携带的 build 后缀，例如 ``"17.0 21A329"`` 或
        ``"26.0 beta"``：对每一段只取开头的连续数字，无法解析则记 0。
        """
        parts = version_str.split(".")
        nums = []
        for p in parts[:3]:
            m = re.match(r"\d+", p.strip())
            nums.append(int(m.group()) if m else 0)
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

            # 通过事件循环执行 async 连接逻辑（版本检测 + 调度 tunnel keeper）
            # 注意：run_sync 会在主线程阻塞，但协程在 loop 线程上跑；
            # _connect_async 内的 tunnel keeper 仅被调度、不阻塞 loop 线程。
            self._loop_thread.run_sync(self._connect_async())

            # iOS 17+: 在主线程上等待 tunnel keeper 就绪。
            # 必须在 loop 线程之外等待，否则 loop 线程被阻塞会导致 keeper 协程无法运行（死锁）。
            if self._is_ios17_plus:
                if not self._tunnel_ready.wait(timeout=30):
                    raise RuntimeError("iOS 17+ tunnel 启动超时")
                if self._tunnel_rsd is None:
                    raise RuntimeError("iOS 17+ tunnel 启动失败")

            # 创建同步代理（此时 RSD/lockdown 已就绪）
            async_lockdown = self._tunnel_rsd if self._is_ios17_plus else self._lockdown
            self._sync_proxy = SyncLockdownProxy(async_lockdown, self._loop_thread)

            self._connected = True
            return True

    async def _connect_async(self) -> None:
        """异步连接逻辑：检测版本 → 选择路径。

        iOS 17+ 时仅调度 tunnel keeper（不阻塞等待），等待逻辑在 ``connect()`` 主线程完成。
        """
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

            # 仅调度 keeper；RSD 就绪的等待交给 connect() 主线程
            await self._schedule_tunnel_keeper()
        else:
            # iOS <17: 直接使用 usbmux lockdown
            self._lockdown = lockdown

    async def _schedule_tunnel_keeper(self) -> None:
        """调度 tunnel keeper 后台协程（iOS 17+ 专用），立即返回不阻塞。

        优先使用 pymobiledevice3 v10.x 的 ``UserspaceRsdTunnel``（纯 Python 网络栈，
        跨平台、无需 root/管理员，且能正确处理 iOS 26 的 CoreDevice 协议变更）。
        若 v10.x 不可用（仍处于 9.x），回退到 ``get_core_device_tunnel_services``
        → ``start_tunnel`` → 手动 RSD 的三段式路径。

        tunnel keeper 跑在事件循环上；RSD 就绪后通过 ``_tunnel_ready`` 通知，
        由 ``connect()`` 在主线程上等待（不能在 loop 线程上 wait，否则死锁）。
        """
        # 选择 tunnel 后端
        use_userspace = UserspaceRsdTunnel is not None
        if not use_userspace and get_core_device_tunnel_services is None:
            raise RuntimeError(
                "pymobiledevice3 版本不支持 tunnel（需要 >=9.0.0），" "无法连接 iOS 17+ 设备"
            )

        # tunnel keeper 作为后台 task 启动
        # 我们需要将 RSD 通过 event 传递出去
        self._tunnel_ready.clear()

        async def keeper():
            try:
                if use_userspace:
                    # v10.x：UserspaceRsdTunnel 直接 yield 已连接的 RSD
                    # serial 直接受 UDID；autopair=True 允许首次自动配对
                    async with UserspaceRsdTunnel(serial=self.udid, autopair=True) as rsd:
                        logger.info(
                            f"iOS 17+ userspace tunnel 建立: {self.udid} "
                            f"(version={getattr(rsd, 'product_version', '?')})"
                        )
                        self._tunnel_rsd = rsd
                        self._tunnel_ready.set()
                        # 保活：持有 async with 上下文直到被取消
                        await asyncio.Event().wait()
                else:
                    # 9.x 回退路径：发现 tunnel 服务 → start_tunnel → 手动 RSD
                    services = await get_core_device_tunnel_services(udid=self.udid)
                    if not services:
                        raise RuntimeError(
                            f"未找到 iOS 17+ tunnel 服务: {self.udid}。"
                            "请确保设备已信任电脑并启用 Developer Mode，"
                            "并升级 pymobiledevice3>=10.3.0 以获得 iOS 26 支持"
                        )
                    service = services[0]
                    async with start_tunnel(service, protocol="tcp") as tunnel_result:
                        logger.info(
                            f"iOS 17+ tunnel 建立: {tunnel_result.address}:{tunnel_result.port}"
                        )
                        # 通过 tunnel 地址建立 RSD
                        rsd = RemoteServiceDiscoveryService(
                            (tunnel_result.address, tunnel_result.port)
                        )
                        await rsd.connect()
                        self._tunnel_rsd = rsd
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

        # 在事件循环上启动后台 task（不等待）
        self._tunnel_keeper_task = self._loop_thread.create_task(keeper())

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

    def get_cpu_core_count(self) -> int:
        """获取设备 CPU 核心数（用于 CPU 使用率归一化）。

        sysmontap 报告的 cpuUsage 是「非归一化」值（按核心累加，可超过 100%），
        业界标准（PerfDog/Xcode）的 AppCPU = sysmontap值 / 核心数。
        通过 DVT 的 ``hardware_information`` 查询 ``numberOfCpus``，结果缓存。

        Returns:
            CPU 核心数；查询失败时返回 1（不归一化，保持原始值）。
        """
        # 缓存命中
        cached = getattr(self, "_cpu_core_count", None)
        if cached is not None:
            return cached

        try:
            count = self.run_async(self._fetch_cpu_core_count(), timeout=10)
            if count and count > 0:
                self._cpu_core_count = count
                logger.info(f"iOS 设备 CPU 核心数: {count}")
                return count
        except Exception as e:
            logger.debug(f"查询 CPU 核心数失败: {e}，CPU 使用率将不归一化")

        self._cpu_core_count = 1  # 失败时不归一化
        return 1

    async def _fetch_cpu_core_count(self) -> int:
        """通过 DVT DeviceInfo.hardware_information() 查询 CPU 核心数。"""
        from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
        from pymobiledevice3.services.dvt.instruments.device_info import DeviceInfo

        lockdown = self.get_async_lockdown()
        async with DvtProvider(lockdown) as dvt:
            async with DeviceInfo(dvt) as di:
                hw = await di.hardware_information()
                return int(hw.get("numberOfCpus", 1))
