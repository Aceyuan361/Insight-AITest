#!/usr/bin/env python3
"""
临时测试文件清理脚本

将根目录的临时测试文件移动到 tests/debug/ 目录
"""
import os
import shutil
from pathlib import Path

# 临时测试文件列表（需要移动）
TEMP_TEST_FILES = [
    'test_code_structure.py',
    'test_config_fix.py',
    'test_config_manager.py',
    'test_deadlock_scenario.py',
    'test_debug.py',
    'test_debug_getattr.py',
    'test_debug_init.py',
    'test_debug_new.py',
    'test_diagnose_startup.py',
    'test_direct.py',
    'test_direct_call.py',
    'test_ensure_dir.py',
    'test_fps_comprehensive.py',
    'test_fps_fix.py',
    'test_import_only.py',
    'test_indent_check.py',
    'test_init_debug.py',
    'test_integration_simple.py',
    'test_ios_foreground_monitoring.py',
    'test_ios_upgrade_integration.py',
    'test_ios_with_foreground.py',
    'test_just_import.py',
    'test_main_window_fix.py',
    'test_manual_new_init.py',
    'test_minimal.py',
    'test_minimal_blocking.py',
    'test_monitoring.py',
    'test_no_init_check.py',
    'test_original.py',
    'test_original_pattern.py',
    'test_print_debug.py',
    'test_qobject.py',
    'test_qobject_init.py',
    'test_real_ios_device.py',
    'test_report_integration.py',
    'test_save_config_deadlock.py',
    'test_shell_true.py',
    'test_simple.py',
    'test_simple_verify.py',
    'test_singleton_behavior.py',
    'test_singleton_simple.py',
    'test_singleton_v3.py',
    'test_startup.py',
    'test_startup_debug.py',
    'test_startup_final.py',
    'test_startup_verification.py',
    'test_step_by_step.py',
    'test_subprocess_run.py',
    'test_task3_final_review.py',
    'test_task3_main_window_delayed_init.py',
    'test_timeout_fix.py',
    'test_variant_pattern.py',
    'test_with_qapp.py',
    'test_without_qapp.py',
]

# 保留在根目录的测试文件
KEEP_IN_ROOT = [
    'final_test.py',
    'quick_test_fps.py',
    'verify_docs.py',
    'verify_fix.py',
    'verify_fix_simple.py',
    'verify_fix_v2.py',
    'verify_logic.py',
    'verify_spec_compliance.py',
    'verify_task3.py',
]

def move_temp_tests():
    """移动临时测试文件到 debug 目录"""
    project_root = Path.cwd()
    debug_dir = project_root / 'insight_eyes' / 'desktop' / 'tests' / 'debug'
    debug_dir.mkdir(parents=True, exist_ok=True)

    moved_count = 0
    not_found_count = 0

    for test_file in TEMP_TEST_FILES:
        source = project_root / test_file
        if source.exists():
            dest = debug_dir / test_file
            shutil.move(str(source), str(dest))
            print(f"[OK] Moved: {test_file}")
            moved_count += 1
        else:
            print(f"[SKIP] {test_file} (not found)")
            not_found_count += 1

    print(f"\nTotal moved: {moved_count} files")
    if not_found_count > 0:
        print(f"Not found: {not_found_count} files")

    # 验证保留的文件
    print("\nFiles kept in root directory:")
    for test_file in KEEP_IN_ROOT:
        source = project_root / test_file
        if source.exists():
            print(f"  [OK] {test_file}")
        else:
            print(f"  [MISSING] {test_file}")

if __name__ == '__main__':
    move_temp_tests()
