# -*- coding: utf-8 -*-
"""
Simple iOS Migration Test Runner

Run iOS migration tests with proper Python path setup.
"""
import sys
import os
from pathlib import Path

# Setup Python path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))
os.chdir(str(script_dir))

def run_test_directly():
    """Run tests directly without importing modules"""
    import unittest

    # Import test classes directly
    from insight_eyes.public.ios.tests.test_pyios_architecture import (
        TestPyIOSConnection,
        TestSysMontapCollector,
        TestGraphicsCollector,
        TestEnergyCollector,
        TestIOSDataNormalizer
    )
    from insight_eyes.public.ios.tests.test_ios_apm_simple import TestIOSAPMSimple

    # Create test suite
    suite = unittest.TestSuite()

    # Add tests
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPyIOSConnection))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestSysMontapCollector))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestGraphicsCollector))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestEnergyCollector))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestIOSDataNormalizer))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestIOSAPMSimple))

    # Run tests
    print("\n" + "=" * 60)
    print("Running iOS Migration Tests")
    print("=" * 60 + "\n")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Success: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failed: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 60)

    if result.wasSuccessful():
        print("\n[SUCCESS] All tests passed!")
        return 0
    else:
        print("\n[FAILED] Some tests failed")
        return 1

if __name__ == '__main__':
    sys.exit(run_test_directly())
