# -*- coding: utf-8 -*-
"""
设备重连功能使用示例
演示如何使用设备重连机制
"""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QPushButton
from PyQt6.QtCore import Qt

from insight_eyes.desktop.core.device_manager import DeviceManager
from insight_eyes.desktop.core.models import ReconnectConfig, DeviceStatus


class ReconnectExampleWindow(QMainWindow):
    """设备重连功能示例窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("设备重连功能示例")
        self.setGeometry(100, 100, 800, 600)

        # 创建设备管理器（带自定义重连配置）
        reconnect_config = ReconnectConfig(
            enable_auto_reconnect=True,      # 启用自动重连
            max_retry_count=10,               # 最多重试10次
            initial_retry_interval=1,         # 初始重试间隔1秒
            max_retry_interval=60,            # 最大重试间隔60秒
            retry_multiplier=2.0,             # 每次间隔翻倍（指数退避）
            enable_heartbeat=True,            # 启用心跳检测
            heartbeat_interval=5,             # 每5秒检测一次
            heartbeat_timeout=15              # 15秒无响应认为断开
        )

        self.device_manager = DeviceManager(reconnect_config=reconnect_config)

        # 连接信号
        self._connect_signals()

        # 初始化UI
        self._init_ui()

        # 启动设备扫描
        self.device_manager.start_scan()

    def _connect_signals(self):
        """连接设备管理器信号"""

        # 设备发现信号
        self.device_manager.device_discovered.connect(self._on_device_discovered)

        # 设备断开信号
        self.device_manager.device_lost.connect(self._on_device_lost)

        # 设备意外断开信号（心跳检测到断开）
        self.device_manager.device_disconnected.connect(self._on_device_disconnected)

        # 重连相关信号
        self.device_manager.reconnect_started.connect(self._on_reconnect_started)
        self.device_manager.reconnect_success.connect(self._on_reconnect_success)
        self.device_manager.reconnect_failed.connect(self._on_reconnect_failed)
        self.device_manager.reconnect_cancelled.connect(self._on_reconnect_cancelled)
        self.device_manager.reconnect_progress.connect(self._on_reconnect_progress)

    def _init_ui(self):
        """初始化UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # 标题
        title = QLabel("设备重连功能示例")
        title.setStyleSheet("font-size: 18pt; font-weight: bold;")
        layout.addWidget(title)

        # 配置信息
        config_info = QLabel(
            f"重连配置：\n"
            f"- 自动重连：启用\n"
            f"- 最大重试次数：{self.device_manager.get_reconnect_config().max_retry_count}\n"
            f"- 初始重试间隔：{self.device_manager.get_reconnect_config().initial_retry_interval}秒\n"
            f"- 最大重试间隔：{self.device_manager.get_reconnect_config().max_retry_interval}秒\n"
            f"- 重试间隔倍数：{self.device_manager.get_reconnect_config().retry_multiplier}x\n"
            f"- 心跳检测：启用（间隔{self.device_manager.get_reconnect_config().heartbeat_interval}秒）"
        )
        config_info.setStyleSheet("color: #64748b; padding: 10px;")
        layout.addWidget(config_info)

        # 状态标签
        self.status_label = QLabel("状态：等待设备连接...")
        self.status_label.setStyleSheet("padding: 10px; background-color: #f1f5f9; border-radius: 5px;")
        layout.addWidget(self.status_label)

        # 手动重连按钮
        self.reconnect_btn = QPushButton("手动重连选中的设备")
        self.reconnect_btn.setEnabled(False)
        self.reconnect_btn.clicked.connect(self._on_manual_reconnect)
        layout.addWidget(self.reconnect_btn)

        # 取消重连按钮
        self.cancel_btn = QPushButton("取消重连")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._on_cancel_reconnect)
        layout.addWidget(self.cancel_btn)

        # 更新配置按钮
        update_config_btn = QPushButton("更新重连配置")
        update_config_btn.clicked.connect(self._on_update_config)
        layout.addWidget(update_config_btn)

    def _on_device_discovered(self, device_info):
        """处理设备发现事件"""
        self.status_label.setText(f"状态：发现设备 - {device_info.name} ({device_info.device_id})")
        self.reconnect_btn.setEnabled(True)

    def _on_device_lost(self, device_id):
        """处理设备断开事件"""
        self.status_label.setText(f"状态：设备已移除 - {device_id}")
        self.reconnect_btn.setEnabled(False)

    def _on_device_disconnected(self, device_id):
        """处理设备意外断开事件"""
        self.status_label.setText(f"状态：设备意外断开 - {device_id}，正在尝试重连...")
        self.cancel_btn.setEnabled(True)

    def _on_reconnect_started(self, device_id):
        """处理重连开始事件"""
        self.status_label.setText(f"状态：开始重连设备 - {device_id}")
        self.cancel_btn.setEnabled(True)

    def _on_reconnect_success(self, device_id, retry_count):
        """处理重连成功事件"""
        self.status_label.setText(f"状态：重连成功！设备ID: {device_id}，重试次数: {retry_count}")
        self.cancel_btn.setEnabled(False)

    def _on_reconnect_failed(self, device_id, error_msg, retry_count):
        """处理重连失败事件"""
        self.status_label.setText(
            f"状态：重连失败 - 设备ID: {device_id}，错误: {error_msg}，重试次数: {retry_count}"
        )
        self.cancel_btn.setEnabled(False)

    def _on_reconnect_cancelled(self, device_id):
        """处理重连取消事件"""
        self.status_label.setText(f"状态：已取消重连 - {device_id}")
        self.cancel_btn.setEnabled(False)

    def _on_reconnect_progress(self, device_id, current, max_count):
        """处理重连进度事件"""
        if max_count > 0:
            self.status_label.setText(f"状态：正在重连 {device_id}... ({current}/{max_count})")
        else:
            self.status_label.setText(f"状态：正在重连 {device_id}... (第{current}次尝试)")

    def _on_manual_reconnect(self):
        """手动重连按钮点击"""
        # 这里可以选择要重连的设备
        # 示例：重连第一个设备
        devices = self.device_manager.get_devices()
        if devices:
            device_id = devices[0].device_id
            success = self.device_manager.start_reconnect(device_id)
            if success:
                self.status_label.setText(f"状态：已手动启动重连 - {device_id}")
            else:
                self.status_label.setText(f"状态：启动重连失败 - {device_id}")

    def _on_cancel_reconnect(self):
        """取消重连按钮点击"""
        # 获取正在重连的设备
        devices = self.device_manager.get_devices()
        for device in devices:
            if self.device_manager.is_reconnecting(device.device_id):
                self.device_manager.cancel_reconnect(device.device_id)
                self.status_label.setText(f"状态：已取消重连 - {device.device_id}")
                return

        self.status_label.setText("状态：没有正在重连的设备")

    def _on_update_config(self):
        """更新重连配置"""
        # 示例：更新配置为更激进的重连策略
        new_config = ReconnectConfig(
            enable_auto_reconnect=True,
            max_retry_count=20,              # 增加到20次
            initial_retry_interval=1,
            max_retry_interval=120,           # 增加到120秒
            retry_multiplier=1.5,             # 降低倍数
            enable_heartbeat=True,
            heartbeat_interval=3,             # 更频繁的心跳检测
            heartbeat_timeout=10
        )

        self.device_manager.set_reconnect_config(new_config)
        self.status_label.setText("状态：已更新重连配置")

    def closeEvent(self, event):
        """窗口关闭事件"""
        # 清理资源
        self.device_manager.cleanup()
        event.accept()


def main():
    """主函数"""
    app = QApplication(sys.argv)

    window = ReconnectExampleWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
