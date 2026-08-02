# -*- coding: utf-8 -*-
"""IOSConnectionManager 单元测试"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from insight_aitest.platform.services.collectors.ios.connection_manager import (
    IOSConnectionManager,
)
from insight_aitest.platform.services.collectors.ios.sync_proxy import SyncLockdownProxy


class TestVersionDetection:
    """iOS 版本检测逻辑"""

    def test_parse_version_major(self):
        assert IOSConnectionManager._parse_version("15.5") == (15, 5, 0)
        assert IOSConnectionManager._parse_version("17.0") == (17, 0, 0)
        assert IOSConnectionManager._parse_version("18.2.1") == (18, 2, 1)

    def test_parse_version_ios26(self):
        """iOS 26 应正确解析为 (26, ...) 并被识别为 iOS 17+"""
        assert IOSConnectionManager._parse_version("26.6") == (26, 6, 0)
        assert IOSConnectionManager._parse_version("26.0") == (26, 0, 0)
        assert IOSConnectionManager._parse_version("26.1.2") == (26, 1, 2)

    def test_parse_version_build_suffix(self):
        """beta/RC 版本可能携带 build 后缀（如 "26.0 21A329"），不应误判为 0"""
        assert IOSConnectionManager._parse_version("26.0 21A329") == (26, 0, 0)
        assert IOSConnectionManager._parse_version("17.0 21A329") == (17, 0, 0)
        # 完全无法解析的段记 0，但不抛异常
        assert IOSConnectionManager._parse_version("26 beta") == (26, 0, 0)

    def test_is_ios17_plus_true(self):
        assert IOSConnectionManager._check_ios17_plus("17.0") is True
        assert IOSConnectionManager._check_ios17_plus("18.2.1") is True
        assert IOSConnectionManager._check_ios17_plus("17.5") is True
        # iOS 26 应被识别为 17+（走 tunnel 路径）
        assert IOSConnectionManager._check_ios17_plus("26.6") is True
        assert IOSConnectionManager._check_ios17_plus("26.0") is True

    def test_is_ios17_plus_false(self):
        assert IOSConnectionManager._check_ios17_plus("15.5") is False
        assert IOSConnectionManager._check_ios17_plus("16.6") is False
        assert IOSConnectionManager._check_ios17_plus("14.0") is False

    def test_is_ios17_plus_invalid(self):
        assert IOSConnectionManager._check_ios17_plus("") is False
        assert IOSConnectionManager._check_ios17_plus("unknown") is False
        assert IOSConnectionManager._check_ios17_plus(None) is False


class FakeUsbmuxLockdown:
    """模拟 pymobiledevice3 async usbmux lockdown"""

    def __init__(self, udid="test-udid", product_version="15.5"):
        self._udid = udid
        self._product_version = product_version
        self._values = {
            "DeviceName": "Test iPhone",
            "ProductVersion": product_version,
            "ProductType": "iPhone12,1",
            "SerialNumber": "SN123",
        }

    @property
    def udid(self):
        return self._udid

    @property
    def product_version(self):
        return self._product_version

    async def get_value(self, domain=None, key=None):
        if key:
            return self._values.get(key)
        return self._values

    async def close(self):
        pass

    async def start_lockdown_service(self, name, include_escrow_bag=False):
        return MagicMock(name=f"service:{name}")


class FakeRSD:
    """模拟 RemoteServiceDiscoveryService"""

    def __init__(self, udid="test-udid", product_version="17.0"):
        self._udid = udid
        self._product_version = product_version

    @property
    def udid(self):
        return self._udid

    @property
    def product_version(self):
        return self._product_version

    async def connect(self):
        pass

    async def close(self):
        pass

    async def get_value(self, domain=None, key=None):
        return {"DeviceName": "Test iPhone 17", "ProductVersion": self._product_version}

    async def start_lockdown_service(self, name, include_escrow_bag=False):
        return MagicMock(name=f"rsd_service:{name}")


class TestUsbmuxConnection:
    """iOS <17 usbmux 连接路径测试"""

    def test_connect_ios16_returns_sync_proxy(self):
        """iOS <17 设备通过 usbmux 连接，返回 SyncLockdownProxy"""
        mgr = IOSConnectionManager("test-udid")

        with patch.object(mgr, "_loop_thread") as mock_lt:
            mock_lt.is_running.return_value = True
            mock_lt.run_sync = lambda coro: asyncio.new_event_loop().run_until_complete(coro)

            fake_ld = FakeUsbmuxLockdown(product_version="16.6")

            with patch(
                "insight_aitest.platform.services.collectors.ios.connection_manager.create_using_usbmux",
                new_callable=AsyncMock,
                return_value=fake_ld,
            ):
                with patch(
                    "insight_aitest.platform.services.collectors.ios.connection_manager.usbmux_list_devices",
                    new_callable=AsyncMock,
                    return_value=[MagicMock(serial="test-udid")],
                ):
                    mgr.connect()

        assert mgr.is_connected is True
        assert mgr.is_ios17_plus is False
        proxy = mgr.get_lockdown()
        assert isinstance(proxy, SyncLockdownProxy)
        assert proxy.get_value(key="ProductVersion") == "16.6"

    def test_connect_raises_when_device_not_found(self):
        """设备不存在时抛异常"""
        mgr = IOSConnectionManager("nonexistent-udid")

        with patch(
            "insight_aitest.platform.services.collectors.ios.connection_manager.usbmux_list_devices",
            new_callable=AsyncMock,
            return_value=[],
        ):
            with patch.object(mgr, "_loop_thread") as mock_lt:
                mock_lt.is_running.return_value = True
                mock_lt.run_sync = lambda coro: asyncio.new_event_loop().run_until_complete(coro)
                with pytest.raises(Exception):
                    mgr.connect()


class FakeUserspaceTunnel:
    """模拟 v10.x UserspaceRsdTunnel 的 async context manager。

    __aenter__ 立即返回 RSD 并触发 _tunnel_ready；
    __aexit__ 时取消保活 Event。
    """

    def __init__(self, rsd):
        self._rsd = rsd
        self._exit = asyncio.Event()

    async def __aenter__(self):
        return self._rsd

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._exit.set()
        return False


class TestTunnelConnection:
    """iOS 17+ tunnel 连接路径测试（mock tunnel）"""

    def test_connect_ios17_routes_to_tunnel(self):
        """iOS >=17 设备应被识别并路由到 tunnel 路径"""
        mgr = IOSConnectionManager("ios17-udid")

        fake_usb_device = MagicMock(serial="ios17-udid")
        fake_usb_ld = FakeUsbmuxLockdown(udid="ios17-udid", product_version="17.5")

        def mock_run_sync(coro):
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()

        with patch.object(mgr, "_loop_thread") as mock_lt:
            mock_lt.is_running.return_value = True
            mock_lt.run_sync = mock_run_sync
            mock_lt.create_task.return_value = MagicMock()

            async def fake_schedule():
                # 直接标记 RSD 就绪，避免真实 tunnel（验证路由逻辑即可）
                mgr._tunnel_rsd = FakeRSD(udid="ios17-udid", product_version="17.5")
                mgr._tunnel_ready.set()

            mock_schedule = AsyncMock(side_effect=fake_schedule)

            with (
                patch(
                    "insight_aitest.platform.services.collectors.ios.connection_manager.usbmux_list_devices",
                    new_callable=AsyncMock,
                    return_value=[fake_usb_device],
                ),
                patch(
                    "insight_aitest.platform.services.collectors.ios.connection_manager.create_using_usbmux",
                    new_callable=AsyncMock,
                    return_value=fake_usb_ld,
                ),
                patch(
                    "insight_aitest.platform.services.collectors.ios.connection_manager.IOSConnectionManager._schedule_tunnel_keeper",
                    mock_schedule,
                ),
            ):
                mgr.connect()

        assert mgr.is_connected is True
        assert mgr.is_ios17_plus is True
        # iOS 17+ 必须走 tunnel 聊度，不能走 usbmux 直连
        mock_schedule.assert_called_once()

    def test_connect_ios26_routes_to_tunnel(self):
        """iOS 26 设备应被识别为 17+ 并走 tunnel 路径"""
        mgr = IOSConnectionManager("ios26-udid")

        fake_usb_device = MagicMock(serial="ios26-udid")
        fake_usb_ld = FakeUsbmuxLockdown(udid="ios26-udid", product_version="26.6")

        def mock_run_sync(coro):
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()

        with patch.object(mgr, "_loop_thread") as mock_lt:
            mock_lt.is_running.return_value = True
            mock_lt.run_sync = mock_run_sync
            mock_lt.create_task.return_value = MagicMock()

            async def fake_schedule():
                mgr._tunnel_rsd = FakeRSD(udid="ios26-udid", product_version="26.6")
                mgr._tunnel_ready.set()

            mock_schedule = AsyncMock(side_effect=fake_schedule)

            with (
                patch(
                    "insight_aitest.platform.services.collectors.ios.connection_manager.usbmux_list_devices",
                    new_callable=AsyncMock,
                    return_value=[fake_usb_device],
                ),
                patch(
                    "insight_aitest.platform.services.collectors.ios.connection_manager.create_using_usbmux",
                    new_callable=AsyncMock,
                    return_value=fake_usb_ld,
                ),
                patch(
                    "insight_aitest.platform.services.collectors.ios.connection_manager.IOSConnectionManager._schedule_tunnel_keeper",
                    mock_schedule,
                ),
            ):
                mgr.connect()

        assert mgr.is_connected is True
        assert mgr.is_ios17_plus is True
        assert mgr.product_version == "26.6"
        mock_schedule.assert_called_once()

    def test_connect_ios26_userspace_full_flow(self):
        """端到端：iOS 26 + v10.x userspace tunnel，verify 无死锁且 RSD 正确设置"""
        from insight_aitest.platform.services.collectors.ios.async_loop import AsyncLoopThread

        mgr = IOSConnectionManager("ios26-udid")
        real_thread = AsyncLoopThread()
        real_thread.start()
        try:
            mgr._loop_thread = real_thread

            fake_usb_device = MagicMock(serial="ios26-udid")
            fake_usb_ld = FakeUsbmuxLockdown(udid="ios26-udid", product_version="26.6")
            fake_rsd = FakeRSD(udid="ios26-udid", product_version="26.6")

            with (
                patch(
                    "insight_aitest.platform.services.collectors.ios.connection_manager.usbmux_list_devices",
                    new_callable=AsyncMock,
                    return_value=[fake_usb_device],
                ),
                patch(
                    "insight_aitest.platform.services.collectors.ios.connection_manager.create_using_usbmux",
                    new_callable=AsyncMock,
                    return_value=fake_usb_ld,
                ),
                patch(
                    "insight_aitest.platform.services.collectors.ios.connection_manager.UserspaceRsdTunnel",
                    return_value=FakeUserspaceTunnel(fake_rsd),
                ) as mock_userspace_cls,
                patch(
                    "insight_aitest.platform.services.collectors.ios.connection_manager.get_core_device_tunnel_services",
                    new_callable=AsyncMock,
                ) as mock_gcdts,
            ):
                # connect() 内部会调度 keeper（在 loop 线程跑），主线程等待 _tunnel_ready
                mgr.connect()

                # 应优先使用 userspace tunnel，且 serial 直传 udid
                mock_userspace_cls.assert_called_once_with(serial="ios26-udid", autopair=True)
                # 9.x 回退路径不应被调用
                mock_gcdts.assert_not_called()

            assert mgr.is_connected is True
            assert mgr.is_ios17_plus is True
            assert mgr._tunnel_rsd is fake_rsd
        finally:
            real_thread.stop()

    def test_connect_ios17_fallback_to_core_device(self):
        """端到端：无 v10.x userspace tunnel（9.x），回退到三段式路径，verify 无死锁"""
        from insight_aitest.platform.services.collectors.ios.async_loop import AsyncLoopThread

        mgr = IOSConnectionManager("ios17-udid")
        real_thread = AsyncLoopThread()
        real_thread.start()
        try:
            mgr._loop_thread = real_thread

            fake_usb_device = MagicMock(serial="ios17-udid")
            fake_usb_ld = FakeUsbmuxLockdown(udid="ios17-udid", product_version="17.5")

            # 9.x 三段式 tunnel：start_tunnel 返回的 TunnelResult 保活协程
            # 需要 wait_closed() 阻塞以保持 tunnel；用一个 Event 模拟永不关闭
            keep_open = asyncio.Event()

            class FakeTunnelResult:
                address = "fd17::1"
                port = 12345

                class _Client:
                    async def wait_closed(self):
                        await keep_open.wait()

                client = _Client()

            fake_tunnel_result = FakeTunnelResult()

            class FakeStartTunnelCtx:
                async def __aenter__(self):
                    return fake_tunnel_result

                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    keep_open.set()
                    return False

            fake_rsd = FakeRSD(udid="ios17-udid", product_version="17.5")

            with (
                patch(
                    "insight_aitest.platform.services.collectors.ios.connection_manager.usbmux_list_devices",
                    new_callable=AsyncMock,
                    return_value=[fake_usb_device],
                ),
                patch(
                    "insight_aitest.platform.services.collectors.ios.connection_manager.create_using_usbmux",
                    new_callable=AsyncMock,
                    return_value=fake_usb_ld,
                ),
                # 模拟 v10.x userspace tunnel 不可用（9.x 环境）
                patch(
                    "insight_aitest.platform.services.collectors.ios.connection_manager.UserspaceRsdTunnel",
                    None,
                ),
                patch(
                    "insight_aitest.platform.services.collectors.ios.connection_manager.get_core_device_tunnel_services",
                    new_callable=AsyncMock,
                    return_value=[MagicMock()],
                ) as mock_gcdts,
                patch(
                    "insight_aitest.platform.services.collectors.ios.connection_manager.start_tunnel",
                    return_value=FakeStartTunnelCtx(),
                ),
                patch(
                    "insight_aitest.platform.services.collectors.ios.connection_manager.RemoteServiceDiscoveryService",
                    return_value=fake_rsd,
                ),
            ):
                mgr.connect()
                # 回退路径应调用 get_core_device_tunnel_services
                mock_gcdts.assert_called_once()

            assert mgr.is_connected is True
            assert mgr.is_ios17_plus is True
            assert mgr._tunnel_rsd is fake_rsd
        finally:
            real_thread.stop()

    def test_disconnect_cleans_up(self):
        """disconnect 清理连接"""
        mgr = IOSConnectionManager("test-udid")
        mgr._connected = True
        mgr._lockdown = MagicMock()

        mgr.disconnect()
        assert mgr.is_connected is False


class TestSingleton:
    """单例模式测试"""

    def test_get_instance_returns_same_instance(self):
        """相同 UDID 返回同一个实例"""
        IOSConnectionManager._instances.clear()
        m1 = IOSConnectionManager.get_instance("udid-A")
        m2 = IOSConnectionManager.get_instance("udid-A")
        assert m1 is m2

    def test_get_instance_different_udids(self):
        """不同 UDID 返回不同实例"""
        IOSConnectionManager._instances.clear()
        m1 = IOSConnectionManager.get_instance("udid-A")
        m2 = IOSConnectionManager.get_instance("udid-B")
        assert m1 is not m2

    def test_clear_instances(self):
        """clear_instances 清除所有实例"""
        IOSConnectionManager.get_instance("udid-A")
        assert len(IOSConnectionManager._instances) > 0
        IOSConnectionManager.clear_instances()
        assert len(IOSConnectionManager._instances) == 0
