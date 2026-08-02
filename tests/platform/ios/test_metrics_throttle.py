# -*- coding: utf-8 -*-
"""MetricsThrottle 单元测试

重点覆盖两个关键修复：
1. 进程名大小写不敏感匹配（aweme 能匹配到进程名 "Aweme"）
2. CPU 使用率按核心数归一化（sysmontap 非归一化值 / 核心数 = PerfDog 标准）
"""

from insight_aitest.platform.services.collectors.ios.metrics_throttle import MetricsThrottle


def _make_proc(pid, name, cpu, mem_bytes, exec_name="", comm=""):
    """构造一个 sysmontap 进程字典。"""
    return {
        "pid": pid,
        "name": name,
        "execName": exec_name,
        "comm": comm,
        "cpuUsage": cpu,
        "physFootprint": mem_bytes,
    }


class TestCpuNormalization:
    """CPU 使用率归一化（按核心数）。"""

    def test_cpu_normalized_by_core_count(self):
        """6 核设备上，原始 cpuUsage=42 应归一化为 7.0（42/6）。

        注意：首批数据用于建立进程缓存（目标 PID 尚未知，不累加 CPU），
        需要第二批数据才能采集到归一化后的值。
        """
        throttle = MetricsThrottle(target_frequency=1.0, cpu_core_count=6)
        # 第一批：填充进程缓存
        throttle.on_raw_batch(
            [_make_proc(pid=609, name="Aweme", cpu=42.13, mem_bytes=449433368)]
        )
        # 第一次 get_metrics 解析出目标 PID
        throttle.get_metrics("com.ss.iphone.aweme")
        assert throttle._target_pid == 609
        # 第二批：此时目标 PID 已知，CPU 会被归一化累加
        throttle.on_raw_batch(
            [_make_proc(pid=609, name="Aweme", cpu=42.13, mem_bytes=449433368)]
        )
        metrics = throttle.get_metrics("com.ss.iphone.aweme")
        # 42.13 / 6 ≈ 7.02（符合 PerfDog 标准，也符合"刷视频 CPU<10%"的直觉）
        assert abs(metrics["cpu_app"] - 7.02) < 0.1

    def test_core_count_1_means_no_normalization(self):
        """核心数为 1（默认/查询失败）时不归一化，保持原始值。"""
        throttle = MetricsThrottle(target_frequency=1.0, cpu_core_count=1)
        throttle.on_raw_batch([_make_proc(pid=1, name="MyApp", cpu=30.0, mem_bytes=1048576)])
        throttle.get_metrics("com.example.myapp")  # 建立目标 PID
        throttle.on_raw_batch([_make_proc(pid=1, name="MyApp", cpu=30.0, mem_bytes=1048576)])
        metrics = throttle.get_metrics("com.example.myapp")
        assert abs(metrics["cpu_app"] - 30.0) < 0.01

    def test_raw_cpu_none_treated_as_zero(self):
        """cpuUsage=None（第一批数据常见）应视为 0，不抛异常。"""
        throttle = MetricsThrottle(target_frequency=1.0, cpu_core_count=6)
        throttle.on_raw_batch(
            [_make_proc(pid=1, name="App", cpu=None, mem_bytes=1048576)]
        )
        metrics = throttle.get_metrics("com.test.app")
        assert metrics["cpu_app"] == 0.0


class TestCaseInsensitiveMatching:
    """进程名大小写不敏感匹配。"""

    def test_aweme_matches_Aweme(self):
        """bundle id 末段 'aweme' 应匹配到进程名 'Aweme'（首字母大写）。"""
        throttle = MetricsThrottle(target_frequency=1.0, cpu_core_count=6)
        throttle.on_raw_batch(
            [
                _make_proc(pid=609, name="Aweme", cpu=42.0, mem_bytes=449433368),
                _make_proc(pid=70, name="backboardd", cpu=22.0, mem_bytes=89851400),
            ]
        )
        proc = throttle.get_process_info("com.ss.iphone.aweme")
        assert proc is not None
        assert proc["pid"] == 609  # 匹配到 Aweme，不是 backboardd

    def test_matching_sets_target_pid_so_only_target_accumulated(self):
        """匹配成功后 _target_pid 被设置，只累加目标进程的 CPU（不再累加全部）。"""
        throttle = MetricsThrottle(target_frequency=1.0, cpu_core_count=6)
        # 第一批：填充缓存
        throttle.on_raw_batch(
            [
                _make_proc(pid=609, name="Aweme", cpu=42.0, mem_bytes=449433368),
                _make_proc(pid=70, name="backboardd", cpu=22.0, mem_bytes=89851400),
            ]
        )
        # 触发进程查找 → 设置 _target_pid=609
        throttle.get_metrics("com.ss.iphone.aweme")
        assert throttle._target_pid == 609
        # 第二批：此时只应累加 Aweme(42/6=7.0)，不含 backboardd(22/6)
        throttle.on_raw_batch(
            [
                _make_proc(pid=609, name="Aweme", cpu=42.0, mem_bytes=449433368),
                _make_proc(pid=70, name="backboardd", cpu=22.0, mem_bytes=89851400),
            ]
        )
        metrics = throttle.get_metrics("com.ss.iphone.aweme")
        # 应只含 Aweme 的归一化值：42/6=7.0，不含 backboardd 的 22/6
        assert abs(metrics["cpu_app"] - 7.0) < 0.1

    def test_execname_matching_also_case_insensitive(self):
        """execName 字段也应大小写不敏感匹配。"""
        throttle = MetricsThrottle(target_frequency=1.0, cpu_core_count=2)
        throttle.on_raw_batch(
            [_make_proc(pid=1, name="proc", cpu=10.0, mem_bytes=1048576, exec_name="MyApp")]
        )
        proc = throttle.get_process_info("com.example.myapp")
        assert proc is not None
        assert proc["pid"] == 1
