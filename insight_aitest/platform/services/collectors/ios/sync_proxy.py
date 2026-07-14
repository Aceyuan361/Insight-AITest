# -*- coding: utf-8 -*-
"""
SyncLockdownProxy — async LockdownServiceProvider 的同步代理

pymobiledevice3 >=9.x 将 lockdown 的 ``get_value``、``start_lockdown_service`` 等
方法改为 ``async def``。现有设备适配器代码以同步方式调用这些方法（如
``lockdown.get_value(key="DeviceName")``）。

SyncLockdownProxy 包装任意 async lockdown 对象，通过 ``__getattr__`` 拦截属性访问：
- 若属性是 coroutine function，返回一个 sync wrapper（内部调用
  ``loop_thread.run_sync(coro)`` 自动 await）
- 否则直接透传

这样现有同步代码无需修改即可与 pymobiledevice3 >=9.x 交互。

使用方式::

    proxy = SyncLockdownProxy(async_lockdown, loop_thread)
    name = proxy.get_value(key="DeviceName")   # 自动 await
    ver = proxy.product_version                  # 直接透传 property
"""

import inspect
from typing import Any


from .async_loop import AsyncLoopThread


class SyncLockdownProxy:
    """将 async LockdownServiceProvider 包装为同步接口。"""

    def __init__(self, inner: Any, loop_thread: AsyncLoopThread) -> None:
        object.__setattr__(self, "_inner", inner)
        object.__setattr__(self, "_loop_thread", loop_thread)

    def __getattr__(self, name: str) -> Any:
        inner = object.__getattribute__(self, "_inner")
        attr = getattr(inner, name)

        # 如果是 coroutine function，返回 sync wrapper
        if inspect.iscoroutinefunction(attr):
            loop_thread = object.__getattribute__(self, "_loop_thread")

            def sync_wrapper(*args, **kwargs):
                coro = attr(*args, **kwargs)
                return loop_thread.run_sync(coro)

            return sync_wrapper

        # 如果是普通方法（非 async），直接调用
        if callable(attr):

            def plain_wrapper(*args, **kwargs):
                return attr(*args, **kwargs)

            return plain_wrapper

        # 非可调用属性：直接透传（property、类变量等）
        return attr

    def get_inner(self) -> Any:
        """返回被包装的原始 async 对象。"""
        return object.__getattribute__(self, "_inner")
