# -*- coding: utf-8 -*-
"""
iOS 监控迁移测试运行器

运行所有 py-ios-device 迁移相关的测试

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License
"""
import unittest
import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
os.chdir(str(project_root))


def run_all_tests():
    """运行所有 iOS 迁移测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加测试模块
    test_modules = [
        'insight_eyes.public.ios.tests.test_pyios_architecture',
        'insight_eyes.public.ios.tests.test_ios_apm_integration',
        'insight_eyes.desktop.tests.test_ios_device_adapter',
    ]

    for module_name in test_modules:
        try:
            module = __import__(module_name, fromlist=[''])
            tests = loader.loadTestsFromModule(module)
            suite.addTests(tests)
            print(f"[OK] Added test module: {module_name}")
        except ImportError as e:
            print(f"[FAIL] Cannot import test module {module_name}: {e}")

    # 运行测试
    print("\n" + "=" * 60)
    print("Running iOS Migration Tests")
    print("=" * 60 + "\n")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出测试结果摘要
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Success: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failed: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    print("=" * 60)

    if result.wasSuccessful():
        print("\n[SUCCESS] All tests passed!")
        return 0
    else:
        print("\n[FAILED] Some tests failed, please check error messages above")
        return 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
