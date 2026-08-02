# -*- coding: utf-8 -*-
"""FpsCollector 单元测试

覆盖：
- collect() 返回契约（fps/jank/bigJank）
- Jank/BigJank 检测启发式（帧率突降）
- 不可用时的优雅降级
- jank 计数自增 + collect 后清零
"""

from unittest.mock import MagicMock

from insight_aitest.platform.services.collectors.ios.fps_collector import FpsCollector


def _make_collector():
    adapter = MagicMock()
    adapter.device_id = "test-udid"
    return FpsCollector(adapter, bundle_id="com.example.app")


class TestCollectContract:
    def test_collect_returns_fps_jank_bigjank_keys(self):
        """collect() 必须返回 fps/jank/bigJank 三个字段。"""
        nc = _make_collector()
        result = nc.collect()
        assert set(result.keys()) == {"fps", "jank", "bigJank"}

    def test_collect_returns_zero_when_unavailable(self):
        """Graphics 服务不可用时应返回全 0。"""
        nc = _make_collector()
        nc._available = False
        assert nc.collect() == {"fps": 0, "jank": 0, "bigJank": 0}


class TestJankDetection:
    def test_stable_fps_no_jank(self):
        """稳定 60 FPS 不应产生 Jank。"""
        nc = _make_collector()
        for _ in range(5):
            nc._on_fps_sample(60)
        result = nc.collect()
        assert result["fps"] == 60
        assert result["jank"] == 0
        assert result["bigJank"] == 0

    def test_moderate_drop_counts_jank(self):
        """FPS 从 60 跌到 40（下降 20）应记一次 Jank。"""
        nc = _make_collector()
        nc._on_fps_sample(60)
        nc._on_fps_sample(40)  # 下降 20 >= _DROP_DELTA(20)
        result = nc.collect()
        assert result["fps"] == 40
        assert result["jank"] >= 1

    def test_severe_drop_counts_bigjank(self):
        """FPS 从 60 暴跌到 25 应记一次 BigJank（而非普通 Jank）。"""
        nc = _make_collector()
        nc._on_fps_sample(60)
        nc._on_fps_sample(25)  # <= _BIGJANK_FPS_THRESHOLD(30)
        result = nc.collect()
        assert result["fps"] == 25
        assert result["bigJank"] >= 1

    def test_jank_counter_resets_after_collect(self):
        """collect() 后 Jank 计数应清零，下次从 0 重新计。"""
        nc = _make_collector()
        nc._on_fps_sample(60)
        nc._on_fps_sample(40)  # 1 次 Jank
        first = nc.collect()
        assert first["jank"] >= 1

        # 之后稳定，第二次 collect 应为 0
        nc._on_fps_sample(60)
        nc._on_fps_sample(60)
        second = nc.collect()
        assert second["jank"] == 0

    def test_first_sample_no_jank(self):
        """首个采样（prev=0）不应误判 Jank（无前值可比）。"""
        nc = _make_collector()
        nc._on_fps_sample(10)  # 即使很低，首次也不计 Jank
        result = nc.collect()
        assert result["jank"] == 0
        assert result["bigJank"] == 0

    def test_fps_zero_means_no_render(self):
        """fps=0（锁屏/静止）不计 Jank，且 collect 返回 0。"""
        nc = _make_collector()
        nc._on_fps_sample(60)
        nc._on_fps_sample(0)  # 无前台渲染
        result = nc.collect()
        assert result["fps"] == 0
        # fps=0 不触发 Jank 检测（无实际掉帧，只是没渲染）
        assert result["jank"] == 0
