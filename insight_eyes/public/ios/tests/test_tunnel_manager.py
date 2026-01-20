# -*- coding: utf-8 -*-
"""
iOS 隧道管理器单元测试
测试 IOSTunnelManager 的核心功能

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License

Author: Aceyuan361
"""
import unittest
from unittest.mock import Mock, MagicMock, patch
import subprocess

# 注意：这些测试需要 pymobiledevice3 才能运行完整


class TestIOSTunnelManager(unittest.TestCase):
    """测试 iOS 隧道管理器"""

    def setUp(self):
        """设置测试环境"""
        self.udid = "test-device-udid"

    @patch('insight_eyes.public.ios.tunnel_manager.subprocess.Popen')
    def test_init_tunnel_manager(self, mock_popen):
        """测试初始化隧道管理器"""
        from insight_eyes.public.ios.tunnel_manager import IOSTunnelManager

        manager = IOSTunnelManager(self.udid)

        self.assertEqual(manager.udid, self.udid)
        self.assertFalse(manager._is_running)
        self.assertIsNone(manager._remote_address)
        self.assertIsNone(manager._tunnel_process)

    @patch('insight_eyes.public.ios.tunnel_manager.subprocess.Popen')
    @patch('insight_eyes.public.ios.tunnel_manager.subprocess.run')
    def test_check_pymobiledevice3_installed(self, mock_run, mock_popen):
        """测试 pymobiledevice3 依赖检查"""
        from insight_eyes.public.ios.tunnel_manager import IOSTunnelManager

        manager = IOSTunnelManager(self.udid)

        # 模拟 pymobiledevice3 已安装
        mock_run.return_value = Mock(returncode=0)

        result = manager._check_pymobiledevice3()

        self.assertTrue(result)
        mock_run.assert_called_once()

    @patch('insight_eyes.public.ios.tunnel_manager.subprocess.Popen')
    @patch('insight_eyes.public.ios.tunnel_manager.subprocess.run')
    def test_check_pymobiledevice3_not_installed(self, mock_run, mock_popen):
        """测试 pymobiledevice3 未安装"""
        from insight_eyes.public.ios.tunnel_manager import IOSTunnelManager

        manager = IOSTunnelManager(self.udid)

        # 模拟 pymobiledevice3 未安装
        mock_run.side_effect = FileNotFoundError()

        result = manager._check_pymobiledevice3()

        self.assertFalse(result)

    def test_parse_tunnel_address_valid(self):
        """测试解析有效隧道地址"""
        from insight_eyes.public.ios.tunnel_manager import IOSTunnelManager

        manager = IOSTunnelManager(self.udid)

        # 测试各种格式
        test_cases = [
            "Starting tunnel on 127.0.0.1:12345...",
            "Tunnel started: 127.0.0.1:54321",
            "Connected to 192.168.1.100:8080"
        ]

        expected = [
            ("127.0.0.1", 12345),
            ("127.0.0.1", 54321),
            ("192.168.1.100", 8080)
        ]

        for line, (exp_host, exp_port) in zip(test_cases, expected):
            result = manager._parse_tunnel_address(line)
            self.assertEqual(result, (exp_host, exp_port))

    def test_parse_tunnel_address_invalid(self):
        """测试解析无效隧道地址"""
        from insight_eyes.public.ios.tunnel_manager import IOSTunnelManager

        manager = IOSTunnelManager(self.udid)

        # 测试无效格式
        test_cases = [
            "No address here",
            "Invalid format",
            ""
        ]

        for line in test_cases:
            result = manager._parse_tunnel_address(line)
            self.assertIsNone(result)

    @patch('insight_eyes.public.ios.tunnel_manager.subprocess.Popen')
    def test_is_alive_running(self, mock_popen):
        """测试检查隧道存活状态（运行中）"""
        from insight_eyes.public.ios.tunnel_manager import IOSTunnelManager

        manager = IOSTunnelManager(self.udid)
        manager._is_running = True

        # 模拟运行中的进程
        mock_process = Mock()
        mock_process.poll.return_value = None  # None 表示进程仍在运行
        manager._tunnel_process = mock_process

        self.assertTrue(manager.is_alive())

    @patch('insight_eyes.public.ios.tunnel_manager.subprocess.Popen')
    def test_is_alive_stopped(self, mock_popen):
        """测试检查隧道存活状态（已停止）"""
        from insight_eyes.public.ios.tunnel_manager import IOSTunnelManager

        manager = IOSTunnelManager(self.udid)
        manager._is_running = True

        # 模拟已停止的进程
        mock_process = Mock()
        mock_process.poll.return_value = 0  # 0 表示进程已退出
        manager._tunnel_process = mock_process

        self.assertFalse(manager.is_alive())

    @patch('insight_eyes.public.ios.tunnel_manager.subprocess.Popen')
    def test_is_alive_no_process(self, mock_popen):
        """测试检查隧道存活状态（无进程）"""
        from insight_eyes.public.ios.tunnel_manager import IOSTunnelManager

        manager = IOSTunnelManager(self.udid)
        manager._is_running = True
        manager._tunnel_process = None

        self.assertFalse(manager.is_alive())

    @patch('insight_eyes.public.ios.tunnel_manager.subprocess.Popen')
    def test_get_remote_address(self, mock_popen):
        """测试获取远程地址"""
        from insight_eyes.public.ios.tunnel_manager import IOSTunnelManager

        manager = IOSTunnelManager(self.udid)
        manager._remote_address = ("127.0.0.1", 12345)

        result = manager.get_remote_address()

        self.assertEqual(result, ("127.0.0.1", 12345))

    @patch('insight_eyes.public.ios.tunnel_manager.subprocess.Popen')
    def test_get_remote_address_not_running(self, mock_popen):
        """测试获取远程地址（未运行）"""
        from insight_eyes.public.ios.tunnel_manager import IOSTunnelManager

        manager = IOSTunnelManager(self.udid)
        manager._remote_address = None

        result = manager.get_remote_address()

        self.assertIsNone(result)


class TestTunnelIntegration(unittest.TestCase):
    """测试隧道集成功能"""

    def setUp(self):
        """设置测试环境"""
        self.udid = "test-device-udid"

    @patch('insight_eyes.public.ios.tunnel_manager.subprocess.Popen')
    @patch('insight_eyes.public.ios.tunnel_manager.subprocess.run')
    def test_start_tunnel_success(self, mock_run, mock_popen):
        """测试成功启动隧道"""
        from insight_eyes.public.ios.tunnel_manager import IOSTunnelManager

        # 模拟 pymobiledevice3 已安装
        mock_run.return_value = Mock(returncode=0)

        # 模拟隧道进程
        mock_process = Mock()
        mock_process.poll.return_value = None  # 进程运行中
        mock_process.stdout.readline.side_effect = [
            "Starting tunnel on 127.0.0.1:12345...\n",
            ""  # 空行表示结束
        ]
        mock_popen.return_value = mock_process

        manager = IOSTunnelManager(self.udid)
        result = manager.start_tunnel()

        self.assertTrue(result)
        self.assertTrue(manager._is_running)
        self.assertEqual(manager._remote_address, ("127.0.0.1", 12345))

    @patch('insight_eyes.public.ios.tunnel_manager.subprocess.Popen')
    @patch('insight_eyes.public.ios.tunnel_manager.subprocess.run')
    def test_start_tunnel_pymobiledevice3_missing(self, mock_run, mock_popen):
        """测试 pymobiledevice3 缺失"""
        from insight_eyes.public.ios.tunnel_manager import IOSTunnelManager

        # 模拟 pymobiledevice3 未安装
        mock_run.side_effect = FileNotFoundError()

        manager = IOSTunnelManager(self.udid)
        result = manager.start_tunnel()

        self.assertFalse(result)
        self.assertFalse(manager._is_running)

    @patch('insight_eyes.public.ios.tunnel_manager.subprocess.Popen')
    @patch('insight_eyes.public.ios.tunnel_manager.subprocess.run')
    def test_stop_tunnel(self, mock_run, mock_popen):
        """测试停止隧道"""
        from insight_eyes.public.ios.tunnel_manager import IOSTunnelManager

        # 模拟启动隧道
        mock_run.return_value = Mock(returncode=0)
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_process.stdout.readline.side_effect = ["Starting tunnel on 127.0.0.1:12345...\n", ""]
        mock_popen.return_value = mock_process

        manager = IOSTunnelManager(self.udid)
        manager.start_tunnel()

        # 停止隧道
        manager.stop_tunnel()

        self.assertFalse(manager._is_running)
        self.assertIsNone(manager._remote_address)

    @patch('insight_eyes.public.ios.tunnel_manager.subprocess.Popen')
    def test_context_manager(self, mock_popen):
        """测试上下文管理器"""
        from insight_eyes.public.ios.tunnel_manager import IOSTunnelManager

        # 模拟 pymobiledevice3
        with patch('insight_eyes.public.ios.tunnel_manager.subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            # 模拟隧道进程
            mock_process = Mock()
            mock_process.poll.return_value = None
            mock_process.stdout.readline.side_effect = ["Starting tunnel on 127.0.0.1:12345...\n", ""]
            mock_popen.return_value = mock_process

            with IOSTunnelManager(self.udid) as manager:
                self.assertTrue(manager._is_running)
                self.assertEqual(manager._remote_address, ("127.0.0.1", 12345))

            # 退出上下文后应自动停止
            self.assertFalse(manager._is_running)


if __name__ == '__main__':
    unittest.main()
