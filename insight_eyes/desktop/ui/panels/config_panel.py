"""
配置与告警面板
右侧面板，显示采集配置、阈值设置和告警记录
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGroupBox, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QPushButton, QListWidget, QListWidgetItem,
    QScrollArea, QFrame, QFormLayout, QLineEdit, QGridLayout, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QDateTime, QTimer, QSignalBlocker
from PyQt6.QtGui import QColor
from datetime import datetime
from typing import List, Dict, Optional

from ..utils.models import AlertRecord, AlertLevel, CollectionConfig


class ConfigPanel(QWidget):
    """
    配置与告警面板
    右侧面板，包含采集配置、阈值设置和告警记录
    """

    # 信号定义
    config_changed = pyqtSignal(dict)  # 配置变更
    threshold_changed = pyqtSignal(dict)  # 阈值变更
    alert_cleared = pyqtSignal(str)  # 告警清除

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = CollectionConfig()
        self.alerts: List[AlertRecord] = []
        self._config_manager: Optional['ConfigManager'] = None  # 延迟初始化
        self.auto_save_enabled = False  # 暂时禁用自动保存，排查崩溃问题

        # 延迟自动保存定时器（避免频繁I/O阻塞UI）
        self._auto_save_timer = QTimer(self)
        self._auto_save_timer.setSingleShot(True)
        self._auto_save_timer.timeout.connect(self._auto_save_config)

        self._init_ui()

    @property
    def config_manager(self):
        """
        延迟获取配置管理器

        使用属性(property)实现懒加载，避免在 __init__ 中直接调用
        get_config_manager()，从而防止在 QApplication 创建之前触发
        ConfigManager 的单例初始化。
        """
        if self._config_manager is None:
            from ...config.config_manager import get_config_manager
            self._config_manager = get_config_manager()
        return self._config_manager

    def _init_ui(self):
        """初始化UI"""
        # 使用滚动区域以支持小屏幕
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #121824;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #1a1f2e;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #2d3748;
            }
        """)

        # 创建容器widget
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        # === 采集配置区 ===
        config_group = self._create_config_group()
        layout.addWidget(config_group)

        # === 阈值设置区 ===
        threshold_group = self._create_threshold_group()
        layout.addWidget(threshold_group)

        # === 告警记录区 ===
        alert_group = self._create_alert_group()
        layout.addWidget(alert_group)

        layout.addStretch()

        scroll_area.setWidget(container)

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll_area)

    def _create_config_group(self) -> QGroupBox:
        """创建采集配置组"""
        group = QGroupBox("采集配置")
        group.setStyleSheet("""
            QGroupBox {
                background-color: transparent;
                color: #7dd3fc;
                border: 1px solid #1a1f2e;
                border-radius: 8px;
                margin-top: 12px;
                padding: 12px;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 12px;
                padding: 4px 8px;
                background-color: #0a0e17;
            }
        """)
        group_layout = QVBoxLayout()

        # 采样频率
        freq_layout = QHBoxLayout()
        freq_label = QLabel("采样频率:")
        freq_label.setStyleSheet("color: #e0e6ed;")
        freq_layout.addWidget(freq_label)

        self.interval_combo = QComboBox()
        # 采集频率选项（秒）- 性能优化：去除 100ms/500ms，最小间隔改为 1 秒
        # 原因：单次采集耗时约 220-700ms，过短间隔会导致任务堆积和 UI 阻塞
        self.interval_combo.addItems(["1s", "3s", "5s", "10s"])
        self.interval_combo.setCurrentText("1s")
        self.interval_combo.setStyleSheet("""
            QComboBox {
                background-color: #121824;
                color: #e0e6ed;
                border: 1px solid #1a1f2e;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QComboBox:hover {
                border-color: #3b82f6;
            }
        """)
        self.interval_combo.currentTextChanged.connect(self._on_config_changed)
        freq_layout.addWidget(self.interval_combo)
        group_layout.addLayout(freq_layout)

        # 添加指标选择区域（使用 card_configs 中的配置）
        metrics_selector = self._create_metrics_selector()
        group_layout.addWidget(metrics_selector)

        group.setLayout(group_layout)
        return group

    def _create_threshold_group(self) -> QGroupBox:
        """创建阈值设置组"""
        group = QGroupBox("告警阈值")
        group.setStyleSheet("""
            QGroupBox {
                background-color: transparent;
                color: #7dd3fc;
                border: 1px solid #1a1f2e;
                border-radius: 8px;
                margin-top: 12px;
                padding: 12px;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 12px;
                padding: 4px 8px;
                background-color: #0a0e17;
            }
        """)
        form_layout = QFormLayout()

        # FPS阈值
        self.fps_threshold = QSpinBox()
        self.fps_threshold.setRange(10, 60)
        self.fps_threshold.setValue(30)
        self.fps_threshold.setSuffix(" fps")
        self.fps_threshold.setStyleSheet("""
            QSpinBox {
                background-color: #121824;
                color: #e0e6ed;
                border: 1px solid #1a1f2e;
                border-radius: 6px;
                padding: 6px;
            }
        """)
        self.fps_threshold.valueChanged.connect(self._on_threshold_changed)
        form_layout.addRow("FPS低于:", self.fps_threshold)

        # 内存阈值
        self.memory_threshold = QSpinBox()
        self.memory_threshold.setRange(100, 2000)
        self.memory_threshold.setValue(500)
        self.memory_threshold.setSuffix(" MB")
        self.memory_threshold.setStyleSheet("""
            QSpinBox {
                background-color: #121824;
                color: #e0e6ed;
                border: 1px solid #1a1f2e;
                border-radius: 6px;
                padding: 6px;
            }
        """)
        self.memory_threshold.valueChanged.connect(self._on_threshold_changed)
        form_layout.addRow("内存超过:", self.memory_threshold)

        # CPU阈值
        self.cpu_threshold = QSpinBox()
        self.cpu_threshold.setRange(50, 100)
        self.cpu_threshold.setValue(80)
        self.cpu_threshold.setSuffix(" %")
        self.cpu_threshold.setStyleSheet("""
            QSpinBox {
                background-color: #121824;
                color: #e0e6ed;
                border: 1px solid #1a1f2e;
                border-radius: 6px;
                padding: 6px;
            }
        """)
        self.cpu_threshold.valueChanged.connect(self._on_threshold_changed)
        form_layout.addRow("CPU超过:", self.cpu_threshold)

        # 电池温度阈值
        self.temp_threshold = QDoubleSpinBox()
        self.temp_threshold.setRange(30.0, 60.0)
        self.temp_threshold.setValue(45.0)
        self.temp_threshold.setSuffix(" °C")
        self.temp_threshold.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #121824;
                color: #e0e6ed;
                border: 1px solid #1a1f2e;
                border-radius: 6px;
                padding: 6px;
            }
        """)
        self.temp_threshold.valueChanged.connect(self._on_threshold_changed)
        form_layout.addRow("温度超过:", self.temp_threshold)

        group.setLayout(form_layout)
        return group

    def _create_alert_group(self) -> QGroupBox:
        """创建告警记录组"""
        group = QGroupBox("告警记录")
        group.setStyleSheet("""
            QGroupBox {
                background-color: transparent;
                color: #7dd3fc;
                border: 1px solid #1a1f2e;
                border-radius: 8px;
                margin-top: 12px;
                padding: 12px;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 12px;
                padding: 4px 8px;
                background-color: #0a0e17;
            }
        """)
        group_layout = QVBoxLayout()

        # 告警列表
        self.alert_list = QListWidget()
        self.alert_list.setMinimumHeight(350)  # 扩展最小高度（原200）
        self.alert_list.setStyleSheet("""
            QListWidget {
                background-color: #121824;
                border: 1px solid #1a1f2e;
                border-radius: 6px;
                outline: none;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
                border: none;
                color: #e0e6ed;
            }
            QListWidget::item:hover {
                background-color: #1a1f2e;
            }
        """)
        # 启用文字换行
        self.alert_list.setWordWrap(True)
        self.alert_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        group_layout.addWidget(self.alert_list)

        # 操作按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        clear_btn = QPushButton("清除全部")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #121824;
                color: #e0e6ed;
                border: 1px solid #1a1f2e;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #1a1f2e;
                border-color: #00d4ff;
            }
        """)
        clear_btn.clicked.connect(self._clear_all_alerts)
        button_layout.addWidget(clear_btn)

        export_btn = QPushButton("导出")
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #121824;
                color: #e0e6ed;
                border: 1px solid #1a1f2e;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #1a1f2e;
                border-color: #00d4ff;
            }
        """)
        export_btn.clicked.connect(self._export_alerts)
        button_layout.addWidget(export_btn)
        button_layout.addStretch()

        group_layout.addLayout(button_layout)

        group.setLayout(group_layout)
        return group

    def _on_config_changed(self):
        """配置变更处理"""
        # 防御性检查：确保控件已初始化
        if not hasattr(self, 'metric_checkboxes') or not self.metric_checkboxes:
            return
        if not hasattr(self, 'interval_combo') or self.interval_combo is None:
            return

        try:
            # 解析采样间隔
            interval_text = self.interval_combo.currentText()
            interval_map = {
                "1s": 1000,
                "3s": 3000,
                "5s": 5000,
                "10s": 10000
            }
            interval_ms = interval_map.get(interval_text, 1000)

            # 使用 .get() 方法安全访问字典
            cpu_cb = self.metric_checkboxes.get("CPU")
            memory_cb = self.metric_checkboxes.get("内存")
            fps_cb = self.metric_checkboxes.get("FPS")
            network_cb = self.metric_checkboxes.get("网络")
            battery_cb = self.metric_checkboxes.get("电池")
            gpu_cb = self.metric_checkboxes.get("GPU")

            config = {
                "interval_ms": interval_ms,
                "enable_cpu": cpu_cb.isChecked() if cpu_cb else True,
                "enable_memory": memory_cb.isChecked() if memory_cb else True,
                "enable_fps": fps_cb.isChecked() if fps_cb else True,
                "enable_network": network_cb.isChecked() if network_cb else True,
                "enable_battery": battery_cb.isChecked() if battery_cb else True,
                "enable_gpu": gpu_cb.isChecked() if gpu_cb else False
            }

            self.config_changed.emit(config)

            # 使用定时器延迟自动保存，避免阻塞UI线程
            if self.auto_save_enabled:
                # 停止之前的定时器
                if self._auto_save_timer.isActive():
                    self._auto_save_timer.stop()
                # 启动延迟保存（1秒后执行，避免频繁I/O）
                self._auto_save_timer.start(1000)
        except Exception as e:
            from logzero import logger
            logger.error(f"配置变更处理失败: {e}", exc_info=True)

    def _on_threshold_changed(self):
        """阈值变更处理"""
        # 防御性检查：确保控件已初始化
        if not hasattr(self, 'fps_threshold') or self.fps_threshold is None:
            return
        if not hasattr(self, 'memory_threshold') or self.memory_threshold is None:
            return
        if not hasattr(self, 'cpu_threshold') or self.cpu_threshold is None:
            return
        if not hasattr(self, 'temp_threshold') or self.temp_threshold is None:
            return

        try:
            thresholds = {
                "fps_threshold": self.fps_threshold.value(),
                "memory_threshold_mb": self.memory_threshold.value(),
                "cpu_threshold_percent": self.cpu_threshold.value(),
                "battery_threshold_temp": self.temp_threshold.value()
            }

            self.threshold_changed.emit(thresholds)

            # 使用定时器延迟自动保存，避免阻塞UI线程
            if self.auto_save_enabled:
                if self._auto_save_timer.isActive():
                    self._auto_save_timer.stop()
                self._auto_save_timer.start(1000)
        except Exception as e:
            from logzero import logger
            logger.error(f"阈值变更处理失败: {e}", exc_info=True)

    def _clear_all_alerts(self):
        """清除所有告警"""
        self.alert_list.clear()
        self.alerts.clear()

    def _export_alerts(self):
        """导出告警记录"""
        # TODO: 实现导出功能
        pass

    def add_alert(self, alert: AlertRecord):
        """
        添加告警记录

        Args:
            alert: 告警记录对象
        """
        self.alerts.append(alert)

        # 创建列表项
        item = QListWidgetItem()

        # 根据级别设置样式
        level_colors = {
            AlertLevel.INFO: "#3b82f6",
            AlertLevel.WARNING: "#f59e0b",
            AlertLevel.ERROR: "#ef4444",
            AlertLevel.CRITICAL: "#dc2626"
        }
        color = level_colors.get(alert.level, "#94a3b8")

        # 格式化时间
        time_str = alert.timestamp.strftime("%H:%M:%S")

        # 设置文本（使用换行符分隔，便于阅读）
        text = f"[{time_str}] {alert.level.value}\n{alert.metric_type}: {alert.message}"
        item.setText(text)

        # 设置大小提示，确保内容能完整显示
        from PyQt6.QtCore import QSize
        item.setSizeHint(QSize(100, 60))  # 每项最小高度60px

        # 设置样式
        item.setData(Qt.ItemDataRole.UserRole, alert.id)
        item.setForeground(QColor(color))

        self.alert_list.addItem(item)

        # 自动滚动到最新
        self.alert_list.scrollToBottom()

    def clear_alert(self, alert_id: str):
        """
        清除指定告警

        Args:
            alert_id: 告警ID
        """
        # 从数据中移除
        self.alerts = [a for a in self.alerts if a.id != alert_id]

        # 从UI中移除
        for i in range(self.alert_list.count()):
            item = self.alert_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == alert_id:
                self.alert_list.takeItem(i)
                break

    def get_current_config(self) -> CollectionConfig:
        """
        获取当前配置

        Returns:
            CollectionConfig对象
        """
        # 防御性检查：确保控件已初始化
        if not hasattr(self, 'interval_combo') or self.interval_combo is None:
            return self.config  # 返回默认配置
        if not hasattr(self, 'metric_checkboxes') or not self.metric_checkboxes:
            return self.config
        if not hasattr(self, 'fps_threshold') or self.fps_threshold is None:
            return self.config

        try:
            # 解析采样间隔
            interval_text = self.interval_combo.currentText()
            interval_map = {
                "1s": 1000,
                "3s": 3000,
                "5s": 5000,
                "10s": 10000
            }

            # 使用 .get() 方法安全访问字典
            cpu_cb = self.metric_checkboxes.get("CPU")
            memory_cb = self.metric_checkboxes.get("内存")
            fps_cb = self.metric_checkboxes.get("FPS")
            network_cb = self.metric_checkboxes.get("网络")
            battery_cb = self.metric_checkboxes.get("电池")
            gpu_cb = self.metric_checkboxes.get("GPU")

            config = CollectionConfig(
                interval_ms=interval_map.get(interval_text, 1000),
                enable_cpu=cpu_cb.isChecked() if cpu_cb else True,
                enable_memory=memory_cb.isChecked() if memory_cb else True,
                enable_fps=fps_cb.isChecked() if fps_cb else True,
                enable_network_up=network_cb.isChecked() if network_cb else True,
                enable_network_down=network_cb.isChecked() if network_cb else True,
                enable_gpu=gpu_cb.isChecked() if gpu_cb else False,
                fps_threshold=self.fps_threshold.value(),
                memory_threshold_mb=self.memory_threshold.value(),
                cpu_threshold_percent=self.cpu_threshold.value()
            )

            return config
        except Exception as e:
            from logzero import logger
            logger.error(f"获取当前配置失败: {e}", exc_info=True)
            return self.config  # 返回默认配置

    def set_config(self, config: CollectionConfig):
        """
        设置配置

        Args:
            config: CollectionConfig对象
        """
        # 防御性检查：确保控件已初始化
        if not hasattr(self, 'interval_combo') or self.interval_combo is None:
            return
        if not hasattr(self, 'metric_checkboxes') or not self.metric_checkboxes:
            return
        if not hasattr(self, 'fps_threshold') or self.fps_threshold is None:
            return

        try:
            # 临时禁用自动保存，避免循环触发
            old_auto_save = self.auto_save_enabled
            self.auto_save_enabled = False

            # 使用 QSignalBlocker 阻止信号发射，避免触发 _on_config_changed
            with QSignalBlocker(self):
                # 设置采样间隔（反向映射：毫秒 -> 文本）
                interval_map = {
                    1000: "1s",
                    3000: "3s",
                    5000: "5s",
                    10000: "10s"
                }
                interval_text = interval_map.get(config.interval_ms, "1s")
                with QSignalBlocker(self.interval_combo):
                    self.interval_combo.setCurrentText(interval_text)

                # 使用 .get() 方法安全访问字典（更新为新的6个指标）
                cpu_cb = self.metric_checkboxes.get("CPU")
                memory_cb = self.metric_checkboxes.get("内存")
                fps_cb = self.metric_checkboxes.get("FPS")
                network_up_cb = self.metric_checkboxes.get("网络上行")
                network_down_cb = self.metric_checkboxes.get("网络下行")
                gpu_cb = self.metric_checkboxes.get("GPU")

                # 设置指标开关（使用 QSignalBlocker 阻止信号）
                if cpu_cb:
                    with QSignalBlocker(cpu_cb):
                        cpu_cb.setChecked(config.enable_cpu)
                if memory_cb:
                    with QSignalBlocker(memory_cb):
                        memory_cb.setChecked(config.enable_memory)
                if fps_cb:
                    with QSignalBlocker(fps_cb):
                        fps_cb.setChecked(config.enable_fps)
                if network_up_cb:
                    with QSignalBlocker(network_up_cb):
                        network_up_cb.setChecked(config.enable_network_up)
                if network_down_cb:
                    with QSignalBlocker(network_down_cb):
                        network_down_cb.setChecked(config.enable_network_down)
                if gpu_cb:
                    with QSignalBlocker(gpu_cb):
                        gpu_cb.setChecked(config.enable_gpu)

                # 设置阈值（使用 QSignalBlocker 阻止信号）
                with QSignalBlocker(self.fps_threshold):
                    self.fps_threshold.setValue(config.fps_threshold)
                with QSignalBlocker(self.memory_threshold):
                    self.memory_threshold.setValue(config.memory_threshold_mb)
                with QSignalBlocker(self.cpu_threshold):
                    self.cpu_threshold.setValue(int(config.cpu_threshold_percent))

            self.config = config

            # 恢复自动保存设置
            self.auto_save_enabled = old_auto_save
        except Exception as e:
            from logzero import logger
            logger.error(f"设置配置失败: {e}", exc_info=True)

    def _auto_save_config(self):
        """自动保存配置"""
        try:
            # 防御性检查：确保配置管理器已初始化
            if not hasattr(self, 'config_manager') or self.config_manager is None:
                return

            current_config = self.get_current_config()
            if current_config:
                self.config_manager.update_collection_config(current_config)
        except Exception as e:
            from logzero import logger
            logger.error(f"自动保存配置失败: {e}", exc_info=True)

    def set_monitoring_state(self, is_monitoring: bool):
        """
        设置监控状态，相应地启用或禁用配置控件

        Args:
            is_monitoring: 是否正在监控
        """
        try:
            # 禁用/启用采样频率选择
            if hasattr(self, 'interval_combo') and self.interval_combo:
                self.interval_combo.setEnabled(not is_monitoring)

            # 禁用/启用指标复选框
            if hasattr(self, 'metric_checkboxes') and self.metric_checkboxes:
                for metric_name, checkbox in self.metric_checkboxes.items():
                    if checkbox:
                        checkbox.setEnabled(not is_monitoring)

            # 禁用/启用阈值设置
            if hasattr(self, 'fps_threshold') and self.fps_threshold:
                self.fps_threshold.setEnabled(not is_monitoring)
            if hasattr(self, 'memory_threshold') and self.memory_threshold:
                self.memory_threshold.setEnabled(not is_monitoring)
            if hasattr(self, 'cpu_threshold') and self.cpu_threshold:
                self.cpu_threshold.setEnabled(not is_monitoring)
            if hasattr(self, 'temp_threshold') and self.temp_threshold:
                self.temp_threshold.setEnabled(not is_monitoring)

            # 添加视觉提示
            if is_monitoring:
                # 监控中，显示提示信息
                if hasattr(self, 'alert_list') and self.alert_list:
                    from PyQt6.QtWidgets import QListWidgetItem, QListWidget
                    # 清空列表并添加提示
                    self.alert_list.clear()
                    item = QListWidgetItem("⚠️ 监控进行中\n配置已锁定，请先停止监控后再修改")
                    from PyQt6.QtCore import Qt
                    item.setForeground(Qt.GlobalColor.gray)
                    self.alert_list.addItem(item)
            else:
                # 停止监控，恢复列表
                if hasattr(self, 'alert_list') and self.alert_list:
                    self.alert_list.clear()

        except Exception as e:
            from logzero import logger
            logger.error(f"设置监控状态失败: {e}", exc_info=True)

    def _create_metrics_selector(self) -> QGroupBox:
        """
        创建指标选择器
        使用 card_configs 中定义的配置生成复选框
        """
        from ..utils.card_configs import ALL_METRIC_CARDS

        group = QGroupBox("监控指标")
        group.setStyleSheet("""
            QGroupBox {
                color: #e0e6ed;
                font-size: 14px;
                font-weight: bold;
                border: 1px solid #1a1f2e;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)

        layout = QGridLayout()
        layout.setSpacing(10)

        # 清空现有的复选框字典
        self.metric_checkboxes = {}

        # 创建指标ID到中文名称的映射（更新为新的6个指标）
        metric_id_to_name = {
            'cpu': 'CPU',
            'memory': '内存',
            'fps': 'FPS',
            'network_up': '网络上行',
            'network_down': '网络下行',
            'gpu': 'GPU'
        }

        for i, card_config in enumerate(ALL_METRIC_CARDS):
            # 使用配置中的标题，或者映射的中文名称
            display_name = metric_id_to_name.get(card_config.metric_id, card_config.title)

            checkbox = QCheckBox(display_name)
            checkbox.setChecked(card_config.enabled)
            checkbox.setStyleSheet(f"""
                QCheckBox {{
                    color: #e0e6ed;
                    spacing: 8px;
                }}
                QCheckBox::indicator {{
                    width: 18px;
                    height: 18px;
                    border: 2px solid #1a1f2e;
                    border-radius: 4px;
                    background-color: #0a0e17;
                }}
                QCheckBox::indicator:checked {{
                    background-color: {card_config.color};
                    border-color: {card_config.color};
                }}
            """)
            checkbox.stateChanged.connect(lambda state, mid=card_config.metric_id: self._on_metric_toggled(mid, state))

            # 使用中文名称作为键，以保持与现有代码的兼容性
            self.metric_checkboxes[display_name] = checkbox

            # 两列布局
            row = i // 2
            col = i % 2
            layout.addWidget(checkbox, row, col)

        group.setLayout(layout)
        return group

    def _on_metric_toggled(self, metric_id: str, state: int):
        """
        指标开关切换事件（使用本地配置对象，避免 ConfigManager 单例问题）

        Args:
            metric_id: 指标ID ('cpu', 'memory', 'fps', 'network_up', 'network_down', 'gpu')
            state: 复选框状态 (0=未选中, 2=已选中)

        Note:
            使用本地配置对象 self._local_config 而不是 ConfigManager 单例，
            避免 PyQt6 + Windows 环境下的多线程竞争条件问题。
        """
        try:
            from logzero import logger
            import traceback
            import sys

            # 创建指标ID到中文名称的映射（更新为新的6个指标）
            metric_id_to_name = {
                'cpu': 'CPU',
                'memory': '内存',
                'fps': 'FPS',
                'network_up': '网络上行',
                'network_down': '网络下行',
                'gpu': 'GPU'
            }

            # 获取对应的中文名称，用于更新配置
            metric_name = metric_id_to_name.get(metric_id, metric_id.upper())

            # 计算是否启用 (Qt.Checked = 2)
            enabled = (state == 2)

            # ===== iOS GPU 监控限制 =====
            # 检查是否是 iOS 设备上的 GPU 监控
            if enabled and metric_id == 'gpu':
                if self._is_ios_device():
                    logger.info("[iOS GPU 限制] 检测到 iOS 设备，阻止启用 GPU 监控")

                    # 找到 GPU 复选框并取消勾选
                    gpu_cb = self.metric_checkboxes.get("GPU")
                    if gpu_cb:
                        with QSignalBlocker(gpu_cb):
                            gpu_cb.setChecked(False)

                    # 显示友好提示
                    QMessageBox.warning(
                        self,
                        "iOS GPU 监控限制",
                        "抱歉，iOS 设备暂不支持 GPU 监控。\n\n"
                        "原因：\n"
                        "• iOS 系统 DVT 通道无法获取 GPU 能耗数据\n"
                        "• CLI 能耗命令超时（20+ 秒），不适合实时监控\n\n"
                        "已启用指标：\n"
                        "• CPU 使用率 ✓\n"
                        "• 内存使用 ✓\n"
                        "• FPS（系统刷新率参考）✓\n"
                        "• 网络流量（系统级）✓\n"
                        "• 电池状态 ✓"
                    )
                    return  # 直接返回，不继续处理

            logger.info(f"[DEBUG-1] 指标 {metric_name} 状态变更: {'启用' if enabled else '禁用'}")

            # 【关键修改】不使用 ConfigManager，直接使用成员变量
            # 避免多线程访问 ConfigManager 单例导致的崩溃
            logger.info(f"[DEBUG-2] 检查本地配置对象...")

            # 如果没有本地配置对象，创建一个默认的
            if not hasattr(self, '_local_config'):
                logger.info(f"[DEBUG-3] 创建本地配置对象...")
                from insight_eyes.desktop.ui.utils.models import CollectionConfig
                self._local_config = CollectionConfig()
                logger.info(f"[DEBUG-4] 本地配置对象创建成功: {self._local_config}")

            config = self._local_config
            logger.info(f"[DEBUG-5] 使用本地配置对象: {config}")

            # 更新对应指标的启用状态
            logger.info(f"[DEBUG-6] 调用 set_metric_enabled({metric_id}, {enabled})...")
            config.set_metric_enabled(metric_id, enabled)
            logger.info(f"[DEBUG-7] set_metric_enabled 调用成功")

            # 构建配置字典（更新为新的6个指标）
            logger.info(f"[DEBUG-8] 构建配置字典...")
            config_dict = {
                "interval_ms": getattr(config, 'interval_ms', 1000),
                "enable_cpu": getattr(config, 'enable_cpu', True),
                "enable_memory": getattr(config, 'enable_memory', True),
                "enable_fps": getattr(config, 'enable_fps', True),
                "enable_network_up": getattr(config, 'enable_network_up', True),
                "enable_network_down": getattr(config, 'enable_network_down', True),
                "enable_gpu": getattr(config, 'enable_gpu', False)
            }
            logger.info(f"[DEBUG-9] 配置字典: {config_dict}")

            # 强制刷新日志
            sys.stdout.flush()
            sys.stderr.flush()

            logger.info(f"[DEBUG-10] *** 即将发射 config_changed 信号 ***")
            self.config_changed.emit(config_dict)
            logger.info(f"[DEBUG-11] *** config_changed 信号发射成功 ***")

            sys.stdout.flush()
            sys.stderr.flush()

        except Exception as e:
            from logzero import logger
            logger.error(f"[DEBUG-EXCEPTION] 指标开关切换异常: {e}")
            logger.error(f"[DEBUG-EXCEPTION] 异常类型: {type(e).__name__}")
            logger.error(f"[DEBUG-EXCEPTION] 堆栈:\n{''.join(traceback.format_exc())}")

    def _is_ios_device(self) -> bool:
        """
        检查当前设备是否为 iOS 设备

        Returns:
            bool: 如果是 iOS 设备返回 True，否则返回 False
        """
        from logzero import logger
        logger.info("[iOS GPU 检测] 开始检测设备类型...")

        try:
            # 方法1: 通过 parent 窗口获取
            logger.info("[iOS GPU 检测] 方法1: 检查 parent 窗口")
            parent = self.parent()
            logger.info(f"[iOS GPU 检测]   parent = {parent}")
            if parent is None:
                logger.info("[iOS GPU 检测]   parent 为 None，跳过方法1")
            else:
                logger.info(f"[iOS GPU 检测]   parent 类型: {type(parent).__name__}")
                logger.info(f"[iOS GPU 检测]   parent 有 current_device_id: {hasattr(parent, 'current_device_id')}")
                logger.info(f"[iOS GPU 检测]   parent 有 device_manager: {hasattr(parent, 'device_manager')}")

                if hasattr(parent, 'current_device_id') and hasattr(parent, 'device_manager'):
                    device_id = parent.current_device_id
                    logger.info(f"[iOS GPU 检测]   device_id = {device_id}")
                    if device_id:
                        device = parent.device_manager.get_device(device_id)
                        logger.info(f"[iOS GPU 检测]   device = {device}")
                        if device:
                            from insight_eyes.desktop.core.models import Platform
                            result = device.platform == Platform.IOS
                            logger.info(f"[iOS GPU 检测]   device.platform = {device.platform}, 是 iOS: {result}")
                            return result
                        else:
                            logger.info("[iOS GPU 检测]   device 为 None，跳过")

            # 方法2: 通过 QApplication 获取主窗口
            logger.info("[iOS GPU 检测] 方法2: 检查 QApplication topLevelWidgets")
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            logger.info(f"[iOS GPU 检测]   QApplication.instance() = {app}")
            if app:
                top_widgets = app.topLevelWidgets()
                logger.info(f"[iOS GPU 检测]   topLevelWidgets 数量: {len(top_widgets)}")
                for i, widget in enumerate(top_widgets):
                    logger.info(f"[iOS GPU 检测]   Widget[{i}]: {type(widget).__name__}, 有 current_device_id: {hasattr(widget, 'current_device_id')}")
                    if hasattr(widget, 'current_device_id') and hasattr(widget, 'device_manager'):
                        device_id = widget.current_device_id
                        logger.info(f"[iOS GPU 检测]     找到 device_id = {device_id}")
                        if device_id:
                            device = widget.device_manager.get_device(device_id)
                            logger.info(f"[iOS GPU 检测]     device = {device}")
                            if device:
                                from insight_eyes.desktop.core.models import Platform
                                result = device.platform == Platform.IOS
                                logger.info(f"[iOS GPU 检测]     device.platform = {device.platform}, 是 iOS: {result}")
                                return True
            else:
                logger.info("[iOS GPU 检测]   QApplication.instance() 返回 None")

            # 方法1和方法2已覆盖主要场景，不再使用方法3以避免UI阻塞
            logger.info("[iOS GPU 检测] 所有方法都失败，返回 False")
            return False

        except Exception as e:
            from logzero import logger
            logger.error(f"[iOS GPU 检测] 检查 iOS 设备异常: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"[iOS GPU 检测] 堆栈: {traceback.format_exc()}")
            return False
