"""
设备选择面板
简化的单设备单应用选择界面，专为专业性能测试设计
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QPushButton, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFont
from typing import List, Dict, Optional
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from ..utils.models import DeviceInfo, AppInfo
from insight_eyes.desktop.core.models import DeviceStatus
from logzero import logger


class DeviceSelectionPanel(QWidget):
    """
    设备与应用选择面板
    专注于单设备单应用的性能监控
    """

    # 信号定义
    target_selected = pyqtSignal(str, str)  # 目标已选择 (device_id, package_name)
    start_monitoring = pyqtSignal()          # 请求开始监控
    stop_monitoring = pyqtSignal()           # 请求停止监控
    refresh_devices = pyqtSignal()           # 请求刷新设备列表

    def __init__(self, parent=None):
        super().__init__(parent)
        self.devices: Dict[str, DeviceInfo] = {}
        self.current_apps: List[AppInfo] = []
        self.selected_device_id: Optional[str] = None
        self.selected_package_name: Optional[str] = None
        self.is_monitoring = False
        self.device_manager = None  # 将在 MainWindow 中设置

        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(16)

        # === 标题 ===
        title_label = QLabel("监控目标")
        title_label.setStyleSheet("""
            font-size: 16pt;
            font-weight: 700;
            color: #00d4ff;
            padding: 4px 0px;
        """)
        main_layout.addWidget(title_label)

        # === 设备选择区 ===
        device_label = QLabel("设备")
        device_label.setStyleSheet("""
            font-size: 11pt;
            font-weight: 600;
            color: #94a3b8;
        """)
        main_layout.addWidget(device_label)

        self.device_combo = QComboBox()
        self.device_combo.setStyleSheet(self._get_combo_style())
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)
        main_layout.addWidget(self.device_combo)

        # === 应用选择区 ===
        app_label = QLabel("应用")
        app_label.setStyleSheet("""
            font-size: 11pt;
            font-weight: 600;
            color: #94a3b8;
        """)
        main_layout.addWidget(app_label)

        self.app_combo = QComboBox()
        self.app_combo.setEditable(True)  # 允许搜索
        self.app_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)  # 不允许插入新项
        self.app_combo.setStyleSheet(self._get_combo_style())
        self.app_combo.currentIndexChanged.connect(self._on_app_changed)
        self.app_combo.lineEdit().setPlaceholderText("搜索应用...")
        main_layout.addWidget(self.app_combo)

        # === 当前目标显示 ===
        target_frame = QFrame()
        target_frame.setStyleSheet("""
            QFrame {
                background-color: #0a0e17;
                border: 1px solid #1a1f2e;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        target_layout = QVBoxLayout(target_frame)
        target_layout.setContentsMargins(12, 12, 12, 12)
        target_layout.setSpacing(8)

        target_label = QLabel("当前目标")
        target_label.setStyleSheet("""
            font-size: 11pt;
            font-weight: 600;
            color: #7dd3fc;
        """)
        target_layout.addWidget(target_label)

        self.device_display = QLabel("设备: 未选择")
        self.device_display.setStyleSheet(self._get_info_label_style())
        target_layout.addWidget(self.device_display)

        self.app_display = QLabel("应用: 未选择")
        self.app_display.setStyleSheet(self._get_info_label_style())
        target_layout.addWidget(self.app_display)

        main_layout.addWidget(target_frame)

        # === 控制按钮区 ===
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        self.start_btn = QPushButton("开始监控")
        self.start_btn.setStyleSheet(self._get_primary_button_style())
        self.start_btn.clicked.connect(self._on_start_clicked)
        self.start_btn.setEnabled(False)
        button_layout.addWidget(self.start_btn)

        self.refresh_btn = QPushButton("刷新设备")
        self.refresh_btn.setStyleSheet(self._get_secondary_button_style())
        self.refresh_btn.clicked.connect(self._on_refresh_clicked)
        button_layout.addWidget(self.refresh_btn)

        main_layout.addLayout(button_layout)

        # === 状态显示 ===
        self.status_label = QLabel("● 未监控")
        self.status_label.setStyleSheet(self._get_status_label_style())
        main_layout.addWidget(self.status_label)

        # === 电池信息显示 ===
        battery_frame = QFrame()
        battery_frame.setStyleSheet("""
            QFrame {
                background-color: #0a0e17;
                border: 1px solid #1a1f2e;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        battery_layout = QVBoxLayout(battery_frame)
        battery_layout.setContentsMargins(12, 12, 12, 12)
        battery_layout.setSpacing(8)

        battery_title = QLabel("电池信息")
        battery_title.setStyleSheet("""
            font-size: 11pt;
            font-weight: 600;
            color: #00ff87;
        """)
        battery_layout.addWidget(battery_title)

        self.battery_level_label = QLabel("电量: --")
        self.battery_level_label.setStyleSheet(self._get_info_label_style())
        battery_layout.addWidget(self.battery_level_label)

        self.battery_temp_label = QLabel("温度: --")
        self.battery_temp_label.setStyleSheet(self._get_info_label_style())
        battery_layout.addWidget(self.battery_temp_label)

        self.battery_capacity_label = QLabel("容量: --")
        self.battery_capacity_label.setStyleSheet(self._get_info_label_style())
        battery_layout.addWidget(self.battery_capacity_label)

        main_layout.addWidget(battery_frame)

        # 添加弹性空间
        main_layout.addStretch()

    def _get_combo_style(self) -> str:
        """获取下拉框样式"""
        return """
            QComboBox {
                background-color: #121824;
                color: #e0e6ed;
                border: 1px solid #1a1f2e;
                border-radius: 6px;
                padding: 10px 12px;
                font-size: 10pt;
            }
            QComboBox:hover {
                border-color: #00d4ff;
            }
            QComboBox:focus {
                border-color: #00d4ff;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #7dd3fc;
                margin-right: 10px;
            }
            QComboBox QAbstractItemView {
                background-color: #121824;
                border: 1px solid #1a1f2e;
                selection-background-color: #00d4ff;
                selection-color: #0a0e17;
                padding: 4px;
            }
            QComboBox QLineEdit {
                background-color: #121824;
                color: #e0e6ed;
                padding: 2px;
                border: none;
            }
        """

    def _get_info_label_style(self) -> str:
        """获取信息标签样式"""
        return """
            font-size: 10pt;
            color: #94a3b8;
            padding: 4px 8px;
        """

    def _get_primary_button_style(self) -> str:
        """获取主要按钮样式"""
        return """
            QPushButton {
                background-color: #00d4ff;
                color: #0a0e17;
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
                font-size: 11pt;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #00b8e6;
            }
            QPushButton:pressed {
                background-color: #0099cc;
            }
            QPushButton:disabled {
                background-color: #1a1f2e;
                color: #64748b;
            }
        """

    def _get_secondary_button_style(self) -> str:
        """获取次要按钮样式"""
        return """
            QPushButton {
                background-color: #1a1f2e;
                color: #e0e6ed;
                border: 1px solid #2d3748;
                border-radius: 6px;
                padding: 12px 24px;
                font-size: 11pt;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2d3748;
                border-color: #00d4ff;
            }
            QPushButton:pressed {
                background-color: #1a1f2e;
            }
        """

    def _get_status_label_style(self, status: str = "idle") -> str:
        """获取状态标签样式"""
        colors = {
            "idle": "#64748b",
            "monitoring": "#22c55e",
            "error": "#ef4444"
        }
        color = colors.get(status, "#64748b")
        return f"""
            font-size: 10pt;
            color: {color};
            padding: 8px;
            background-color: #0a0e17;
            border-radius: 6px;
        """

    def _on_device_changed(self, index: int):
        """设备选择改变"""
        logger.debug(f"设备选择改变，索引: {index}")

        if index < 0:
            logger.debug("设备索引无效，忽略")
            return

        device_id = self.device_combo.currentData()
        logger.debug(f"选择的设备ID: {device_id}")

        if device_id and device_id != self.selected_device_id:
            self.selected_device_id = device_id
            logger.info(f"设备已选择: {device_id}")

            self._load_apps_for_device(device_id)
            self._update_target_display()
            self._check_can_start()

    def _on_app_changed(self, index: int):
        """应用选择改变"""
        logger.debug(f"应用选择改变，索引: {index}")

        if index < 0:
            logger.debug("应用索引无效，忽略")
            return

        package_name = self.app_combo.currentData()
        logger.debug(f"选择的应用包名: {package_name}")

        if package_name:
            self.selected_package_name = package_name
            logger.info(f"应用已选择: {package_name}")

            self._update_target_display()

            # 发射 target_selected 信号
            if self.selected_device_id:
                logger.info(f"发射 target_selected 信号: ({self.selected_device_id}, {package_name})")
                self.target_selected.emit(self.selected_device_id, package_name)
            else:
                logger.warning("设备未选择，无法发射信号")

            self._check_can_start()

    def _on_start_clicked(self):
        """开始/停止监控按钮点击"""
        if self.is_monitoring:
            self.stop_monitoring.emit()
            self._set_monitoring_state(False)
        else:
            if self.selected_device_id and self.selected_package_name:
                self.start_monitoring.emit()
                # 不在这里设置状态，等待MainWindow确认成功后再设置
                # 如果MainWindow检查失败（如应用未运行），状态不会改变

    def _on_refresh_clicked(self):
        """刷新按钮点击"""
        self.refresh_devices.emit()

    def _load_apps_for_device(self, device_id: str):
        """加载指定设备的应用列表"""
        # 清空应用列表
        self.app_combo.clear()
        self.app_combo.lineEdit().setPlaceholderText("搜索应用...")
        self.selected_package_name = None

        # 从 DeviceManager 获取应用列表
        if self.device_manager:
            try:
                apps = self.device_manager.get_device_apps(device_id)
                self.current_apps = apps

                if not apps:
                    self.app_combo.addItem("未找到应用", None)
                    self.app_combo.setEnabled(False)
                else:
                    # 启用搜索
                    self.app_combo.setEnabled(True)
                    self.app_combo.lineEdit().setPlaceholderText("搜索应用...")

                    # 添加应用到下拉框
                    for app in apps:
                        self.app_combo.addItem(app.app_name, app.package_name)

                    logger.info(f"已加载 {len(apps)} 个应用到下拉框")
            except Exception as e:
                logger.error(f"加载应用列表失败: {e}")
                self.app_combo.addItem("加载应用列表失败", None)
                self.app_combo.setEnabled(False)
        else:
            self.app_combo.addItem("请先刷新设备", None)
            self.app_combo.setEnabled(False)

    def _update_target_display(self):
        """更新目标显示"""
        # 更新设备显示
        if self.selected_device_id and self.selected_device_id in self.devices:
            device = self.devices[self.selected_device_id]
            self.device_display.setText(f"设备: {device.name}")
            self.device_display.setStyleSheet(self._get_info_label_style() + "color: #e0e6ed;")
        else:
            self.device_display.setText("设备: 未选择")

        # 更新应用显示
        if self.selected_package_name:
            app_name = self.app_combo.currentText()
            self.app_display.setText(f"应用: {app_name}")
            self.app_display.setStyleSheet(self._get_info_label_style() + "color: #e0e6ed;")
        else:
            self.app_display.setText("应用: 未选择")

    def _check_can_start(self):
        """检查是否可以开始监控"""
        can_start = (
            self.selected_device_id is not None and
            self.selected_package_name is not None and
            not self.is_monitoring
        )
        self.start_btn.setEnabled(can_start)

    def _set_monitoring_state(self, is_monitoring: bool):
        """设置监控状态"""
        self.is_monitoring = is_monitoring

        if is_monitoring:
            self.start_btn.setText("停止监控")
            self.status_label.setText("● 监控中")
            self.status_label.setStyleSheet(self._get_status_label_style("monitoring"))
            # 禁用选择控件
            self.device_combo.setEnabled(False)
            self.app_combo.setEnabled(False)
        else:
            self.start_btn.setText("开始监控")
            self.status_label.setText("● 未监控")
            self.status_label.setStyleSheet(self._get_status_label_style("idle"))
            # 启用选择控件
            self.device_combo.setEnabled(True)
            self.app_combo.setEnabled(True)
            self._check_can_start()

    # ========== 公共方法 ==========

    def set_devices(self, devices: List[DeviceInfo]):
        """
        设置设备列表

        Args:
            devices: 设备信息列表
        """
        # 保存设备信息
        self.devices.clear()
        for device in devices:
            self.devices[device.device_id] = device

        # 保存当前选择
        current_device_id = self.device_combo.currentData()

        # 重建下拉框
        self.device_combo.clear()
        self.device_combo.addItem("选择设备...", None)

        for device in devices:
            status_text = self._get_device_status_text(device.status)
            display_text = f"{device.name} ({status_text})"
            self.device_combo.addItem(display_text, device.device_id)

        # 尝试恢复之前的选择
        if current_device_id and current_device_id in self.devices:
            index = self.device_combo.findData(current_device_id)
            if index >= 0:
                self.device_combo.setCurrentIndex(index)

    def set_apps(self, device_id: str, apps: List[AppInfo]):
        """
        设置指定设备的应用列表

        Args:
            device_id: 设备ID
            apps: 应用信息列表
        """
        if device_id != self.selected_device_id:
            return

        self.current_apps = apps
        self.app_combo.clear()
        self.app_combo.setEnabled(True)

        # 添加提示项
        if not apps:
            self.app_combo.addItem("未找到应用", None)
        else:
            self.app_combo.lineEdit().setPlaceholderText("搜索应用...")
            for app in apps:
                # 显示：包名
                self.app_combo.addItem(app.app_name, app.package_name)

    def get_selected_target(self) -> Optional[tuple]:
        """
        获取当前选择的目标

        Returns:
            (device_id, package_name) 或 None
        """
        if self.selected_device_id and self.selected_package_name:
            return (self.selected_device_id, self.selected_package_name)
        return None

    def _get_device_status_text(self, status: DeviceStatus) -> str:
        """获取设备状态文本"""
        status_map = {
            DeviceStatus.CONNECTED: "在线",
            DeviceStatus.DISCONNECTED: "离线",
            DeviceStatus.AUTHORIZING: "授权中",
            DeviceStatus.OFFLINE: "离线",
            DeviceStatus.UNAUTHORIZED: "未授权",
            DeviceStatus.RECONNECTING: "重连中"
        }
        return status_map.get(status, "未知")

    def clear(self):
        """清空选择"""
        self.devices.clear()
        self.current_apps.clear()
        self.selected_device_id = None
        self.selected_package_name = None

        self.device_combo.clear()
        self.device_combo.addItem("选择设备...", None)

        self.app_combo.clear()
        self.app_combo.addItem("选择应用...", None)

        self._update_target_display()
        self._set_monitoring_state(False)

    def update_battery_info(self, level: int, temperature: float, capacity: int = None):
        """
        更新电池信息显示

        Args:
            level: 电量百分比 (0-100)
            temperature: 电池温度 (摄氏度)
            capacity: 电池容量 (mAh，可选)
        """
        from logzero import logger
        self.battery_level_label.setText(f"电量: {level}%")
        self.battery_temp_label.setText(f"温度: {temperature:.1f}°C")
        if capacity:
            self.battery_capacity_label.setText(f"容量: {capacity} mAh")
        else:
            self.battery_capacity_label.setText("容量: --")

        # 强制刷新UI
        self.battery_level_label.repaint()
        self.battery_temp_label.repaint()
        self.battery_capacity_label.repaint()

        logger.debug(f"[设备面板] 电池信息已更新: 电量={level}%, 温度={temperature}°C, 容量={capacity}")
