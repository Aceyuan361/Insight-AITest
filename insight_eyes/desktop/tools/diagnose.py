# -*- coding: utf-8 -*-
import sys
import os
import traceback

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

print("=== Insight-Eye 诊断启动 ===")
print(f"Python: {sys.version}")
print(f"Project root: {project_root}")

try:
    print("\n[1/6] 导入 PyQt6...")
    from PyQt6.QtWidgets import QApplication
    print("  OK")

    print("\n[2/6] 创建 QApplication...")
    app = QApplication(sys.argv)
    print("  OK")

    print("\n[3/6] 导入 MainWindow...")
    from insight_eyes.desktop.ui.main_window import MainWindow
    print("  OK")

    print("\n[4/6] 创建 MainWindow...")
    window = MainWindow()
    print("  OK")

    print("\n[5/6] 显示窗口...")
    window.show()
    print("  OK")

    print("\n[6/6] 进入事件循环...")
    print("  窗口应该已经显示，按 Ctrl+C 退出")

    # 设置状态栏消息
    window.statusBar().showMessage("Insight-Eye 已启动 - 请连接设备开始监控", 5000)

    exit_code = app.exec()
    print(f"\n应用退出，退出码: {exit_code}")

except Exception as e:
    print(f"\n错误: {e}")
    print("\n详细错误信息:")
    traceback.print_exc()
    sys.exit(1)
