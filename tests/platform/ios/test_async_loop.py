# -*- coding: utf-8 -*-
"""AsyncLoopThread 单元测试"""

import asyncio

import pytest

from insight_aitest.platform.services.collectors.ios.async_loop import AsyncLoopThread


class TestAsyncLoopThread:
    """AsyncLoopThread 基础功能测试"""

    def test_run_sync_returns_result(self):
        """run_sync 提交协程并阻塞等待结果"""
        loop_thread = AsyncLoopThread()
        loop_thread.start()

        try:

            async def coro():
                await asyncio.sleep(0.01)
                return 42

            result = loop_thread.run_sync(coro())
            assert result == 42
        finally:
            loop_thread.stop(timeout=2)

    def test_run_sync_with_exception(self):
        """协程内抛异常时 run_sync 重新抛出"""
        loop_thread = AsyncLoopThread()
        loop_thread.start()

        try:

            async def coro():
                raise ValueError("boom")

            with pytest.raises(ValueError, match="boom"):
                loop_thread.run_sync(coro())
        finally:
            loop_thread.stop(timeout=2)

    def test_create_task_runs_in_background(self):
        """create_task 启动后台协程，不阻塞调用线程"""
        loop_thread = AsyncLoopThread()
        loop_thread.start()

        try:
            done_event = asyncio.Event()

            async def bg_coro():
                await asyncio.sleep(0.05)
                done_event.set()

            task = loop_thread.create_task(bg_coro())
            assert task is not None

            # 等待完成
            loop_thread.run_sync(done_event.wait())
        finally:
            loop_thread.stop(timeout=2)

    def test_stop_cleans_up(self):
        """stop 后线程退出"""
        loop_thread = AsyncLoopThread()
        loop_thread.start()
        assert loop_thread.is_running()

        loop_thread.stop(timeout=2)
        assert not loop_thread.is_running()

    def test_stop_idempotent(self):
        """重复 stop 不报错"""
        loop_thread = AsyncLoopThread()
        loop_thread.start()
        loop_thread.stop(timeout=2)
        loop_thread.stop(timeout=2)  # no error
        assert not loop_thread.is_running()

    def test_run_sync_without_start_raises(self):
        """未 start 时 run_sync 抛 RuntimeError"""
        loop_thread = AsyncLoopThread()

        async def coro():
            return 1

        coro_obj = coro()  # 先创建，避免 pytest.raises 退出时未 await 警告
        with pytest.raises(RuntimeError):
            loop_thread.run_sync(coro_obj)
        coro_obj.close()  # 清理未 await 的协程

    def test_is_running_flag(self):
        """is_running 反映线程状态"""
        loop_thread = AsyncLoopThread()
        assert not loop_thread.is_running()
        loop_thread.start()
        assert loop_thread.is_running()
        loop_thread.stop(timeout=2)
        assert not loop_thread.is_running()

    def test_concurrent_run_sync(self):
        """多线程同时调用 run_sync"""
        import threading

        loop_thread = AsyncLoopThread()
        loop_thread.start()
        results = []
        lock = threading.Lock()

        try:

            async def coro(n):
                await asyncio.sleep(0.01)
                return n * 2

            def worker(n):
                r = loop_thread.run_sync(coro(n))
                with lock:
                    results.append(r)

            threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=5)

            assert sorted(results) == [0, 2, 4, 6, 8]
        finally:
            loop_thread.stop(timeout=2)
