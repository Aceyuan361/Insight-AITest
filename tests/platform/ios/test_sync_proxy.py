# -*- coding: utf-8 -*-
"""SyncLockdownProxy 单元测试"""

import asyncio

import pytest

from insight_aitest.platform.services.collectors.ios.async_loop import AsyncLoopThread
from insight_aitest.platform.services.collectors.ios.sync_proxy import SyncLockdownProxy


class FakeAsyncLockdown:
    """模拟 pymobiledevice3 v9.x async LockdownServiceProvider"""

    def __init__(self, product_version="15.0"):
        self._values = {
            "DeviceName": "Test iPhone",
            "ProductVersion": product_version,
            "ProductType": "iPhone12,1",
        }
        self.product_version = product_version
        self.closed = False

    async def get_value(self, domain=None, key=None):
        await asyncio.sleep(0.001)
        if key:
            return self._values.get(key)
        return self._values

    async def close(self):
        self.closed = True

    async def start_lockdown_service(self, name, include_escrow_bag=False):
        return f"service:{name}"

    @property
    def udid(self):
        return "test-udid-1234"


class TestSyncLockdownProxy:
    """SyncLockdownProxy 自动 await 桥接测试"""

    @pytest.fixture
    def loop_thread(self):
        lt = AsyncLoopThread()
        lt.start()
        yield lt
        lt.stop(timeout=2)

    def test_async_method_auto_awaited(self, loop_thread):
        """async 方法通过 proxy 调用时自动 await"""
        inner = FakeAsyncLockdown(product_version="15.5")
        proxy = SyncLockdownProxy(inner, loop_thread)

        result = proxy.get_value(key="ProductVersion")
        assert result == "15.5"

    def test_sync_property_passthrough(self, loop_thread):
        """非 async 属性直接透传"""
        inner = FakeAsyncLockdown()
        proxy = SyncLockdownProxy(inner, loop_thread)

        assert proxy.product_version == "15.0"
        assert proxy.udid == "test-udid-1234"

    def test_method_with_multiple_args(self, loop_thread):
        """带多个参数的 async 方法正常工作"""
        inner = FakeAsyncLockdown()
        proxy = SyncLockdownProxy(inner, loop_thread)

        result = proxy.start_lockdown_service("com.apple.test", include_escrow_bag=True)
        assert result == "service:com.apple.test"

    def test_method_no_args(self, loop_thread):
        """无参数 async 方法正常工作"""
        inner = FakeAsyncLockdown()
        proxy = SyncLockdownProxy(inner, loop_thread)

        proxy.close()
        assert inner.closed is True

    def test_method_raises_propagates(self, loop_thread):
        """async 方法内异常传播到调用方"""

        class ErrorLockdown:
            async def get_value(self, domain=None, key=None):
                raise RuntimeError("device error")

        proxy = SyncLockdownProxy(ErrorLockdown(), loop_thread)
        with pytest.raises(RuntimeError, match="device error"):
            proxy.get_value(key="X")

    def test_get_inner(self, loop_thread):
        """get_inner 返回原始 async 对象"""
        inner = FakeAsyncLockdown()
        proxy = SyncLockdownProxy(inner, loop_thread)

        assert proxy.get_inner() is inner

    def test_is_async_method_detection(self, loop_thread):
        """正确识别 coroutine function vs 普通方法"""

        class Mixed:
            sync_attr = "hello"

            def sync_method(self):
                return 42

            async def async_method(self):
                return 99

        obj = Mixed()
        proxy = SyncLockdownProxy(obj, loop_thread)

        # sync 属性/方法直接透传
        assert proxy.sync_attr == "hello"
        # 注意：sync_method 返回的是结果而非协程，因为 __getattr__ 对非 coroutine 不拦截
        # 但 SyncLockdownProxy 设计为：方法调用先返回 callable wrapper，判断返回值
        # sync 方法应该直接调用
        assert proxy.sync_method() == 42
        # async 方法自动 await
        assert proxy.async_method() == 99
