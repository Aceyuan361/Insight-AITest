# -*- coding: utf-8 -*-
"""
Insight-Eye 桌面应用入口
启动移动设备性能监控工具

使用方法:
    python -m insight_eyes.desktop.main
    或
    python main.py (在desktop目录下)
"""
import sys
import os
import traceback

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTranslator, QLocale
from PyQt6.QtGui import QFont

from insight_eyes.desktop.ui.main_window import MainWindow
from logzero import logger


class SafeApplication(QApplication):
    """
    安全的QApplication子类，重写notify方法以捕获事件处理中的异常
    """

    def notify(self, receiver, event):
        """
        重写notify方法，捕获事件处理中的所有异常

        Args:
            receiver: 接收事件的对象
            event: 事件对象

        Returns:
            bool: 事件是否被处理
        """
        try:
            return super().notify(receiver, event)
        except Exception as e:
            logger.critical("=" * 80)
            logger.critical("Qt事件处理中发生异常!")
            logger.critical(f"接收者: {receiver.__class__.__name__ if receiver else 'None'}")
            logger.critical(f"事件类型: {event.__class__.__name__ if event else 'None'}")
            logger.critical(f"异常类型: {type(e).__name__}")
            logger.critical(f"异常信息: {e}")
            logger.critical("\n堆栈跟踪:")
            logger.critical("".join(traceback.format_exception(type(e), e, e.__traceback__)))
            logger.critical("=" * 80)

            # 显示错误对话框
            try:
                from PyQt6.QtWidgets import QMessageBox
                error_msg = f"UI事件处理发生异常:\n\n接收者: {receiver.__class__.__name__}\n事件: {event.__class__.__name__}\n\n{type(e).__name__}: {e}\n\n请查看日志文件获取详细信息。"
                QMessageBox.critical(None, "UI事件错误", error_msg)
            except:
                pass

            return False


def global_exception_handler(exctype, value, tb):
    """
    全局异常处理器
    捕获所有未处理的异常并记录详细日志
    """
    if issubclass(exctype, KeyboardInterrupt):
        # 允许Ctrl+C正常退出
        sys.__excepthook__(exctype, value, tb)
        return

    # 记录详细的错误信息
    logger.critical("=" * 80)
    logger.critical("未捕获的异常!")
    logger.critical(f"异常类型: {exctype.__name__}")
    logger.critical(f"异常信息: {value}")
    logger.critical("\n堆栈跟踪:")
    logger.critical("".join(traceback.format_exception(exctype, value, tb)))
    logger.critical("=" * 80)

    # 显示错误对话框
    try:
        from PyQt6.QtWidgets import QMessageBox
        error_msg = f"程序发生未处理的异常:\n\n{exctype.__name__}: {value}\n\n请查看日志文件获取详细信息。"
        QMessageBox.critical(None, "严重错误", error_msg)
    except:
        pass

    # 调用默认的异常处理器
    sys.__excepthook__(exctype, value, tb)


def handle_exception_in_slot(exception):
    """
    处理Qt信号槽中的异常
    """
    logger.critical("=" * 80)
    logger.critical("Qt信号槽中发生异常!")
    logger.critical(f"异常类型: {type(exception).__name__}")
    logger.critical(f"异常信息: {exception}")
    logger.critical("\n堆栈跟踪:")
    logger.critical("".join(traceback.format_exception(type(exception), exception, exception.__traceback__)))
    logger.critical("=" * 80)

    # 显示错误对话框
    try:
        from PyQt6.QtWidgets import QMessageBox
        error_msg = f"UI操作发生异常:\n\n{type(exception).__name__}: {exception}\n\n请查看日志文件获取详细信息。"
        QMessageBox.critical(None, "UI错误", error_msg)
    except:
        pass


def setup_application_pre():
    """
    配置应用程序（创建 QApplication 之前）
    设置高DPI支持等必须在 QApplication 创建前调用的设置
    """
    # 启用高DPI支持（必须在创建 QApplication 之前调用）
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # 设置应用属性（必须在创建 QApplication 之前调用）
    QApplication.setApplicationName("Insight-Eye")
    QApplication.setApplicationVersion("1.0.0")
    QApplication.setOrganizationName("InsightEye")
    QApplication.setOrganizationDomain("insighteye.dev")


def setup_application_post(app):
    """
    配置应用程序（创建 QApplication 之后）
    设置字体等需要 QApplication 实例的设置

    Args:
        app: QApplication 实例
    """
    # 设置默认字体（需要在 QApplication 实例创建后调用）
    font = app.font()
    font.setFamily("Microsoft YaHei UI")
    font.setPointSize(9)
    app.setFont(font)


def check_and_install_dependencies():
    """
    检查并安装缺失的依赖库
    主要用于自动安装 PDF 导出所需的 reportlab 库
    """
    import subprocess
    import sys

    # 需要检查的依赖库
    required_packages = {
        'reportlab': 'reportlab>=4.0.0',
    }

    missing_packages = []

    # 检查每个依赖是否已安装
    for package_name in required_packages:
        try:
            __import__(package_name)
            logger.info(f"✓ {package_name} 已安装")
        except ImportError:
            logger.warning(f"✗ {package_name} 未安装")
            missing_packages.append(required_packages[package_name])

    # 如果有缺失的包，自动安装
    if missing_packages:
        logger.info("=" * 60)
        logger.info(f"检测到缺失的依赖库，准备自动安装: {', '.join(missing_packages)}")
        logger.info("=" * 60)

        try:
            # 使用 pip 安装缺失的包
            for package_spec in missing_packages:
                logger.info(f"正在安装 {package_spec}...")
                subprocess.check_call([
                    sys.executable,
                    '-m',
                    'pip',
                    'install',
                    package_spec,
                    '--quiet'
                ])
                logger.info(f"✓ {package_spec} 安装成功")

            logger.info("=" * 60)
            logger.info("所有依赖库安装完成！")
            logger.info("=" * 60)

            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"安装依赖失败: {e}")
            logger.error("请手动运行以下命令安装依赖:")
            for pkg in missing_packages:
                logger.error(f"  pip install {pkg}")
            return False
        except Exception as e:
            logger.error(f"安装依赖时发生异常: {e}")
            return False

    return True


def is_debug_mode():
    """
    检查是否启用调试模式

    检查方式（按优先级）：
    1. 命令行参数: --debug 或 -d
    2. 环境变量: INSIGHT_EYE_DEBUG=1
    3. 配置文件: config.json 中的 debug_mode

    Returns:
        bool: 是否启用调试模式
    """
    import os

    # 检查命令行参数
    if '--debug' in sys.argv or '-d' in sys.argv:
        return True

    # 检查环境变量
    if os.getenv('INSIGHT_EYE_DEBUG', '0') == '1':
        return True

    # 检查配置文件
    try:
        import json
        config_path = os.path.expanduser('~/.insight-eye/config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('debug_mode', False)
    except:
        pass

    return False


def create_application():
    """
    创建QApplication实例（使用SafeApplication来捕获异常）

    Returns:
        SafeApplication: 应用程序实例
    """
    # 如果已经存在实例，直接返回
    if QApplication.instance():
        return QApplication.instance()

    app = SafeApplication(sys.argv)

    # 设置应用样式
    app.setStyle('Fusion')

    return app


def main():
    """
    主函数
    创建并显示主窗口
    """
    # 检查是否启用调试模式
    debug_mode = is_debug_mode()

    if debug_mode:
        logger.info("=" * 60)
        logger.info("调试模式已启用")
        logger.info("将打印全链路调试日志")
        logger.info("=" * 60)

    # 设置全局异常处理器
    sys.excepthook = global_exception_handler

    # 配置应用（创建 QApplication 之前）
    setup_application_pre()

    # 创建应用实例
    app = create_application()

    # 配置应用（创建 QApplication 之后）
    setup_application_post(app)

    # 将debug模式存储到app属性中，供全局使用
    app.debug_mode = debug_mode

    # 检查并安装缺失的依赖（如 reportlab）
    logger.info("检查程序依赖...")
    if not check_and_install_dependencies():
        logger.warning("部分依赖安装失败，PDF导出功能可能不可用")

    # 设置Qt信号槽异常处理
    # 注意：PyQt6没有内置的slot异常处理，我们需要在每个槽函数中使用try-except
    # 但我们可以通过覆盖QApplication的notify方法来捕获部分异常

    # ============ 系统信号捕获（检测段错误等致命错误）============
    import signal
    def signal_handler(signum, frame):
        """系统信号处理器"""
        signal_name = signal.Signals(signum).name
        logger.critical("=" * 80)
        logger.critical(f"收到系统信号: {signal_name} ({signum})")
        logger.critical("这通常表示程序崩溃（如段错误、总线错误等）")
        logger.critical(f"堆栈信息:\n{''.join(traceback.format_stack(frame))}")
        logger.critical("=" * 80)

    # 捕获常见的崩溃信号
    signal.signal(signal.SIGSEGV, signal_handler)  # 段错误
    signal.signal(signal.SIGABRT, signal_handler)  # abort
    signal.signal(signal.SIGFPE, signal_handler)   # 浮点异常
    signal.signal(signal.SIGILL, signal_handler)   # 非法指令

    # 创建并显示主窗口
    window = None
    try:
        if debug_mode:
            logger.info("[主程序] 开始创建主窗口...")

        window = MainWindow(debug_mode=debug_mode)
        window.show()

        # 显示启动提示
        debug_suffix = " [DEBUG模式]" if debug_mode else ""
        window.statusBar().showMessage(f"Insight-Eye 已启动{debug_suffix} - 请连接设备开始监控", 5000)

        if debug_mode:
            logger.info("[主程序] 主窗口已创建并显示")
            logger.info("[主程序] 进入事件循环...")

        # 进入事件循环
        exit_code = app.exec()

        if debug_mode:
            logger.info(f"[主程序] 事件循环结束，退出码: {exit_code}")

    except Exception as e:
        logger.critical(f"主窗口创建或运行时发生异常: {e}", exc_info=True)
        try:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "启动失败", f"程序启动失败:\n\n{e}\n\n请查看日志文件获取详细信息。")
        except:
            pass
        exit_code = 1

    # 清理资源
    logger.info(f"程序退出，退出码: {exit_code}")

    if debug_mode and exit_code != 0:
        logger.critical(f"[崩溃警告] 程序异常退出，退出码: {exit_code}")
        if exit_code < 0:
            logger.critical(f"[崩溃警告] 负退出码通常表示被信号终止")

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
