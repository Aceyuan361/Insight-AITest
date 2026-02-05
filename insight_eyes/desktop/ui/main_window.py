# -*- coding: utf-8 -*-
"""
主窗口模块
Insight-Eye 桌面应用的主窗口
"""
import sys
import os
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
import threading

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QMenuBar, QMenu, QToolBar, QStatusBar,
    QMessageBox, QFileDialog, QDialog, QFormLayout,
    QSpinBox, QDoubleSpinBox, QComboBox, QPushButton,
    QDialogButtonBox, QLabel, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize, QThread, QObject, QRunnable, QThreadPool, QMutex
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QShortcut
from datetime import datetime
from logzero import logger

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from insight_eyes.desktop.ui.panels.device_selection_panel import DeviceSelectionPanel
from insight_eyes.desktop.ui.panels.monitor_panel_v2 import MonitorPanelV2
from insight_eyes.desktop.ui.panels.config_panel import ConfigPanel
from insight_eyes.desktop.ui.panels.report_panel import ReportPanel
from insight_eyes.desktop.core.device_manager import DeviceManager
from insight_eyes.desktop.core.models import AppStatus
from insight_eyes.desktop.analytics.metrics_processor import MetricsProcessor
from insight_eyes.desktop.analytics.anomaly_detector import AnomalyDetector
from insight_eyes.desktop.analytics.statistics import StatisticsAnalyzer
from insight_eyes.desktop.analytics.correlation_analyzer import CorrelationAnalyzer
from insight_eyes.desktop.analytics.thresholds import ThresholdManager
from insight_eyes.desktop.config.config_manager import AppConfig, UIConfig
from insight_eyes.desktop.data.database import DatabaseManager
from insight_eyes.desktop.data.exporter import DataExporter
from insight_eyes.desktop.analytics.metrics_batch_collector import MetricsBatchCollector, MetricsSnapshot
from insight_eyes.desktop.ui.widgets.processing_dialog import ProcessingDialog


# ========== 并行采集架构 - QRunnable 任务类 ==========

class MetricCollectorRunnable(QRunnable):
    """
    单个指标采集任务（QRunnable）
    每个 Runnable 负责采集一个指标，支持并行执行
    """
    def __init__(self, metric_type: str, adapter, package_name: str):
        super().__init__()
        self.metric_type = metric_type  # 'cpu', 'memory', 'network', 'battery', 'fps'
        self.adapter = adapter
        self.package_name = package_name
        self.result = None
        self.error = None
        self.is_done = False  # 标记任务是否完成
        self._mutex = QMutex()  # 保护结果的互斥锁

    def run(self):
        """执行采集任务（在后台线程中运行）"""
        try:
            logger.debug(f"[{self.metric_type}] 并行采集任务开始")

            if self.metric_type == 'cpu':
                data = self.adapter.collect_cpu(self.package_name)
                self._set_result(data if data else {'error': 'No data'})

            elif self.metric_type == 'memory':
                data = self.adapter.collect_memory(self.package_name)
                self._set_result(data if data else {'error': 'No data'})

            elif self.metric_type == 'network':
                data = self.adapter.collect_network(self.package_name)
                self._set_result(data if data else {'error': 'No data'})

            elif self.metric_type == 'battery':
                data = self.adapter.collect_battery()
                self._set_result(data if data else {'error': 'No data'})

            elif self.metric_type == 'fps':
                # FPS 已经在后台线程中运行，直接读取缓存
                data = self.adapter.collect_fps(self.package_name)
                self._set_result(data if data else {'error': 'No data'})

            logger.debug(f"[{self.metric_type}] 并行采集任务完成")

        except Exception as e:
            logger.error(f"[{self.metric_type}] 采集失败: {e}")
            self._set_result({'error': str(e)})
        finally:
            # 标记任务完成
            self._mutex.lock()
            self.is_done = True
            self._mutex.unlock()

    def _set_result(self, data):
        """线程安全地设置结果"""
        self._mutex.lock()
        try:
            self.result = data
        finally:
            self._mutex.unlock()

    def get_result(self):
        """获取采集结果"""
        self._mutex.lock()
        try:
            return self.result
        finally:
            self._mutex.unlock()

    def is_complete(self):
        """检查任务是否完成"""
        self._mutex.lock()
        try:
            return self.is_done
        finally:
            self._mutex.unlock()


class DatabaseSaveRunnable(QRunnable):
    """
    数据库保存任务（QRunnable）

    异步保存指标数据到数据库，避免阻塞 UI 线程

    改进（P1 - Task 14）：
    - 将数据库操作移到后台线程
    - 使用 QThreadPool 管理任务执行
    - 不阻塞 UI 更新流程
    - 支持保存指标和告警两种数据类型
    """
    def __init__(self, database: DatabaseManager, session_id: int, data_dict: dict, data_type: str = 'metrics'):
        """
        初始化数据库保存任务

        Args:
            database: 数据库管理器实例
            session_id: 会话 ID
            data_dict: 要保存的数据字典
            data_type: 数据类型 ('metrics' 或 'alert')
        """
        super().__init__()
        self.database = database
        self.session_id = session_id
        self.data_dict = data_dict
        self.data_type = data_type  # 'metrics' 或 'alert'
        self._mutex = QMutex()

    def run(self):
        """执行数据库保存（在后台线程中运行）"""
        try:
            if self.data_type == 'metrics':
                # 保存指标数据
                metric_id = self.database.save_metrics(self.session_id, self.data_dict)

                if metric_id > 0:
                    logger.debug(f"[数据库保存] ✓ 样本已保存: session={self.session_id}, id={metric_id}")
                else:
                    logger.warning(f"[数据库保存] ⚠ 保存失败: session={self.session_id}")

            elif self.data_type == 'alert':
                # 保存告警数据
                alert_id = self.database.save_alert(self.session_id, self.data_dict)

                if alert_id > 0:
                    logger.debug(f"[数据库保存] ✓ 告警已保存: session={self.session_id}, id={alert_id}")
                else:
                    logger.warning(f"[数据库保存] ⚠ 告警保存失败: session={self.session_id}")

        except Exception as e:
            logger.error(f"[数据库保存] ✗ 保存失败 ({self.data_type}): {e}", exc_info=True)


class MetricsCollectionWorker(QObject):
    """
    采集协调器 - 并行批量采集策略

    架构说明：
    - Android：使用并行批量采集（快速响应）

    Android 并行采集：
    - 5 个线程同时采集
    - 总耗时：~300ms
    - 优势：快速响应
    """
    # 信号：采集完成，发送原始指标数据
    collection_finished = pyqtSignal(dict)

    # 信号：采集失败
    collection_failed = pyqtSignal(str)

    # 信号：采集进度（用于调试）
    collection_progress = pyqtSignal(str)  # 发送进度信息

    def __init__(self, adapter, package_name: str):
        super().__init__()
        self.adapter = adapter
        self.package_name = package_name
        self.batch_collector = None  # 并行批量采集器（Android）

        logger.debug(f"采集协调器初始化: package={package_name}")

    def collect_metrics(self):
        """
        并行批量采集策略（支持 Android 和 iOS）
        """
        try:
            import time
            start_time = time.time()

            # 检测平台类型
            from desktop.core.models import Platform

            platform = self.adapter.platform if hasattr(self.adapter, 'platform') else None

            if platform == Platform.IOS:
                logger.info("===== 开始 iOS 指标采集 =====")
                raw_metrics = self._collect_ios()
            else:
                logger.info("===== 开始 Android 并行指标采集 =====")
                raw_metrics = self._collect_android_batch()

            # 记录采集完成
            elapsed_time = (time.time() - start_time) * 1000

            # 打印性能指标摘要（兼容两种平台的格式）
            if platform == Platform.IOS:
                cpu_val = raw_metrics.get('cpu', {}).get('cpu_app', 0)
                mem_val = raw_metrics.get('memory', {}).get('used_mb', 0)
                fps_val = raw_metrics.get('fps', {}).get('fps', 0)
                jank_val = raw_metrics.get('fps', {}).get('jank', 0)

                logger.info(f"[✓] iOS 采集完成: "
                           f"CPU={cpu_val}%, Memory={mem_val}MB, FPS={fps_val}, Jank={jank_val}, "
                           f"耗时={elapsed_time:.0f}ms")
            else:
                cpu_val = raw_metrics.get('cpu', {}).get('appCpuRate', 0)
                mem_val = raw_metrics.get('memory', {}).get('totalPass', 0)
                fps_val = raw_metrics.get('fps', {}).get('fps', 0)
                jank_val = raw_metrics.get('fps', {}).get('jank', 0)

                logger.info(f"[✓] Android 采集完成: "
                           f"CPU={cpu_val}%, Memory={mem_val}MB, FPS={fps_val}, Jank={jank_val}, "
                           f"耗时={elapsed_time:.0f}ms")

            # 发送采集完成信号
            self.collection_finished.emit(raw_metrics)

            # 通知线程退出
            if self.thread():
                self.thread().quit()

        except Exception as e:
            logger.error(f"采集失败: {e}", exc_info=True)
            self.collection_failed.emit(str(e))
            if self.thread():
                self.thread().quit()

    def _collect_android_batch(self) -> dict:
        """Android 并行批量采集（快速响应）"""
        import time

        # 获取 APM 实例
        apm = self.adapter._get_apm(self.package_name)

        # 创建批量采集器（首次）
        if self.batch_collector is None:
            self.batch_collector = MetricsBatchCollector(apm)  # 使用默认超时（8秒，适配 iOS sysmon）
            logger.debug("Android 批量采集器创建成功")

        # 预热 APM 实例
        time.sleep(0.05)

        # 执行批量采集
        device_id = self.adapter.device_id
        snapshot = self.batch_collector.collect_batch(device_id, self.package_name)

        # 转换为 raw_metrics 格式
        raw_metrics = {
            'fps': snapshot.fps if snapshot.fps else {},
            'memory': snapshot.memory if snapshot.memory else {},
            'cpu': snapshot.cpu if snapshot.cpu else {},
            'network': snapshot.network if snapshot.network else {},
            'battery': snapshot.battery if snapshot.battery else {},
            'app_status': {
                'is_alive': True,
                'status_changed': False
            },
            'snapshot_timestamp': snapshot.snapshot_timestamp,
            'collection_duration_ms': snapshot.collection_duration_ms,
            'collection_success': snapshot.collection_success
        }

        # 记录未完成的指标
        if snapshot.incomplete_metrics:
            for metric in snapshot.incomplete_metrics:
                raw_metrics[metric] = {'error': snapshot.collection_errors.get(metric, 'Unknown')}
                logger.warning(f"[{metric}] 采集失败")

        return raw_metrics

    def _collect_ios(self) -> dict:
        """iOS 串行采集（简化实现）"""
        import time

        # 获取 APM 实例
        apm = self.adapter._get_apm(self.package_name)

        # 预热 APM 实例
        time.sleep(0.05)

        # 采集各指标
        cpu_data = apm.collectCpu() or {}
        memory_data = apm.collectMemory() or {}
        fps_data = apm.collectFps() or {}
        network_data = apm.collectFlow() or {}
        logger.debug(f"[iOS 数据采集] network_data = {network_data}")
        battery_data = apm.collectBattery() or {}

        # 转换为与 Android 兼容的格式（用于数据库存储）
        raw_metrics = {
            'cpu': {
                'appCpuRate': cpu_data.get('cpu_app', 0),
                'sysCpuRate': cpu_data.get('cpu_system', 0),
                'cpu_app': cpu_data.get('cpu_app', 0),  # 数据库格式
                'cpu_system': cpu_data.get('cpu_system', 0),
            },
            'memory': {
                'totalPass': memory_data.get('used_mb', 0),
                'nativePass': 0,  # iOS 暂不支持
                'dalvikPass': 0,  # iOS 暂不支持
                'memory_app_private': memory_data.get('used_mb', 0),  # 数据库格式
            },
            'fps': fps_data,
            'network': {
                'upFlow': network_data.get('upFlow', 0),
                'downFlow': network_data.get('downFlow', 0),
            },
            'battery': battery_data,
            'app_status': {
                'is_alive': True,
                'status_changed': False
            },
            'snapshot_timestamp': time.time(),
            'collection_duration_ms': 0,
            'collection_success': True
        }

        logger.debug(f"[iOS 数据采集] raw_metrics['network'] = {raw_metrics['network']}")
        return raw_metrics


class MainWindow(QMainWindow):
    """
    Insight-Eye 主窗口
    包含设备列表、监控面板和配置面板的完整界面
    """

    # 信号定义
    monitoring_started = pyqtSignal()
    monitoring_stopped = pyqtSignal()

    # UI 更新频率限制（防止卡顿）
    MAX_UI_UPDATE_FPS = 30  # 最大 UI 更新频率
    MIN_UI_UPDATE_INTERVAL = 1 / MAX_UI_UPDATE_FPS  # 约 0.033s（33毫秒）

    @property
    def config_manager(self):
        """延迟获取配置管理器"""
        if self._config_manager is None:
            from insight_eyes.desktop.config.config_manager import get_config_manager
            self._config_manager = get_config_manager()

            # 首次访问时连接配置管理器信号
            # 这样可以避免在 __init__ 中触发 ConfigManager 的单例初始化
            try:
                self._config_manager.config_loaded.connect(self._on_config_loaded)
                self._config_manager.config_saved.connect(self._on_config_saved)
            except Exception as e:
                logger.warning(f"连接配置管理器信号失败: {e}")

            # 加载配置（首次访问时）
            # 直接使用 _config_manager 而不是 self.config_manager 避免递归
            try:
                config = self._config_manager.load_config()
                # 应用UI配置
                self._apply_ui_config(config.ui)
                # 应用采集配置到配置面板
                if hasattr(self, 'config_panel'):
                    self.config_panel.set_config(config.collection)
                logger.info(f"配置已加载: {config.config_version}")
            except Exception as e:
                logger.warning(f"加载配置失败: {e}")

        return self._config_manager

    def __init__(self, debug_mode=False):
        super().__init__()

        # 调试模式：控制是否打印详细的调试日志
        self.debug_mode = debug_mode
        if self.debug_mode:
            logger.info("[主窗口] 调试模式已启用，将打印全链路日志")

        # 核心组件
        self.device_manager = DeviceManager()
        self.metrics_processor = None  # 将在开始监控时创建
        self.anomaly_detector = None  # 将在开始监控时创建
        self.statistics_analyzer = None  # 将在开始监控时创建
        self.correlation_analyzer = None  # 将在开始监控时创建
        self.threshold_manager = ThresholdManager()  # 阈值管理器
        self.database = DatabaseManager()
        self.exporter = DataExporter(self.database)

        # 配置管理器（延迟初始化）
        self._config_manager = None

        # 不启动持续扫描，改为按需扫描（用户点击刷新时）
        # self.device_manager.start_scan()  # 已移除持续扫描

        # 监控状态
        self.is_monitoring = False
        self.current_device_id: Optional[str] = None
        self.current_package_name: Optional[str] = None
        self.current_session_id: Optional[int] = None  # 当前监控会话ID
        self.monitoring_start_time: Optional[datetime] = None
        self.monitoring_duration = 0  # 秒

        # 设备适配器缓存（避免每次采集都创建新实例）
        self._cached_adapter = None
        self._cached_device_id = None

        # 异步采集线程（性能优化：将数据采集移到后台线程）
        self._collection_thread = None
        self._collection_worker = None
        self._is_collecting = False  # 采集锁，防止重复采集

        # UI 更新频率限制（防止卡顿）
        self._last_ui_update_time = 0  # 上次 UI 更新时间戳
        self._pending_ui_update = False  # 是否有待处理的 UI 更新

        # ============ 方案3：信号槽连接跟踪系统 ============
        # 保存所有信号连接引用，确保能够精确断开（避免内存泄漏）
        # 格式: [(signal, slot, connection_id), ...]
        self._signal_connections = []

        # ============ 方案3：QThreadPool 任务跟踪 ============
        # 专用的数据库保存线程池（避免使用全局线程池）
        from PyQt6.QtCore import QThreadPool
        self._db_thread_pool = QThreadPool()
        self._db_thread_pool.setMaxThreadCount(2)  # 限制并发数
        # 跟踪活跃任务
        self._active_db_tasks = []
        self._active_db_tasks_lock = threading.Lock()

        # 定时器
        self.update_timer = QTimer()
        self._connect_signal(self.update_timer.timeout, self._on_update_timer)
        self.duration_timer = QTimer()
        self.duration_timer.timeout.connect(self._update_duration)
        self.duration_timer.setInterval(1000)  # 每秒更新时长

        # 初始化UI
        self._init_ui()
        self._connect_signals()
        self._setup_shortcuts()

        # 加载样式表
        self._load_styles()

        # 加载配置（延迟到首次访问 config_manager 时）
        # 不在 __init__ 中调用 _load_app_config()，避免触发 ConfigManager 的单例初始化
        # self._load_app_config()  # 已移除，改为延迟加载

        # 刷新设备列表
        QTimer.singleShot(1000, self._refresh_devices)

    def _init_ui(self):
        """初始化UI"""
        # 设置窗口属性
        self.setWindowTitle("Insight-Eye 移动设备性能监控")

        # 获取屏幕可用大小
        from PyQt6.QtGui import QScreen
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()

        # 根据屏幕大小设置合适的窗口大小
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()

        # 窗口大小不超过屏幕的 95%
        window_width = min(1600, int(screen_width * 0.95))
        window_height = min(1000, int(screen_height * 0.95))

        # 最小窗口大小
        min_width = min(1400, int(screen_width * 0.9))
        min_height = min(900, int(screen_height * 0.9))

        self.setMinimumSize(min_width, min_height)
        self.resize(window_width, window_height)

        # 确保窗口显示在屏幕中央
        window_geometry = self.frameGeometry()
        center_point = screen_geometry.center()
        window_geometry.moveCenter(center_point)

        # 确保窗口不会超出屏幕边界
        x = max(0, min(window_geometry.left(), screen_width - window_width))
        y = max(0, min(window_geometry.top(), screen_height - window_height))
        self.move(x, y)

        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 创建导航栏
        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(10, 10, 10, 10)
        nav_layout.setSpacing(10)

        # 导航按钮
        self.monitor_btn = QPushButton("实时监控")
        self.monitor_btn.setCheckable(True)
        self.monitor_btn.setChecked(True)
        self.monitor_btn.setMinimumWidth(120)
        self.monitor_btn.setStyleSheet("""
            QPushButton {
                background-color: #121824;
                color: #e0e6ed;
                border: 1px solid #1a1f2e;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #1a1f2e;
                border-color: #00d4ff;
                color: #00d4ff;
            }
            QPushButton:checked {
                background-color: #00d4ff;
                color: #0a0e17;
                border-color: #00d4ff;
            }
        """)
        self.monitor_btn.clicked.connect(self._show_monitoring_view)
        nav_layout.addWidget(self.monitor_btn)

        self.report_btn = QPushButton("测试报告")
        self.report_btn.setCheckable(True)
        self.report_btn.setMinimumWidth(120)
        self.report_btn.setStyleSheet(self.monitor_btn.styleSheet())
        self.report_btn.clicked.connect(self._show_report_view)
        nav_layout.addWidget(self.report_btn)

        nav_layout.addStretch()

        main_layout.addLayout(nav_layout)

        # 创建堆栈窗口（用于切换监控和报告视图）
        from PyQt6.QtWidgets import QStackedWidget
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("background-color: #0a0e17;")

        # === 监控视图 ===
        monitor_widget = QWidget()
        monitor_layout = QHBoxLayout(monitor_widget)
        monitor_layout.setContentsMargins(0, 0, 0, 0)
        monitor_layout.setSpacing(0)

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

        monitor_layout.addWidget(splitter)
        self.stacked_widget.addWidget(monitor_widget)

        # === 报告视图 ===
        self.report_panel = ReportPanel()
        self.stacked_widget.addWidget(self.report_panel)

        main_layout.addWidget(self.stacked_widget)

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

        # 开始/停止按钮
        self.start_btn = toolbar.addAction("开始")
        self.start_btn.triggered.connect(self._start_monitoring)

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

        # 配置管理器信号（延迟连接）
        # 不在 __init__ 中连接，而是在首次访问 config_manager 时连接
        # 这样可以避免在 QApplication 创建之前触发 ConfigManager 的单例初始化

    def _setup_shortcuts(self):
        """设置快捷键"""
        # 开始监控: F5
        QShortcut(QKeySequence("F5"), self, self._start_monitoring)

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

    # ==================== 菜单操作 ====================

    def _save_template(self):
        """保存模板"""
        self.statusBar().showMessage("保存模板功能开发中...", 3000)

    def _export_data(self):
        """导出数据"""
        # 检查是否有会话数据
        if not self.current_session_id:
            QMessageBox.warning(
                self,
                "无法导出",
                "没有可导出的监控数据。\n请先开始监控并采集一些数据。"
            )
            return

        try:
            # 检查会话是否有数据
            session = self.database.get_session(self.current_session_id)
            if not session:
                QMessageBox.warning(self, "无法导出", "找不到监控会话数据")
                return

            metrics = self.database.get_metrics(self.current_session_id)
            if not metrics:
                QMessageBox.warning(
                    self,
                    "无法导出",
                    "当前会话没有采集到任何指标数据。\n请先开始监控采集数据。"
                )
                return

            # 选择导出格式和文件路径
            file_path, selected_filter = QFileDialog.getSaveFileName(
                self,
                "导出监控数据",
                os.path.join(
                    os.path.expanduser("~"),
                    f"insight_eye_{session['package_name']}_{self.current_session_id}"
                ),
                "Excel文件 (*.xlsx);;CSV文件 (*.csv);;JSON文件 (*.json)"
            )

            if not file_path:
                return

            # 根据选择的格式导出
            success = False
            if file_path.endswith('.xlsx') or selected_filter == "Excel文件 (*.xlsx)":
                if not file_path.endswith('.xlsx'):
                    file_path += '.xlsx'
                success = self.exporter.export_to_excel(self.current_session_id, file_path)
            elif file_path.endswith('.csv') or selected_filter == "CSV文件 (*.csv)":
                if not file_path.endswith('.csv'):
                    file_path += '.csv'
                success = self.exporter.export_to_csv(self.current_session_id, file_path)
            elif file_path.endswith('.json') or selected_filter == "JSON文件 (*.json)":
                if not file_path.endswith('.json'):
                    file_path += '.json'
                success = self.exporter.export_to_json(self.current_session_id, file_path)

            if success:
                QMessageBox.information(
                    self,
                    "导出成功",
                    f"数据已成功导出到:\n{file_path}\n\n共导出 {len(metrics)} 条指标记录"
                )
                self.statusBar().showMessage(f"数据已导出: {file_path}", 5000)
            else:
                QMessageBox.critical(self, "导出失败", "导出数据时发生错误，请查看日志")

        except Exception as e:
            logger.error(f"导出数据失败: {e}", exc_info=True)
            QMessageBox.critical(self, "导出失败", f"导出数据时发生错误:\n{str(e)}")

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

        # 简单输入对话框
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
            "<h2>Insight-Eye 移动设备性能监控工具</h2>"
            "<h3>快速开始</h3>"
            "<ol>"
            "<li>连接 Android 或 iOS 设备</li>"
            "<li>在左侧选择要监控的应用</li>"
            "<li>点击\"开始\"或按 <b>F5</b> 开始监控</li>"
            "<li>查看实时性能数据和趋势图</li>"
            "</ol>"
            "<h3>监控指标</h3>"
            "<p><b>Android 平台</b>：CPU、内存、FPS、网络(上行/下行)、GPU（开发中）、电池</p>"
            "<p><b>iOS 平台</b>：CPU、内存、FPS、网络(系统级)、电池</p>"
            "<p><i>注意：iOS GPU 监控受系统限制，暂不支持</i></p>"
            "<h3>平台支持</h3>"
            "<p><b>Android</b>：支持 Android 7.0 及以上版本</p>"
            "<p><b>iOS</b>：支持 iOS 16.x 版本（不支持 iOS 17+）</p>"
            "<p><i>注：iOS 需要信任电脑并启用开发者模式</i></p>"
            "<h3>快捷键</h3>"
            "<ul>"
            "<li><b>F5</b> - 开始监控</li>"
            "<li><b>Shift+F5</b> - 停止监控</li>"
            "<li><b>Ctrl+M</b> - 标记场景</li>"
            "<li><b>Ctrl+E</b> - 导出数据</li>"
            "<li><b>F4</b> - 刷新设备列表</li>"
            "</ul>"
        )

    def _show_shortcuts(self):
        """显示快捷键"""
        QMessageBox.information(
            self, "快捷键",
            "Insight-Eye 快捷键\n\n"
            "F5 - 开始监控\n"
            "Shift+F5 - 停止监控\n"
            "Ctrl+M - 标记场景\n"
            "Ctrl+E - 导出数据\n"
            "F4 - 刷新设备列表"
        )

    def _show_about(self):
        """显示关于"""
        QMessageBox.about(
            self, "关于 Insight-Eye",
            "<h2>Insight-Eye v1.0.3</h2>"
            "<p><b>移动设备性能监控工具</b></p>"
            "<p>作者：<b>Aceyuan361</b></p>"
            "<p>欢迎在 GitHub 上交流学习与讨论</p>"
            "<p>支持平台：Android、iOS</p>"
            "<h3>平台支持</h3>"
            "<p><b>Android</b>：支持 Android 7.0 及以上版本</p>"
            "<p><b>iOS</b>：支持 iOS 16.x 版本（不支持 iOS 17+）</p>"
            "<h3>监控能力</h3>"
            "<p><b>Android</b>：CPU、内存、FPS、网络(上行/下行)、GPU（开发中）、电池</p>"
            "<p><b>iOS</b>：CPU、内存、FPS、网络(系统级流量)、电池</p>"
            "<p><i>注：iOS GPU 受系统 DVT 限制，网络为系统级流量</i></p>"
        )

    # ==================== 监控控制 ====================

    def _start_monitoring(self):
        """开始监控"""
        if self.is_monitoring:
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
        # 注意：iOS 平台由于 pymobiledevice3 限制，无法检测运行状态，跳过检查直接监控
        try:
            # 获取设备平台信息
            from insight_eyes.desktop.core.models import Platform
            device = self.device_manager.get_device(self.current_device_id)
            is_ios = device and device.platform == Platform.IOS

            if is_ios:
                # iOS 平台：检查进程是否存在（使用 SysmonService）
                logger.info(f"iOS 平台检测到，检查进程是否存在: {self.current_package_name}")
                logger.info(f"iOS 设备: {device.name if device else self.current_device_id}")
                logger.info(f"iOS Bundle ID: {self.current_package_name}")

                try:
                    from insight_eyes.public.ios.sysmon_service import SysmonService
                    from insight_eyes.public.ios.exceptions import ProcessNotFoundError

                    sysmon_service = SysmonService.get_instance(self.current_device_id)

                    if not sysmon_service.connect():
                        QMessageBox.warning(
                            self,
                            "连接失败",
                            f"无法连接到 iOS 设备: {self.current_device_id}\n\n"
                            f"请检查设备连接状态。"
                        )
                        return

                    target_process = sysmon_service.get_process_by_bundle_id(self.current_package_name)

                    if not target_process:
                        # 进程不存在
                        QMessageBox.warning(
                            self,
                            "应用未运行",
                            f"没有找到应用正在运行的进程\n\n"
                            f"应用: {self.current_package_name}\n\n"
                            f"请检查应用是否在运行中，然后重试。"
                        )
                        logger.warning(f"iOS 应用进程不存在，无法启动监控: {self.current_package_name}")
                        return

                    logger.info(f"✓ 找到目标进程: PID={target_process.get('pid')}, Name={target_process.get('name')}")
                    target_app = None

                except Exception as check_error:
                    logger.error(f"检查 iOS 进程失败: {check_error}")
                    # 如果检查失败，允许用户尝试监控（在采集时会再检查）
                    reply = QMessageBox.question(
                        self,
                        "无法检查进程状态",
                        f"无法确认应用是否在运行\n\n"
                        f"应用: {self.current_package_name}\n"
                        f"错误: {str(check_error)}\n\n"
                        f"是否仍要尝试监控？",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.No:
                        logger.info(f"用户取消监控: {self.current_package_name}")
                        return
                    logger.info(f"用户确认尝试监控: {self.current_package_name}")
                    target_app = None
            else:
                # Android 平台：正常检查运行状态
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

        # 开始新监控 - 创建数据库会话
        try:
            # 获取配置
            config = self.config_panel.get_current_config()

            # 获取平台信息（转换为小写以匹配数据库约束）
            device = self.device_manager.get_device(self.current_device_id)
            platform_value = device.platform.value.lower() if device else 'android'

            # 创建监控会话
            self.current_session_id = self.database.create_session(
                device_id=self.current_device_id,
                package_name=self.current_package_name,
                sample_interval=config.interval_ms,
                platform=platform_value,
                tags={"scenario": "manual_monitoring"}
            )

            logger.info(f"创建监控会话: {self.current_session_id}")

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

            # 使用定时采集
            logger.info("===== 启动定时采集 =====")
            # 启动定时器
            self.update_timer.start(config.interval_ms)
            self.duration_timer.start()

            self.statusBar().showMessage(f"监控已开始 (会话ID: {self.current_session_id})", 3000)

        except Exception as e:
            logger.error(f"启动监控失败: {e}", exc_info=True)
            QMessageBox.critical(self, "启动失败", f"启动监控时发生错误:\n{str(e)}")
            return

        # 更新UI状态
        self._update_monitoring_ui_state()
        self.monitoring_started.emit()

    def _stop_monitoring(self):
        """停止监控 - 异步处理避免UI冻结"""
        if not self.is_monitoring:
            return

        try:
            # 保存会话ID用于后续处理
            session_id = self.current_session_id

            # 停止监控（立即执行，不阻塞）
            self.is_monitoring = False
            self.update_timer.stop()
            self.duration_timer.stop()

            # 显示处理对话框
            self.processing_dialog = ProcessingDialog(self)
            self.processing_dialog.finished.connect(self._on_processing_complete)
            self.processing_dialog.show()

            # 保存适配器引用，传递给后台线程处理
            cached_adapter = self._cached_adapter

            # 创建后台工作线程处理数据
            from insight_eyes.desktop.ui.widgets.processing_dialog import ProcessingWorker
            self.processing_worker = ProcessingWorker(
                session_id,
                self.database,
                self.metrics_processor,
                cached_adapter=cached_adapter,  # 传递适配器到后台线程
                parent=self
            )
            self.processing_worker.progress_updated.connect(
                lambda progress, status: self.processing_dialog.set_progress(progress)
            )
            self.processing_worker.progress_updated.connect(
                lambda progress, status: self.processing_dialog.update_status(status)
            )
            self.processing_worker.finished.connect(self._on_processing_worker_complete)

            # 立即更新UI状态
            self.statusBar().showMessage(
                f"正在停止监控 (会话ID: {session_id})...",
                2000
            )

            # 启动后台处理
            self.processing_worker.start()

            # 关键修复：立即清理采集线程（不等待后台处理完成）
            # 这样可以快速释放采集资源，避免UI阻塞
            self._is_collecting = False

            # 清理采集线程（快速操作，不阻塞）
            if self._collection_thread and self._collection_thread.isRunning():
                logger.debug("快速清理采集线程...")
                self._disconnect_collection_signals()
                self._collection_thread.quit()
                if not self._collection_thread.wait(2000):
                    logger.warning("采集线程未能在2秒内退出，强制终止")
                    self._collection_thread.terminate()
                    self._collection_thread.wait(500)
                logger.debug("采集线程已清理")

            self._collection_thread = None
            self._collection_worker = None

            # 清理设备适配器缓存引用（实际清理由后台线程执行）
            # 注意：不在这里执行 apm.stop() 和 cleanup()，避免阻塞主线程
            self._cached_adapter = None
            self._cached_device_id = None

            # 立即清除监控面板数据（不等待后台处理）
            self.monitor_panel.reset_monitoring()

            # 解锁配置面板
            self.config_panel.set_monitoring_state(False)

            logger.info(f"监控已停止 (会话ID: {session_id})，后台处理中...")

        except Exception as e:
            logger.error(f"停止监控失败: {e}", exc_info=True)
            self.statusBar().showMessage("监控已停止（部分数据可能未保存）", 3000)
            if hasattr(self, 'processing_dialog'):
                self.processing_dialog.complete(False, f"处理失败: {e}")

    def _on_processing_worker_complete(self, success: bool, message: str):
        """后台处理完成回调"""
        logger.info(f"后台处理完成: success={success}, message={message}")

        if success:
            # 更新状态栏
            self.statusBar().showMessage(
                f"监控已停止 (会话ID: {self.current_session_id}, 样本数: {self.monitoring_duration})",
                5000
            )
            # 完成对话框
            if hasattr(self, 'processing_dialog'):
                self.processing_dialog.complete(True, message)
        else:
            self.statusBar().showMessage("监控已停止（处理失败）", 3000)
            if hasattr(self, 'processing_dialog'):
                self.processing_dialog.complete(False, message)

        # 断开处理工作线程的信号连接（防止内存泄漏）
        self._disconnect_processing_signals()

        self._update_monitoring_ui_state()

    def _disconnect_processing_signals(self):
        """断开处理工作线程的所有信号连接"""
        if hasattr(self, 'processing_worker') and self.processing_worker:
            try:
                self.processing_worker.progress_updated.disconnect()
                self.processing_worker.finished.disconnect()
                logger.debug("处理工作线程信号连接已断开")
            except Exception as e:
                logger.warning(f"断开信号连接失败: {e}")

    def _update_monitoring_ui_state(self):
        """更新监控UI状态"""
        if self.is_monitoring:
            # 监控中
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.stop_action.setEnabled(True)
            self.status_label.setText("监控中")
            self.status_label.setStyleSheet("color: #22c55e;")
            # 同步更新设备选择面板状态
            self.device_panel._set_monitoring_state(True)
        else:
            # 未监控
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.stop_action.setEnabled(False)
            self.status_label.setText("就绪")
            self.status_label.setStyleSheet("color: #94a3b8;")
            # 同步更新设备选择面板状态
            self.device_panel._set_monitoring_state(False)

    # ==================== 数据更新 ====================

    def _on_update_timer(self):
        """
        更新定时器（异步采集数据 - 性能优化）

        改进（P1 - Task 13）：
        - 处理待处理的 UI 更新（由于节流而延迟的更新）
        - 如果有待处理的更新，且已满足时间间隔，则立即更新 UI
        """
        # 处理待处理的 UI 更新（节流补偿机制）
        if self._pending_ui_update:
            import time
            current_time = time.time()
            time_since_last_update = current_time - self._last_ui_update_time

            # 如果满足最小间隔条件，执行待处理的更新
            if time_since_last_update >= self.MIN_UI_UPDATE_INTERVAL:
                # 注意：由于我们已经丢失了最新的 metrics 数据，
                # 这里只能清除标志。下一次采集会自动更新 UI
                self._pending_ui_update = False
                logger.debug("[UI节流] 执行待处理的UI更新补偿")

        if not self.is_monitoring:
            return

        # 验证必要条件
        if not self.current_device_id or not self.current_package_name or not self.current_session_id:
            logger.error("数据采集失败: 缺少必要的设备、应用或会话信息")
            return

        # 采集锁：如果上一次采集还在进行中，跳过本次
        # 这样可以避免任务堆积，保证 UI 流畅
        if self._is_collecting:
            logger.debug("上一次采集未完成，跳过本次采集")
            return

        try:
            # 获取设备信息
            device = self.device_manager.get_device(self.current_device_id)
            if not device:
                logger.error(f"设备不存在: {self.current_device_id}")
                return

            # 复用或创建设备适配器（缓存机制）
            if (self._cached_adapter is None or
                self._cached_device_id != self.current_device_id):

                logger.debug(f"创建新的设备适配器: {self.current_device_id}")
                from desktop.core.device_adapters import DeviceAdapterFactory

                self._cached_adapter = DeviceAdapterFactory.create_adapter(
                    self.current_device_id,
                    device.platform
                )
                self._cached_device_id = self.current_device_id

            adapter = self._cached_adapter

            # 防御性检查：确保适配器创建成功
            if not adapter:
                logger.error(f"无法创建设备适配器: {self.current_device_id}, 平台: {device.platform}")
                self.statusBar().showMessage(f"设备适配器创建失败: {self.current_device_id}", 3000)
                return

            # 检查设备连接状态
            if not adapter.is_connected():
                logger.warning(f"设备未连接: {self.current_device_id}")
                if not adapter.connect():
                    logger.error(f"设备连接失败: {self.current_device_id}")
                    self.statusBar().showMessage(f"设备连接失败: {self.current_device_id}", 3000)
                    return

            # 启动异步采集（性能优化：后台线程采集，主线程不阻塞）
            self._start_async_collection(adapter)

        except Exception as e:
            logger.error(f"启动采集失败: {e}", exc_info=True)
            self._is_collecting = False

    def _start_async_collection(self, adapter):
        """启动异步采集线程 - 修复版（方案3：使用信号跟踪系统 + 线程安全）"""
        if self.debug_mode:
            logger.debug("[崩溃追踪] _start_async_collection 开始执行")

        # 安全检查：确保旧线程已清理
        if self._collection_thread is not None:
            if self._collection_thread.isRunning():
                logger.error("[线程安全] 检测到旧线程仍在运行，强制跳过本次采集")
                self._is_collecting = False
                return

            if self.debug_mode:
                logger.debug("[线程安全] 清理旧线程对象")

            self._collection_thread = None
            self._collection_worker = None

        # 标记采集开始
        self._is_collecting = True

        # 创建采集线程和工作对象
        self._collection_thread = QThread()
        self._collection_worker = MetricsCollectionWorker(adapter, self.current_package_name)

        # 将工作对象移动到线程
        self._collection_worker.moveToThread(self._collection_thread)

        if self.debug_mode:
            logger.debug("[线程安全] QThread 和 Worker 已创建")

        # ============ 方案3：使用信号跟踪系统连接信号 ============
        # 1. 线程启动时执行采集
        self._connect_signal(self._collection_thread.started, self._collection_worker.collect_metrics)

        # 2. 采集完成时处理结果
        self._connect_signal(self._collection_worker.collection_finished, self._on_collection_completed)

        # 3. 采集失败时处理错误
        self._connect_signal(self._collection_worker.collection_failed, self._on_collection_failed)

        # 4. 线程结束时清理资源
        self._connect_signal(self._collection_thread.finished, self._on_collection_thread_finished)

        if self.debug_mode:
            logger.debug("[线程安全] 信号连接已完成")

        # 启动线程
        self._collection_thread.start()

        if self.debug_mode:
            logger.debug(f"[线程安全] 线程已启动: thread_id={id(self._collection_thread)}")

    def _on_collection_completed(self, raw_metrics: dict):
        """异步采集完成回调（在主线程执行）- 增强版（崩溃追踪）"""
        if self.debug_mode:
            logger.debug("[崩溃追踪] _on_collection_completed 开始执行")

        try:
            # 使用指标处理器处理数据
            if self.metrics_processor and raw_metrics:
                if self.debug_mode:
                    logger.debug("[崩溃追踪] 开始处理原始指标数据")

                processed = self.metrics_processor.process_raw_data(raw_metrics)
                if self.debug_mode:
                    logger.debug(f"[崩溃追踪] 指标处理完成: fps={processed.fps.fps if processed and processed.fps else 0}")

                if processed:
                    # 检查 UI 更新频率限制
                    import time
                    current_time = time.time()
                    time_since_last_update = current_time - self._last_ui_update_time
                    if self.debug_mode:
                        logger.debug(f"[崩溃追踪] 距上次UI更新: {time_since_last_update:.2f}s")

                    # 只有当距离上次更新超过最小间隔时才更新 UI
                    should_update_ui = (time_since_last_update >= self.MIN_UI_UPDATE_INTERVAL)
                    if self.debug_mode:
                        logger.debug(f"[崩溃追踪] UI更新判断: time_since={time_since_last_update:.2f}s, MIN_INTERVAL={self.MIN_UI_UPDATE_INTERVAL:.3f}s, should_update={should_update_ui}")
                        logger.debug(f"[崩溃追踪] _last_ui_update_time={self._last_ui_update_time}, current_time={current_time}")

                    if should_update_ui:
                        # 更新监控面板UI
                        if self.debug_mode:
                            logger.debug("[崩溃追踪] 开始更新监控面板")
                        self._update_monitor_panel(processed)
                        if self.debug_mode:
                            logger.debug("[崩溃追踪] 监控面板更新完成")

                        self._last_ui_update_time = current_time
                        self._pending_ui_update = False
                    else:
                        # 标记有待处理的更新（在下次定时器时处理）
                        self._pending_ui_update = True
                        if self.debug_mode:
                            logger.debug("[崩溃追踪] 标记待处理的UI更新")

                    # 异步保存到数据库（不阻塞 UI）
                    if self.debug_mode:
                        logger.debug("[崩溃追踪] 开始异步保存数据库")
                    self._save_metrics_to_db_async(processed)
                    if self.debug_mode:
                        logger.debug("[崩溃追踪] 数据库保存任务已提交")

                    # 执行异常检测（轻量级操作）
                    if self.anomaly_detector:
                        if self.debug_mode:
                            logger.debug("[崩溃追踪] 开始异常检测")
                        alerts = self.anomaly_detector.detect_all(processed)
                        if alerts:
                            if self.debug_mode:
                                logger.debug(f"[崩溃追踪] 检测到 {len(alerts)} 个告警")
                            self._handle_alerts(alerts)
                            if self.debug_mode:
                                logger.debug("[崩溃追踪] 告警处理完成")
                        else:
                            if self.debug_mode:
                                logger.debug("[崩溃追踪] 无告警")

                    # 更新样本计数
                    if self.debug_mode:
                        logger.debug("[崩溃追踪] 更新样本计数")
                    self.monitoring_duration += 1
                    self.samples_status_label.setText(f"样本数: {self.monitoring_duration}")
                    if self.debug_mode:
                        logger.debug(f"[崩溃追踪] 样本计数已更新: {self.monitoring_duration}")

            if self.debug_mode:
                logger.debug("[崩溃追踪] _on_collection_completed 即将完成")

        except Exception as e:
            logger.critical(f"[崩溃追踪] 处理采集结果时发生异常: {e}", exc_info=True)
            logger.critical(f"[崩溃追踪] 异常类型: {type(e).__name__}")
            import traceback
            logger.critical(f"[崩溃追踪] 完整堆栈:\n{traceback.format_exc()}")
        finally:
            # 采集完成，释放锁
            if self.debug_mode:
                logger.debug("[崩溃追踪] 释放采集锁")
            self._is_collecting = False
            if self.debug_mode:
                logger.debug("[崩溃追踪] _on_collection_completed 完成")

    def _on_collection_failed(self, error_msg: str):
        """异步采集失败回调"""
        logger.error(f"异步采集失败: {error_msg}")
        self._is_collecting = False

    def _on_collection_thread_finished(self):
        """采集线程结束清理 - 增强版（崩溃追踪）"""
        if self.debug_mode:
            logger.debug("[崩溃追踪] _on_collection_thread_finished 开始执行")

        # 释放采集锁（关键修复：确保无论线程如何退出都能释放锁）
        self._is_collecting = False
        if self.debug_mode:
            logger.debug("[崩溃追踪] 采集锁已释放")

        # 清理线程对象
        if self._collection_thread:
            if self.debug_mode:
                logger.debug("[崩溃追踪] 准备删除 collection_thread")

            # 安全等待线程完全结束
            if self._collection_thread.isRunning():
                if self.debug_mode:
                    logger.debug("[崩溃追踪] 线程仍在运行，等待结束...")
                # 不使用 wait()，因为它会阻塞事件循环
                # deleteLater() 会在下一个事件循环周期安全删除对象
                pass

            self._collection_thread.deleteLater()
            if self.debug_mode:
                logger.debug("[崩溃追踪] deleteLater() 已调用")

            self._collection_thread = None
            if self.debug_mode:
                logger.debug("[崩溃追踪] collection_thread 已设置为 None")

        self._collection_worker = None
        if self.debug_mode:
            logger.debug("[崩溃追踪] collection_worker 已设置为 None")
            logger.debug("[崩溃追踪] _on_collection_thread_finished 完成")

    def _collect_device_metrics(self, adapter, package_name: str) -> dict:
        """
        使用设备适配器采集真实性能指标

        Args:
            adapter: 设备适配器实例
            package_name: 应用包名

        Returns:
            dict: 原始指标数据字典
        """
        raw_metrics = {
            'fps': {},
            'memory': {},
            'cpu': {},
            'network': {},
            'battery': {},  # 添加电池数据
            'app_status': {}  # 添加应用状态信息
        }

        # 检测应用是否仍在运行
        try:
            apps = self.device_manager.get_device_apps(self.current_device_id, force_refresh=False)
            target_app = None
            for app in apps:
                if app.package_name == package_name:
                    target_app = app
                    break

            if not target_app or not target_app.is_running:
                # 添加二次确认：通过PID检查应用是否真的停止了
                if self._verify_app_still_running(package_name):
                    # 二次确认成功，应用仍在运行，状态检查可能有误
                    logger.warning(f"应用状态检查失败，但PID确认应用仍在运行: {package_name}")
                    raw_metrics['app_status']['is_alive'] = True
                    raw_metrics['app_status']['status'] = 'unknown'
                    raw_metrics['app_status']['warning'] = 'status_check_failed'
                else:
                    # 确认应用已停止
                    logger.error(f"应用已停止运行: {package_name}")
                    raw_metrics['app_status']['is_alive'] = False
                    raw_metrics['app_status']['reason'] = 'app_not_running'
                    # 触发应用停止处理
                    self._handle_app_stopped()
                    return raw_metrics
            else:
                raw_metrics['app_status']['is_alive'] = True
                raw_metrics['app_status']['status'] = target_app.status.value

                # 检测应用状态变化（前台/后台切换）
                if hasattr(self, '_last_app_status'):
                    if self._last_app_status != target_app.status:
                        logger.info(f"应用状态变化: {self._last_app_status} → {target_app.status}")
                        raw_metrics['app_status']['status_changed'] = True
                        raw_metrics['app_status']['previous_status'] = self._last_app_status.value
                self._last_app_status = target_app.status

        except Exception as e:
            logger.warning(f"检查应用状态失败: {e}")
            raw_metrics['app_status']['is_alive'] = True  # 假设仍在运行

        try:
            # 采集FPS数据
            fps_data = adapter.collect_fps(package_name)
            if fps_data:
                raw_metrics['fps'] = fps_data
                logger.debug(f"FPS采集成功: {fps_data.get('fps', 0)}")
            else:
                logger.debug("FPS数据为空，可能是应用在后台")

        except Exception as e:
            logger.warning(f"FPS采集失败: {e}")
            raw_metrics['fps']['error'] = str(e)

        try:
            # 采集内存数据
            memory_data = adapter.collect_memory(package_name)
            if memory_data:
                raw_metrics['memory'] = memory_data
                logger.debug(f"内存采集成功: {memory_data.get('totalPass', 0)} MB")
            else:
                logger.debug("内存数据为空")

        except Exception as e:
            logger.warning(f"内存采集失败: {e}")
            raw_metrics['memory']['error'] = str(e)

        try:
            # 采集CPU数据
            cpu_data = adapter.collect_cpu(package_name)
            if cpu_data:
                raw_metrics['cpu'] = cpu_data
                logger.debug(f"CPU采集成功: {cpu_data.get('appCpuRate', 0)}%")
            else:
                logger.debug("CPU数据为空")

        except Exception as e:
            # 特别处理 iOS 进程不存在错误
            from insight_eyes.public.ios.exceptions import ProcessNotFoundError
            if isinstance(e, ProcessNotFoundError):
                logger.error(f"iOS 应用进程不存在: {package_name}")
                raw_metrics['cpu']['error'] = 'process_not_found'
                raw_metrics['app_status']['is_alive'] = False
                raw_metrics['app_status']['reason'] = 'process_not_found'
                # 触发应用停止处理
                self._handle_app_stopped()
                return raw_metrics
            else:
                logger.warning(f"CPU采集失败: {e}")
                raw_metrics['cpu']['error'] = str(e)

        try:
            # 采集网络数据
            network_data = adapter.collect_network(package_name)
            if network_data:
                raw_metrics['network'] = network_data
                logger.debug(f"网络采集成功: 上行{network_data.get('upFlow', 0)} KB/s")
            else:
                logger.debug("网络数据为空")

        except Exception as e:
            logger.warning(f"网络采集失败: {e}")
            raw_metrics['network']['error'] = str(e)

        try:
            # 采集电池数据
            battery_data = adapter.collect_battery()
            if battery_data:
                raw_metrics['battery'] = battery_data
                level = battery_data.get('level', 0)
                temperature = battery_data.get('temperature', 0)
                logger.debug(f"电池采集成功: level={level}%, temp={temperature}°C, data={battery_data}")
            else:
                logger.debug(f"电池采集返回空数据: battery_data={battery_data}")

        except Exception as e:
            logger.warning(f"电池采集失败: {e}")
            raw_metrics['battery']['error'] = str(e)

        return raw_metrics

    def _verify_app_still_running(self, package_name: str) -> bool:
        """
        二次确认应用是否仍在运行（通过PID检查）

        Args:
            package_name: 应用包名

        Returns:
            bool: True表示应用仍在运行，False表示已停止
        """
        try:
            # 使用pidof命令检查进程是否存在
            from insight_eyes.public.adb import adb

            result = adb.shell(f'pidof {package_name}', self.current_device_id)
            if result and result.strip():
                # PID存在，应用仍在运行
                return True

            # 备选方法：使用ps命令检查
            result = adb.shell(f'ps | grep {package_name}', self.current_device_id)
            if result and package_name in result:
                return True

            # 确认应用已停止
            return False

        except Exception as e:
            logger.debug(f"二次确认应用状态失败: {e}")
            # 检查失败时保守处理，假设应用仍在运行
            return True

    def _handle_app_stopped(self):
        """处理应用停止运行的情况"""
        logger.warning(f"检测到应用已停止: {self.current_package_name}")

        # 保存当前会话数据
        if self.current_session_id:
            try:
                self.database.end_session(self.current_session_id)
                logger.info(f"会话已保存: {self.current_session_id}")
            except Exception as e:
                logger.error(f"保存会话失败: {e}")

        # 停止监控
        self.stop_monitoring()

        # 提示用户
        QMessageBox.warning(
            self,
            "应用已停止",
            f"应用 {self.current_package_name} 已停止运行\n\n"
            f"监控已自动停止，数据已保存。"
        )

        # 采集电池数据（可选，不需要包名）
        try:
            battery_data = adapter.collect_battery()
            if battery_data:
                raw_metrics['battery'] = battery_data
                logger.debug(f"电池采集成功: {battery_data.get('level', 0)}%")
        except Exception as e:
            logger.debug(f"电池采集失败: {e}")

        return raw_metrics

    def _update_monitor_panel(self, processed_metrics):
        """
        更新监控面板显示

        Args:
            processed_metrics: 处理后的指标对象
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

                # 更新设备面板的电池信息
                if processed_metrics.battery and hasattr(self.device_panel, 'update_battery_info'):
                    battery = processed_metrics.battery
                    level = getattr(battery, 'level', 0)
                    temperature = getattr(battery, 'temperature', 0.0)
                    capacity = getattr(battery, 'capacity', None)
                    logger.debug(f"更新电池信息: level={level}, temp={temperature}, capacity={capacity}")
                    self.device_panel.update_battery_info(level, temperature, capacity)
                else:
                    logger.debug(f"电池数据为空或设备面板不支持: battery={processed_metrics.battery}, has_method={hasattr(self.device_panel, 'update_battery_info')}")
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
        """
        保存指标数据到数据库

        Args:
            processed_metrics: 处理后的指标对象
        """
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
                # 添加电池数据
                'battery_level': processed_metrics.battery.level if processed_metrics.battery else None,
                'battery_temp': processed_metrics.battery.temperature if processed_metrics.battery else None,
            }

            # 保存到数据库
            metric_id = self.database.save_metrics(self.current_session_id, metrics_dict)

            # 每10次保存显示确认反馈（避免日志过多）
            if metric_id > 0 and self.monitoring_duration % 10 == 0:
                saved_count = len(self.database.get_metrics(self.current_session_id))
                logger.debug(f"数据已保存: 会话{self.current_session_id}, 共{saved_count}条")
                self.samples_status_label.setText(f"样本数: {saved_count}")

            # 检查并处理告警
            if processed_metrics.alerts:
                for alert in processed_metrics.alerts:
                    self.database.save_alert(self.current_session_id, {
                        'alert_type': alert.alert_type.value,
                        'metric_name': alert.metric_name,
                        'current_value': alert.current_value,
                        'threshold_value': alert.threshold,
                        'severity': alert.severity.value,
                        'description': alert.message
                    })

        except Exception as e:
            logger.error(f"保存数据到数据库失败: {e}", exc_info=True)
            # 在状态栏显示错误提示，让用户感知到保存失败
            self.statusBar().showMessage(f"数据保存失败: {str(e)[:30]}", 5000)

    def _save_metrics_to_db_async(self, processed_metrics):
        """
        异步保存指标数据到数据库（不阻塞 UI 线程）

        改进（P1 - Task 14）：
        - 使用 QThreadPool 将数据库操作移到后台线程
        - 避免 UI 冻结
        - 每 10 次保存更新样本计数显示

        Args:
            processed_metrics: 处理后的指标对象
        """
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
                # 添加电池数据
                'battery_level': processed_metrics.battery.level if processed_metrics.battery else None,
                'battery_temp': processed_metrics.battery.temperature if processed_metrics.battery else None,
            }

            # 创建数据库保存任务（指标数据）
            save_task = DatabaseSaveRunnable(
                self.database,
                self.current_session_id,
                metrics_dict,
                data_type='metrics'
            )

            # ============ 方案3：使用专用线程池 + 任务跟踪 ============
            # 保存任务引用（用于清理时等待）
            with self._active_db_tasks_lock:
                self._active_db_tasks.append(save_task)

            # 使用专用线程池执行（而非全局线程池）
            self._db_thread_pool.start(save_task)

            # 每10次保存更新样本计数显示（主线程操作，轻量级）
            if self.monitoring_duration % 10 == 0:
                # 注意：这里不能直接查询数据库（会阻塞），
                # 改用计数器作为近似值
                self.samples_status_label.setText(f"样本数: {self.monitoring_duration}")

            # 异步保存告警（如果有）
            if processed_metrics.alerts:
                for alert in processed_metrics.alerts:
                    alert_dict = {
                        'alert_type': alert.alert_type.value,
                        'metric_name': alert.metric_name,
                        'current_value': alert.current_value,
                        'threshold_value': alert.threshold,
                        'severity': alert.severity.value,
                        'description': alert.message
                    }
                    # 将告警保存也放到后台线程
                    alert_task = DatabaseSaveRunnable(
                        self.database,
                        self.current_session_id,
                        alert_dict,
                        data_type='alert'
                    )
                    # 使用专用线程池 + 任务跟踪
                    with self._active_db_tasks_lock:
                        self._active_db_tasks.append(alert_task)
                    self._db_thread_pool.start(alert_task)

        except Exception as e:
            logger.error(f"异步保存数据失败: {e}", exc_info=True)

    def _handle_alerts(self, alerts):
        """
        处理异常告警

        Args:
            alerts: 告警列表（Alert 对象来自 analytics/models.py）
        """
        try:
            from ..ui.utils.models import AlertRecord, AlertLevel

            for alert in alerts:
                # 保存告警到数据库
                self.database.save_alert(self.current_session_id, {
                    'alert_type': alert.alert_type.value,
                    'metric_name': alert.metric_name,
                    'current_value': alert.current_value,
                    'threshold_value': alert.threshold,
                    'severity': alert.severity.value,
                    'description': alert.message
                })

                # 转换 Alert (analytics/models.py) 为 AlertRecord (ui/utils/models.py)
                # 映射 severity 到 level
                severity_to_level = {
                    'info': AlertLevel.INFO,
                    'warning': AlertLevel.WARNING,
                    'critical': AlertLevel.CRITICAL
                }

                alert_record = AlertRecord(
                    timestamp=alert.timestamp,
                    level=severity_to_level.get(alert.severity.value, AlertLevel.INFO),
                    device_id=alert.device_id,
                    package_name=alert.app_id,
                    metric_type=alert.metric_name,
                    message=alert.message,
                    current_value=alert.current_value,
                    threshold=alert.threshold
                )

                # 更新配置面板的告警显示
                self.config_panel.add_alert(alert_record)

                # 如果是严重告警，在状态栏显示
                if alert.severity.value == 'critical':
                    self.statusBar().showMessage(
                        f"严重告警: {alert.metric_name} - {alert.message}",
                        5000
                    )

                # 使用关联分析器分析告警
                if self.correlation_analyzer and alert.severity.value in ['warning', 'critical']:
                    try:
                        context = self.correlation_analyzer.analyze_alert_context(alert)
                        if context:
                            logger.info(f"告警关联分析: {alert.metric_name} - {context}")
                    except Exception as e:
                        logger.warning(f"告警关联分析失败: {e}")

        except Exception as e:
            logger.error(f"处理告警失败: {e}", exc_info=True)

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

    # ==================== 设备和应用事件 ====================

    def _refresh_devices(self):
        """刷新设备列表 - 按需扫描，不使用持续监听"""
        logger.info("开始刷新设备列表")
        self.statusBar().showMessage("正在扫描设备...", 2000)

        # 清空现有列表
        self.device_panel.clear()

        # 停止 DeviceManager 的自动扫描器，避免重复触发信号
        was_scanning = self.device_manager._scanner_thread is not None
        if was_scanning:
            self.device_manager.stop_scan()

        try:
            # 使用 DeviceManager 扫描设备（支持 Android 和 iOS）
            from insight_eyes.desktop.core.models import Platform, DeviceStatus
            from insight_eyes.public.common import Devices

            # 扫描 Android 设备
            android_devices_info = []
            try:
                devices_detector = Devices()
                device_list = devices_detector.getDevices()
                logger.info(f"Android 扫描结果: {device_list}")

                for device_str in device_list:
                    if device_str.startswith("Android "):
                        device_id = device_str[8:].strip()
                        from insight_eyes.desktop.core.device_adapters import AndroidDeviceAdapter

                        adapter = AndroidDeviceAdapter(device_id)
                        if adapter.connect():
                            device_info = adapter.get_device_info()
                            if device_info:
                                device_info.status = DeviceStatus.CONNECTED
                                android_devices_info.append(device_info)

            except Exception as e:
                logger.error(f"扫描 Android 设备失败: {e}")

            # 扫描 iOS 设备
            ios_devices_info = []
            try:
                from pymobiledevice3.usbmux import list_devices
                ios_devices = list_devices()
                logger.info(f"iOS 扫描结果: {len(ios_devices)} 个设备")

                for ios_device in ios_devices:
                    udid = ios_device.serial
                    from insight_eyes.desktop.core.ios_device_adapter import IOSDeviceAdapter

                    adapter = IOSDeviceAdapter(udid)
                    if adapter.connect():
                        device_info = adapter.get_device_info()
                        if device_info:
                            device_info.status = DeviceStatus.CONNECTED
                            ios_devices_info.append(device_info)

            except Exception as e:
                logger.error(f"扫描 iOS 设备失败: {e}")

            # 合并设备列表
            devices_info = android_devices_info + ios_devices_info

            # 去重：使用 device_id 作为唯一标识符
            unique_devices = {}
            for device in devices_info:
                if device.device_id not in unique_devices:
                    unique_devices[device.device_id] = device
                else:
                    logger.debug(f"跳过重复设备: {device.device_id}")

            devices_info = list(unique_devices.values())
            logger.info(f"总共扫描到 {len(android_devices_info + ios_devices_info)} 个设备（去重后 {len(devices_info)} 个）")

            # 如果没有设备，提示用户
            if not devices_info:
                logger.warning("未获取到任何设备，请检查:")
                logger.warning("  1. 设备是否通过USB连接")
                logger.warning("  2. 设备是否开启开发者模式")
                logger.warning("  3. 是否允许USB调试")
                self.statusBar().showMessage("未检测到设备，请检查USB连接和调试设置", 5000)
                return

            # 预加载应用列表到 DeviceManager
            for device_info in devices_info:
                try:
                    logger.info(f"正在处理设备: {device_info.device_id} ({device_info.platform.value})")

                    # 先将设备添加到 DeviceManager（因为 get_device_apps 需要设备已存在）
                    self.device_manager._on_device_discovered(device_info)

                    # 预加载应用列表
                    apps = self.device_manager.get_device_apps(device_info.device_id, force_refresh=True)
                    logger.info(f"设备 {device_info.device_id} 上有 {len(apps)} 个应用")

                except Exception as e:
                    logger.error(f"处理设备 {device_info.device_id} 时出错: {e}", exc_info=True)

            # 设置设备列表到面板
            self.device_panel.set_devices(devices_info)

            device_count = len(devices_info)
            self.statusBar().showMessage(f"已刷新: {device_count} 个设备", 3000)
            logger.info(f"刷新完成: {device_count} 个设备")

            # 恢复 DeviceManager 的自动扫描器
            if was_scanning:
                self.device_manager.start_scan()

        except Exception as e:
            logger.error(f"刷新设备列表时出错: {e}", exc_info=True)
            self.statusBar().showMessage(f"刷新设备列表失败: {e}", 5000)

    def _on_target_selected(self, device_id: str, package_name: str):
        """监控目标已选择"""
        logger.info(f"收到 target_selected 信号: device_id={device_id}, package_name={package_name}")

        self.current_device_id = device_id
        self.current_package_name = package_name

        # 获取应用信息并更新监控面板
        device = self.device_manager.get_device(device_id)
        if device:
            app = device.find_app_by_package(package_name)
            if app:
                self.monitor_panel.set_monitoring_target(device_id, package_name, app.app_name)
                logger.info(f"监控目标已设置: {device.name} - {app.app_name}")
                self.statusBar().showMessage(f"目标: {device.name} - {app.app_name}", 3000)
            else:
                logger.warning(f"未找到应用: {package_name}")
        else:
            logger.warning(f"未找到设备: {device_id}")

    def _on_config_changed(self, config: dict):
        """配置变更 - DEBUG 模式增强日志（避免使用 ConfigManager）"""
        try:
            import sys
            import traceback
            from logzero import logger

            logger.info("[MAIN-DEBUG-1] >>> _on_config_changed 开始执行")
            logger.info(f"[MAIN-DEBUG-2] 收到配置: {config}")
            logger.info(f"[MAIN-DEBUG-3] 调用栈:\n{''.join(traceback.format_stack()[-5:])}")

            # 刷新监控面板卡片（根据新配置重建布局）
            logger.info("[MAIN-DEBUG-4] 检查 monitor_panel 是否有 refresh_cards 方法...")
            if hasattr(self.monitor_panel, 'refresh_cards'):
                logger.info(f"[MAIN-DEBUG-5] monitor_panel.refresh_cards 存在: {self.monitor_panel.refresh_cards}")
                logger.info(f"[MAIN-DEBUG-6] monitor_panel 类型: {type(self.monitor_panel)}")

                # 【关键修改】直接传递配置字典给 refresh_cards，避免使用 ConfigManager
                logger.info("[MAIN-DEBUG-7] 准备直接调用 refresh_cards 并传递配置字典...")

                # 强制刷新日志
                sys.stdout.flush()
                sys.stderr.flush()

                logger.info(f"[MAIN-DEBUG-8] *** 即将调用 refresh_cards({config}) ***")
                # 直接调用，不使用 QTimer（简化调用链）
                self.monitor_panel.refresh_cards(config)
                logger.info("[MAIN-DEBUG-9] *** refresh_cards 调用成功 ***")

                sys.stdout.flush()
                sys.stderr.flush()

            else:
                logger.warning("[MAIN-DEBUG-WARNING] monitor_panel 没有 refresh_cards 方法")

            # 更新定时器间隔
            logger.info("[MAIN-DEBUG-10] 检查是否需要更新定时器...")
            if self.is_monitoring:
                interval_ms = config.get("interval_ms", 1000)
                logger.info(f"[MAIN-DEBUG-11] 正在监控中，更新定时器间隔: {interval_ms}ms")
                self.update_timer.setInterval(interval_ms)
                self.statusBar().showMessage(f"配置已更新，采样间隔: {interval_ms}ms", 3000)
            else:
                logger.info("[MAIN-DEBUG-12] 未在监控中，仅显示配置已更新消息")
                self.statusBar().showMessage("配置已更新", 3000)

            logger.info("[MAIN-DEBUG-13] >>> _on_config_changed 执行成功")

        except Exception as e:
            from logzero import logger
            logger.error(f"[MAIN-DEBUG-EXCEPTION] _on_config_changed 异常: {e}")
            logger.error(f"[MAIN-DEBUG-EXCEPTION] 异常类型: {type(e).__name__}")
            logger.error(f"[MAIN-DEBUG-EXCEPTION] 堆栈:\n{''.join(traceback.format_exc())}")

    def _on_threshold_changed(self, thresholds: dict):
        """阈值变更"""
        self.statusBar().showMessage("告警阈值已更新", 3000)

    def _add_scenario_marker(self, scenario_name: str):
        """添加场景标记"""
        self.statusBar().showMessage(f"场景标记已添加: {scenario_name}", 3000)

    # ==================== 配置管理 ====================

    def _load_app_config(self):
        """加载应用程序配置"""
        config = self.config_manager.load_config()

        # 应用UI配置
        self._apply_ui_config(config.ui)

        # 应用采集配置到配置面板（如果面板已经创建）
        if hasattr(self, 'config_panel'):
            self.config_panel.set_config(config.collection)

        print(f"配置已加载: {config.config_version}")

    def _apply_ui_config(self, ui_config: UIConfig):
        """
        应用UI配置

        Args:
            ui_config: UI配置对象
        """
        # 设置窗口大小
        self.resize(ui_config.window_width, ui_config.window_height)

        if ui_config.window_maximized:
            self.showMaximized()

    def _save_ui_config(self):
        """保存当前UI配置"""
        config = self.config_manager.get_config()

        # 更新UI配置
        config.ui.window_width = self.width()
        config.ui.window_height = self.height()
        config.ui.window_maximized = self.isMaximized()

        # TODO: 保存splitter大小
        # config.ui.splitter_sizes = self.splitter.sizes()

        # 保存配置
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
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出配置",
            os.path.join(os.path.expanduser("~"), "insight-eye-config.json"),
            "JSON文件 (*.json)"
        )

        if file_path:
            if self.config_manager.export_config(file_path):
                QMessageBox.information(self, "成功", f"配置已导出到:\n{file_path}")
                self.statusBar().showMessage("配置已导出", 3000)
            else:
                QMessageBox.warning(self, "失败", "导出配置失败")

    def _import_config(self):
        """导入配置"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入配置",
            os.path.expanduser("~"),
            "JSON文件 (*.json)"
        )

        if file_path:
            reply = QMessageBox.question(
                self,
                "确认导入",
                "导入配置将覆盖当前配置，是否继续？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                if self.config_manager.import_config(file_path):
                    # 重新加载配置
                    self._load_app_config()
                    QMessageBox.information(self, "成功", "配置已导入，请重启应用以生效")
                    self.statusBar().showMessage("配置已导入", 3000)
                else:
                    QMessageBox.warning(self, "失败", "导入配置失败")

    def _reset_config(self):
        """重置配置"""
        reply = QMessageBox.question(
            self,
            "确认重置",
            "确定要重置为默认配置吗？此操作不可撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.config_manager.reset_to_default():
                # 重新加载配置
                self._load_app_config()
                QMessageBox.information(self, "成功", "配置已重置，请重启应用以生效")
                self.statusBar().showMessage("配置已重置", 3000)
            else:
                QMessageBox.warning(self, "失败", "重置配置失败")

    def _open_config_dir(self):
        """打开配置目录"""
        import subprocess
        import platform

        config_dir = self.config_manager.config_dir

        try:
            if platform.system() == "Windows":
                os.startfile(config_dir)
            elif platform.system() == "Darwin":  # macOS
                subprocess.call(["open", config_dir])
            else:  # Linux
                subprocess.call(["xdg-open", config_dir])
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开配置目录:\n{e}")

    # ==================== 方案3：信号槽连接管理系统 ====================

    def _connect_signal(self, signal, slot):
        """
        连接信号并保存引用（方案3：信号槽连接跟踪）

        Args:
            signal: PyQt6 信号对象
            slot: 槽函数

        Returns:
            连接对象（可用于 disconnect）
        """
        try:
            result = signal.connect(slot)
            # PyQt6: signal.connect() 返回 True 表示成功，False 表示失败
            # 只有在成功连接时才保存引用
            if result:
                # 保存连接引用（使用 slot 作为标识）
                self._signal_connections.append((signal, slot, result))
                return result
            else:
                logger.warning(f"信号连接失败: signal.connect() 返回 False")
                return None
        except Exception as e:
            logger.warning(f"信号连接失败: {e}")
            return None

    def _disconnect_all_signals(self):
        """
        断开所有信号连接（优化版：快速清理）

        在窗口关闭前调用，确保所有信号连接被正确断开
        优化：减少日志输出，提高关闭速度
        """
        # 直接清空信号连接列表，不再逐个断开
        # PyQt 会在对象销毁时自动清理信号连接
        connection_count = len(self._signal_connections)
        if connection_count > 0:
            logger.debug(f"[信号清理] 清空 {connection_count} 个信号连接（快速清理模式）")
        self._signal_connections.clear()
        logger.debug("[信号清理] 信号连接列表已清空")

    def _disconnect_collection_signals(self):
        """
        断开采集线程相关的信号（方案3：精确断开）

        只断开与采集线程相关的信号，不影响其他信号连接
        """
        # 查找并断开采集相关的信号连接
        connections_to_remove = []
        for signal, slot, conn in self._signal_connections:
            # 检查是否是采集相关的信号
            # 注意：需要检查 self._collection_worker 是否存在
            should_disconnect = False
            if self._collection_worker and slot == self._collection_worker.collect_metrics:
                should_disconnect = True
            elif slot == self._on_collection_completed:
                should_disconnect = True
            elif slot == self._on_collection_failed:
                should_disconnect = True
            elif slot == self._on_collection_thread_finished:
                should_disconnect = True

            if should_disconnect:
                try:
                    # 尝试使用 signal.disconnect(slot) 断开
                    # 如果失败（信号已断开或未连接），捕获异常并继续
                    signal.disconnect(slot)
                    connections_to_remove.append((signal, slot, conn))
                except TypeError as e:
                    # PyQt6 可能抛出 TypeError 当 signal 未连接时
                    logger.debug(f"断开信号时出错（信号可能未连接）: {e}")
                    # 仍然从列表中移除，因为连接已经无效
                    connections_to_remove.append((signal, slot, conn))
                except Exception as e:
                    logger.debug(f"断开信号时出错（可忽略）: {e}")
                    # 仍然从列表中移除
                    connections_to_remove.append((signal, slot, conn))

        # 从列表中移除已断开的连接
        for conn in connections_to_remove:
            self._signal_connections.remove(conn)

        logger.debug(f"采集相关信号连接已断开（{len(connections_to_remove)}个）")

    # ==================== 窗口事件 ====================

    def _show_monitoring_view(self):
        """切换到监控视图"""
        self.stacked_widget.setCurrentIndex(0)
        self.monitor_btn.setChecked(True)
        self.report_btn.setChecked(False)

    def _show_report_view(self):
        """切换到报告视图"""
        self.stacked_widget.setCurrentIndex(1)
        self.report_btn.setChecked(True)
        self.monitor_btn.setChecked(False)

        # 刷新报告列表
        self.report_panel.load_sessions()

    def _on_processing_complete(self, success: bool, message: str):
        """处理完成回调

        Args:
            success: 是否成功
            message: 完成消息
        """
        if success:
            logger.info(f"监控数据处理完成: {message}")
            # 刷新报告列表
            self.report_panel.load_sessions()
            # 切换到报告视图
            QTimer.singleShot(500, self._show_report_view)
        else:
            logger.error(f"监控数据处理失败: {message}")
            QMessageBox.warning(self, "处理失败", message)

    def closeEvent(self, event):
        """
        窗口关闭事件 - 修复版（同步停止监控，避免线程冲突）

        修复内容：
        1. 改为同步停止监控，确保监控线程完全停止后再清理资源
        2. 添加超时保护，避免永久阻塞
        3. 添加详细的调试日志
        """
        try:
            logger.info(f"[窗口关闭] closeEvent 被调用, is_monitoring={self.is_monitoring}")

            # 如果正在监控，提示用户确认
            if self.is_monitoring:
                reply = QMessageBox.question(
                    self, "确认退出",
                    "监控正在进行中，确定要退出吗？\n\n退出后将自动停止监控并保存数据。",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No  # 默认焦点在No上
                )
                if reply == QMessageBox.StandardButton.Yes:
                    logger.info("[窗口关闭] 用户确认退出，开始停止监控...")
                    # 关键修复：同步停止监控，不使用异步 QTimer
                    self._stop_monitoring_sync()
                else:
                    logger.info("[窗口关闭] 用户取消退出")
                    event.ignore()
                    return

            # 无论什么情况，都执行清理
            logger.info("[窗口关闭] 开始清理资源...")

            # 1. 保存配置（快速操作，不阻塞）
            try:
                self._save_ui_config()
                logger.info("[窗口关闭] 配置已保存")
            except Exception as e:
                logger.warning(f"保存配置失败: {e}")

            # 2. 断开信号连接（快速操作）
            try:
                self._disconnect_all_signals()
                logger.info("[窗口关闭] 信号连接已断开")
            except Exception as e:
                logger.warning(f"断开信号连接失败: {e}")

            # 2.5. 强制停止后台处理工作线程（崩溃恢复机制）
            try:
                if hasattr(self, 'processing_worker') and self.processing_worker:
                    if self.processing_worker.isRunning():
                        logger.warning("[窗口关闭] 检测到正在运行的处理工作线程，强制终止...")
                        self.processing_worker.terminate()
                        # 等待最多2秒让线程终止
                        if not self.processing_worker.wait(2000):
                            logger.error("[窗口关闭] 处理工作线程未能在2秒内终止")
                        else:
                            logger.info("[窗口关闭] 处理工作线程已强制终止")
            except Exception as e:
                logger.warning(f"[窗口关闭] 强制终止处理工作线程失败: {e}")

            # 3. 清理资源（有超时保护）
            try:
                self._cleanup_resources()
                logger.info("[窗口关闭] 资源清理完成")
            except Exception as e:
                logger.error(f"清理资源失败: {e}")
                # 即使清理失败，也允许退出，避免程序无法关闭

            # 4. 强制接受关闭事件，确保窗口能关闭
            logger.info("[窗口关闭] 接受关闭事件")
            event.accept()

        except Exception as e:
            logger.error(f"[窗口关闭] 关闭事件处理异常: {e}", exc_info=True)
            # 即使发生异常，也允许退出，避免程序无法关闭
            event.accept()

    def _stop_monitoring_sync(self):
        """
        同步停止监控（修复版）

        关键改进：
        1. 直接调用 _stop_monitoring()，不使用 QTimer
        2. 等待采集线程完全停止
        3. 有超时保护，最多等待 5 秒
        """
        import time
        logger.info("[同步停止] 开始同步停止监控")

        stop_start_time = time.time()
        timeout = 5.0  # 最多等待5秒

        try:
            # 调用停止监控
            self._stop_monitoring()

            # 等待采集线程停止
            if hasattr(self, '_collection_thread') and self._collection_thread:
                logger.info("[同步停止] 等待采集线程停止...")

                # 使用 isRunning() 检查，然后等待
                wait_interval = 0.1  # 每100ms检查一次
                while self._collection_thread.isRunning():
                    elapsed = time.time() - stop_start_time
                    if elapsed > timeout:
                        logger.warning(f"[同步停止] 等待超时（{timeout}秒），强制继续")
                        break

                    # 处理事件循环，避免 UI 冻结
                    QApplication.processEvents()
                    time.sleep(wait_interval)

                if not self._collection_thread.isRunning():
                    logger.info(f"[同步停止] 采集线程已停止（耗时 {time.time() - stop_start_time:.2f}秒）")

            logger.info("[同步停止] 监控已完全停止")

        except Exception as e:
            logger.error(f"[同步停止] 停止监控失败: {e}", exc_info=True)

    def _stop_monitoring_safe(self):
        """安全停止监控（带超时保护）"""
        try:
            # 设置标志，防止重复调用
            if hasattr(self, '_is_stopping') and self._is_stopping:
                logger.warning("[停止监控] 正在停止中，跳过重复调用")
                return
            self._is_stopping = True

            # 使用 QTimer 避免阻塞
            QTimer.singleShot(0, self._do_stop_monitoring)

        except Exception as e:
            logger.error(f"[停止监控] 安全停止失败: {e}", exc_info=True)

    def _do_stop_monitoring(self):
        """实际执行停止监控"""
        try:
            # 调用原始的停止方法
            self._stop_monitoring()
            self._is_stopping = False
        except Exception as e:
            logger.error(f"[停止监控] 停止监控失败: {e}", exc_info=True)
            self._is_stopping = False

    def _cleanup_resources_safe(self):
        """安全清理资源（带超时保护）"""
        import threading
        import time

        # 在子线程中执行清理，避免阻塞UI
        cleanup_done = threading.Event()
        cleanup_result = {'success': False}

        def cleanup_thread():
            try:
                self._cleanup_resources()
                cleanup_result['success'] = True
            except Exception as e:
                logger.error(f"[资源清理] 清理线程异常: {e}", exc_info=True)
                cleanup_result['success'] = False
            finally:
                cleanup_done.set()

        # 启动清理线程
        thread = threading.Thread(target=cleanup_thread, daemon=True)
        thread.start()

        # 等待清理完成，最多等待3秒
        if cleanup_done.wait(timeout=3.0):
            logger.info("[资源清理] 清理完成")
        else:
            logger.warning("[资源清理] 清理超时（3秒），强制退出")

    def _cleanup_resources(self):
        """清理资源 - 修复版（方案3：等待线程池任务完成 + 修复设备适配器清理）"""
        logger.info("[资源清理] _cleanup_resources 开始执行")

        try:
            # ============ 关键修复：无论监控状态如何，都清理设备适配器 ============
            # 这是修复 QThread: Destroyed while thread is still running 的关键
            logger.info(f"[资源清理] 检查设备适配器: _cached_adapter={self._cached_adapter is not None}")

            if self._cached_adapter:
                # 检查是否已经清理过（防止重复清理）
                has_apm = hasattr(self._cached_adapter, '_apm') and self._cached_adapter._apm is not None
                logger.info(f"[资源清理] 检查 APM 实例: has_apm={has_apm}")

                if has_apm:
                    try:
                        logger.info("清理设备适配器（防止 QThread 泄漏）")
                        # 停止 APM 实例（包括 FPS 监控线程）
                        self._cached_adapter._apm.stop()
                        # 清理适配器
                        self._cached_adapter.cleanup()
                        logger.info("设备适配器已清理")
                    except Exception as e:
                        logger.warning(f"清理设备适配器失败: {e}")
                    finally:
                        self._cached_adapter = None
                        self._cached_device_id = None
                else:
                    # 已经清理过，直接清空引用
                    logger.info("[资源清理] APM 已清理过，直接清空引用")
                    self._cached_adapter = None
                    self._cached_device_id = None
            else:
                logger.info("[资源清理] 无设备适配器需要清理")

            # ============ 方案3：清理数据库线程池 ============
            if self._db_thread_pool:
                # 取消未开始的任务
                self._db_thread_pool.clear()
                # 等待已运行的任务完成（最多 5 秒）
                self._db_thread_pool.waitForDone(5000)
                logger.info("数据库线程池已清理")

            # ============ 方案3：清理活跃任务列表 ============
            with self._active_db_tasks_lock:
                if self._active_db_tasks:
                    logger.info(f"清理活跃任务列表: {len(self._active_db_tasks)} 个任务")
                self._active_db_tasks.clear()

            # 不再需要停止扫描（已改为按需扫描）
            # 清理设备管理器
            if self.device_manager:
                self.device_manager.cleanup()
                logger.info("设备管理器资源已清理")

            # 清理数据库管理器
            if self.database:
                self.database.cleanup()
                logger.info("数据库资源已清理")

            # 清理线程池
            self._db_thread_pool = None

            logger.info("[资源清理] _cleanup_resources 执行完成")

        except Exception as e:
            logger.error(f"清理资源时出错: {e}")

    # ==================== 方案3：线程监控和诊断工具 ====================

    def diagnose_threads(self) -> dict:
        """
        诊断当前线程状态（方案3：线程监控工具）

        Returns:
            dict: 包含所有线程状态信息的字典
        """
        import threading

        diagnosis = {
            'timestamp': datetime.now().isoformat(),
            'python_threads': [],
            'qt_threads': {},
            'signal_connections': len(self._signal_connections),
            'db_thread_pool': {},
        }

        # 1. 检查 Python threading.Thread 状态
        main_thread = threading.main_thread()
        for thread in threading.enumerate():
            thread_info = {
                'name': thread.name,
                'is_alive': thread.is_alive(),
                'is_daemon': thread.daemon,
                'is_main': thread == main_thread,
            }
            diagnosis['python_threads'].append(thread_info)

        # 2. 检查 PyQt6 QThread 状态
        if self._collection_thread:
            diagnosis['qt_threads']['collection_thread'] = {
                'is_running': self._collection_thread.isRunning(),
                'is_finished': self._collection_thread.isFinished(),
            }

        if hasattr(self.device_manager, '_scanner_thread') and self.device_manager._scanner_thread:
            diagnosis['qt_threads']['scanner_thread'] = {
                'is_running': self.device_manager._scanner_thread.isRunning(),
                'is_finished': self.device_manager._scanner_thread.isFinished(),
            }

        # 3. 检查线程池状态
        if self._db_thread_pool:
            diagnosis['db_thread_pool'] = {
                'max_thread_count': self._db_thread_pool.maxThreadCount(),
                'active_thread_count': self._db_thread_pool.activeThreadCount(),
                'active_tasks': len(self._active_db_tasks),
            }

        # 4. 检查信号连接
        diagnosis['signal_connections'] = len(self._signal_connections)

        return diagnosis

    def print_thread_diagnosis(self):
        """
        打印线程诊断信息（方案3：线程监控工具）

        用于调试和监控线程状态
        """
        diagnosis = self.diagnose_threads()

        logger.info("========== 线程诊断报告 ==========")
        logger.info(f"诊断时间: {diagnosis['timestamp']}")

        # Python 线程
        logger.info(f"Python 线程数: {len(diagnosis['python_threads'])}")
        for thread_info in diagnosis['python_threads']:
            status = "运行中" if thread_info['is_alive'] else "已停止"
            daemon_str = "守护" if thread_info['is_daemon'] else "用户"
            main_str = " (主线程)" if thread_info['is_main'] else ""
            logger.info(f"  - {thread_info['name']}: {status}, {daemon_str}{main_str}")

        # Qt 线程
        logger.info("Qt 线程状态:")
        for name, info in diagnosis['qt_threads'].items():
            status = "运行中" if info['is_running'] else "已停止"
            logger.info(f"  - {name}: {status}")

        # 线程池
        logger.info("数据库线程池:")
        if diagnosis['db_thread_pool']:
            pool = diagnosis['db_thread_pool']
            logger.info(f"  - 最大线程数: {pool['max_thread_count']}")
            logger.info(f"  - 活跃线程数: {pool['active_thread_count']}")
            logger.info(f"  - 活跃任务数: {pool['active_tasks']}")

        # 信号连接
        logger.info(f"信号连接数: {diagnosis['signal_connections']}")

        logger.info("====================================")
