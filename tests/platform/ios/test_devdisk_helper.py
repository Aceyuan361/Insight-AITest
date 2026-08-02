# -*- coding: utf-8 -*-
"""DevDiskHelper 单元测试

重点验证 iOS 17+ 的 DDI 挂载行为：
- auto_mount 内部按版本分发到 personalized DDI
- pymobiledevice3 抛 DeveloperModeIsNotEnabledError 时，转换为项目自定义异常
- AlreadyMountedError 视为已挂载成功
"""

from unittest.mock import MagicMock, patch

import pytest

from insight_aitest.platform.services.collectors.ios.devdisk_helper import DevDiskHelper
from insight_aitest.platform.services.collectors.ios.exceptions import (
    DeveloperModeNotEnabledError,
)


def _make_connected_mgr():
    """返回一个已连接的 mock IOSConnectionManager。"""
    mgr = MagicMock()
    mgr.is_connected = True
    mgr.get_async_lockdown.return_value = MagicMock(name="rsd")
    return mgr


class TestDevDiskHelperCaching:
    def test_mount_uses_cache_after_success(self):
        """首次挂载成功后，再次调用应命中缓存、不再触发 auto_mount。"""
        DevDiskHelper.clear_cache()
        mgr = _make_connected_mgr()

        with (
            patch(
                "insight_aitest.platform.services.collectors.ios.devdisk_helper.IOSConnectionManager.get_instance",
                return_value=mgr,
            ),
            patch("pymobiledevice3.services.mobile_image_mounter.auto_mount") as mock_auto,
        ):
            # 第一次：实际挂载（run_async 正常返回）
            result1 = DevDiskHelper.ensure_developer_disk_mounted("dev-A")
            assert result1 is True
            assert mock_auto.call_count == 1

            # 第二次：应命中缓存，不再调用 auto_mount
            result2 = DevDiskHelper.ensure_developer_disk_mounted("dev-A")
            assert result2 is True
            # 调用次数仍为 1（缓存命中）
            assert mock_auto.call_count == 1

        DevDiskHelper.clear_cache()


class TestDevModeErrorMapping:
    def test_ios17_dev_mode_off_raises_custom_exception(self):
        """iOS 17+ 未启用 Developer Mode：run_async 抛 DeveloperModeIsNotEnabledError，
        应转换为项目的 DeveloperModeNotEnabledError（在 NO_RETRY_EXCEPTIONS 中）。"""
        DevDiskHelper.clear_cache()
        mgr = _make_connected_mgr()

        from pymobiledevice3.exceptions import DeveloperModeIsNotEnabledError

        with (
            patch(
                "insight_aitest.platform.services.collectors.ios.devdisk_helper.IOSConnectionManager.get_instance",
                return_value=mgr,
            ),
            patch("pymobiledevice3.services.mobile_image_mounter.auto_mount"),
        ):
            mgr.run_async.side_effect = DeveloperModeIsNotEnabledError()

            with pytest.raises(DeveloperModeNotEnabledError):
                DevDiskHelper.ensure_developer_disk_mounted("ios17-udid")

        DevDiskHelper.clear_cache()

    def test_already_mounted_returns_true(self):
        """已挂载（AlreadyMountedError）应视为成功。"""
        DevDiskHelper.clear_cache()
        mgr = _make_connected_mgr()

        from pymobiledevice3.exceptions import AlreadyMountedError

        with patch(
            "insight_aitest.platform.services.collectors.ios.devdisk_helper.IOSConnectionManager.get_instance",
            return_value=mgr,
        ):
            mgr.run_async.side_effect = AlreadyMountedError()
            result = DevDiskHelper.ensure_developer_disk_mounted("dev-mounted")

        assert result is True
        DevDiskHelper.clear_cache()


class TestRevealDeveloperMode:
    def test_reveal_uses_usbmux_path(self):
        """reveal_developer_mode 应通过独立 usbmux 连接执行（不走 RSD）。"""
        import asyncio

        mgr = _make_connected_mgr()
        # run_async 必须真正执行传入的协程（_do 内部会调 create_using_usbmux）
        mgr.run_async = lambda coro, timeout=60: asyncio.new_event_loop().run_until_complete(coro)

        fake_lockdown = MagicMock(name="usbmux_lockdown")
        fake_amfi = MagicMock()

        async def fake_create(udid):
            return fake_lockdown

        async def fake_reveal():
            return None

        with (
            patch(
                "insight_aitest.platform.services.collectors.ios.devdisk_helper.IOSConnectionManager.get_instance",
                return_value=mgr,
            ),
            patch("pymobiledevice3.lockdown.create_using_usbmux", side_effect=fake_create) as mock_create,
            patch("pymobiledevice3.services.amfi.AmfiService", return_value=fake_amfi) as mock_amfi_cls,
        ):
            fake_amfi.reveal_developer_mode_option_in_ui = fake_reveal

            result = DevDiskHelper.reveal_developer_mode("ios26-udid")

        assert result is True
        mock_create.assert_called_once_with("ios26-udid")
        # AmfiService 用 usbmux lockdown 构造（不是 RSD）
        mock_amfi_cls.assert_called_once_with(lockdown=fake_lockdown)

    def test_reveal_without_udid_returns_false(self):
        assert DevDiskHelper.reveal_developer_mode(None) is False

