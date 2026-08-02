# -*- coding: utf-8 -*-
"""NetworkCollector 单元测试

重点覆盖 iOS 17+/26 上 pcapd 服务不可用时的优雅降级。
"""

from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from insight_aitest.platform.services.collectors.ios.network_collector import NetworkCollector


def _make_collector():
    """构造一个 NetworkCollector（mock adapter）。"""
    adapter = MagicMock()
    adapter.device_id = "test-udid"
    return NetworkCollector(adapter, bundle_id="com.example.app")


class TestGracefulDegradation:
    def test_collect_returns_zero_when_unavailable(self):
        """pcapd 不可用时 collect() 应直接返回 0，不做无意义计算。"""
        nc = _make_collector()
        nc._available = False
        result = nc.collect()
        assert result == {"upFlow": 0.0, "downFlow": 0.0}

    def test_startservice_error_marks_unavailable(self):
        """iOS 17+/26 上 pcapd 启动被拒绝（StartServiceError）应标记为不可用。"""
        import asyncio
        from pymobiledevice3.exceptions import StartServiceError

        nc = _make_collector()

        # mock mgr 让 _capture_coroutine 跑起来后立即抛 StartServiceError
        mgr = MagicMock()
        mgr.is_connected = True
        mgr.get_async_lockdown.return_value = MagicMock()
        mgr.loop_thread.create_task = MagicMock(return_value=MagicMock())

        # 直接测试 _capture_coroutine 对 StartServiceError 的处理
        async def run():
            with (
                patch(
                    "insight_aitest.platform.services.collectors.ios.network_collector.IOSConnectionManager.get_instance",
                    return_value=mgr,
                ),
                patch(
                    "insight_aitest.platform.services.collectors.ios.network_collector.PcapdService"
                ) as mock_pcapd_cls,
            ):
                mock_pcapd_cls.return_value.watch = MagicMock(
                    side_effect=StartServiceError(
                        "com.apple.pcapd.shim.remote", "service rejected"
                    )
                )
                await nc._capture_coroutine()

        asyncio.new_event_loop().run_until_complete(run())

        # 应标记为不可用
        assert nc._available is False
        assert nc._running is False
