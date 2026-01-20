# -*- coding: utf-8 -*-
"""
监控结束处理对话框
显示处理进度和状态动画
"""
from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QProgressBar, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread
from PyQt6.QtGui import QFont
from logzero import logger


class ProcessingDialog(QDialog):
    """监控结束处理对话框

    显示数据处理进度条和状态信息
    """

    # 信号：处理完成
    finished = pyqtSignal(bool, str)  # (成功, 消息)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.processing_steps = [
            "停止数据采集...",
            "保存监控数据...",
            "生成性能报告...",
            "分析异常指标...",
            "完成"
        ]

        self.current_step = 0
        self.progress_value = 0

        self._init_ui()
        self._setup_animation()

    def _init_ui(self):
        """初始化UI"""
        self.setWindowTitle("处理监控数据")
        self.setModal(True)
        self.setFixedSize(400, 180)

        # 对话框样式
        self.setStyleSheet("""
            QDialog {
                background-color: #0a0e17;
                color: #e0e6ed;
            }
            QLabel {
                color: #e0e6ed;
                background-color: transparent;
            }
            QProgressBar {
                background-color: #1a1f2e;
                border: none;
                border-radius: 3px;
                height: 20px;
                text-align: center;
                color: #e0e6ed;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 #00d4ff, stop:1 #0099cc);
                border-radius: 3px;
            }
            QPushButton {
                background-color: #121824;
                color: #e0e6ed;
                border: 1px solid #1a1f2e;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #1a1f2e;
                border-color: #00d4ff;
                color: #00d4ff;
            }
            QPushButton:disabled {
                background-color: #1a1f2e;
                color: #4b5563;
                border-color: #1a1f2e;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # 标题
        title_label = QLabel("正在处理监控数据")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #00d4ff;")
        layout.addWidget(title_label)

        # 状态标签
        self.status_label = QLabel("准备中...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #94a3b8; font-size: 10pt;")
        layout.addWidget(self.status_label)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        # 占位
        layout.addStretch()

        # 关闭按钮（初始禁用）
        self.close_btn = QPushButton("关闭")
        self.close_btn.setEnabled(False)
        self.close_btn.clicked.connect(self.accept)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.close_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _setup_animation(self):
        """设置动画定时器"""
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._update_progress)
        self.animation_timer.setInterval(100)  # 100ms更新一次

    def start_animation(self, total_steps: int = 5):
        """开始动画

        Args:
            total_steps: 总处理步骤数
        """
        self.total_steps = total_steps
        self.current_step = 0
        self.progress_value = 0
        self.progress_bar.setValue(0)
        self.close_btn.setEnabled(False)

        # 更新状态
        if self.current_step < len(self.processing_steps):
            self.status_label.setText(self.processing_steps[self.current_step])

        # 启动动画
        self.animation_timer.start()

    def _update_progress(self):
        """更新进度"""
        if self.current_step >= self.total_steps:
            # 完成
            self.animation_timer.stop()
            self.progress_bar.setValue(100)
            self.status_label.setText("处理完成！")
            self.close_btn.setEnabled(True)
            self.close_btn.setFocus()
            self.finished.emit(True, "处理完成")
            return

        # 计算进度
        step_progress = 100 / self.total_steps
        target_value = int((self.current_step + 1) * step_progress)

        if self.progress_value < target_value:
            # 平滑增加进度
            self.progress_value += 2
            if self.progress_value > target_value:
                self.progress_value = target_value
            self.progress_bar.setValue(self.progress_value)
        else:
            # 当前步骤完成，进入下一步
            self.current_step += 1
            if self.current_step < len(self.processing_steps):
                self.status_label.setText(self.processing_steps[self.current_step])

    def complete(self, success: bool = True, message: str = "处理完成"):
        """手动完成处理

        Args:
            success: 是否成功
            message: 完成消息
        """
        self.animation_timer.stop()
        self.progress_bar.setValue(100)
        self.status_label.setText(message)
        self.close_btn.setEnabled(True)
        self.close_btn.setFocus()

        if not success:
            self.status_label.setStyleSheet("color: #ef4444; font-size: 10pt;")
        else:
            self.status_label.setStyleSheet("color: #22c55e; font-size: 10pt;")

        self.finished.emit(success, message)

    def update_status(self, status: str):
        """更新状态文本

        Args:
            status: 状态文本
        """
        self.status_label.setText(status)

    def set_progress(self, value: int):
        """设置进度值

        Args:
            value: 进度值（0-100）
        """
        self.progress_value = value
        self.progress_bar.setValue(value)

    def closeEvent(self, event):
        """关闭事件"""
        # 如果还在处理中，不允许关闭
        if self.animation_timer.isActive():
            event.ignore()
        else:
            super().closeEvent(event)


class ProcessingWorker(QThread):
    """处理工作线程

    在后台执行数据处理任务
    """

    # 信号：进度更新
    progress_updated = pyqtSignal(int, str)  # (进度, 状态)
    # 信号：处理完成
    finished = pyqtSignal(bool, str)  # (成功, 消息)

    def __init__(self, session_id: int, parent=None):
        super().__init__(parent)
        self.session_id = session_id

    def run(self):
        """执行处理任务"""
        try:
            # 步骤1：停止采集
            self.progress_updated.emit(20, "停止数据采集...")
            self.msleep(500)

            # 步骤2：保存数据
            self.progress_updated.emit(40, "保存监控数据...")
            self.msleep(800)

            # 步骤3：生成报告
            self.progress_updated.emit(60, "生成性能报告...")
            self.msleep(600)

            # 步骤4：分析异常
            self.progress_updated.emit(80, "分析异常指标...")
            self.msleep(400)

            # 完成
            self.progress_updated.emit(100, "处理完成！")
            self.finished.emit(True, "监控数据已保存")

        except Exception as e:
            logger.error(f"处理数据失败: {e}")
            self.finished.emit(False, f"处理失败: {e}")
