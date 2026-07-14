# -*- coding: utf-8 -*-
"""
SysmonService.get_process_by_bundle_id 单元测试

重点验证修复后的进程匹配逻辑：
- 通过 CFBundleExecutable 精确匹配 DVT 进程 name
- 不再用 Bundle ID 后缀子串匹配（旧逻辑的根因缺陷）
"""

import time
from unittest.mock import patch, MagicMock, PropertyMock
from insight_aitest.platform.services.collectors.ios.sysmon_service import SysmonService


def _make_service(udid="test-udid"):
    """创建一个已连接的 SysmonService（绕过真实设备连接）。"""
    svc = SysmonService(udid=udid)
    svc._connected = True
    return svc


def _patch_app_lookup(apps_dict):
    """Patch AppLookup 返回指定的 apps_dict。"""
    from insight_aitest.platform.services.collectors.ios.app_lookup import AppLookup
    AppLookup.invalidate()
    return patch.object(AppLookup, "_fetch_installed_apps", return_value=apps_dict or {})


def test_get_process_by_bundle_id_matches_executable():
    """通过 CFBundleExecutable 精确匹配到运行中的进程。"""
    apps = {
        "com.tencent.xin": {
            "CFBundleDisplayName": "微信",
            "CFBundleExecutable": "WeChat",
        }
    }
    processes = [
        {"pid": 8215, "name": "WeChat", "cpuUsage": 5.0, "physFootprint": 100000},
    ]

    svc = _make_service()
    with (
        _patch_app_lookup(apps),
        patch.object(SysmonService, "get_processes", return_value=processes),
    ):
        result = svc.get_process_by_bundle_id("com.tencent.xin")

    assert result is not None
    assert result["pid"] == 8215
    assert result["name"] == "WeChat"


def test_get_process_by_bundle_id_case_insensitive():
    """进程名大小写不敏感匹配。"""
    apps = {"com.test.app": {"CFBundleExecutable": "MyApp"}}
    processes = [{"pid": 1, "name": "myapp"}]

    svc = _make_service()
    with (
        _patch_app_lookup(apps),
        patch.object(SysmonService, "get_processes", return_value=processes),
    ):
        result = svc.get_process_by_bundle_id("com.test.app")

    assert result is not None
    assert result["pid"] == 1


def test_get_process_by_bundle_id_no_substring_false_positive():
    """关键回归：clipserviced 不应被误匹配为 Clips 应用。"""
    apps = {"com.apple.clips": {"CFBundleExecutable": "Clips"}}
    processes = [{"pid": 3058, "name": "clipserviced"}]

    svc = _make_service()
    with (
        _patch_app_lookup(apps),
        patch.object(SysmonService, "get_processes", return_value=processes),
    ):
        result = svc.get_process_by_bundle_id("com.apple.clips")

    # Clips 应用未运行（只有守护进程），不应匹配
    assert result is None


def test_get_process_by_bundle_id_app_not_running():
    """应用未运行（进程列表中没有对应可执行文件）返回 None。"""
    apps = {"com.tencent.xin": {"CFBundleExecutable": "WeChat"}}
    processes = [{"pid": 1, "name": "OtherApp"}]

    svc = _make_service()
    with (
        _patch_app_lookup(apps),
        patch.object(SysmonService, "get_processes", return_value=processes),
    ):
        result = svc.get_process_by_bundle_id("com.tencent.xin")

    assert result is None


def test_get_process_by_bundle_id_no_processes():
    """进程列表为空时返回 None。"""
    apps = {"com.test.app": {"CFBundleExecutable": "MyApp"}}

    svc = _make_service()
    with (
        _patch_app_lookup(apps),
        patch.object(SysmonService, "get_processes", return_value=None),
    ):
        result = svc.get_process_by_bundle_id("com.test.app")

    assert result is None


def test_get_process_by_bundle_id_unknown_bundle():
    """未知 Bundle ID（不在已安装列表）返回 None。"""
    processes = [{"pid": 1, "name": "SomeApp"}]

    svc = _make_service()
    with (
        _patch_app_lookup({}),
        patch.object(SysmonService, "get_processes", return_value=processes),
    ):
        result = svc.get_process_by_bundle_id("com.unknown.app")

    assert result is None


def test_get_process_by_bundle_id_no_udid_returns_none():
    """无 UDID 时返回 None（无法查询应用列表）。"""
    svc = SysmonService(udid=None)
    svc._connected = True
    with patch.object(SysmonService, "get_processes", return_value=[]):
        result = svc.get_process_by_bundle_id("com.test.app")
    assert result is None
