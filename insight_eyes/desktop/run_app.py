# -*- coding: utf-8 -*-
"""
Insight-Eye 桌面应用启动脚本
用于快速启动和测试应用
"""
import sys
import os

# 确保项目根目录在路径中
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 设置Qt平台插件
os.environ.setdefault('QT_QPA_PLATFORM', 'windows')

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt


def setup_app():
    """配置应用程序"""
    # 启用高DPI
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # 设置应用信息
    QApplication.setApplicationName("Insight-Eye")
    QApplication.setApplicationVersion("1.0.0")
    QApplication.setOrganizationName("InsightEye")

    # 设置样式
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    return app


def main():
    """主函数"""
    print("=" * 60)
    print("Insight-Eye 桌面应用启动中...")
    print("=" * 60)

    # 创建应用
    app = setup_app()

    try:
        # 导入主窗口
        from insight_eyes.desktop.ui.main_window import MainWindow

        # 创建主窗口
        print("正在创建主窗口...")
        window = MainWindow()

        # 显示窗口
        print("正在显示窗口...")
        window.show()

        # 显示状态提示
        window.statusBar().showMessage("Insight-Eye 已启动 - 请连接设备开始监控", 5000)

        print("\n应用已成功启动！")
        print("- 点击左侧'刷新'按钮扫描设备")
        print("- 选择要监控的应用")
        print("- 按 F5 或点击'开始'按钮开始监控")
        print("=" * 60)

        # 运行事件循环
        sys.exit(app.exec())

    except Exception as e:
        print(f"\n错误: 应用启动失败")
        print(f"异常信息: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
