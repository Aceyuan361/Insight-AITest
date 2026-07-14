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

    def test_is_ios17_plus_true(self):
        assert IOSConnectionManager._check_ios17_plus("17.0") is True
        assert IOSConnectionManager._check_ios17_plus("18.2.1") is True
        assert IOSConnectionManager._check_ios17_plus("17.5") is True

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


class TestTunnelConnection:
    """iOS 17+ tunnel 连接路径测试（mock tunnel）"""

    def test_connect_ios17_starts_tunnel(self):
        """iOS >=17 设备通过 tunnel 连接"""
        mgr = IOSConnectionManager("ios17-udid")

        # 模拟 usbmux 发现设备（iOS 17+ 设备也会出现在 usbmux 列表中）
        fake_usb_device = MagicMock(serial="ios17-udid")

        # 模拟 usbmux lockdown 获取版本
        fake_usb_ld = FakeUsbmuxLockdown(udid="ios17-udid", product_version="17.5")

        # 模拟 tunnel 服务
        fake_tunnel = MagicMock()
        fake_tunnel.__aenter__ = AsyncMock(return_value=fake_tunnel)
        fake_tunnel.__aexit__ = AsyncMock(return_value=None)
        fake_tunnel.address = "fd17::1"
        fake_tunnel.port = 12345

        fake_tunnel_service = MagicMock()

        fake_rsd = FakeRSD(udid="ios17-udid", product_version="17.5")

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
                    "insight_aitest.platform.services.collectors.ios.connection_manager.get_core_device_tunnel_services",
                    new_callable=AsyncMock,
                    return_value=[fake_tunnel_service],
                ),
                patch(
                    "insight_aitest.platform.services.collectors.ios.connection_manager.start_tunnel"
                ) as mock_start_tunnel,
                patch(
                    "insight_aitest.platform.services.collectors.ios.connection_manager.RemoteServiceDiscoveryService"
                ) as mock_rsd_cls,
                patch(
                    "insight_aitest.platform.services.collectors.ios.connection_manager.IOSConnectionManager._start_tunnel_keeper"
                ),
            ):
                # 配置 start_tunnel 为 async context manager
                mock_start_tunnel.return_value = fake_tunnel
                mock_rsd_cls.return_value = fake_rsd

                mgr.connect()

        assert mgr.is_connected is True
        assert mgr.is_ios17_plus is True

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
