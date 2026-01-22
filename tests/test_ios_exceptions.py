# -*- coding: utf-8 -*-
"""
iOS 异常处理单元测试
"""

import pytest
from insight_eyes.public.ios.exceptions import (
    DeviceNotTrustedError,
    DeviceNotFoundError,
    DeviceConnectionError,
    DeveloperModeNotEnabledError,
    PMD3NotInstalledError,
    InvalidBundleIdError,
    CollectionTimeoutError
)


class TestDeviceNotTrustedError:
    """测试设备未信任异常"""

    def test_basic(self):
        """测试基本异常"""
        error = DeviceNotTrustedError("test_device")
        assert "未信任" in str(error)
        assert "test_device" in error.details
        print("✓ DeviceNotTrustedError 基本测试通过")

    def test_user_guide(self):
        """测试用户指南"""
        error = DeviceNotTrustedError()
        guide = error.get_user_guide()
        assert "信任" in guide
        assert "解锁" in guide
        print("✓ 用户指南测试通过")


class TestPMD3NotInstalledError:
    """测试 pymobiledevice3 未安装异常"""

    def test_basic(self):
        """测试基本异常"""
        error = PMD3NotInstalledError()
        assert "pymobiledevice3" in str(error)
        assert "未安装" in str(error)
        print("✓ PMD3NotInstalledError 基本测试通过")

    def test_install_command(self):
        """测试安装命令"""
        error = PMD3NotInstalledError()
        cmd = error.get_install_command()
        assert "pip install" in cmd
        assert "pymobiledevice3" in cmd
        print("✓ 安装命令测试通过")


class TestInvalidBundleIdError:
    """测试无效 Bundle ID 异常"""

    def test_basic(self):
        """测试基本异常"""
        error = InvalidBundleIdError("invalid..bundle")
        assert "无效" in str(error)
        assert "invalid..bundle" in error.details
        print("✓ InvalidBundleIdError 基本测试通过")


class TestCollectionTimeoutError:
    """测试采集超时异常"""

    def test_basic(self):
        """测试基本异常"""
        error = CollectionTimeoutError("CPU", 5.0)
        assert "超时" in str(error)
        assert "CPU" in error.details
        assert "5.0" in error.details
        assert error.metric_name == "CPU"
        assert error.timeout == 5.0
        print("✓ CollectionTimeoutError 基本测试通过")


class TestDeviceConnectionError:
    """测试设备连接异常"""

    def test_with_reason(self):
        """测试带原因的异常"""
        error = DeviceConnectionError("device123", "timeout")
        assert "无法连接" in str(error)
        assert "device123" in error.details
        assert "timeout" in error.details
        assert error.device_id == "device123"
        assert error.reason == "timeout"
        print("✓ DeviceConnectionError 带原因测试通过")

    def test_without_reason(self):
        """测试不带原因的异常"""
        error = DeviceConnectionError("device123")
        assert "device123" in str(error)
        assert error.reason is None
        print("✓ DeviceConnectionError 不带原因测试通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
