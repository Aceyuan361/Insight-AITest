# -*- coding: utf-8 -*-
"""
测试报告面板
展示监控会话列表和报告详情
"""
from typing import Optional, List, Dict
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QLabel, QPushButton, QLineEdit, QComboBox,
    QAbstractItemView, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor
from logzero import logger

from insight_eyes.desktop.data.database import DatabaseManager
from insight_eyes.desktop.data.session_manager import SessionManager
from insight_eyes.desktop.ui.widgets.session_report_widget import SessionReportWidget


class ReportPanel(QWidget):
    """测试报告面板

    左侧：会话列表表格
    右侧：报告详情区域
    """

    # 信号：选择会话
    session_selected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self.session_manager = SessionManager(self)  # 添加会话管理器
        self.current_session_id: Optional[int] = None
        self.sessions_data: List[Dict] = []

        self._init_ui()
        self._connect_signals()

        # 延迟加载数据
        QTimer.singleShot(100, self.load_sessions)

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 标题栏
        header_layout = QHBoxLayout()

        title_label = QLabel("测试报告")
        title_label.setProperty("class", "title")
        title_label.setStyleSheet("font-size: 18pt; font-weight: 600; color: #00d4ff;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # 筛选控件
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["全部设备", "Android"])
        self.filter_combo.setMinimumWidth(120)
        self.filter_combo.setStyleSheet("""
            QComboBox {
                background-color: #121824;
                color: #e0e6ed;
                border: 1px solid #1a1f2e;
                border-radius: 6px;
                padding: 6px 12px;
            }
        """)
        header_layout.addWidget(self.filter_combo)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索包名或应用名...")
        self.search_input.setMinimumWidth(200)
        header_layout.addWidget(self.search_input)

        refresh_btn = QPushButton("刷新")
        refresh_btn.setProperty("class", "primary")
        refresh_btn.setMinimumWidth(80)
        header_layout.addWidget(refresh_btn)

        # 批量删除按钮
        batch_delete_btn = QPushButton("批量删除")
        batch_delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
            QPushButton:pressed {
                background-color: #b91c1c;
            }
        """)
        batch_delete_btn.setMinimumWidth(80)
        batch_delete_btn.clicked.connect(self._on_batch_delete_clicked)
        header_layout.addWidget(batch_delete_btn)

        layout.addLayout(header_layout)

        # 主分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # 左侧：会话列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # 会话列表表格
        self.sessions_table = QTableWidget()
        self.sessions_table.setColumnCount(5)
        self.sessions_table.setHorizontalHeaderLabels(["时间", "设备", "应用", "时长", "状态"])

        # 设置表格样式
        self.sessions_table.setStyleSheet("""
            QTableWidget {
                background-color: #121824;
                border: 1px solid #1a1f2e;
                border-radius: 6px;
                gridline-color: #1a1f2e;
            }
            QTableWidget::item {
                padding: 8px;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: #00d4ff;
                color: #0a0e17;
            }
            QTableWidget::item:hover {
                background-color: #1a1f2e;
            }
            QHeaderView::section {
                background-color: #121824;
                color: #7dd3fc;
                border: none;
                border-bottom: 1px solid #1a1f2e;
                border-right: 1px solid #1a1f2e;
                padding: 8px;
                font-weight: 600;
            }
        """)

        # 设置列宽
        header = self.sessions_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        # 设置选择行为（支持多选）
        self.sessions_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.sessions_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.sessions_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.sessions_table.verticalHeader().setVisible(False)

        left_layout.addWidget(self.sessions_table)

        # 添加到分割器
        splitter.addWidget(left_widget)

        # 右侧：报告详情
        self.report_widget = SessionReportWidget()
        splitter.addWidget(self.report_widget)

        # 设置分割器比例（30:70）
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 7)
        splitter.setSizes([300, 700])

        layout.addWidget(splitter)

    def _connect_signals(self):
        """连接信号"""
        self.sessions_table.itemSelectionChanged.connect(self._on_selection_changed)
        self.filter_combo.currentTextChanged.connect(self._refresh_list)
        self.search_input.textChanged.connect(self._refresh_list)
        refresh_btn = self.findChild(QPushButton, "refresh_btn")
        if refresh_btn:
            refresh_btn.clicked.connect(self.load_sessions)

        # 连接报告组件的信号
        self.report_widget.export_requested.connect(self._on_export_requested)
        self.report_widget.delete_requested.connect(self._on_delete_requested)

        # 连接会话管理器的信号
        self.session_manager.session_deleted.connect(self._on_session_deleted)
        self.session_manager.sessions_deleted.connect(self._on_sessions_deleted)
        self.session_manager.delete_failed.connect(self._on_delete_failed)

    def load_sessions(self):
        """加载会话列表"""
        try:
            # 从数据库获取最近的会话
            self.sessions_data = self.db.get_recent_sessions(limit=100)

            logger.info(f"加载了 {len(self.sessions_data)} 个会话")

            # 刷新表格显示
            self._refresh_list()

        except Exception as e:
            logger.error(f"加载会话列表失败: {e}")
            QMessageBox.critical(self, "错误", f"加载会话列表失败: {e}")

    def _refresh_list(self):
        """刷新会话列表（应用筛选）"""
        try:
            # 获取筛选条件
            platform_filter = self.filter_combo.currentText()
            search_text = self.search_input.text().lower()

            # 过滤数据
            filtered_data = []
            for session in self.sessions_data:
                # 平台筛选
                if platform_filter == "Android":
                    # 需要从设备信息判断平台
                    device = self.db.get_device(session['device_id'])
                    if device and device['platform'] != 'android':
                        continue

                # 搜索筛选
                if search_text:
                    package_name = session['package_name'].lower()
                    if search_text not in package_name:
                        continue

                filtered_data.append(session)

            # 更新表格
            self.sessions_table.setRowCount(len(filtered_data))

            for row, session in enumerate(filtered_data):
                # 时间（数据库存储UTC时间，需要转换为本地时间）
                from datetime import timezone
                start_time_utc = datetime.fromisoformat(session['start_time'])
                start_time_utc = start_time_utc.replace(tzinfo=timezone.utc)
                start_time = start_time_utc.astimezone().replace(tzinfo=None)
                time_item = QTableWidgetItem(start_time.strftime("%Y-%m-%d %H:%M:%S"))
                time_item.setData(Qt.ItemDataRole.UserRole, session['id'])
                self.sessions_table.setItem(row, 0, time_item)

                # 设备
                device = self.db.get_device(session['device_id'])
                device_name = device['name'] if device else session['device_id']
                self.sessions_table.setItem(row, 1, QTableWidgetItem(device_name))

                # 应用
                self.sessions_table.setItem(row, 2, QTableWidgetItem(session['package_name']))

                # 时长
                if session['end_time']:
                    end_time_utc = datetime.fromisoformat(session['end_time'])
                    end_time_utc = end_time_utc.replace(tzinfo=timezone.utc)
                    end_time = end_time_utc.astimezone().replace(tzinfo=None)
                    duration = (end_time - start_time).total_seconds()
                    duration_str = f"{int(duration // 60)}:{int(duration % 60):02d}"
                else:
                    duration_str = "进行中"
                self.sessions_table.setItem(row, 3, QTableWidgetItem(duration_str))

                # 状态
                status_item = QTableWidgetItem("已完成" if session['end_time'] else "进行中")
                if session['end_time']:
                    status_item.setForeground(QColor("#22c55e"))
                else:
                    status_item.setForeground(QColor("#f59e0b"))
                self.sessions_table.setItem(row, 4, status_item)

        except Exception as e:
            logger.error(f"刷新会话列表失败: {e}")

    def _on_selection_changed(self):
        """选择改变事件"""
        try:
            selected_items = self.sessions_table.selectedItems()
            if not selected_items:
                return

            # 获取选中的会话ID
            row = selected_items[0].row()
            session_id_item = self.sessions_table.item(row, 0)
            if session_id_item:
                session_id = session_id_item.data(Qt.ItemDataRole.UserRole)
                self.current_session_id = session_id

                # 加载会话详情
                self.report_widget.load_session(session_id)

                # 发送信号
                self.session_selected.emit(session_id)

        except Exception as e:
            logger.error(f"处理选择事件失败: {e}")

    def refresh_current_session(self):
        """刷新当前会话的详情"""
        if self.current_session_id:
            self.report_widget.load_session(self.current_session_id)

    def get_current_session_id(self) -> Optional[int]:
        """获取当前选中的会话ID"""
        return self.current_session_id

    def _on_export_requested(self, session_id: int):
        """处理导出请求"""
        try:
            from PyQt6.QtWidgets import QFileDialog
            import os
            from pathlib import Path

            # 选择保存位置
            default_dir = os.path.expanduser("~/Documents/InsightEye")
            os.makedirs(default_dir, exist_ok=True)

            file_path, selected_filter = QFileDialog.getSaveFileName(
                self,
                "导出报告",
                os.path.join(default_dir, f"report_{session_id}.pdf"),
                "PDF 文件 (*.pdf);;CSV 文件 (*.csv)"
            )

            if file_path:
                if file_path.endswith('.pdf'):
                    # PDF 导出（包含图表）
                    from insight_eyes.desktop.data.exporter import DataExporter
                    exporter = DataExporter(self.db)

                    # 获取图表组件
                    chart_widgets = {}
                    if hasattr(self.report_widget, 'fps_chart_widget'):
                        chart_widgets['fps'] = self.report_widget.fps_chart_widget
                    if hasattr(self.report_widget, 'cpu_chart_widget'):
                        chart_widgets['cpu'] = self.report_widget.cpu_chart_widget
                    if hasattr(self.report_widget, 'memory_chart_widget'):
                        chart_widgets['memory'] = self.report_widget.memory_chart_widget
                    if hasattr(self.report_widget, 'network_chart_widget'):
                        chart_widgets['network'] = self.report_widget.network_chart_widget

                    success = exporter.export_to_pdf(session_id, file_path, include_charts=True, chart_widgets=chart_widgets)
                else:
                    # CSV 导出
                    from insight_eyes.desktop.data.exporter import DataExporter
                    exporter = DataExporter(self.db)
                    success = exporter.export_to_csv(session_id, file_path)

                if success:
                    QMessageBox.information(self, "成功", f"报告已导出到:\n{file_path}")
                    logger.info(f"报告导出成功: {file_path}")
                else:
                    QMessageBox.warning(self, "失败", "导出失败，请查看日志")

        except Exception as e:
            logger.error(f"导出报告失败: {e}")
            QMessageBox.critical(self, "错误", f"导出报告失败: {e}")

    def _on_delete_requested(self, session_id: int):
        """处理删除请求"""
        # 确认对话框
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除会话 {session_id} 吗？\n\n此操作不可撤销，将删除该会话的所有数据和告警记录。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # 执行删除
            success = self.session_manager.delete_session(session_id)
            if not success:
                QMessageBox.warning(self, "失败", "删除会话失败，请查看日志")

    def _on_session_deleted(self, session_id: int):
        """单个会话删除成功后的处理"""
        logger.info(f"会话 {session_id} 已删除")
        QMessageBox.information(self, "成功", f"会话 {session_id} 已删除")

        # 清空报告显示
        if self.current_session_id == session_id:
            self.report_widget.clear()
            self.current_session_id = None

        # 重新加载会话列表
        self.load_sessions()

    def _on_sessions_deleted(self, session_ids: list):
        """
        批量会话删除成功后的处理

        注意：这里不显示消息框，因为批量删除结果已经在 _on_batch_delete_clicked 中显示了
        这里只需要重新加载会话列表即可
        """
        logger.info(f"批量删除了 {len(session_ids)} 个会话: {session_ids}")

        # 如果当前显示的会话被删除了，清空报告
        if self.current_session_id in session_ids:
            self.report_widget.clear()
            self.current_session_id = None

        # 重新加载会话列表（不显示消息，避免重复）
        try:
            self.sessions_data = self.db.get_recent_sessions(limit=100)
            self._refresh_list()
        except Exception as e:
            logger.error(f"重新加载会话列表失败: {e}")

    def _on_delete_failed(self, error_message: str):
        """删除失败的处理"""
        logger.error(f"删除会话失败: {error_message}")
        QMessageBox.critical(self, "错误", f"删除会话失败:\n{error_message}")

    def _on_batch_delete_clicked(self):
        """批量删除按钮点击"""
        selected_items = self.sessions_table.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "提示", "请先选择要删除的会话")
            return

        # 获取选中的会话ID（去重）
        selected_rows = set(item.row() for item in selected_items)
        session_ids = []
        for row in selected_rows:
            session_id_item = self.sessions_table.item(row, 0)
            if session_id_item:
                session_id = session_id_item.data(Qt.ItemDataRole.UserRole)
                session_ids.append(session_id)

        if not session_ids:
            QMessageBox.information(self, "提示", "无法获取会话ID")
            return

        # 确认对话框
        reply = QMessageBox.question(
            self,
            "批量删除确认",
            f"确定要删除选中的 {len(session_ids)} 个会话吗？\n\n此操作不可撤销，将删除这些会话的所有数据和告警记录。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # 执行批量删除
            result = self.session_manager.delete_sessions(session_ids)

            # 显示结果（注意：会话列表会通过 sessions_deleted 信号自动刷新）
            success_count = result.get('success', 0)
            failed_count = result.get('failed', 0)
            failed_ids = result.get('failed_ids', [])

            if failed_count == 0:
                QMessageBox.information(
                    self,
                    "批量删除成功",
                    f"成功删除 {success_count} 个会话"
                )
            else:
                QMessageBox.warning(
                    self,
                    "批量删除完成",
                    f"成功: {success_count} 个\n失败: {failed_count} 个\n\n失败的会话ID: {failed_ids}"
                )

            # 注意：不需要手动调用 load_sessions()，因为 sessions_deleted 信号会触发刷新
