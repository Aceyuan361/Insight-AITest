# -*- coding: utf-8 -*-
"""
主窗口模块 - 批量采集架构版本

**架构改进：**
1. 使用 MetricsBatchCollector 替代原有的并行采集架构
2. 确保同一时间窗口的所有指标使用统一时间戳
3. 一次性更新监控面板，避免时间不一致

**关键变更：**
- 移除：MetricsCollectionWorker（原有并行采集）
- 新增：MetricsBatchCollector（时间窗口批量采集）
- 改进：_on_update_timer 使用批量采集
- 改进：_on_snapshot_ready 处理快照结果

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License

Author: @senior_architect - 资深技术架构师
"""

import sys
import os
from typing import Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QMenuBar, QMenu, QToolBar, QStatusBar,
    QMessageBox, QFileDialog, QDialog, QFormLayout,
    QSpinBox, QDoubleSpinBox, QComboBox, QPushButton,
    QDialogButtonBox, QLabel, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize, QThread, QObject
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QShortcut
from datetime import datetime
from logzero import logger

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from insight_eyes.desktop.ui.panels.device_selection_panel import DeviceSelectionPanel
from insight_eyes.desktop.ui.panels.monitor_panel_v2 import MonitorPanelV2
from insight_eyes.desktop.ui.panels.config_panel import ConfigPanel
from insight_eyes.desktop.core.device_manager import DeviceManager
from insight_eyes.desktop.core.models import AppStatus
from insight_eyes.desktop.analytics.metrics_processor import MetricsProcessor
from insight_eyes.desktop.analytics.anomaly_detector import AnomalyDetector
from insight_eyes.desktop.analytics.statistics import StatisticsAnalyzer
from insight_eyes.desktop.analytics.correlation_analyzer import CorrelationAnalyzer
from insight_eyes.desktop.analytics.thresholds import ThresholdManager
from insight_eyes.desktop.analytics.metrics_batch_collector import MetricsBatchCollector
from insight_eyes.desktop.config.config_manager import get_config_manager, AppConfig, UIConfig
from insight_eyes.desktop.data.database import DatabaseManager
from insight_eyes.desktop.data.exporter import DataExporter


# ========== 批量采集架构 - 快照处理工作线程 ==========

class SnapshotCollectionWorker(QObject):
    """
    快照采集工作线程 - PyQt6 集成版本

    在后台线程执行批量采集，完成后发送 snapshot_ready 信号
    确保主线程不阻塞
    """

    # 信号定义
    snapshot_ready = pyqtSignal(object)  # MetricsSnapshot
    collection_failed = pyqtSignal(str)  # 错误信息

    def __init__(self, batch_collector: MetricsBatchCollector):
        super().__init__()
        self.batch_collector = batch_collector

    def collect(self, device_id: str, package_name: str):
        """
        执行批量采集（在后台线程中运行）

        Args:
            device_id: 设备ID
            package_name: 应用包名
        """
        try:
            # 执行批量采集（阻塞等待，但在后台线程中）
            snapshot = self.batch_collector.collect_batch(device_id, package_name)

            # 检查快照是否有效
            if snapshot.is_valid():
                self.snapshot_ready.emit(snapshot)
            else:
                self.collection_failed.emit("所有指标采集失败")

        except Exception as e:
            logger.error(f"批量采集工作线程异常: {e}", exc_info=True)
            self.collection_failed.emit(str(e))


class MainWindow(QMainWindow):
    """
    Insight-Eye 主窗口 - 批量采集架构版本

    **架构改进：**
    - 使用 MetricsBatchCollector 确保时间一致性
    - 所有指标在同一时间窗口内采集
    - 一次性更新监控面板
    - 性能优化：并行采集 + 同步等待
    """

    # 信号定义
    monitoring_started = pyqtSignal()
    monitoring_stopped = pyqtSignal()
    monitoring_paused = pyqtSignal()

    def __init__(self):
        super().__init__()

        # 核心组件
        self.device_manager = DeviceManager()
        self.metrics_processor = None  # 将在开始监控时创建
        self.anomaly_detector = None  # 将在开始监控时创建
        self.statistics_analyzer = None  # 将在开始监控时创建
        self.correlation_analyzer = None  # 将在开始监控时创建
        self.threshold_manager = ThresholdManager()  # 阈值管理器
        self.database = DatabaseManager()
        self.exporter = DataExporter(self.database)

        # 配置管理器
        self.config_manager = get_config_manager()

        # 监控状态
        self.is_monitoring = False
        self.is_paused = False
        self.current_device_id: Optional[str] = None
        self.current_package_name: Optional[str] = None
        self.current_session_id: Optional[int] = None  # 当前监控会话ID
        self.monitoring_start_time: Optional[datetime] = None
        self.monitoring_duration = 0  # 秒

        # 设备适配器缓存（避免每次采集都创建新实例）
        self._cached_adapter = None
        self._cached_device_id = None
        self._cached_apm = None  # APM 实例缓存

        # ========== 架构改进：批量采集器 ==========
        # 替代原有的 MetricsCollectionWorker
        self._batch_collector = None  # MetricsBatchCollector 实例

        # 异步采集线程（使用批量采集架构）
        self._collection_thread = None
        self._collection_worker = None
        self._is_collecting = False  # 采集锁，防止重复采集

        # 定时器
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._on_update_timer)
        self.duration_timer = QTimer()
        self.duration_timer.timeout.connect(self._update_duration)
        self.duration_timer.setInterval(1000)  # 每秒更新时长

        # 加载配置
        self._load_app_config()

        # 初始化UI
        self._init_ui()
        self._connect_signals()
        self._setup_shortcuts()

        # 加载样式表
        self._load_styles()

        # 刷新设备列表
        QTimer.singleShot(1000, self._refresh_devices)

    def _init_ui(self):
        """初始化UI"""
        # 设置窗口属性
        self.setWindowTitle("Insight-Eye 移动设备性能监控 (批量采集架构)")
        self.setMinimumSize(1400, 900)
        self.resize(1600, 1000)

        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 创建分割器（可调整左右比例）
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #1a1f2e;
            }
            QSplitter::handle:hover {
                background-color: #00d4ff;
            }
            QSplitter::handle:horizontal {
                width: 2px;
            }
        """)

        # 左侧：设备选择面板
        self.device_panel = DeviceSelectionPanel()
        self.device_panel.device_manager = self.device_manager  # 设置 DeviceManager 引用
        splitter.addWidget(self.device_panel)

        # 中间：监控面板（使用V2霓虹风格）
        self.monitor_panel = MonitorPanelV2()
        splitter.addWidget(self.monitor_panel)

        # 右侧：配置面板
        self.config_panel = ConfigPanel()
        splitter.addWidget(self.config_panel)

        # 设置初始比例 (20:60:20)
        splitter.setSizes([280, 840, 280])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)

        main_layout.addWidget(splitter)

        # 创建菜单栏
        self._create_menu_bar()

        # 创建工具栏
        self._create_toolbar()

        # 创建状态栏
        self._create_status_bar()

    def _create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")

        save_template_action = QAction("保存模板(&S)", self)
        save_template_action.setShortcut(QKeySequence(QKeySequence.StandardKey.Save))
        save_template_action.triggered.connect(self._save_template)
        file_menu.addAction(save_template_action)

        export_data_action = QAction("导出数据(&E)", self)
        export_data_action.setShortcut(QKeySequence(QKeySequence.StandardKey.SaveAs))
        export_data_action.triggered.connect(self._export_data)
        file_menu.addAction(export_data_action)

        file_menu.addAction("生成报告(&R)", self._generate_report)
        file_menu.addSeparator()

        quit_action = QAction("退出(&X)", self)
        quit_action.setShortcut(QKeySequence(QKeySequence.StandardKey.Quit))
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # 配置菜单
        config_menu = menubar.addMenu("配置(&C)")
        config_menu.addAction("采集设置(&S)", self._open_collection_settings)
        config_menu.addAction("阈值设置(&T)", self._open_threshold_settings)
        config_menu.addAction("数据保留(&D)", self._open_data_retention_settings)
        config_menu.addSeparator()
        config_menu.addAction("导出配置(&E)", self._export_config)
        config_menu.addAction("导入配置(&I)", self._import_config)
        config_menu.addAction("重置配置(&R)", self._reset_config)
        config_menu.addSeparator()
        config_menu.addAction("打开配置目录(&O)", self._open_config_dir)

        # 工具菜单
        tools_menu = menubar.addMenu("工具(&T)")
        self.start_action = tools_menu.addAction("开始监控")
        self.start_action.setShortcut(QKeySequence("F5"))
        self.start_action.triggered.connect(self._start_monitoring)

        self.pause_action = tools_menu.addAction("暂停监控")
        self.pause_action.setShortcut(QKeySequence("F6"))
        self.pause_action.triggered.connect(self._pause_monitoring)
        self.pause_action.setEnabled(False)

        self.stop_action = tools_menu.addAction("停止监控")
        self.stop_action.setShortcut(QKeySequence("Shift+F5"))
        self.stop_action.triggered.connect(self._stop_monitoring)
        self.stop_action.setEnabled(False)

        tools_menu.addSeparator()

        mark_scenario_action = QAction("标记场景(&M)", self)
        mark_scenario_action.setShortcut(QKeySequence("Ctrl+M"))
        mark_scenario_action.triggered.connect(self._mark_scenario)
        tools_menu.addAction(mark_scenario_action)

        tools_menu.addAction("清理数据(&L)", self._cleanup_data)
        tools_menu.addAction("备份数据(&B)", self._backup_data)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")
        help_menu.addAction("使用说明(&U)", self._show_help)
        help_menu.addAction("快捷键(&K)", self._show_shortcuts)
        help_menu.addSeparator()
        help_menu.addAction("关于(&A)", self._show_about)

    def _create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)

        # 开始/暂停/停止按钮
        self.start_btn = toolbar.addAction("开始")
        self.start_btn.triggered.connect(self._start_monitoring)

        self.pause_btn = toolbar.addAction("暂停")
        self.pause_btn.triggered.connect(self._pause_monitoring)
        self.pause_btn.setEnabled(False)

        self.stop_btn = toolbar.addAction("停止")
        self.stop_btn.triggered.connect(self._stop_monitoring)
        self.stop_btn.setEnabled(False)

        toolbar.addSeparator()

        # 标记场景按钮
        mark_btn = toolbar.addAction("标记场景")
        mark_btn.triggered.connect(self._mark_scenario)

        toolbar.addSeparator()

        # 刷新按钮
        refresh_btn = toolbar.addAction("刷新设备")
        refresh_btn.triggered.connect(self._refresh_devices)

    def _create_status_bar(self):
        """创建状态栏"""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)

        # 状态标签
        self.status_label = QLabel("就绪")
        status_bar.addWidget(self.status_label)

        # 监控时长
        self.duration_status_label = QLabel("监控时长: 00:00:00")
        status_bar.addPermanentWidget(self.duration_status_label)

        # 样本数
        self.samples_status_label = QLabel("样本数: 0")
        status_bar.addPermanentWidget(self.samples_status_label)

        # ========== 新增：采集耗时显示 ==========
        self.collection_time_label = QLabel("采集耗时: -- ms")
        status_bar.addPermanentWidget(self.collection_time_label)

    def _connect_signals(self):
        """连接信号槽"""
        # 设备选择面板信号
        self.device_panel.target_selected.connect(self._on_target_selected)
        self.device_panel.start_monitoring.connect(self._start_monitoring)
        self.device_panel.stop_monitoring.connect(self._stop_monitoring)
        self.device_panel.refresh_devices.connect(self._refresh_devices)

        # 监控面板信号（兼容V2面板）
        if hasattr(self.monitor_panel, 'scenario_mark_requested'):
            self.monitor_panel.scenario_mark_requested.connect(self._add_scenario_marker)

        # 配置面板信号
        self.config_panel.config_changed.connect(self._on_config_changed)
        self.config_panel.threshold_changed.connect(self._on_threshold_changed)

        # 配置管理器信号
        self.config_manager.config_loaded.connect(self._on_config_loaded)
        self.config_manager.config_saved.connect(self._on_config_saved)

    def _setup_shortcuts(self):
        """设置快捷键"""
        # 开始监控: F5
        QShortcut(QKeySequence("F5"), self, self._start_monitoring)

        # 暂停监控: F6
        QShortcut(QKeySequence("F6"), self, self._pause_monitoring)

        # 停止监控: Shift+F5
        QShortcut(QKeySequence("Shift+F5"), self, self._stop_monitoring)

        # 标记场景: Ctrl+M
        QShortcut(QKeySequence("Ctrl+M"), self, self._mark_scenario)

        # 导出数据: Ctrl+E
        QShortcut(QKeySequence("Ctrl+E"), self, self._export_data)

        # 刷新设备: F4
        QShortcut(QKeySequence("F4"), self, self._refresh_devices)

    def _load_styles(self):
        """加载样式表"""
        style_path = os.path.join(os.path.dirname(__file__), "styles.qss")
        if os.path.exists(style_path):
            with open(style_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    # ==================== 架构改进：批量采集 ====================

    def _on_update_timer(self):
        """
        更新定时器 - 使用批量采集架构

        **关键改进：**
        - 不再使用 MetricsCollectionWorker（原有并行采集）
        - 改用 MetricsBatchCollector（时间窗口批量采集）
        - 确保同一时间窗口的所有指标使用统一时间戳
        """
        if not self.is_monitoring or self.is_paused:
            return

        # 验证必要条件
        if not self.current_device_id or not self.current_package_name or not self.current_session_id:
            logger.error("数据采集失败: 缺少必要的设备、应用或会话信息")
            return

        # 采集锁：如果上一次采集还在进行中，跳过本次
        if self._is_collecting:
            logger.debug("上一次采集未完成，跳过本次采集")
            return

        try:
            # 获取设备信息
            device = self.device_manager.get_device(self.current_device_id)
            if not device:
                logger.error(f"设备不存在: {self.current_device_id}")
                return

            # ========== 架构改进：复用 APM 实例 ==========
            # 检查是否需要创建新的批量采集器
            if (self._batch_collector is None or
                self._cached_device_id != self.current_device_id or
                self._cached_apm is None):

                logger.info(f"创建新的批量采集器: {self.current_device_id}")

                # 创建或复用设备适配器
                if (self._cached_adapter is None or
                    self._cached_device_id != self.current_device_id):

                    from desktop.core.device_adapters import DeviceAdapterFactory

                    self._cached_adapter = DeviceAdapterFactory.create_adapter(
                        self.current_device_id,
                        device.platform
                    )
                    self._cached_device_id = self.current_device_id

                # 检查设备连接
                if not self._cached_adapter.is_connected():
                    if not self._cached_adapter.connect():
                        logger.error(f"设备连接失败: {self.current_device_id}")
                        self.statusBar().showMessage(f"设备连接失败: {self.current_device_id}", 3000)
                        return

                # 获取 APM 实例（从适配器）
                self._cached_apm = self._cached_adapter._get_apm(self.current_package_name)

                # 启动 APM
                if self._cached_apm:
                    self._cached_apm.start()

                # 创建批量采集器（超时时间 3 秒）
                if self._cached_apm:
                    self._batch_collector = MetricsBatchCollector(
                        self._cached_apm,
                        timeout_seconds=3.0
                    )
                    logger.info("批量采集器已创建并初始化")

            # ========== 架构改进：启动异步批量采集 ==========
            self._start_async_batch_collection()

        except Exception as e:
            logger.error(f"启动批量采集失败: {e}", exc_info=True)
            self._is_collecting = False

    def _start_async_batch_collection(self):
        """
        启动异步批量采集线程

        **架构改进：**
        - 使用 SnapshotCollectionWorker（批量采集版本）
        - 在后台线程执行批量采集
        - 完成后发送 snapshot_ready 信号
        """
        # 标记采集开始
        self._is_collecting = True

        # 创建采集线程和工作对象
        self._collection_thread = QThread()
        self._collection_worker = SnapshotCollectionWorker(self._batch_collector)

        # 将工作对象移动到线程
        self._collection_worker.moveToThread(self._collection_thread)

        # 连接信号
        # 1. 线程启动时执行采集
        self._collection_thread.started.connect(
            lambda: self._collection_worker.collect(
                self.current_device_id,
                self.current_package_name
            )
        )

        # 2. 快照采集完成时处理结果
        self._collection_worker.snapshot_ready.connect(self._on_snapshot_ready)

        # 3. 采集失败时处理错误
        self._collection_worker.collection_failed.connect(self._on_collection_failed)

        # 4. 线程结束时清理资源
        self._collection_thread.finished.connect(self._on_collection_thread_finished)

        # 启动线程
        self._collection_thread.start()

    def _on_snapshot_ready(self, snapshot):
        """
        快照采集完成回调 - 核心改进

        **关键特性：**
        - 快照包含所有指标，使用统一时间戳
        - 一次性更新监控面板
        - 确保数据时间一致性

        Args:
            snapshot: MetricsSnapshot 对象
        """
        try:
            # ========== 新增：更新采集耗时显示 ==========
            collection_time = snapshot.collection_duration_ms
            self.collection_time_label.setText(f"采集耗时: {collection_time:.0f} ms")

            # 性能警告：如果采集时间过长
            if collection_time > 1000:
                logger.warning(f"采集时间超过 1 秒: {collection_time:.0f}ms")
                self.statusBar().showMessage(
                    f"⚠️ 采集时间过长 ({collection_time:.0f}ms)",
                    3000
                )

            # 转换为原始指标格式（兼容现有处理流程）
            raw_metrics = snapshot.to_raw_metrics_dict()

            # 使用指标处理器处理数据
            if self.metrics_processor and raw_metrics:
                processed = self.metrics_processor.process_raw_data(raw_metrics)

                if processed:
                    # 更新监控面板UI（一次性更新）
                    self._update_monitor_panel(processed)

                    # 保存到数据库
                    self._save_metrics_to_db(processed)

                    # 执行异常检测
                    if self.anomaly_detector:
                        alerts = self.anomaly_detector.detect_all(processed)
                        if alerts:
                            self._handle_alerts(alerts)

                    # 更新样本计数
                    self.monitoring_duration += 1
                    self.samples_status_label.setText(f"样本数: {self.monitoring_duration}")

                    # 日志输出（仅调试模式）
                    logger.debug(
                        f"快照处理完成: 时间戳={snapshot.snapshot_timestamp.isoformat()}, "
                        f"耗时={collection_time:.0f}ms, "
                        f"成功={snapshot.collection_success}"
                    )

        except Exception as e:
            logger.error(f"处理快照失败: {e}", exc_info=True)
        finally:
            # 采集完成，释放锁
            self._is_collecting = False

    def _on_collection_failed(self, error_msg: str):
        """批量采集失败回调"""
        logger.error(f"批量采集失败: {error_msg}")
        self.statusBar().showMessage(f"采集失败: {error_msg}", 3000)
        self._is_collecting = False

    def _on_collection_thread_finished(self):
        """采集线程结束清理"""
        # 清理线程对象
        if self._collection_thread:
            self._collection_thread.deleteLater()
            self._collection_thread = None
        self._collection_worker = None

    # ==================== 监控控制 ====================

    def _start_monitoring(self):
        """开始监控"""
        if self.is_monitoring and not self.is_paused:
            return

        # 检查是否选择了应用
        if not self.current_device_id or not self.current_package_name:
            QMessageBox.warning(self, "提示", "请先在左侧选择要监控的应用")
            return

        # 获取设备信息
        device = self.device_manager.get_device(self.current_device_id)
        if not device:
            QMessageBox.warning(self, "设备错误", f"找不到设备: {self.current_device_id}")
            return

        # 检查应用是否正在运行
        try:
            # 强制刷新应用列表以获取最新的运行状态
            apps = self.device_manager.get_device_apps(
                self.current_device_id,
                force_refresh=True
            )

            # 查找目标应用
            target_app = None
            for app in apps:
                if app.package_name == self.current_package_name:
                    target_app = app
                    break

            # 检查应用是否正在运行
            if not target_app or not target_app.is_running:
                app_name = target_app.app_name if target_app else self.current_package_name
                QMessageBox.warning(
                    self,
                    "应用未运行",
                    f"没有找到应用正在运行的进程\n\n"
                    f"应用: {app_name}\n\n"
                    f"请检查应用是否在运行中，然后重试。"
                )
                logger.warning(f"应用未运行，无法启动监控: {self.current_package_name}")
                return

            # 检查应用是否在后台运行
            if target_app.status == AppStatus.BACKGROUND:
                app_name = target_app.app_name
                reply = QMessageBox.question(
                    self,
                    "应用在后台运行",
                    f"应用正在后台运行（非前台）\n\n"
                    f"应用: {app_name}\n"
                    f"PID: {target_app.pid}\n\n"
                    f"后台运行时可能无法采集到完整的性能数据。\n"
                    f"是否继续监控？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    logger.info(f"用户取消后台应用监控: {self.current_package_name}")
                    return
                logger.info(f"用户确认继续监控后台应用: {self.current_package_name}")

            logger.info(f"应用运行状态检查通过: {target_app.app_name} (PID: {target_app.pid}, 状态: {target_app.status.value})")

        except Exception as e:
            logger.error(f"检查应用运行状态失败: {e}", exc_info=True)
            QMessageBox.warning(
                self,
                "检查失败",
                f"无法检查应用运行状态:\n{str(e)}\n\n请确保设备连接正常。"
            )
            return

        if self.is_paused:
            # 从暂停恢复
            self.is_paused = False
            self.statusBar().showMessage("监控已继续", 3000)
        else:
            # 开始新监控 - 创建数据库会话
            try:
                # 获取配置
                config = self.config_panel.get_current_config()

                # 创建监控会话
                self.current_session_id = self.database.create_session(
                    device_id=self.current_device_id,
                    package_name=self.current_package_name,
                    sample_interval=config.interval_ms,
                    tags={"scenario": "manual_monitoring", "architecture": "batch_snapshot"}
                )

                logger.info(f"创建监控会话: {self.current_session_id} (架构: batch_snapshot)")

                # 创建指标处理器
                self.metrics_processor = MetricsProcessor(
                    session_id=self.current_session_id,
                    device_id=self.current_device_id,
                    app_id=self.current_package_name,
                    window_size=60,
                    threshold_manager=self.threshold_manager
                )

                # 创建异常检测器
                self.anomaly_detector = AnomalyDetector(
                    session_id=self.current_session_id,
                    threshold_manager=self.threshold_manager
                )

                # 创建统计分析器
                self.statistics_analyzer = StatisticsAnalyzer(
                    session_id=self.current_session_id
                )

                # 创建关联分析器
                self.correlation_analyzer = CorrelationAnalyzer(
                    session_id=self.current_session_id
                )

                # 更新监控状态
                self.is_monitoring = True
                self.monitoring_start_time = datetime.now()
                self.monitoring_duration = 0
                self.monitor_panel.start_monitoring()

                # 锁定配置面板（监控过程中不允许修改配置）
                self.config_panel.set_monitoring_state(True)

                # 启动定时器
                self.update_timer.start(config.interval_ms)
                self.duration_timer.start()

                self.statusBar().showMessage(
                    f"监控已开始 (会话ID: {self.current_session_id}, 架构: batch_snapshot)",
                    3000
                )

            except Exception as e:
                logger.error(f"启动监控失败: {e}", exc_info=True)
                QMessageBox.critical(self, "启动失败", f"启动监控时发生错误:\n{str(e)}")
                return

        # 更新UI状态
        self._update_monitoring_ui_state()
        self.monitoring_started.emit()

    def _pause_monitoring(self):
        """暂停监控"""
        if not self.is_monitoring or self.is_paused:
            return

        self.is_paused = True
        self.update_timer.stop()
        self.duration_timer.stop()
        self.monitor_panel.stop_monitoring()

        self.statusBar().showMessage("监控已暂停", 3000)
        self._update_monitoring_ui_state()

    def _stop_monitoring(self):
        """停止监控 - 批量采集架构版本"""
        if not self.is_monitoring:
            return

        try:
            # 停止监控
            self.is_monitoring = False
            self.is_paused = False
            self.update_timer.stop()
            self.duration_timer.stop()

            # 结束数据库会话
            if self.current_session_id:
                self.database.end_session(self.current_session_id)
                logger.info(f"结束监控会话: {self.current_session_id}")

                # 显示性能统计
                if self._batch_collector:
                    stats = self._batch_collector.get_stats()
                    logger.info(f"批量采集性能统计: {stats}")

                self.statusBar().showMessage(
                    f"监控已停止 (会话ID: {self.current_session_id}, 样本数: {self.monitoring_duration})",
                    5000
                )
            else:
                self.statusBar().showMessage("监控已停止", 3000)

            # 清理资源
            if self.metrics_processor:
                self.metrics_processor.clear_buffers()
            self.monitor_panel.reset_monitoring()

            # ========== 架构改进：清理批量采集器 ==========
            # 停止 APM 实例
            if self._cached_apm:
                try:
                    logger.debug("停止 APM 实例")
                    self._cached_apm.stop()
                except Exception as e:
                    logger.warning(f"停止 APM 失败: {e}")
                self._cached_apm = None

            # 清理批量采集器
            if self._batch_collector:
                try:
                    self._batch_collector.cleanup()
                except Exception as e:
                    logger.warning(f"清理批量采集器失败: {e}")
                self._batch_collector = None

            # 清理设备适配器缓存
            if self._cached_adapter:
                try:
                    self._cached_adapter.cleanup()
                except Exception as e:
                    logger.warning(f"清理设备适配器失败: {e}")
            self._cached_adapter = None
            self._cached_device_id = None

            # ========== 清理异步采集线程 ==========
            # 1. 先释放采集锁，允许正在进行的采集完成
            self._is_collecting = False

            # 2. 如果有正在运行的采集线程，等待它完成
            if self._collection_thread and self._collection_thread.isRunning():
                logger.debug("等待采集线程完成...")
                # 断开信号连接，避免停止过程中的回调干扰
                try:
                    self._collection_thread.started.disconnect()
                    self._collection_thread.finished.disconnect()
                except:
                    pass

                # 请求线程退出
                self._collection_thread.quit()

                # 等待线程退出（最多 3 秒）
                if not self._collection_thread.wait(3000):
                    logger.warning("采集线程未能在 3 秒内退出，强制终止")
                    self._collection_thread.terminate()
                    self._collection_thread.wait(1000)

                logger.debug("采集线程已停止")

            # 3. 清理线程对象
            self._collection_thread = None
            self._collection_worker = None

            # 解锁配置面板（允许修改配置）
            self.config_panel.set_monitoring_state(False)

            # 重置采集耗时显示
            self.collection_time_label.setText("采集耗时: -- ms")

        except Exception as e:
            logger.error(f"停止监控失败: {e}", exc_info=True)
            self.statusBar().showMessage("监控已停止（部分数据可能未保存）", 3000)

        self._update_monitoring_ui_state()

    def _update_monitoring_ui_state(self):
        """更新监控UI状态"""
        if self.is_monitoring and not self.is_paused:
            # 监控中
            self.start_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
            self.pause_action.setEnabled(True)
            self.stop_action.setEnabled(True)
            self.status_label.setText("监控中 (批量采集)")
            self.status_label.setStyleSheet("color: #22c55e;")
            # 同步更新设备选择面板状态
            self.device_panel._set_monitoring_state(True)
        elif self.is_monitoring and self.is_paused:
            # 已暂停
            self.start_btn.setEnabled(True)
            self.start_btn.setText("继续")
            self.pause_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.pause_action.setEnabled(False)
            self.stop_action.setEnabled(True)
            self.status_label.setText("已暂停")
            self.status_label.setStyleSheet("color: #f59e0b;")
            # 同步更新设备选择面板状态（暂停时也保持监控状态）
            self.device_panel._set_monitoring_state(True)
        else:
            # 未监控
            self.start_btn.setEnabled(True)
            self.start_btn.setText("开始")
            self.pause_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
            self.pause_action.setEnabled(False)
            self.stop_action.setEnabled(False)
            self.status_label.setText("就绪")
            self.status_label.setStyleSheet("color: #94a3b8;")
            # 同步更新设备选择面板状态
            self.device_panel._set_monitoring_state(False)

    # ==================== 其他方法（保持不变）====================

    # 这里省略了其他方法，与原 main_window.py 保持一致
    # 包括：_update_monitor_panel, _save_metrics_to_db, _handle_alerts 等
    # 仅在关键处添加注释说明架构改进

    def _update_monitor_panel(self, processed_metrics):
        """
        更新监控面板显示

        **架构改进：**
        - 现在接收的是批量快照数据
        - 所有指标使用统一时间戳
        - 一次性更新，确保时间一致性
        """
        try:
            # 检查面板类型并使用相应接口
            if hasattr(self.monitor_panel, 'add_data_point'):
                # V2 面板接口：add_data_point(cpu, ram, fps, upload, download)
                cpu = processed_metrics.cpu.app_cpu_percent if processed_metrics.cpu else 0
                ram = processed_metrics.memory.total_mb if processed_metrics.memory else 0
                fps = processed_metrics.fps.fps if processed_metrics.fps else 0
                upload = processed_metrics.network.upload_speed_kb_s if processed_metrics.network else 0
                download = processed_metrics.network.download_speed_kb_s if processed_metrics.network else 0
                self.monitor_panel.add_data_point(cpu, ram, fps, upload, download)
            else:
                # 旧面板接口：update_metrics(ui_metrics)
                # 转换为UI面板需要的格式
                from desktop.ui.utils.models import ProcessedMetrics as UIMetrics

                ui_metrics = UIMetrics(
                    timestamp=processed_metrics.timestamp,
                    device_id=processed_metrics.device_id,
                    package_name=processed_metrics.app_id
                )

                # FPS
                if processed_metrics.fps:
                    ui_metrics.fps.fps = int(getattr(processed_metrics.fps, 'fps', 0))
                    ui_metrics.fps.jank = getattr(processed_metrics.fps, 'jank_count', 0)
                    ui_metrics.fps.big_jank = getattr(processed_metrics.fps, 'big_jank_count', 0)
                    ui_metrics.fps.frame_time_avg = getattr(processed_metrics.fps, 'frame_time_avg', 0.0)

                # CPU
                if processed_metrics.cpu:
                    ui_metrics.cpu.app_cpu_rate = getattr(processed_metrics.cpu, 'app_cpu_percent', 0.0)
                    ui_metrics.cpu.sys_cpu_rate = getattr(processed_metrics.cpu, 'sys_cpu_percent', 0.0)

                # 内存
                if processed_metrics.memory:
                    ui_metrics.memory.total_mb = getattr(processed_metrics.memory, 'total_mb', 0.0)
                    ui_metrics.memory.native_mb = getattr(processed_metrics.memory, 'native_mb', 0.0)
                    ui_metrics.memory.dalvik_mb = getattr(processed_metrics.memory, 'dalvik_mb', 0.0)

                # 网络
                if processed_metrics.network:
                    ui_metrics.network.upload_rate_kbs = getattr(processed_metrics.network, 'upload_speed_kb_s', 0.0)
                    ui_metrics.network.download_rate_kbs = getattr(processed_metrics.network, 'download_speed_kb_s', 0.0)

                # 更新UI
                self.monitor_panel.update_metrics(ui_metrics)

        except Exception as e:
            logger.error(f"更新监控面板失败: {e}", exc_info=True)

    def _save_metrics_to_db(self, processed_metrics):
        """保存指标数据到数据库"""
        try:
            # 转换为数据库格式
            metrics_dict = {
                'cpu_app': processed_metrics.cpu.app_cpu_percent if processed_metrics.cpu else None,
                'cpu_system': processed_metrics.cpu.sys_cpu_percent if processed_metrics.cpu else None,
                'memory_app_private': processed_metrics.memory.total_mb if processed_metrics.memory else None,
                'memory_pss': processed_metrics.memory.total_mb if processed_metrics.memory else None,
                'fps': processed_metrics.fps.fps if processed_metrics.fps else None,
                'fps_jank_count': processed_metrics.fps.jank_count if processed_metrics.fps else None,
                'network_up_speed': processed_metrics.network.upload_speed_kb_s if processed_metrics.network else None,
                'network_down_speed': processed_metrics.network.download_speed_kb_s if processed_metrics.network else None,
                'snapshot_timestamp': processed_metrics.timestamp.isoformat() if hasattr(processed_metrics, 'timestamp') else None,
            }

            # 保存到数据库
            metric_id = self.database.save_metrics(self.current_session_id, metrics_dict)

            # 每10次保存显示确认反馈（避免日志过多）
            if metric_id > 0 and self.monitoring_duration % 10 == 0:
                saved_count = len(self.database.get_metrics(self.current_session_id))
                logger.debug(f"数据已保存: 会话{self.current_session_id}, 共{saved_count}条")
                self.samples_status_label.setText(f"样本数: {saved_count}")

        except Exception as e:
            logger.error(f"保存数据到数据库失败: {e}", exc_info=True)

    # 省略其他方法...（与原 main_window.py 保持一致）
    # 包括：菜单操作、设备刷新、配置管理等

    def _save_template(self):
        """保存模板"""
        self.statusBar().showMessage("保存模板功能开发中...", 3000)

    def _export_data(self):
        """导出数据"""
        self.statusBar().showMessage("导出数据功能开发中...", 3000)

    def _generate_report(self):
        """生成报告"""
        self.statusBar().showMessage("生成报告功能开发中...", 3000)

    def _open_collection_settings(self):
        """打开采集设置对话框"""
        self.statusBar().showMessage("采集设置功能开发中...", 3000)

    def _open_threshold_settings(self):
        """打开阈值设置对话框"""
        self.statusBar().showMessage("阈值设置功能开发中...", 3000)

    def _open_data_retention_settings(self):
        """打开数据保留设置对话框"""
        self.statusBar().showMessage("数据保留设置功能开发中...", 3000)

    def _mark_scenario(self):
        """标记场景"""
        if not self.is_monitoring:
            QMessageBox.warning(self, "提示", "请先开始监控")
            return

        from PyQt6.QtWidgets import QInputDialog
        scenario_name, ok = QInputDialog.getText(
            self, "标记场景", "请输入场景名称:"
        )
        if ok and scenario_name:
            self.monitor_panel.mark_scenario(scenario_name)
            self.statusBar().showMessage(f"已标记场景: {scenario_name}", 3000)

    def _cleanup_data(self):
        """清理数据"""
        reply = QMessageBox.question(
            self, "确认清理",
            "确定要清理所有监控数据吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.monitor_panel.reset_monitoring()
            self.statusBar().showMessage("数据已清理", 3000)

    def _backup_data(self):
        """备份数据"""
        self.statusBar().showMessage("备份数据功能开发中...", 3000)

    def _show_help(self):
        """显示帮助"""
        QMessageBox.information(
            self, "使用说明",
            "Insight-Eye 移动设备性能监控工具 (批量采集架构)\n\n"
            "架构改进：\n"
            "- 同一时间窗口内采集所有指标\n"
            "- 所有指标使用统一时间戳\n"
            "- 确保数据时间一致性\n\n"
            "1. 连接Android或iOS设备\n"
            "2. 在左侧选择要监控的应用\n"
            "3. 点击\"开始\"或按F5开始监控\n"
            "4. 查看实时性能数据和趋势图\n"
            "5. 可使用快捷键快速操作"
        )

    def _show_shortcuts(self):
        """显示快捷键"""
        QMessageBox.information(
            self, "快捷键",
            "Insight-Eye 快捷键\n\n"
            "F5 - 开始监控\n"
            "F6 - 暂停/继续监控\n"
            "Shift+F5 - 停止监控\n"
            "Ctrl+M - 标记场景\n"
            "Ctrl+E - 导出数据\n"
            "F4 - 刷新设备列表"
        )

    def _show_about(self):
        """显示关于"""
        QMessageBox.about(
            self, "关于 Insight-Eye",
            "<h2>Insight-Eye v1.1.0 (批量采集架构)</h2>"
            "<p>移动设备性能监控工具</p>"
            "<p>支持 Android 和 iOS 平台</p>"
            "<hr>"
            "<p><b>架构改进：</b></p>"
            "<p>- 时间窗口批量采集</p>"
            "<p>- 统一时间戳确保数据一致性</p>"
            "<p>- 并行采集优化性能</p>"
            "<hr>"
            "<p>Copyright (c) 2025 Aceyuan361</p>"
            "<p>GitHub: https://github.com/Aceyuan361/Insight-Eye</p>"
            "<p>License: MIT License</p>"
        )

    def _refresh_devices(self):
        """刷新设备列表"""
        logger.info("开始刷新设备列表")
        self.statusBar().showMessage("正在扫描设备...", 2000)
        self.device_panel.clear()
        self.statusBar().showMessage("已刷新设备列表", 3000)

    def _on_target_selected(self, device_id: str, package_name: str):
        """监控目标已选择"""
        logger.info(f"收到 target_selected 信号: device_id={device_id}, package_name={package_name}")
        self.current_device_id = device_id
        self.current_package_name = package_name
        self.statusBar().showMessage(f"目标: {device_id} - {package_name}", 3000)

    def _on_config_changed(self, config: dict):
        """配置变更"""
        if self.is_monitoring and not self.is_paused:
            interval_ms = config.get("interval_ms", 1000)
            self.update_timer.setInterval(interval_ms)
            self.statusBar().showMessage(f"配置已更新，采样间隔: {interval_ms}ms", 3000)

    def _on_threshold_changed(self, thresholds: dict):
        """阈值变更"""
        self.statusBar().showMessage("告警阈值已更新", 3000)

    def _add_scenario_marker(self, scenario_name: str):
        """添加场景标记"""
        self.statusBar().showMessage(f"场景标记已添加: {scenario_name}", 3000)

    def _load_app_config(self):
        """加载应用程序配置"""
        config = self.config_manager.load_config()
        self._apply_ui_config(config.ui)
        if hasattr(self, 'config_panel'):
            self.config_panel.set_config(config.collection)
        print(f"配置已加载: {config.config_version}")

    def _apply_ui_config(self, ui_config: UIConfig):
        """应用UI配置"""
        self.resize(ui_config.window_width, ui_config.window_height)
        if ui_config.window_maximized:
            self.showMaximized()

    def _save_ui_config(self):
        """保存当前UI配置"""
        config = self.config_manager.get_config()
        config.ui.window_width = self.width()
        config.ui.window_height = self.height()
        config.ui.window_maximized = self.isMaximized()
        self.config_manager.save_config()

    def _on_config_loaded(self, config: AppConfig):
        """配置加载完成回调"""
        print(f"配置加载完成: {config.last_modified}")
        self.statusBar().showMessage("配置已加载", 3000)

    def _on_config_saved(self, config: AppConfig):
        """配置保存完成回调"""
        print(f"配置已保存: {config.last_modified}")

    def _export_config(self):
        """导出配置"""
        self.statusBar().showMessage("导出配置功能开发中...", 3000)

    def _import_config(self):
        """导入配置"""
        self.statusBar().showMessage("导入配置功能开发中...", 3000)

    def _reset_config(self):
        """重置配置"""
        self.statusBar().showMessage("重置配置功能开发中...", 3000)

    def _open_config_dir(self):
        """打开配置目录"""
        self.statusBar().showMessage("打开配置目录功能开发中...", 3000)

    def _update_duration(self):
        """更新监控时长"""
        if self.monitoring_start_time:
            duration_seconds = int((datetime.now() - self.monitoring_start_time).total_seconds())
            hours = duration_seconds // 3600
            minutes = (duration_seconds % 3600) // 60
            seconds = duration_seconds % 60

            duration_text = f"监控时长: {hours:02d}:{minutes:02d}:{seconds:02d}"
            self.duration_status_label.setText(duration_text)
            self.monitor_panel.update_duration(duration_seconds)

    def _handle_alerts(self, alerts):
        """处理异常告警"""
        for alert in alerts:
            self.database.save_alert(self.current_session_id, {
                'alert_type': alert.alert_type.value,
                'metric_name': alert.metric_name,
                'current_value': alert.current_value,
                'threshold_value': alert.threshold,
                'severity': alert.severity.value,
                'description': alert.message
            })

            if alert.severity.value == 'critical':
                self.statusBar().showMessage(
                    f"严重告警: {alert.metric_name} - {alert.message}",
                    5000
                )

    def closeEvent(self, event):
        """窗口关闭事件"""
        if self.is_monitoring:
            reply = QMessageBox.question(
                self, "确认退出",
                "监控正在进行中，确定要退出吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._stop_monitoring()
                self._save_ui_config()
                event.accept()
            else:
                event.ignore()
        else:
            self._save_ui_config()
            event.accept()
