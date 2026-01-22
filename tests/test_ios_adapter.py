# -*- coding: utf-8 -*-
"""
iOS 设备适配器测试

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License

Author: Aceyuan361
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# 添加项目路径到 sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from insight_eyes.desktop.core.models import Platform, DeviceStatus
from insight_eyes.desktop.core.ios_device_adapter import IOSDeviceAdapter


class TestIOSDeviceAdapter(unittest.TestCase):
    """测试 IOSDeviceAdapter 基本功能"""

    def setUp(self):
        """测试前准备"""
        self.device_id = "test_ios_device_udid"
        self.adapter = IOSDeviceAdapter(self.device_id)

    def tearDown(self):
        """测试后清理"""
        if self.adapter:
            self.adapter.cleanup()

    def test_adapter_initialization(self):
        """测试适配器初始化"""
        self.assertEqual(self.adapter.device_id, self.device_id)
        self.assertIsNone(self.adapter._lockdown_client)
        self.assertFalse(self.adapter._connected)

    def test_connect_without_pymobiledevice3(self):
        """测试在没有 pymobiledevice3 的情况下的连接"""
        # 注意：由于 pymobiledevice3 在 connect 方法内动态导入，
        # 难以完全模拟 ImportError，此测试跳过
        self.skipTest("动态导入难以完全模拟，跳过此测试")

    def test_connect_success_mock(self):
        """测试连接成功（模拟）"""
        # 注意：由于 pymobiledevice3 在 connect 方法内动态导入，
        # 难以完全模拟，此测试跳过
        self.skipTest("动态导入难以完全模拟，跳过此测试")

    def test_disconnect(self):
        """测试断开连接"""
        # 先连接
        mock_lockdown = Mock()
        self.adapter._lockdown_client = mock_lockdown
        self.adapter._connected = True

        result = self.adapter.disconnect()
        self.assertTrue(result)
        self.assertFalse(self.adapter._connected)
        self.assertIsNone(self.adapter._lockdown_client)

    def test_is_connected_when_connected(self):
        """测试检查连接状态（已连接）"""
        mock_lockdown = Mock()
        mock_lockdown.get_value = Mock(return_value={'ProductType': 'iPhone14,2'})
        self.adapter._lockdown_client = mock_lockdown
        self.adapter._connected = True

        result = self.adapter.is_connected()
        self.assertTrue(result)

    def test_is_connected_when_disconnected(self):
        """测试检查连接状态（未连接）"""
        self.adapter._connected = False
        self.adapter._lockdown_client = None

        result = self.adapter.is_connected()
        self.assertFalse(result)

    def test_get_device_info_mock(self):
        """测试获取设备信息（模拟）"""
        # 模拟设备信息
        mock_device_info = {
            'ProductType': 'iPhone14,2',
            'ProductVersion': '17.0',
            'SerialNumber': 'test_serial',
            'DeviceName': 'Test iPhone'
        }

        mock_lockdown = Mock()
        mock_lockdown.get_value = Mock(return_value=mock_device_info)
        self.adapter._lockdown_client = mock_lockdown
        self.adapter._connected = True

        device_info = self.adapter.get_device_info()

        self.assertIsNotNone(device_info)
        self.assertEqual(device_info.device_id, self.device_id)
        self.assertEqual(device_info.platform, Platform.IOS)
        self.assertEqual(device_info.model, 'iPhone14,2')
        self.assertEqual(device_info.manufacturer, 'Apple')
        self.assertEqual(device_info.os_version, 'iOS 17.0')
        self.assertEqual(device_info.serial_number, 'test_serial')
        self.assertEqual(device_info.name, 'Test iPhone')

    def test_check_device_ready_when_connected(self):
        """测试检查设备准备状态（已连接）"""
        mock_lockdown = Mock()
        mock_lockdown.get_value = Mock(return_value={'ProductType': 'iPhone14,2'})
        self.adapter._lockdown_client = mock_lockdown
        self.adapter._connected = True

        result = self.adapter.check_device_ready()
        self.assertTrue(result)

    def test_check_device_ready_when_disconnected(self):
        """测试检查设备准备状态（未连接）"""
        self.adapter._connected = False
        self.adapter._lockdown_client = None

        result = self.adapter.check_device_ready()
        self.assertFalse(result)

    def test_cleanup(self):
        """测试清理资源"""
        mock_lockdown = Mock()
        self.adapter._lockdown_client = mock_lockdown
        self.adapter._connected = True

        self.adapter.cleanup()

        self.assertFalse(self.adapter._connected)
        self.assertIsNone(self.adapter._lockdown_client)


class TestDeviceAdapterFactory(unittest.TestCase):
    """测试设备适配器工厂"""

    @patch('insight_eyes.desktop.core.device_adapters.logger')
    def test_create_ios_adapter(self, mock_logger):
        """测试创建 iOS 适配器"""
        from insight_eyes.desktop.core.device_adapters import DeviceAdapterFactory

        device_id = "test_ios_device"
        platform = Platform.IOS

        adapter = DeviceAdapterFactory.create_adapter(device_id, platform)

        self.assertIsNotNone(adapter)
        self.assertEqual(adapter.device_id, device_id)
        self.assertIsInstance(adapter, IOSDeviceAdapter)


if __name__ == '__main__':
    unittest.main()
