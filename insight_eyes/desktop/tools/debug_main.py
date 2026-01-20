# -*- coding: utf-8 -*-
"""调试启动脚本"""
import sys
import os
import traceback

# 添加项目根目录到路径
# 从 desktop/tools/debug_main.py 回到项目根目录
# 结构: project_root/insight_eyes/desktop/tools/debug_main.py
# 需要往上3级: ../../..
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print(f"Python版本: {sys.version}")
print(f"项目根目录: {project_root}")
print(f"sys.path: {sys.path[:3]}...")

try:
    print("\n1. 测试导入 PyQt6...")
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    print("   PyQt6 导入成功")
except Exception as e:
    print(f"   PyQt6 导入失败: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("\n2. 测试导入 logzero...")
    from logzero import logger
    print("   logzero 导入成功")
except Exception as e:
    print(f"   logzero 导入失败: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("\n3. 测试导入 MainWindow...")
    from insight_eyes.desktop.ui.main_window import MainWindow
    print("   MainWindow 导入成功")
except Exception as e:
    print(f"   MainWindow 导入失败: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("\n4. 创建 QApplication...")
    app = QApplication(sys.argv)
    print("   QApplication 创建成功")
except Exception as e:
    print(f"   QApplication 创建失败: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("\n5. 创建 MainWindow...")
    window = MainWindow()
    print("   MainWindow 创建成功")
except Exception as e:
    print(f"   MainWindow 创建失败: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("\n6. 显示窗口...")
    window.show()
    print("   窗口显示成功")
except Exception as e:
    print(f"   窗口显示失败: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n启动成功，进入事件循环...")
sys.exit(app.exec())
