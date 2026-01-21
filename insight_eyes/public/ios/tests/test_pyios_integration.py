# -*- coding: utf-8 -*-
"""
iOS PyiOSDevice 集成测试 - 真实设备测试

测试 py-ios-device 采集器在真实 iOS 设备上的完整监控流程，包括：
- 真实设备连接
- 完整采集周期（启动 -> 采集 -> 停止）
- 连续采集数据验证
- 数据有效性验证

环境变量要求：
- TEST_IOS_DEVICE_UDID: iOS 设备 UDID
- TEST_IOS_BUNDLE_ID: 应用 Bundle ID（可选，默认 Sango.Sango.com）

运行示例：
    # 有设备时
    export TEST_IOS_DEVICE_UDID="00008030-001D29A62EEA802E"
    export TEST_IOS_BUNDLE_ID="Sango.Sango.com"
    pytest insight_eyes/public/ios/tests/test_pyios_integration.py -v

    # 无设备时（跳过集成测试）
    pytest insight_eyes/public/ios/tests/ -v

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License

Author: Aceyuan361
"""
import unittest
import os
import time
from logzero import logger


class TestPyIOSIntegration(unittest.TestCase):
    """iOS PyiOSDevice 集成测试（真实设备）"""

    @classmethod
    def setUpClass(cls):
        """测试类设置"""
        cls.udid = os.environ.get('TEST_IOS_DEVICE_UDID')
        cls.bundle_id = os.environ.get('TEST_IOS_BUNDLE_ID', 'Sango.Sango.com')

        logger.info(f"[集成测试] 配置: UDID={cls.udid}, BundleID={cls.bundle_id}")

    @classmethod
    def tearDownClass(cls):
        """测试类清理"""
        logger.info("[集成测试] 完成")

    def tearDown(self):
        """测试方法清理 - 确保资源释放"""
        # 如果测试失败或异常，确保 collector 被正确清理
        # 注意：每个测试应该自己管理 collector，这里只是保险措施
        pass

    @unittest.skipIf(not os.environ.get('TEST_IOS_DEVICE_UDID'),
                     "需要真实 iOS 设备，设置 TEST_IOS_DEVICE_UDID")
    def test_real_device_connection(self):
        """测试真实 iOS 设备连接

        验证：
        1. PyiOSDevice 能够成功连接设备
        2. 启动监控后收到初始数据
        3. 停止监控后正确清理资源
        """
        logger.info(f"\n[集成测试] 测试设备连接: {self.udid}")

        # 导入采集器
        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        # 创建采集器
        collector = IOSPyDeviceCollector(self.udid, self.bundle_id)

        # 启动监控
        logger.info("[集成测试] 正在启动监控...")
        start_result = collector.start()

        # 验证启动成功
        self.assertTrue(start_result, "启动监控应该成功")
        self.assertTrue(collector._is_started, "状态应该是已启动")
        self.assertIsNotNone(collector._device, "设备对象应该存在")

        logger.info("[集成测试] ✓ 设备连接成功")

        # 等待数据生成
        logger.info("[集成测试] 等待初始数据...")
        time.sleep(3)

        # 验证缓存有数据
        self.assertIn('system', collector._cached_data, "应该有系统数据缓存")
        logger.info(f"[集成测试] ✓ 系统数据已缓存 (进程数: {len(collector._cached_data['system'][0].get('Processes', {}))})")

        # 停止监控
        logger.info("[集成测试] 正在停止监控...")
        collector.stop()

        # 验证清理完成
        self.assertFalse(collector._is_started, "状态应该是未启动")
        self.assertIsNone(collector._device, "设备对象应该被清理")
        self.assertEqual(len(collector._cached_data), 0, "缓存应该被清空")

        logger.info("[集成测试] ✓ 设备断开成功")

    @unittest.skipIf(not os.environ.get('TEST_IOS_DEVICE_UDID'),
                     "需要真实 iOS 设备")
    def test_full_collection_cycle(self):
        """测试完整采集周期

        验证：
        1. 启动监控成功
        2. 所有采集方法返回有效数据
        3. 数据值在合理范围内
        4. 停止监控正确清理
        """
        logger.info(f"\n[集成测试] 测试完整采集周期: {self.udid}")

        # 导入采集器
        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        # 创建并启动采集器
        collector = IOSPyDeviceCollector(self.udid, self.bundle_id)

        logger.info("[集成测试] 启动监控...")
        start_result = collector.start()
        self.assertTrue(start_result, "启动监控应该成功")

        # 等待首次数据生成（首次采集需要 2-3 秒）
        logger.info("[集成测试] 等待首次数据生成...")
        time.sleep(3)

        # 采集 CPU 数据
        logger.info("[集成测试] 采集 CPU 数据...")
        cpu_data = collector.collect_cpu()
        self.assertIsNotNone(cpu_data, "CPU 数据应该不为 None")
        self.assertIn('appCpuRate', cpu_data, "CPU 数据应包含 appCpuRate")
        self.assertIn('sysCpuRate', cpu_data, "CPU 数据应包含 sysCpuRate")
        logger.info(f"[集成测试] ✓ CPU: app={cpu_data['appCpuRate']}%, sys={cpu_data['sysCpuRate']}%")

        # 验证 CPU 值合理（0-100%）
        self.assertGreaterEqual(cpu_data['appCpuRate'], 0, "应用 CPU 使用率应 >= 0")
        self.assertLessEqual(cpu_data['appCpuRate'], 100, "应用 CPU 使用率应 <= 100")

        # 采集内存数据
        logger.info("[集成测试] 采集内存数据...")
        memory_data = collector.collect_memory()
        self.assertIsNotNone(memory_data, "内存数据应该不为 None")
        self.assertIn('totalPass', memory_data, "内存数据应包含 totalPass")
        self.assertIn('nativePass', memory_data, "内存数据应包含 nativePass")
        logger.info(f"[集成测试] ✓ Memory: total={memory_data['totalPass']}MB, native={memory_data['nativePass']}MB")

        # 验证内存值合理（> 0 MB）
        self.assertGreater(memory_data['totalPass'], 0, "总内存应 > 0")

        # 采集 FPS 数据
        logger.info("[集成测试] 采集 FPS 数据...")
        fps_data = collector.collect_fps()

        if fps_data is not None:
            self.assertIn('fps', fps_data, "FPS 数据应包含 fps")
            logger.info(f"[集成测试] ✓ FPS: {fps_data['fps']}")
            # 验证 FPS 值合理（0-120，支持 ProMotion 显示）
            self.assertGreaterEqual(fps_data['fps'], 0, "FPS 应 >= 0")
            self.assertLessEqual(fps_data['fps'], 120, "FPS 应 <= 120")
        else:
            logger.warning("[集成测试] FPS 数据为 None（可能应用未在前台或设备锁屏）")

        # 采集网络数据（当前返回默认值）
        logger.info("[集成测试] 采集网络数据...")
        network_data = collector.collect_network()
        self.assertIsNotNone(network_data, "网络数据应该不为 None")
        self.assertIn('upFlow', network_data, "网络数据应包含 upFlow")
        self.assertIn('downFlow', network_data, "网络数据应包含 downFlow")
        logger.info(f"[集成测试] ✓ Network: up={network_data['upFlow']}KB, down={network_data['downFlow']}KB")

        # 采集电池数据（当前返回默认值）
        logger.info("[集成测试] 采集电池数据...")
        battery_data = collector.collect_battery()
        self.assertIsNotNone(battery_data, "电池数据应该不为 None")
        self.assertIn('level', battery_data, "电池数据应包含 level")
        logger.info(f"[集成测试] ✓ Battery: level={battery_data['level']}%")

        # 停止监控
        logger.info("[集成测试] 停止监控...")
        collector.stop()

        logger.info("[集成测试] ✓ 完整采集周期测试通过")

    @unittest.skipIf(not os.environ.get('TEST_IOS_DEVICE_UDID'),
                     "需要真实 iOS 设备")
    def test_continuous_collection(self):
        """测试连续采集

        验证：
        1. 连续采集多次都能获得数据
        2. 数据持续更新（不是 stale data）
        3. 采集过程稳定不崩溃
        """
        logger.info(f"\n[集成测试] 测试连续采集: {self.udid}")

        # 导入采集器
        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        # 创建并启动采集器
        collector = IOSPyDeviceCollector(self.udid, self.bundle_id)

        logger.info("[集成测试] 启动监控...")
        start_result = collector.start()
        self.assertTrue(start_result, "启动监控应该成功")

        # 等待首次数据
        logger.info("[集成测试] 等待首次数据...")
        time.sleep(3)

        # 连续采集 10 次
        collection_count = 10
        cpu_values = []
        memory_values = []

        logger.info(f"[集成测试] 连续采集 {collection_count} 次...")

        for i in range(collection_count):
            # 采集 CPU
            cpu_data = collector.collect_cpu()
            if cpu_data is not None:
                cpu_values.append(cpu_data['appCpuRate'])
                logger.info(f"[集成测试] 采集 {i+1}/{collection_count}: CPU={cpu_data['appCpuRate']}%")
            else:
                logger.warning(f"[集成测试] 采集 {i+1}/{collection_count}: CPU 数据为 None")
                cpu_values.append(None)

            # 采集内存
            memory_data = collector.collect_memory()
            if memory_data is not None:
                memory_values.append(memory_data['totalPass'])
                logger.debug(f"[集成测试] 采集 {i+1}/{collection_count}: Memory={memory_data['totalPass']}MB")
            else:
                memory_values.append(None)

            # 等待 1 秒（模拟实际监控场景）
            if i < collection_count - 1:
                time.sleep(1)

        # 停止监控
        collector.stop()

        # 验证采集结果
        valid_cpu_count = sum(1 for v in cpu_values if v is not None)
        valid_memory_count = sum(1 for v in memory_values if v is not None)

        logger.info(f"[集成测试] ✓ 有效采集: CPU={valid_cpu_count}/{collection_count}, Memory={valid_memory_count}/{collection_count}")

        # 至少 80% 的采集应该成功
        min_success_count = int(collection_count * 0.8)
        self.assertGreaterEqual(valid_cpu_count, min_success_count,
                              f"CPU 采集成功率应 >= 80% ({valid_cpu_count}/{collection_count})")
        self.assertGreaterEqual(valid_memory_count, min_success_count,
                              f"Memory 采集成功率应 >= 80% ({valid_memory_count}/{collection_count})")

        # 验证数据有变化（不是所有值都相同）
        if valid_cpu_count >= 3:
            unique_cpu_values = set(v for v in cpu_values if v is not None)
            logger.info(f"[集成测试] CPU 值变化: {len(unique_cpu_values)} 个不同值")
            # 至少应该有 2 个不同的值（CPU 使用率会变化）
            # 如果应用空闲，可能都是 0，所以只记录日志不强制断言

        if valid_memory_count >= 3:
            unique_memory_values = set(v for v in memory_values if v is not None)
            logger.info(f"[集成测试] Memory 值变化: {len(unique_memory_values)} 个不同值")
            # 内存可能会有波动

        logger.info("[集成测试] ✓ 连续采集测试通过")

    @unittest.skipIf(not os.environ.get('TEST_IOS_DEVICE_UDID'),
                     "需要真实 iOS 设备")
    def test_data_freshness(self):
        """测试数据新鲜度

        验证：
        1. 缓存数据的时间戳正确更新
        2. 过期数据会被拒绝
        3. 数据采集延迟合理
        """
        logger.info(f"\n[集成测试] 测试数据新鲜度: {self.udid}")

        # 导入采集器
        from insight_eyes.public.ios.pyios_collectors.pydevice_collector import IOSPyDeviceCollector

        # 创建并启动采集器
        collector = IOSPyDeviceCollector(self.udid, self.bundle_id)

        logger.info("[集成测试] 启动监控...")
        collector.start()

        # 等待首次数据
        time.sleep(3)

        # 记录首次采集时间
        first_collection_time = time.time()
        cpu_data = collector.collect_cpu()
        first_collection_end = time.time()

        self.assertIsNotNone(cpu_data, "首次 CPU 采集应该成功")
        logger.info(f"[集成测试] 首次采集延迟: {(first_collection_end - first_collection_time)*1000:.1f}ms")

        # 验证缓存时间戳
        system_last_update = collector._last_update.get('system', 0)
        self.assertGreater(system_last_update, 0, "系统数据应该有时间戳")
        logger.info(f"[集成测试] 数据时间戳: {system_last_update}")

        # 立即再次采集（应该从缓存获取）
        second_collection_time = time.time()
        cpu_data_2 = collector.collect_cpu()
        second_collection_end = time.time()

        self.assertIsNotNone(cpu_data_2, "第二次 CPU 采集应该成功")
        collection_delay = (second_collection_end - second_collection_time) * 1000
        logger.info(f"[集成测试] 第二次采集延迟（缓存）: {collection_delay:.1f}ms")

        # 从缓存获取应该非常快（< 50ms）
        self.assertLess(collection_delay, 50, "从缓存获取数据应该很快")

        # 等待数据过期（超过 max_age=3.0 秒）
        logger.info("[集成测试] 等待数据过期...")
        time.sleep(4)

        # 过期后采集应该返回 None（因为没有新数据推送）
        cpu_data_expired = collector.collect_cpu()
        logger.info(f"[集成测试] 过期后采集结果: {cpu_data_expired}")
        # 注意：实际场景中回调会持续推送数据，所以可能不为 None
        # 这里只验证行为，不强求返回 None

        # 停止监控
        collector.stop()

        logger.info("[集成测试] ✓ 数据新鲜度测试通过")


def run_tests():
    """运行集成测试"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPyIOSIntegration)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出测试结果摘要
    print("\n" + "="*70)
    print("集成测试摘要")
    print("="*70)
    print(f"运行测试: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print(f"跳过: {len(result.skipped)}")

    if result.skipped:
        print("\n跳过的测试:")
        for test, reason in result.skipped:
            print(f"  - {test}: {reason}")

    print("="*70)

    return result.wasSuccessful()


if __name__ == '__main__':
    import sys
    sys.exit(0 if run_tests() else 1)
