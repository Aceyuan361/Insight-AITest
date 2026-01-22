# -*- coding: utf-8 -*-
"""
IOSAPM 单元测试
"""

import pytest
from insight_eyes.public.ios.ios_apm import IOSAPM, _validate_bundle_id


class TestValidateBundleId:
    """测试 Bundle ID 验证"""

    def test_valid_bundle_id(self):
        """测试有效的 Bundle ID"""
        assert _validate_bundle_id("com.example.app")
        assert _validate_bundle_id("com.company.myapp")
        assert _validate_bundle_id("org.test.app123")
        print("✓ 有效 Bundle ID 验证通过")

    def test_invalid_bundle_id(self):
        """测试无效的 Bundle ID"""
        assert not _validate_bundle_id("example")  # 只有一级
        assert not _validate_bundle_id("")  # 空字符串
        assert not _validate_bundle_id(None)  # None
        assert not _validate_bundle_id("com..app")  # 连续点
        assert not _validate_bundle_id("-com.example")  # 以连字符开头
        assert not _validate_bundle_id("com.example.")  # 以点结尾
        print("✓ 无效 Bundle ID 验证通过")

    def test_bundle_id_too_long(self):
        """测试过长的 Bundle ID"""
        long_id = "com." + "a" * 250
        assert not _validate_bundle_id(long_id)
        print("✓ Bundle ID 长度限制验证通过")


class TestIOSAPMInit:
    """测试 IOSAPM 初始化"""

    def test_init_valid_params(self):
        """测试有效的初始化参数"""
        apm = IOSAPM(
            bundle_name="com.test.app",
            device_id="test_device_udid"
        )

        assert apm.bundle_name == "com.test.app"
        assert apm.device_id == "test_device_udid"
        assert apm.adapter is None
        print("✓ IOSAPM 初始化测试通过")

    def test_init_invalid_bundle_id(self):
        """测试无效的 Bundle ID"""
        with pytest.raises(ValueError, match="无效的 Bundle ID 格式"):
            IOSAPM(
                bundle_name="invalid",
                device_id="test_device"
            )
        print("✓ 无效 Bundle ID 异常抛出测试通过")

    def test_init_invalid_frequency(self):
        """测试无效的采集频率"""
        with pytest.raises(ValueError, match="无效的采集频率"):
            IOSAPM(
                bundle_name="com.test.app",
                device_id="test_device",
                frequency=100
            )

        with pytest.raises(ValueError, match="无效的采集频率"):
            IOSAPM(
                bundle_name="com.test.app",
                device_id="test_device",
                frequency=0
            )
        print("✓ 无效频率异常抛出测试通过")

    def test_init_invalid_device_id(self):
        """测试无效的设备 ID"""
        with pytest.raises(ValueError, match="无效的设备 ID"):
            IOSAPM(
                bundle_name="com.test.app",
                device_id=""
            )

        with pytest.raises(ValueError, match="无效的设备 ID"):
            IOSAPM(
                bundle_name="com.test.app",
                device_id=None
            )
        print("✓ 无效设备 ID 异常抛出测试通过")


class TestIOSAPMCollect:
    """测试 IOSAPM 采集接口"""

    def test_collect_cpu_default(self):
        """测试 CPU 采集（未初始化时返回默认值）"""
        apm = IOSAPM(
            bundle_name="com.test.app",
            device_id="test_device"
        )

        cpu = apm.collectCpu()
        assert 'cpu_app' in cpu
        assert 'cpu_system' in cpu
        assert cpu['cpu_app'] == 0.0
        assert cpu['cpu_system'] == 0.0
        print("✓ CPU 采集默认值测试通过")

    def test_collect_memory_default(self):
        """测试内存采集（未初始化时返回默认值）"""
        apm = IOSAPM(
            bundle_name="com.test.app",
            device_id="test_device"
        )

        memory = apm.collectMemory()
        assert 'used_mb' in memory
        assert 'total_mb' in memory
        assert memory['used_mb'] == 0.0
        assert memory['total_mb'] == 0.0
        print("✓ 内存采集默认值测试通过")

    def test_collect_fps_default(self):
        """测试 FPS 采集（返回默认值）"""
        apm = IOSAPM(
            bundle_name="com.test.app",
            device_id="test_device"
        )

        fps = apm.collectFps()
        assert 'fps' in fps
        assert 'jank' in fps
        assert fps['fps'] == 60
        assert fps['jank'] == 0
        print("✓ FPS 采集默认值测试通过")

    def test_collect_battery_default(self):
        """测试电池采集（未初始化时返回默认值）"""
        apm = IOSAPM(
            bundle_name="com.test.app",
            device_id="test_device"
        )

        battery = apm.collectBattery()
        assert 'level' in battery
        assert 'temperature' in battery
        assert battery['level'] == 100
        assert battery['temperature'] == 25.0
        print("✓ 电池采集默认值测试通过")

    def test_collect_flow_default(self):
        """测试网络流量采集（返回默认值）"""
        apm = IOSAPM(
            bundle_name="com.test.app",
            device_id="test_device"
        )

        flow = apm.collectFlow()
        assert 'upFlow' in flow
        assert 'downFlow' in flow
        assert flow['upFlow'] == 0.0
        assert flow['downFlow'] == 0.0
        print("✓ 网络流量采集默认值测试通过")

    def test_get_all_metrics(self):
        """测试获取所有指标"""
        apm = IOSAPM(
            bundle_name="com.test.app",
            device_id="test_device"
        )

        metrics = apm.getAllMetrics()
        assert 'cpu' in metrics
        assert 'memory' in metrics
        assert 'fps' in metrics
        assert 'network' in metrics
        assert 'battery' in metrics
        print("✓ 所有指标获取测试通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
