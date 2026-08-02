# -*- coding: utf-8 -*-
"""
iOS FPS（帧率）采集器 (pymobiledevice3 v10.x async API)

通过 DVT 的 Graphics 服务（``com.apple.instruments.server.services.graphics.opengl``）
持续采样 ``CoreAnimationFramesPerSecond``，得到前台应用的真实渲染帧率。
该机制与 PerfDog / Xcode OpenGL ES Analyzer 一致，是系统级 Core Animation 合成帧率，
非越狱即可用。

Jank 检测：由于 Graphics 服务按 ~1Hz 推送（无法拿到逐帧时间戳），
这里采用「帧率突降」启发式 —— 连续两次采集的 FPS 显著下降时计入 Jank/BigJank，
参考 PerfDog 的 BigJank（单帧 >700ms ≈ FPS 暴跌到极低）。
"""

import asyncio
import threading
import time
from typing import Dict, Any, Optional
from logzero import logger

from .connection_manager import IOSConnectionManager


class FpsCollector:
    """iOS 帧率采集器（基于 DVT Graphics 服务的 CoreAnimation 帧率）。

    在 IOSConnectionManager 的事件循环上运行后台 Graphics 流，
    持续缓存最新的 FPS；对外提供同步 ``collect()`` 接口。
    """

    # Jank 判定阈值（基于 ~1Hz 的 FPS 采样，启发式）
    # 正常满帧 60；显著掉帧视为 Jank/BigJank
    _JANK_FPS_THRESHOLD = 45  # FPS 跌到 45 以下记一次 Jank
    _BIGJANK_FPS_THRESHOLD = 30  # FPS 跌到 30 以下记一次 BigJank
    _DROP_DELTA = 20  # 相比上次 FPS 下降 >=20 也视为掉帧

    def __init__(self, adapter, bundle_id: str):
        """初始化 FPS 采集器。

        Args:
            adapter: IOSDeviceAdapter 实例（用于获取 device_id）
            bundle_id: 应用 Bundle ID（Graphics 服务是系统级，不按 bundle 过滤，
                       但保留以便日志/未来扩展）
        """
        self.adapter = adapter
        self.bundle_id = bundle_id

        # 最新缓存值（后台流写入，collect() 读取）
        self._latest_fps: int = 0
        self._prev_fps: int = 0
        self._last_sample_time: float = 0.0
        self._lock = threading.Lock()

        # 累计 Jank 计数（自上次 collect() 以来的新增量）
        self._jank_count: int = 0
        self._bigjank_count: int = 0

        # 后台流 task
        self._stream_task: Optional[asyncio.Future] = None
        self._running = False
        self._available = True  # Graphics 服务是否可用

    def start(self):
        """启动 FPS 后台采集流。"""
        if self._running:
            logger.warning("FPS 采集器已在运行")
            return

        device_id = getattr(self.adapter, "device_id", None)
        if not device_id:
            logger.error("无 device_id，无法启动 FPS 采集")
            return

        logger.info("启动 iOS FPS 采集器（DVT Graphics 服务）...")
        self._running = True

        mgr = IOSConnectionManager.get_instance(device_id)
        if not mgr.is_connected:
            mgr.connect()

        self._stream_task = mgr.loop_thread.create_task(self._stream_coroutine())
        logger.info("iOS FPS 采集器已启动")

    def stop(self):
        """停止 FPS 采集流。"""
        if not self._running:
            return

        logger.info("停止 iOS FPS 采集器...")
        self._running = False

        if self._stream_task is not None:
            try:
                self._stream_task.cancel()
            except Exception:
                pass
            self._stream_task = None

        logger.info("iOS FPS 采集器已停止")

    def collect(self) -> Dict[str, Any]:
        """采集当前 FPS 与自上次以来的 Jank/BigJank 增量。

        Returns:
            {'fps': int, 'jank': int, 'bigJank': int}
            - fps: 最新 CoreAnimation 帧率（0 表示当前无前台渲染/锁屏）
            - jank: 自上次 collect() 以来的 Jank 次数
            - bigJank: 自上次 collect() 以来的 BigJank 次数
        """
        if not self._available:
            return {"fps": 0, "jank": 0, "bigJank": 0}

        with self._lock:
            fps = self._latest_fps
            # 取出累计的 Jank 增量并清零（下次从 0 重新计）
            jank = self._jank_count
            bigjank = self._bigjank_count
            self._jank_count = 0
            self._bigjank_count = 0

        logger.debug(f"[iOS FPS] collect: fps={fps}, jank={jank}, bigJank={bigjank}")
        return {"fps": fps, "jank": jank, "bigJank": bigjank}

    async def _stream_coroutine(self):
        """后台协程：通过 DVT Graphics 服务持续接收帧率数据。

        运行在 IOSConnectionManager 的 AsyncLoopThread 上。
        """
        from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
        from pymobiledevice3.services.dvt.instruments.graphics import Graphics

        try:
            device_id = getattr(self.adapter, "device_id", None)
            if not device_id:
                logger.error("FPS 采集协程: 无 device_id")
                self._running = False
                return

            mgr = IOSConnectionManager.get_instance(device_id)
            lockdown = mgr.get_async_lockdown()

            async with DvtProvider(lockdown) as dvt:
                async with Graphics(dvt) as gfx:
                    logger.info("DVT Graphics 流已建立，开始接收帧率数据")

                    async for event in gfx:
                        if not self._running:
                            break

                        fps = event.get("CoreAnimationFramesPerSecond")
                        if fps is None:
                            continue

                        self._on_fps_sample(int(fps))

        except asyncio.CancelledError:
            logger.info("FPS 采集协程已取消")
            raise
        except Exception as e:
            error_type = type(e).__name__
            if "StartService" in error_type or "InvalidService" in error_type:
                logger.warning(
                    f"iOS FPS 采集不可用：Graphics 服务无法启动 ({error_type})。"
                    "将返回占位 FPS。"
                )
                with self._lock:
                    self._available = False
                    self._running = False
                return
            logger.error(f"FPS 采集协程异常: {error_type}: {e}")
            with self._lock:
                self._running = False

    def _on_fps_sample(self, fps: int):
        """处理单个 FPS 采样值：更新缓存 + 检测 Jank。"""
        with self._lock:
            prev = self._prev_fps
            now = time.time()

            # Jank 检测（启发式，基于 ~1Hz 采样）：
            # 1) FPS 绝对值低于阈值
            # 2) 相比上次显著下降（掉帧）
            # 仅在有实际渲染时检测（fps>0 且非首次）
            if prev > 0 and fps > 0:
                dropped = prev - fps
                if fps <= self._BIGJANK_FPS_THRESHOLD or dropped >= self._DROP_DELTA * 2:
                    self._bigjank_count += 1
                elif fps <= self._JANK_FPS_THRESHOLD or dropped >= self._DROP_DELTA:
                    self._jank_count += 1

            self._prev_fps = fps
            self._latest_fps = fps
            self._last_sample_time = now
