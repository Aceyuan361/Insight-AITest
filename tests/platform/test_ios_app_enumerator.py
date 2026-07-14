# -*- coding: utf-8 -*-
"""
iOS 应用枚举器单元测试 (pymobiledevice3 v9.x async API)

重点覆盖 get_running_apps() 的修复：
- 不应在宿主机上读取设备端路径（如 /private/var/containers/...）的 Info.plist
- 应通过 InstallationProxyService.get_apps() 交叉匹配进程名 -> bundle_id
- 通过 IOSConnectionManager.run_async() 执行 async API
"""

from unittest.mock import patch, MagicMock


def _make_mock_mgr(apps_dict=None, processes=None):
    """创建一个 mock IOSConnectionManager。

    Args:
        apps_dict: InstallationProxyService.get_apps() 返回的应用字典
        processes: DeviceInfo.proclist() 返回的进程列表
    """
    mgr = MagicMock()
    mgr.is_connected = True
    mgr.get_async_lockdown.return_value = MagicMock()

    def mock_run_async(coro, timeout=60):
        # 如果传入的是协程，获取它的名称来判断应该返回什么
        coro_name = coro.__qualname__ if hasattr(coro, "__qualname__") else ""
        if "get_apps" in str(coro) or "_fetch_apps" in coro_name:
            return apps_dict or {}
        if "proclist" in str(coro) or "_fetch_processes" in coro_name:
            return processes or []
        return None

    mgr.run_async = MagicMock(side_effect=mock_run_async)
    return mgr


def _patch_app_lookup(apps_dict):
    """Patch AppLookup 使其返回指定的 apps_dict（避免真实设备连接）。

    同时清空缓存确保使用 patch 后的数据。
    """
    from insight_aitest.platform.services.collectors.ios import app_lookup

    # 清空缓存，强制重建
    app_lookup.AppLookup.invalidate()
    return patch(
        "insight_aitest.platform.services.collectors.ios.app_lookup.AppLookup._fetch_installed_apps",
        return_value=apps_dict or {},
    )


def _make_enum(mgr):
    """构造一个使用 mock mgr 的 IOSAppEnumerator。"""
    from insight_aitest.platform.services.device_adapters.ios_app_enumerator import (
        IOSAppEnumerator,
    )

    enum = IOSAppEnumerator("test-udid")
    enum._get_mgr = MagicMock(return_value=mgr)
    return enum


def test_get_running_apps_uses_installation_proxy():
    """get_running_apps 应通过 InstallationProxyService 交叉匹配，而非读取宿主机 plist。"""
    apps_dict = {
        "com.example.app": {
            "CFBundleDisplayName": "MyApp",
            "CFBundleName": "MyApp",
            "CFBundleExecutable": "MyApp",
            "Path": "/private/var/containers/...",
            "ApplicationType": "User",
        }
    }
    processes = [{"pid": 123, "name": "MyApp", "bundlePath": "/private/var/containers/..."}]

    mgr = _make_mock_mgr(apps_dict=apps_dict, processes=processes)

    # Mock InstallationProxyService + AppLookup（避免真实设备连接）
    with (
        patch("pymobiledevice3.services.installation_proxy.InstallationProxyService"),
        _patch_app_lookup(apps_dict),
    ):
        enum = _make_enum(mgr)
        apps = enum.get_running_apps()

    assert len(apps) == 1
    assert apps[0].package_name == "com.example.app"
    assert apps[0].is_running is True
    assert apps[0].pid == 123


def test_get_running_apps_matches_by_bundle_id():
    """进程名直接等于 bundle_id 时也应能匹配。"""
    apps_dict = {
        "com.example.direct": {
            "CFBundleDisplayName": "DirectApp",
            "CFBundleName": "DirectApp",
            "CFBundleExecutable": "DirectApp",
            "ApplicationType": "User",
        }
    }
    processes = [
        {"pid": 456, "name": "com.example.direct"},
    ]

    mgr = _make_mock_mgr(apps_dict=apps_dict, processes=processes)

    with (
        patch("pymobiledevice3.services.installation_proxy.InstallationProxyService"),
        _patch_app_lookup(apps_dict),
    ):
        enum = _make_enum(mgr)
        apps = enum.get_running_apps()

    assert len(apps) == 1
    assert apps[0].package_name == "com.example.direct"


def test_get_running_apps_dedupes_same_bundle():
    """同一 bundle_id 对应多个进程时只应返回一条（去重）。"""
    apps_dict = {
        "com.example.dup": {
            "CFBundleDisplayName": "DupApp",
            "CFBundleName": "DupApp",
            "CFBundleExecutable": "DupApp",
            "ApplicationType": "User",
        }
    }
    processes = [
        {"pid": 1, "name": "DupApp"},
        {"pid": 2, "name": "com.example.dup"},
    ]

    mgr = _make_mock_mgr(apps_dict=apps_dict, processes=processes)

    with (
        patch("pymobiledevice3.services.installation_proxy.InstallationProxyService"),
        _patch_app_lookup(apps_dict),
    ):
        enum = _make_enum(mgr)
        apps = enum.get_running_apps()

    assert len(apps) == 1
    assert apps[0].package_name == "com.example.dup"


def test_get_running_apps_does_not_touch_host_filesystem():
    """get_running_apps 绝不应在宿主机上打开/读取设备端 Info.plist。"""
    apps_dict = {
        "com.example.app": {
            "CFBundleDisplayName": "MyApp",
            "CFBundleName": "MyApp",
            "CFBundleExecutable": "MyApp",
            "ApplicationType": "User",
        }
    }
    processes = [
        {"pid": 123, "name": "MyApp", "bundlePath": "/private/var/containers/..."},
    ]

    mgr = _make_mock_mgr(apps_dict=apps_dict, processes=processes)

    with (
        patch("pymobiledevice3.services.installation_proxy.InstallationProxyService"),
        _patch_app_lookup(apps_dict),
        patch("builtins.open", side_effect=AssertionError("不应读取宿主机文件")) as mock_open,
        patch("os.path.exists", side_effect=AssertionError("不应检查宿主机路径")) as mock_exists,
    ):
        enum = _make_enum(mgr)
        apps = enum.get_running_apps()

    mock_open.assert_not_called()
    mock_exists.assert_not_called()
    assert len(apps) == 1
    assert apps[0].package_name == "com.example.app"


def test_get_running_apps_without_apps_returns_empty():
    """无已安装应用数据时 get_running_apps 应返回空列表。"""
    mgr = _make_mock_mgr(apps_dict={}, processes=[{"pid": 1, "name": "SomeApp"}])

    with (
        patch("pymobiledevice3.services.installation_proxy.InstallationProxyService"),
        _patch_app_lookup({}),
    ):
        enum = _make_enum(mgr)
        apps = enum.get_running_apps()

    assert apps == []


def test_get_running_apps_matches_by_executable_not_bundle_suffix():
    """关键回归：进程 name 是 CFBundleExecutable（如 WeChat），
    与 Bundle ID（com.tencent.xin）和显示名（微信）完全不同时也必须匹配。

    这是本修复的核心场景：旧代码从 Bundle ID 提取后缀 "xin" 去子串匹配，
    无法匹配进程名 "WeChat"，导致已运行的应用被误判为未运行。
    """
    apps_dict = {
        "com.tencent.xin": {
            "CFBundleDisplayName": "微信",
            "CFBundleName": "微信",
            "CFBundleExecutable": "WeChat",  # DVT 进程 name 的真正来源
            "ApplicationType": "User",
        }
    }
    processes = [{"pid": 8215, "name": "WeChat"}]

    mgr = _make_mock_mgr(apps_dict=apps_dict, processes=processes)

    with (
        patch("pymobiledevice3.services.installation_proxy.InstallationProxyService"),
        _patch_app_lookup(apps_dict),
    ):
        enum = _make_enum(mgr)
        apps = enum.get_running_apps()

    assert len(apps) == 1
    assert apps[0].package_name == "com.tencent.xin"
    assert apps[0].pid == 8215


def test_get_running_apps_does_not_match_daemon_substring():
    """关键回归：进程名子串匹配会产生误报。

    旧代码从 com.apple.clips 提取 "clips"，会误匹配到系统守护进程 "clipserviced"。
    新代码用 CFBundleExecutable 精确匹配，不会产生这种误报。
    """
    apps_dict = {
        "com.apple.clips": {
            "CFBundleDisplayName": "可立拍",
            "CFBundleName": "可立拍",
            "CFBundleExecutable": "Clips",
            "ApplicationType": "User",
        }
    }
    # clipserviced 是系统守护进程，不是 Clips 应用本身
    processes = [{"pid": 3058, "name": "clipserviced"}]

    mgr = _make_mock_mgr(apps_dict=apps_dict, processes=processes)

    with (
        patch("pymobiledevice3.services.installation_proxy.InstallationProxyService"),
        _patch_app_lookup(apps_dict),
    ):
        enum = _make_enum(mgr)
        apps = enum.get_running_apps()

    # Clips 应用未运行（只有守护进程 clipserviced），不应匹配
    assert apps == []


def test_enumerate_apps_returns_app_list():
    """enumerate_apps 应返回正确的应用列表。"""
    apps_dict = {
        "com.example.app1": {
            "CFBundleDisplayName": "App1",
            "CFBundleShortVersionString": "1.0.0",
            "ApplicationType": "User",
        },
        "com.apple.system": {
            "CFBundleDisplayName": "System",
            "ApplicationType": "System",
        },
    }

    mgr = _make_mock_mgr(apps_dict=apps_dict)

    with patch("pymobiledevice3.services.installation_proxy.InstallationProxyService"):
        enum = _make_enum(mgr)
        apps = enum.enumerate_apps(include_system_apps=False)

    # System app should be filtered out
    assert len(apps) == 1
    assert apps[0].package_name == "com.example.app1"
    assert apps[0].app_name == "App1"
    assert apps[0].version == "1.0.0"
