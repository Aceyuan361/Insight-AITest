# -*- coding: utf-8 -*-
"""
AppLookup 单元测试

验证 iOS 应用进程匹配的核心逻辑：
- 从 InstallationProxyService 返回的应用字典构建查找表
- 查找表必须包含 CFBundleExecutable（DVT 进程 name 的真正来源）
- 精确匹配，不做子串匹配（避免 clipserviced 误匹配 Clips）
"""

from unittest.mock import patch
from insight_aitest.platform.services.collectors.ios.app_lookup import AppLookup


def _sample_apps():
    """模拟 InstallationProxyService.get_apps() 返回的应用字典。"""
    return {
        "com.tencent.xin": {
            "CFBundleDisplayName": "微信",
            "CFBundleName": "微信",
            "CFBundleExecutable": "WeChat",
            "ApplicationType": "User",
        },
        "com.apple.clips": {
            "CFBundleDisplayName": "可立拍",
            "CFBundleName": "可立拍",
            "CFBundleExecutable": "Clips",
            "ApplicationType": "User",
        },
        "com.example.noexec": {
            "CFBundleDisplayName": "NoExec",
            "CFBundleName": "NoExec",
            "ApplicationType": "User",
        },
    }


def test_build_lookup_includes_executable():
    """查找表必须包含 CFBundleExecutable 作为键。"""
    apps = _sample_apps()
    AppLookup.invalidate()
    with patch.object(
        AppLookup, "_fetch_installed_apps", return_value=apps
    ):
        lookup = AppLookup._get_lookup("test-udid")

    # CFBundleExecutable 是 DVT 进程 name 的来源，必须能在查找表中找到
    assert lookup.get("WeChat") == "com.tencent.xin"
    assert lookup.get("Clips") == "com.apple.clips"


def test_build_lookup_includes_display_and_bundle_id():
    """查找表也应包含 CFBundleDisplayName 和 Bundle ID 作为备选键。"""
    apps = _sample_apps()
    AppLookup.invalidate()
    with patch.object(
        AppLookup, "_fetch_installed_apps", return_value=apps
    ):
        lookup = AppLookup._get_lookup("test-udid")

    assert lookup.get("com.tencent.xin") == "com.tencent.xin"
    assert lookup.get("微信") == "com.tencent.xin"


def test_get_bundle_id_by_executable_exact_match():
    """进程名精确匹配到可执行文件名。"""
    AppLookup.invalidate()
    with patch.object(
        AppLookup, "_fetch_installed_apps", return_value=_sample_apps()
    ):
        bid = AppLookup.get_bundle_id_by_executable("test-udid", "WeChat")
    assert bid == "com.tencent.xin"


def test_get_bundle_id_by_executable_case_insensitive():
    """大小写不敏感匹配。"""
    AppLookup.invalidate()
    with patch.object(
        AppLookup, "_fetch_installed_apps", return_value=_sample_apps()
    ):
        bid = AppLookup.get_bundle_id_by_executable("test-udid", "wechat")
    assert bid == "com.tencent.xin"


def test_get_bundle_id_by_executable_no_substring_match():
    """关键：不应子串匹配（clipserviced 不应匹配到 Clips）。"""
    AppLookup.invalidate()
    with patch.object(
        AppLookup, "_fetch_installed_apps", return_value=_sample_apps()
    ):
        # clipserviced 是守护进程，不是 Clips 应用
        bid = AppLookup.get_bundle_id_by_executable("test-udid", "clipserviced")
    assert bid is None


def test_get_bundle_id_by_executable_not_found():
    """未运行的应用返回 None。"""
    AppLookup.invalidate()
    with patch.object(
        AppLookup, "_fetch_installed_apps", return_value=_sample_apps()
    ):
        bid = AppLookup.get_bundle_id_by_executable("test-udid", "NonExistent")
    assert bid is None


def test_find_executable_for_bundle():
    """根据 Bundle ID 查找可执行文件名。"""
    AppLookup.invalidate()
    with patch.object(
        AppLookup, "_fetch_installed_apps", return_value=_sample_apps()
    ):
        exe = AppLookup.find_executable_for_bundle("test-udid", "com.tencent.xin")
    assert exe == "WeChat"


def test_find_executable_for_bundle_missing_falls_back_to_display():
    """无 CFBundleExecutable 时退回到 CFBundleDisplayName。"""
    AppLookup.invalidate()
    with patch.object(
        AppLookup, "_fetch_installed_apps", return_value=_sample_apps()
    ):
        exe = AppLookup.find_executable_for_bundle("test-udid", "com.example.noexec")
    assert exe == "NoExec"


def test_find_executable_for_bundle_unknown():
    """未知 Bundle ID 返回 None。"""
    AppLookup.invalidate()
    with patch.object(
        AppLookup, "_fetch_installed_apps", return_value=_sample_apps()
    ):
        exe = AppLookup.find_executable_for_bundle("test-udid", "com.unknown.app")
    assert exe is None


def test_cache_is_shared_across_calls():
    """缓存：同一 UDID 多次调用只查一次应用列表。"""
    AppLookup.invalidate()
    with patch.object(
        AppLookup, "_fetch_installed_apps", return_value=_sample_apps()
    ) as mock_fetch:
        AppLookup.get_bundle_id_by_executable("test-udid", "WeChat")
        AppLookup.get_bundle_id_by_executable("test-udid", "Clips")
        AppLookup.find_executable_for_bundle("test-udid", "com.tencent.xin")
    # 只应查询一次（缓存命中）
    assert mock_fetch.call_count == 1


def test_invalidate_clears_cache():
    """invalidate 后强制重新查询。"""
    AppLookup.invalidate()
    with patch.object(
        AppLookup, "_fetch_installed_apps", return_value=_sample_apps()
    ) as mock_fetch:
        AppLookup.get_bundle_id_by_executable("test-udid", "WeChat")
        AppLookup.invalidate("test-udid")
        AppLookup.get_bundle_id_by_executable("test-udid", "WeChat")
    assert mock_fetch.call_count == 2
