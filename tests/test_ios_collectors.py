# -*- coding: utf-8 -*-
"""
iOS 采集器单元测试
"""

import pytest
from insight_eyes.public.ios.cpu_collector import CPUCollector
from insight_eyes.public.ios.memory_collector import MemoryCollector
from insight_eyes.public.ios.battery_collector import BatteryCollector


class MockAdapter:
    """模拟设备适配器"""

    def __init__(self):
        self._connection = None


class TestCPUCollector:
    """测试 CPU 采集器"""

    def test_cpu_collector_init(self):
        """测试 CPU 采集器初始化"""
        adapter = MockAdapter()
        collector = CPUCollector(adapter)

        assert collector.adapter == adapter
        print("✓ CPU 采集器初始化测试通过")

    def test_cpu_collect(self):
        """测试 CPU 采集"""
        adapter = MockAdapter()
        collector = CPUCollector(adapter)

        result = collector.collect()

        assert 'cpu_app' in result
        assert 'cpu_system' in result
        assert isinstance(result['cpu_app'], (int, float))
        assert isinstance(result['cpu_system'], (int, float))
        print("✓ CPU 采集测试通过")


class TestMemoryCollector:
    """测试内存采集器"""

    def test_memory_collector_init(self):
        """测试内存采集器初始化"""
        adapter = MockAdapter()
        collector = MemoryCollector(adapter)

        assert collector.adapter == adapter
        print("✓ 内存采集器初始化测试通过")

    def test_memory_collect(self):
        """测试内存采集"""
        adapter = MockAdapter()
        collector = MemoryCollector(adapter)

        result = collector.collect()

        assert 'used_mb' in result
        assert 'total_mb' in result
        assert isinstance(result['used_mb'], (int, float))
        assert isinstance(result['total_mb'], (int, float))
        print("✓ 内存采集测试通过")


class TestBatteryCollector:
    """测试电池采集器"""

    def test_battery_collector_init(self):
        """测试电池采集器初始化"""
        adapter = MockAdapter()
        collector = BatteryCollector(adapter)

        assert collector.adapter == adapter
        print("✓ 电池采集器初始化测试通过")

    def test_battery_collect(self):
        """测试电池采集"""
        adapter = MockAdapter()
        collector = BatteryCollector(adapter)

        result = collector.collect()

        assert 'level' in result
        assert 'temperature' in result
        assert isinstance(result['level'], (int, float))
        assert isinstance(result['temperature'], (int, float))
        print("✓ 电池采集测试通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
