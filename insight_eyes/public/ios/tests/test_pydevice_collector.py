# -*- coding: utf-8 -*-
"""
IOSPyDeviceCollector 单元测试

测试 py-ios-device 采集器的核心功能，包括：
- 启动/停止功能
- 数据提取（CPU/Memory/FPS/Network/Battery）
- 回调处理
- 线程安全性

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License

Author: Aceyuan361
"""
import unittest
import time
import threading
from unittest.mock import Mock, MagicMock, patch, call


class TestIOSPyDeviceCollector(unittest.TestCase):
    """测试 IOSPyDeviceCollector 核心功能"""

    def setUp(self):
        """测试前置设置"""
        self.test_udid = "00008030-001D29A62EEA802E"
        self.test_bundle_id = "com.example.app"

        # 模拟回调数据
        self.mock_system_data = [
            {
                'Processes': {
                    1234: [1234, 'com.example.app', 0.15, 1024000, 256000000],
                    5678: [5678, 'com.other.app', 0.08, 512000, 128000000]
                },
                'SystemCPUUsage': 0.25
            }
        ]

        self.mock_fps_data = {
            'currentTime': '2025-01-21 12:00:00',
            'fps': 60
        }

    @patch('ios_device.py_ios_device.PyiOSDevice')
    def test_start_success(self, mock_pyiOSDevice_class):
        """测试启动成功"""
        # Mock PyiOSDevice 类
        mock_device = MagicMock()
        mock_pyiOSDevice_class.return_value = mock_device

        # 导入并创建采集器
        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        collector = IOSPyDeviceCollector(self.test_udid, self.test_bundle_id)

        # 启动监控
        result = collector.start()

        # 验证启动成功
        self.assertTrue(result)
        self.assertTrue(collector._is_started)

        # 验证 PyiOSDevice 被创建
        mock_pyiOSDevice_class.assert_called_once_with(device_id=self.test_udid)

        # 验证服务被启动
        mock_device.start_get_system.assert_called_once()
        mock_device.start_get_fps.assert_called_once()

        # 验证回调被设置
        start_get_system_call = mock_device.start_get_system.call_args
        start_get_fps_call = mock_device.start_get_fps.call_args

        self.assertIsNotNone(start_get_system_call[1]['callback'])
        self.assertIsNotNone(start_get_fps_call[1]['callback'])

    @patch("ios_device.py_ios_device.PyiOSDevice")
    def test_start_already_started(self, mock_pyiOSDevice_class):
        """测试重复启动（幂等性）"""
        mock_device = MagicMock()
        mock_pyiOSDevice_class.return_value = mock_device

        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        collector = IOSPyDeviceCollector(self.test_udid, self.test_bundle_id)
        collector._is_started = True  # 模拟已启动

        # 再次启动
        result = collector.start()

        # 验证返回 True（幂等）
        self.assertTrue(result)

        # 验证 PyiOSDevice 不会被重复创建
        mock_pyiOSDevice_class.assert_not_called()

    @patch("ios_device.py_ios_device.PyiOSDevice")
    def test_start_import_error(self, mock_pyiOSDevice_class):
        """测试依赖库缺失"""
        # Mock ImportError
        mock_pyiOSDevice_class.side_effect = ImportError("No module named 'ios_device'")

        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        collector = IOSPyDeviceCollector(self.test_udid, self.test_bundle_id)

        # 启动应该失败
        result = collector.start()

        self.assertFalse(result)
        self.assertFalse(collector._is_started)

    @patch("ios_device.py_ios_device.PyiOSDevice")
    def test_start_exception(self, mock_pyiOSDevice_class):
        """测试启动异常"""
        # Mock 其他异常
        mock_pyiOSDevice_class.side_effect = Exception("Device connection failed")

        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        collector = IOSPyDeviceCollector(self.test_udid, self.test_bundle_id)

        # 启动应该失败
        result = collector.start()

        self.assertFalse(result)
        self.assertFalse(collector._is_started)

    @patch("ios_device.py_ios_device.PyiOSDevice")
    def test_stop(self, mock_pyiOSDevice_class):
        """测试停止功能"""
        mock_device = MagicMock()
        mock_pyiOSDevice_class.return_value = mock_device

        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        collector = IOSPyDeviceCollector(self.test_udid, self.test_bundle_id)
        collector._is_started = True
        collector._device = mock_device

        # 模拟缓存数据
        collector._cached_data['system'] = self.mock_system_data
        collector._cached_data['fps'] = self.mock_fps_data

        # 停止监控
        collector.stop()

        # 验证服务被停止
        mock_device.stop_get_fps.assert_called_once()
        mock_device.stop_get_system.assert_called_once()
        mock_device.stop.assert_called_once()

        # 验证状态被重置
        self.assertFalse(collector._is_started)
        self.assertIsNone(collector._device)

        # 验证缓存被清除
        self.assertEqual(len(collector._cached_data), 0)
        self.assertEqual(len(collector._last_update), 0)

    @patch("ios_device.py_ios_device.PyiOSDevice")
    def test_stop_not_started(self, mock_pyiOSDevice_class):
        """测试停止未启动的采集器（幂等性）"""
        mock_device = MagicMock()
        mock_pyiOSDevice_class.return_value = mock_device

        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        collector = IOSPyDeviceCollector(self.test_udid, self.test_bundle_id)

        # 停止（未启动状态）
        collector.stop()

        # 验证不会调用停止方法
        mock_device.stop_get_fps.assert_not_called()
        mock_device.stop_get_system.assert_not_called()

    @patch("ios_device.py_ios_device.PyiOSDevice")
    def test_stop_exception_handling(self, mock_pyiOSDevice_class):
        """测试停止时的异常处理"""
        mock_device = MagicMock()
        mock_pyiOSDevice_class.return_value = mock_device

        # Mock 停止方法抛出异常
        mock_device.stop_get_fps.side_effect = Exception("Stop failed")

        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        collector = IOSPyDeviceCollector(self.test_udid, self.test_bundle_id)
        collector._is_started = True
        collector._device = mock_device

        # 停止应该处理异常
        collector.stop()

        # 验证状态仍然被重置
        self.assertFalse(collector._is_started)
        self.assertIsNone(collector._device)

    @patch("ios_device.py_ios_device.PyiOSDevice")
    def test_on_system_data_callback(self, mock_pyiOSDevice_class):
        """测试系统数据回调处理"""
        mock_device = MagicMock()
        mock_pyiOSDevice_class.return_value = mock_device

        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        collector = IOSPyDeviceCollector(self.test_udid, self.test_bundle_id)

        # 创建 Mock 回调数据对象
        mock_res = MagicMock()
        mock_res.selector = self.mock_system_data

        # 调用回调
        collector._on_system_data(mock_res)

        # 验证数据被缓存
        self.assertIn('system', collector._cached_data)
        self.assertEqual(collector._cached_data['system'], self.mock_system_data)

        # 验证时间戳被更新
        self.assertIn('system', collector._last_update)
        self.assertGreater(collector._last_update['system'], 0)

    @patch("ios_device.py_ios_device.PyiOSDevice")
    def test_on_fps_data_callback(self, mock_pyiOSDevice_class):
        """测试 FPS 数据回调处理"""
        mock_device = MagicMock()
        mock_pyiOSDevice_class.return_value = mock_device

        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        collector = IOSPyDeviceCollector(self.test_udid, self.test_bundle_id)

        # 创建 Mock 回调数据对象
        mock_res = MagicMock()
        mock_res.selector = self.mock_fps_data

        # 调用回调
        collector._on_fps_data(mock_res)

        # 验证数据被缓存
        self.assertIn('fps', collector._cached_data)
        self.assertEqual(collector._cached_data['fps'], self.mock_fps_data)

        # 验证时间戳被更新
        self.assertIn('fps', collector._last_update)
        self.assertGreater(collector._last_update['fps'], 0)

    @patch("ios_device.py_ios_device.PyiOSDevice")
    def test_on_system_data_callback_exception(self, mock_pyiOSDevice_class):
        """测试系统数据回调异常处理"""
        mock_device = MagicMock()
        mock_pyiOSDevice_class.return_value = mock_device

        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        collector = IOSPyDeviceCollector(self.test_udid, self.test_bundle_id)

        # 传入无效数据（没有 selector 属性）
        mock_res = MagicMock(spec=[])  # 空 spec，没有 selector

        # 调用回调应该不抛出异常
        collector._on_system_data(mock_res)

        # 验证数据没有被缓存
        self.assertNotIn('system', collector._cached_data)

    @patch("ios_device.py_ios_device.PyiOSDevice")
    def test_extract_cpu_success(self, mock_pyiOSDevice_class):
        """测试 CPU 数据提取（成功）"""
        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        collector = IOSPyDeviceCollector(self.test_udid, self.test_bundle_id)

        # 提取 CPU 数据
        cpu_data = collector._extract_cpu(self.mock_system_data, self.test_bundle_id)

        # 验证返回值格式
        self.assertIn('appCpuRate', cpu_data)
        self.assertIn('sysCpuRate', cpu_data)

        # 验证数值计算（0.15 * 100 = 15%）
        self.assertEqual(cpu_data['appCpuRate'], 15.0)
        self.assertEqual(cpu_data['sysCpuRate'], 0.0)

    @patch("ios_device.py_ios_device.PyiOSDevice")
    def test_extract_cpu_no_matching_process(self, mock_pyiOSDevice_class):
        """测试 CPU 数据提取（无匹配进程）"""
        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        collector = IOSPyDeviceCollector(self.test_udid, "org.unknown.app")

        # 提取 CPU 数据（不匹配的 bundle_id - "org" 不在 "com.example.app" 中）
        cpu_data = collector._extract_cpu(self.mock_system_data, "org.unknown.app")

        # 验证返回默认值
        self.assertEqual(cpu_data['appCpuRate'], 0.0)
        self.assertEqual(cpu_data['sysCpuRate'], 0.0)

    @patch("ios_device.py_ios_device.PyiOSDevice")
    def test_extract_cpu_empty_data(self, mock_pyiOSDevice_class):
        """测试 CPU 数据提取（空数据）"""
        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        collector = IOSPyDeviceCollector(self.test_udid, self.test_bundle_id)

        # 测试空列表
        cpu_data = collector._extract_cpu([], self.test_bundle_id)
        self.assertEqual(cpu_data['appCpuRate'], 0.0)
        self.assertEqual(cpu_data['sysCpuRate'], 0.0)

        # 测试 None
        cpu_data = collector._extract_cpu(None, self.test_bundle_id)
        self.assertEqual(cpu_data['appCpuRate'], 0.0)
        self.assertEqual(cpu_data['sysCpuRate'], 0.0)

    @patch("ios_device.py_ios_device.PyiOSDevice")
    def test_extract_cpu_malformed_data(self, mock_pyiOSDevice_class):
        """测试 CPU 数据提取（格式错误）"""
        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        collector = IOSPyDeviceCollector(self.test_udid, self.test_bundle_id)

        # 测试没有 'Processes' 键
        malformed_data = [{'SystemCPUUsage': 0.25}]
        cpu_data = collector._extract_cpu(malformed_data, self.test_bundle_id)

        self.assertEqual(cpu_data['appCpuRate'], 0.0)
        self.assertEqual(cpu_data['sysCpuRate'], 0.0)

    @patch("ios_device.py_ios_device.PyiOSDevice")
    def test_extract_cpu_partial_process_data(self, mock_pyiOSDevice_class):
        """测试 CPU 数据提取（进程数据不完整）"""
        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        collector = IOSPyDeviceCollector(self.test_udid, self.test_bundle_id)

        # 进程数据长度 < 3
        partial_data = [
            {
                'Processes': {
                    1234: [1234, 'com.example.app']  # 只有 2 个元素
                }
            }
        ]

        cpu_data = collector._extract_cpu(partial_data, self.test_bundle_id)

        self.assertEqual(cpu_data['appCpuRate'], 0.0)

    @patch("ios_device.py_ios_device.PyiOSDevice")
    def test_extract_memory_success(self, mock_pyiOSDevice_class):
        """测试内存数据提取（成功）"""
        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        collector = IOSPyDeviceCollector(self.test_udid, self.test_bundle_id)

        # 提取内存数据
        memory_data = collector._extract_memory(self.mock_system_data, self.test_bundle_id)

        # 验证返回值格式
        self.assertIn('totalPass', memory_data)
        self.assertIn('nativePass', memory_data)
        self.assertIn('dalvikPass', memory_data)

        # 验证数值计算（256000000 bytes / (1024*1024) ≈ 244.14 MB）
        expected_mb = 256000000 / (1024 * 1024)
        self.assertAlmostEqual(memory_data['totalPass'], expected_mb, places=2)
        self.assertEqual(memory_data['nativePass'], memory_data['totalPass'])
        self.assertEqual(memory_data['dalvikPass'], 0.0)

    @patch("ios_device.py_ios_device.PyiOSDevice")
    def test_extract_memory_no_matching_process(self, mock_pyiOSDevice_class):
        """测试内存数据提取（无匹配进程）"""
        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        collector = IOSPyDeviceCollector(self.test_udid, "org.unknown.app")

        # 提取内存数据（不匹配的 bundle_id - "org" 不在 "com.example.app" 中）
        memory_data = collector._extract_memory(self.mock_system_data, "org.unknown.app")

        # 验证返回默认值
        self.assertEqual(memory_data['totalPass'], 0.0)
        self.assertEqual(memory_data['nativePass'], 0.0)
        self.assertEqual(memory_data['dalvikPass'], 0.0)

    @patch("ios_device.py_ios_device.PyiOSDevice")
    def test_extract_memory_empty_data(self, mock_pyiOSDevice_class):
        """测试内存数据提取（空数据）"""
        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        collector = IOSPyDeviceCollector(self.test_udid, self.test_bundle_id)

        # 测试空列表
        memory_data = collector._extract_memory([], self.test_bundle_id)
        self.assertEqual(memory_data['totalPass'], 0.0)
        self.assertEqual(memory_data['nativePass'], 0.0)

        # 测试 None
        memory_data = collector._extract_memory(None, self.test_bundle_id)
        self.assertEqual(memory_data['totalPass'], 0.0)
        self.assertEqual(memory_data['nativePass'], 0.0)

    @patch("ios_device.py_ios_device.PyiOSDevice")
    def test_extract_memory_malformed_data(self, mock_pyiOSDevice_class):
        """测试内存数据提取（格式错误）"""
        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        collector = IOSPyDeviceCollector(self.test_udid, self.test_bundle_id)

        # 测试没有 'Processes' 键
        malformed_data = [{'SystemCPUUsage': 0.25}]
        memory_data = collector._extract_memory(malformed_data, self.test_bundle_id)

        self.assertEqual(memory_data['totalPass'], 0.0)
        self.assertEqual(memory_data['nativePass'], 0.0)

    @patch("ios_device.py_ios_device.PyiOSDevice")
    def test_extract_memory_partial_process_data(self, mock_pyiOSDevice_class):
        """测试内存数据提取（进程数据不完整）"""
        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        collector = IOSPyDeviceCollector(self.test_udid, self.test_bundle_id)

        # 进程数据长度 < 5
        partial_data = [
            {
                'Processes': {
                    1234: [1234, 'com.example.app', 0.15]  # 只有 3 个元素
                }
            }
        ]

        memory_data = collector._extract_memory(partial_data, self.test_bundle_id)

        self.assertEqual(memory_data['totalPass'], 0.0)

    @patch("ios_device.py_ios_device.PyiOSDevice")
    def test_collect_cpu_with_cache(self, mock_pyiOSDevice_class):
        """测试 CPU 采集（从缓存）"""
        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        collector = IOSPyDeviceCollector(self.test_udid, self.test_bundle_id)

        # 设置缓存数据
        collector._cached_data['system'] = self.mock_system_data
        collector._last_update['system'] = time.time()

        # 采集 CPU
        cpu_data = collector.collect_cpu()

        # 验证返回值
        self.assertIsNotNone(cpu_data)
        self.assertEqual(cpu_data['appCpuRate'], 15.0)

    @patch("ios_device.py_ios_device.PyiOSDevice")
    def test_collect_cpu_no_cache(self, mock_pyiOSDevice_class):
        """测试 CPU 采集（无缓存数据）"""
        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        collector = IOSPyDeviceCollector(self.test_udid, self.test_bundle_id)

        # 不设置缓存数据
        # 采集 CPU 应该返回 None
        cpu_data = collector.collect_cpu()

        self.assertIsNone(cpu_data)

    @patch("ios_device.py_ios_device.PyiOSDevice")
    def test_collect_cpu_expired_cache(self, mock_pyiOSDevice_class):
        """测试 CPU 采集（缓存过期）"""
        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        collector = IOSPyDeviceCollector(self.test_udid, self.test_bundle_id)

        # 设置过期缓存（5 秒前）
        collector._cached_data['system'] = self.mock_system_data
        collector._last_update['system'] = time.time() - 5.0

        # 采集 CPU 应该返回 None（过期）
        cpu_data = collector.collect_cpu()

        self.assertIsNone(cpu_data)

    @patch("ios_device.py_ios_device.PyiOSDevice")
    def test_collect_memory_with_cache(self, mock_pyiOSDevice_class):
        """测试内存采集（从缓存）"""
        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        collector = IOSPyDeviceCollector(self.test_udid, self.test_bundle_id)

        # 设置缓存数据
        collector._cached_data['system'] = self.mock_system_data
        collector._last_update['system'] = time.time()

        # 采集内存
        memory_data = collector.collect_memory()

        # 验证返回值
        self.assertIsNotNone(memory_data)
        expected_mb = 256000000 / (1024 * 1024)
        self.assertAlmostEqual(memory_data['totalPass'], expected_mb, places=2)

    @patch("ios_device.py_ios_device.PyiOSDevice")
    def test_collect_memory_no_cache(self, mock_pyiOSDevice_class):
        """测试内存采集（无缓存数据）"""
        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        collector = IOSPyDeviceCollector(self.test_udid, self.test_bundle_id)

        # 不设置缓存数据
        memory_data = collector.collect_memory()

        self.assertIsNone(memory_data)

    @patch("ios_device.py_ios_device.PyiOSDevice")
    def test_collect_fps_with_cache(self, mock_pyiOSDevice_class):
        """测试 FPS 采集（从缓存）"""
        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        collector = IOSPyDeviceCollector(self.test_udid, self.test_bundle_id)

        # 设置缓存数据
        collector._cached_data['fps'] = self.mock_fps_data
        collector._last_update['fps'] = time.time()

        # 采集 FPS
        fps_data = collector.collect_fps()

        # 验证返回值
        self.assertIsNotNone(fps_data)
        self.assertEqual(fps_data['fps'], 60)

    @patch("ios_device.py_ios_device.PyiOSDevice")
    def test_collect_fps_no_cache(self, mock_pyiOSDevice_class):
        """测试 FPS 采集（无缓存数据）"""
        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        collector = IOSPyDeviceCollector(self.test_udid, self.test_bundle_id)

        # 不设置缓存数据
        fps_data = collector.collect_fps()

        self.assertIsNone(fps_data)

    @patch("ios_device.py_ios_device.PyiOSDevice")
    def test_collect_network(self, mock_pyiOSDevice_class):
        """测试网络采集"""
        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        collector = IOSPyDeviceCollector(self.test_udid, self.test_bundle_id)

        # 采集网络（返回默认值）
        network_data = collector.collect_network()

        # 验证返回值格式
        self.assertIsNotNone(network_data)
        self.assertEqual(network_data['upFlow'], 0.0)
        self.assertEqual(network_data['downFlow'], 0.0)

    @patch("ios_device.py_ios_device.PyiOSDevice")
    def test_collect_battery(self, mock_pyiOSDevice_class):
        """测试电池采集"""
        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        collector = IOSPyDeviceCollector(self.test_udid, self.test_bundle_id)

        # 采集电池（返回默认值）
        battery_data = collector.collect_battery()

        # 验证返回值格式
        self.assertIsNotNone(battery_data)
        self.assertEqual(battery_data['level'], 100)
        self.assertEqual(battery_data['temperature'], 25.0)
        self.assertEqual(battery_data['current'], 0.0)

    @patch("ios_device.py_ios_device.PyiOSDevice")
    def test_get_cached_data_valid(self, mock_pyiOSDevice_class):
        """测试获取有效缓存数据"""
        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        collector = IOSPyDeviceCollector(self.test_udid, self.test_bundle_id)

        # 设置缓存数据（1 秒前）
        test_data = {'test': 'data'}
        collector._cached_data['test'] = test_data
        collector._last_update['test'] = time.time() - 1.0

        # 获取缓存（最大有效时间 3 秒）
        cached = collector._get_cached_data('test', max_age=3.0)

        self.assertEqual(cached, test_data)

    @patch("ios_device.py_ios_device.PyiOSDevice")
    def test_get_cached_data_expired(self, mock_pyiOSDevice_class):
        """测试获取过期缓存数据"""
        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        collector = IOSPyDeviceCollector(self.test_udid, self.test_bundle_id)

        # 设置缓存数据（5 秒前）
        test_data = {'test': 'data'}
        collector._cached_data['test'] = test_data
        collector._last_update['test'] = time.time() - 5.0

        # 获取缓存（最大有效时间 3 秒）
        cached = collector._get_cached_data('test', max_age=3.0)

        # 应该返回 None（过期）
        self.assertIsNone(cached)

    @patch("ios_device.py_ios_device.PyiOSDevice")
    def test_get_cached_data_not_exists(self, mock_pyiOSDevice_class):
        """测试获取不存在的缓存数据"""
        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        collector = IOSPyDeviceCollector(self.test_udid, self.test_bundle_id)

        # 获取不存在的缓存
        cached = collector._get_cached_data('nonexistent', max_age=3.0)

        self.assertIsNone(cached)

    @patch("ios_device.py_ios_device.PyiOSDevice")
    def test_thread_safety_callback(self, mock_pyiOSDevice_class):
        """测试回调处理的线程安全性"""
        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        collector = IOSPyDeviceCollector(self.test_udid, self.test_bundle_id)

        # 模拟多线程回调
        def callback_worker(thread_id):
            mock_res = MagicMock()
            mock_res.selector = [
                {
                    'Processes': {
                        thread_id: [thread_id, f'com.app.{thread_id}', 0.1, 1000000, 100000000]
                    }
                }
            ]
            for _ in range(100):
                collector._on_system_data(mock_res)

        # 启动多个线程
        threads = []
        for i in range(10):
            t = threading.Thread(target=callback_worker, args=(i,))
            threads.append(t)
            t.start()

        # 等待所有线程完成
        for t in threads:
            t.join()

        # 验证缓存数据一致性（不应该崩溃）
        self.assertIn('system', collector._cached_data)
        self.assertIn('system', collector._last_update)

    @patch("ios_device.py_ios_device.PyiOSDevice")
    def test_thread_safety_collect(self, mock_pyiOSDevice_class):
        """测试采集方法的线程安全性"""
        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        collector = IOSPyDeviceCollector(self.test_udid, self.test_bundle_id)

        # 设置缓存数据
        collector._cached_data['system'] = self.mock_system_data
        collector._cached_data['fps'] = self.mock_fps_data
        collector._last_update['system'] = time.time()
        collector._last_update['fps'] = time.time()

        results = {'cpu': [], 'memory': [], 'fps': []}
        errors = []

        def collect_worker():
            try:
                for _ in range(50):
                    cpu = collector.collect_cpu()
                    memory = collector.collect_memory()
                    fps = collector.collect_fps()
                    results['cpu'].append(cpu)
                    results['memory'].append(memory)
                    results['fps'].append(fps)
            except Exception as e:
                errors.append(e)

        # 启动多个线程
        threads = []
        for _ in range(5):
            t = threading.Thread(target=collect_worker)
            threads.append(t)
            t.start()

        # 等待所有线程完成
        for t in threads:
            t.join()

        # 验证没有异常
        self.assertEqual(len(errors), 0)

        # 验证所有结果都有效
        self.assertEqual(len(results['cpu']), 250)  # 5 threads * 50 iterations
        self.assertEqual(len(results['memory']), 250)
        self.assertEqual(len(results['fps']), 250)

        # 验证数据一致性
        for cpu in results['cpu']:
            if cpu is not None:
                self.assertIn('appCpuRate', cpu)

    @patch("ios_device.py_ios_device.PyiOSDevice")
    def test_wait_for_initial_data_success(self, mock_pyiOSDevice_class):
        """测试等待初始数据（成功）"""
        mock_device = MagicMock()
        mock_pyiOSDevice_class.return_value = mock_device

        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        collector = IOSPyDeviceCollector(self.test_udid, self.test_bundle_id)

        # 模拟在 0.5 秒后收到数据
        def delayed_data():
            time.sleep(0.5)
            collector._cached_data['system'] = self.mock_system_data

        delay_thread = threading.Thread(target=delayed_data)
        delay_thread.start()

        # 等待初始数据（超时 5 秒）
        collector._wait_for_initial_data(timeout=5.0)

        delay_thread.join()

        # 验证数据已被缓存
        self.assertIn('system', collector._cached_data)

    @patch("ios_device.py_ios_device.PyiOSDevice")
    def test_wait_for_initial_data_timeout(self, mock_pyiOSDevice_class):
        """测试等待初始数据（超时）"""
        mock_device = MagicMock()
        mock_pyiOSDevice_class.return_value = mock_device

        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        collector = IOSPyDeviceCollector(self.test_udid, self.test_bundle_id)

        # 不设置任何数据，等待超时
        collector._wait_for_initial_data(timeout=0.5)

        # 验证没有数据被缓存
        self.assertNotIn('system', collector._cached_data)


def run_tests():
    """运行测试"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestIOSPyDeviceCollector)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    import sys
    sys.exit(0 if run_tests() else 1)
