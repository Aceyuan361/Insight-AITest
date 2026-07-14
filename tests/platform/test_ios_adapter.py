# -*- coding: utf-8 -*-
"""
iOS 设备适配器单元测试 (pymobiledevice3 v9.x async API)

覆盖：
- BaseDeviceAdapter 抽取到 base.py（消除重复 ABC）
- connect() 通过 IOSConnectionManager 建立连接
- get_device_info() 通过 SyncLockdownProxy 查询设备信息
- get_battery_level() 通过 async DiagnosticsService.get_battery()
- install/uninstall_app 通过 async InstallationProxyService
- start/stop_app 通过 async ProcessControl/DeviceInfo
"""

from unittest.mock import patch, MagicMock


def test_ios_adapter_inherits_shared_base():
    """IOSDeviceAdapter 必须继承共享的 BaseDeviceAdapter（来自 base.py）。"""
    from insight_aitest.platform.services.device_adapters.base import BaseDeviceAdapter
    from insight_aitest.platform.services.device_adapters.ios_device_adapter import IOSDeviceAdapter

    assert issubclass(IOSDeviceAdapter, BaseDeviceAdapter)


def test_device_adapters_reexport_same_base():
    """device_adapters.py 导出的 BaseDeviceAdapter 应与 base.py 是同一个类。"""
    from insight_aitest.platform.services.device_adapters import base
    from insight_aitest.platform.services.device_adapters import device_adapters

    assert device_adapters.BaseDeviceAdapter is base.BaseDeviceAdapter


def _make_mock_mgr(product_version="15.5", values=None):
    """创建一个 mock IOSConnectionManager"""
    if values is None:
        values = {
            "DeviceName": "Test iPhone",
            "ProductType": "iPhone12,1",
            "ProductVersion": product_version,
            "SerialNumber": "SN12345",
        }

    mock_proxy = MagicMock()
    mock_proxy.get_value.side_effect = lambda domain=None, key=None: values.get(key, None)

    mgr = MagicMock()
    mgr.is_connected = True
    mgr.product_version = product_version
    mgr.is_ios17_plus = False
    mgr.get_lockdown.return_value = mock_proxy
    mgr.get_async_lockdown.return_value = MagicMock()
    mgr.run_async = lambda coro, timeout=60: None  # 占位
    return mgr


@patch("insight_aitest.platform.services.device_adapters.ios_device_adapter.usbmux")
@patch("insight_aitest.platform.services.device_adapters.ios_device_adapter.DevDiskHelper")
def test_attempt_connect_uses_connection_manager(mock_dd, mock_usbmux):
    """connect() should use IOSConnectionManager to establish connection."""
    mock_usbmux.list_devices.return_value = [MagicMock(serial="test-udid-1234")]
    mock_dd.ensure_developer_disk_mounted.return_value = True

    mock_mgr = _make_mock_mgr()

    with patch(
        "insight_aitest.platform.services.collectors.ios.connection_manager.IOSConnectionManager.get_instance",
        return_value=mock_mgr,
    ):
        from insight_aitest.platform.services.device_adapters.ios_device_adapter import (
            IOSDeviceAdapter,
        )

        adapter = IOSDeviceAdapter("test-udid-1234")
        result = adapter.connect()
        assert result is True
        assert adapter._lockdown_client is mock_mgr.get_lockdown.return_value


def test_get_device_info_queries_lockdown():
    """get_device_info() 应通过 SyncLockdownProxy 查询设备信息。"""
    values = {
        "DeviceName": "My iPhone",
        "ProductType": "iPhone15,2",
        "ProductVersion": "17.0",
        "SerialNumber": "SN12345",
    }
    mock_mgr = _make_mock_mgr(product_version="17.0", values=values)

    from insight_aitest.platform.services.device_adapters.ios_device_adapter import IOSDeviceAdapter
    from insight_aitest.platform.services.device_adapters.models import Platform

    adapter = IOSDeviceAdapter("udid-info")
    adapter._conn_mgr = mock_mgr
    adapter._lockdown_proxy = mock_mgr.get_lockdown.return_value
    adapter._connected = True

    info = adapter.get_device_info()
    assert info is not None
    assert info.platform is Platform.IOS
    assert info.name == "My iPhone"
    assert info.model == "iPhone15,2"
    assert info.os_version == "17.0"
    assert info.serial_number == "SN12345"


def test_get_device_info_without_connection_returns_none():
    """未连接时 get_device_info() 返回 None。"""
    from insight_aitest.platform.services.device_adapters.ios_device_adapter import IOSDeviceAdapter

    adapter = IOSDeviceAdapter("not-connected")
    assert adapter._lockdown_client is None
    assert adapter.get_device_info() is None


def test_get_battery_level_uses_diagnostics_service():
    """get_battery_level() 应通过 async DiagnosticsService.get_battery() 读取真实电量。"""
    from insight_aitest.platform.services.device_adapters.ios_device_adapter import IOSDeviceAdapter

    adapter = IOSDeviceAdapter("udid-battery")
    mock_mgr = _make_mock_mgr()
    mock_mgr.run_async = lambda coro, timeout=60: {"BatteryCurrentCapacity": 87}
    adapter._conn_mgr = mock_mgr
    adapter._connected = True

    with patch("pymobiledevice3.services.diagnostics.DiagnosticsService"):
        assert adapter.get_battery_level() == 87


def test_get_battery_level_without_connection_returns_default():
    """未连接时 get_battery_level() 返回默认值 100。"""
    from insight_aitest.platform.services.device_adapters.ios_device_adapter import IOSDeviceAdapter

    adapter = IOSDeviceAdapter("udid-bat-default")
    # _conn_mgr is None → should return 100
    assert adapter.get_battery_level() == 100


def test_get_network_type_unknown_without_connection():
    """未连接时 get_network_type() 返回 Unknown。"""
    from insight_aitest.platform.services.device_adapters.ios_device_adapter import IOSDeviceAdapter

    adapter = IOSDeviceAdapter("udid-net")
    assert adapter.get_network_type() == "Unknown"


def test_install_app_uses_installation_proxy():
    """install_app() 应通过 async InstallationProxyService.install_from_local() 安装。"""
    from insight_aitest.platform.services.device_adapters.ios_device_adapter import IOSDeviceAdapter

    adapter = IOSDeviceAdapter("udid-install")
    mock_mgr = _make_mock_mgr()
    mock_mgr.run_async = MagicMock()
    adapter._conn_mgr = mock_mgr

    with patch("pymobiledevice3.services.installation_proxy.InstallationProxyService"):
        result = adapter.install_app("/tmp/app.ipa")
        assert result is True
        mock_mgr.run_async.assert_called_once()


def test_install_app_without_connection_returns_false():
    """未连接时 install_app() 返回 False。"""
    from insight_aitest.platform.services.device_adapters.ios_device_adapter import IOSDeviceAdapter

    adapter = IOSDeviceAdapter("udid-install-nocnx")
    assert adapter.install_app("/tmp/app.ipa") is False


def test_uninstall_app_uses_installation_proxy():
    """uninstall_app() 应通过 async InstallationProxyService.uninstall() 卸载。"""
    from insight_aitest.platform.services.device_adapters.ios_device_adapter import IOSDeviceAdapter

    adapter = IOSDeviceAdapter("udid-uninstall")
    mock_mgr = _make_mock_mgr()
    mock_mgr.run_async = MagicMock()
    adapter._conn_mgr = mock_mgr

    with patch("pymobiledevice3.services.installation_proxy.InstallationProxyService"):
        result = adapter.uninstall_app("com.example.app")
        assert result is True
        mock_mgr.run_async.assert_called_once()


def test_uninstall_app_without_connection_returns_false():
    """未连接时 uninstall_app() 返回 False。"""
    from insight_aitest.platform.services.device_adapters.ios_device_adapter import IOSDeviceAdapter

    adapter = IOSDeviceAdapter("udid-uninstall-nocnx")
    assert adapter.uninstall_app("com.example.app") is False


def test_start_app_uses_process_control():
    """start_app() 应通过 async ProcessControl.launch() 启动应用。"""
    from insight_aitest.platform.services.device_adapters.ios_device_adapter import IOSDeviceAdapter

    adapter = IOSDeviceAdapter("udid-start")
    mock_mgr = _make_mock_mgr()
    mock_mgr.run_async = MagicMock(return_value=12345)
    adapter._conn_mgr = mock_mgr

    result = adapter.start_app("com.example.app")
    assert result is True
    mock_mgr.run_async.assert_called_once()


def test_start_app_without_connection_returns_false():
    """未连接时 start_app() 返回 False。"""
    from insight_aitest.platform.services.device_adapters.ios_device_adapter import IOSDeviceAdapter

    adapter = IOSDeviceAdapter("udid-start-nocnx")
    assert adapter.start_app("com.example.app") is False


def test_stop_app_uses_process_control():
    """stop_app() 应通过 async DeviceInfo.proclist() + ProcessControl.kill() 停止应用。"""
    from insight_aitest.platform.services.device_adapters.ios_device_adapter import IOSDeviceAdapter

    adapter = IOSDeviceAdapter("udid-stop")
    mock_mgr = _make_mock_mgr()
    mock_mgr.run_async = MagicMock()
    adapter._conn_mgr = mock_mgr

    result = adapter.stop_app("com.example.app")
    assert result is True
    mock_mgr.run_async.assert_called_once()


def test_stop_app_without_connection_returns_false():
    """未连接时 stop_app() 返回 False。"""
    from insight_aitest.platform.services.device_adapters.ios_device_adapter import IOSDeviceAdapter

    adapter = IOSDeviceAdapter("udid-stop-nocnx")
    assert adapter.stop_app("com.example.app") is False
