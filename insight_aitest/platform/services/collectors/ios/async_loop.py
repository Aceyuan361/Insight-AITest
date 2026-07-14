# -*- coding: utf-8 -*-
"""
AsyncLoopThread — 持久事件循环线程

pymobiledevice3 >=9.x 全面 async 化（create_using_usbmux、get_value、DVT 服务等
均为协程），而设备适配器对外暴露的是同步 API。AsyncLoopThread 在独立线程中运行
一个持久 asyncio 事件循环，供同步代码通过 run_sync() 提交协程。

使用方式::

    loop_thread = AsyncLoopThread()
    loop_thread.start()
    result = loop_thread.run_sync(some_coroutine())
    # 后台长协程
    task = loop_thread.create_task(background_coroutine())
    loop_thread.stop()
"""

import asyncio
import threading
from typing import Any, Awaitable, Optional

from logzero import logger


class AsyncLoopThread:
    """在后台线程中运行持久 asyncio 事件循环。"""

    def __init__(self) -> None:
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._ready = threading.Event()

    def start(self) -> None:
        """启动后台线程和事件循环。"""
        if self._thread is not None and self._thread.is_alive():
            return

        self._ready.clear()
        self._thread = threading.Thread(target=self._run_loop, name="iOSAsyncLoop", daemon=True)
        self._thread.start()
        # 等待 loop 就绪
        self._ready.wait(timeout=5)
        if self._loop is None:
            raise RuntimeError("Failed to start asyncio loop thread")

    def _run_loop(self) -> None:
        """线程入口：创建并运行事件循环。"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._ready.set()
        try:
            self._loop.run_forever()
        finally:
            # 清理未完成的任务
            try:
                pending = asyncio.all_tasks(self._loop)
                for task in pending:
                    task.cancel()
                if pending:
                    self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception:
                pass
            self._loop.close()
            logger.debug("AsyncLoopThread 事件循环已关闭")

    def run_sync(self, coro: Awaitable[Any], timeout: float = 60.0) -> Any:
        """在持久事件循环中执行协程，阻塞当前线程直到完成。

        Args:
            coro: 待执行的协程（或 Awaitable）
            timeout: 超时时间（秒）

        Returns:
            协程的返回值

        Raises:
            RuntimeError: 线程未启动
            TimeoutError: 超时
        """
        if self._loop is None or not self._loop.is_running():
            raise RuntimeError("AsyncLoopThread 未启动，请先调用 start()")

        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    def create_task(self, coro: Awaitable[Any]) -> Optional[asyncio.Task]:
        """在事件循环中创建后台任务（非阻塞）。

        Args:
            coro: 长期运行的协程

        Returns:
            asyncio.Task handle（可在外部 cancel），或 None（loop 未运行）
        """
        if self._loop is None or not self._loop.is_running():
            return None
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    def call_soon_threadsafe(self, callback, *args) -> None:
        """线程安全地在事件循环中调度同步回调。"""
        if self._loop is not None and self._loop.is_running():
            self._loop.call_soon_threadsafe(callback, *args)

    def is_running(self) -> bool:
        """事件循环是否正在运行。"""
        return (
            self._loop is not None
            and self._loop.is_running()
            and self._thread is not None
            and self._thread.is_alive()
        )

    def stop(self, timeout: float = 5.0) -> None:
        """停止事件循环和线程。幂等。"""
        if self._loop is not None and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread is not None:
            self._thread.join(timeout=timeout)
        self._loop = None
        self._thread = None
        self._ready.clear()
