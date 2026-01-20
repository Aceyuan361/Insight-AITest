"""
监控面板 - 完全复刻HTML设计 V2
参考：C:\\Users\\86132\\Desktop\\图表.html (最新版本)

2x2等分网格布局：
- 左上：CPU Usage (%)
- 右上：Memory Usage (MB)
- 左下：Frame Rate (FPS)
- 右下：Network I/O (KB/s)

运行方式：
python monitor_dashboard_v2.py
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame
)
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QColor, QPen, QFont
from datetime import datetime
import pyqtgraph as pg
from logzero import logger


class DesignTokens:
    """霓虹主题设计规范（完全复刻HTML V2）"""

    # 颜色
    BG_COLOR = "#0a0a0a"          # 主背景
    CARD_BG = "#141414"           # 卡片背景
    TEXT_PRIMARY = "#ffffff"      # 主文字
    TEXT_SECONDARY = "#aaaaaa"     # 次要文字

    # 霓虹主题色
    NEON_CPU = "#00f2ff"          # 青色
    NEON_RAM = "#7000ff"          # 紫色
    NEON_FPS = "#ffb400"          # 橙色
    NEON_NET_UP = "#00ff87"       # 绿色
    NEON_NET_DOWN = "#0062ff"     # 蓝色

    # 尺寸
    WINDOW_MIN_WIDTH = 1000
    WINDOW_MIN_HEIGHT = 600
    CARD_PADDING = 15
    CHART_GRID_TOP = 35
    CHART_GRID_LEFT = 55
    CHART_GRID_RIGHT = 20
    CHART_GRID_BOTTOM = 30


class NeonChartCard(QFrame):
    """
    霓虹风格图表卡片 V2
    完全复刻HTML中的独立卡片样式
    """

    def __init__(self, title: str, color: str, y_axis_config: dict, parent=None):
        """
        Args:
            title: 图表标题
            color: 霓虹主题色
            y_axis_config: Y轴配置 {min, max, formatter}
        """
        super().__init__(parent)
        self.title = title
        self.accent_color = color
        self.y_axis_config = y_axis_config
        self.data = []
        self.timestamps = []
        self.curve = None
        self.fill = None

        # 悬停提示相关
        self.tooltip = None
        self.vLine = None
        self.hover_point = None

        self._init_ui()

    def _init_ui(self):
        """初始化UI（完全复刻HTML样式）"""
        # 设置卡片最小高度
        self.setMinimumHeight(180)  # 增加最小高度，防止被压缩

        # 卡片样式（使用 Qt 支持的属性实现霓虹顶边框）
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignTokens.CARD_BG};
                border-radius: 12px;
                border: 1px solid rgba(255,255,255,0.05);
                border-top: 2px solid {self.accent_color};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            DesignTokens.CARD_PADDING,
            DesignTokens.CARD_PADDING,
            DesignTokens.CARD_PADDING,
            DesignTokens.CARD_PADDING
        )
        layout.setSpacing(10)  # 减少内部spacing

        # 标题栏（带统计信息）
        header = self._create_header()
        layout.addWidget(header)

        # 图表
        self.chart = self._create_chart()
        layout.addWidget(self.chart, 1)  # 占据剩余空间

    def _create_header(self) -> QWidget:
        """创建标题栏（完全复刻HTML）"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # 标题
        title_label = QLabel(self.title)
        title_label.setStyleSheet(f"""
            QLabel {{
                font-size: 1.1rem;
                font-weight: 500;
                color: {DesignTokens.TEXT_PRIMARY};
                background: transparent;
            }}
        """)
        layout.addWidget(title_label)

        layout.addStretch()

        # 统计信息
        self.stats_label = QLabel("Loading...")
        self.stats_label.setStyleSheet(f"""
            QLabel {{
                font-size: 0.85rem;
                font-family: 'Roboto Mono', monospace;
                color: {self.accent_color};
                background: transparent;
            }}
        """)
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.stats_label)

        return widget

    def _create_chart(self) -> pg.PlotWidget:
        """创建图表（完全复刻ECharts配置）"""
        chart = pg.PlotWidget()
        chart.setBackground(QColor(DesignTokens.CARD_BG))

        # 启用抗锯齿渲染
        chart.setAntialiasing(True)

        # 设置渲染优化
        chart.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        chart.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

        # 网格线（参考HTML：rgba(255, 255, 255, 0.08)）
        chart.showGrid(x=True, y=True, alpha=0.08)

        # 配置Y轴
        y_axis = chart.getAxis('left')
        y_axis.setStyle(tickFont=QFont("Arial", 11))
        y_axis.setTickPen(QPen(QColor("#444"), 1))
        y_axis.setTextPen(QPen(QColor("#888"), 1))
        y_axis.setWidth(self.y_axis_config.get('width', 55))
        # Y轴格式化器
        if 'formatter' in self.y_axis_config:
            # 需要在数据更新时应用格式化
            pass

        # 配置X轴（时间轴）
        x_axis = chart.getAxis('bottom')
        x_axis.setStyle(tickFont=QFont("Arial", 11))
        x_axis.setTickPen(QPen(QColor("#444"), 1))
        x_axis.setTextPen(QPen(QColor("#888"), 1))
        x_axis.setHeight(30)
        x_axis.setStyle(tickFont=QFont("Arial", 11))

        # 禁用交互
        chart.setMenuEnabled(False)
        chart.setMouseEnabled(x=False, y=False)

        # 设置边距（参考HTML：grid: { top: 35, left: 55, right: 20, bottom: 30 }）
        chart.getViewBox().setContentsMargins(
            self.y_axis_config.get('grid_left', 55),
            DesignTokens.CHART_GRID_TOP,
            DesignTokens.CHART_GRID_RIGHT,
            DesignTokens.CHART_GRID_BOTTOM
        )

        # 设置Y轴范围
        if 'min' in self.y_axis_config and 'max' in self.y_axis_config:
            min_val = self.y_axis_config['min']
            max_val = self.y_axis_config['max']
            # 只有当 min_val 和 max_val 都不是 None 且不是字符串特殊值时才设置固定范围
            if (min_val == 'dataMin' or max_val == 'dataMax' or
                min_val is None or max_val is None):
                # 自适应，稍后在数据更新时处理
                pass
            else:
                chart.setYRange(min_val, max_val, padding=0)

        # 创建曲线 - 使用 connect='all' 实现平滑连接
        pen = pg.mkPen(color=self.accent_color, width=2.5)
        self.curve = chart.plot(
            pen=pen,
            connect='all',  # 所有点按顺序连接
            antialias=True  # 启用抗锯齿
        )

        # 渐变填充
        r, g, b = self._hex_to_rgb(self.accent_color)
        alpha = int(255 * 0.35)  # 稍微降低透明度
        brush = pg.mkBrush(QColor(r, g, b, alpha))
        self.fill = chart.plot(pen=None, brush=brush, connect='all')

        # 创建悬停提示线
        self.vLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen(color='#444', width=1, style=Qt.PenStyle.DashLine))
        chart.addItem(self.vLine)
        self.vLine.hide()

        # 创建悬停点标记
        self.hover_point = pg.ScatterPlotItem(
            size=12,
            pen=pg.mkPen(color=self.accent_color, width=2),
            brush=pg.mkBrush(color=self.accent_color),
        )
        chart.addItem(self.hover_point)
        self.hover_point.hide()

        # 连接鼠标移动事件
        chart.scene().sigMouseMoved.connect(self._on_mouse_moved)

        return chart

    def _hex_to_rgb(self, color: str) -> tuple:
        """转换颜色"""
        hex_color = color.lstrip('#')
        return (
            int(hex_color[0:2], 16),
            int(hex_color[2:4], 16),
            int(hex_color[4:6], 16)
        )

    def add_data_point(self, value: float):
        """
        添加数据点

        Args:
            value: 数值
        """
        # 记录时间戳
        current_time = datetime.now()
        self.timestamps.append(current_time)
        if len(self.timestamps) > 120:  # 从 60 改为 120，获得更平滑的曲线
            self.timestamps.pop(0)

        # 添加数据
        self.data.append(value)
        if len(self.data) > 120:  # 从 60 改为 120
            self.data.pop(0)

        self._update_curve()
        self._update_stats()

    def _update_curve(self):
        """更新曲线"""
        if not self.data:
            return

        x_data = list(range(len(self.data)))
        y_data = self.data

        # 更新曲线
        self.curve.setData(x_data, y_data)

        # 更新填充
        if len(x_data) > 1:
            x_fill = [x_data[0]] + x_data + [x_data[-1]]
            y_fill = [0] + y_data + [0]
            self.fill.setData(x_fill, y_fill)
        else:
            self.fill.setData([], [])

        # 更新X轴范围和标签
        x_range = (0, len(self.data) - 1)
        self.chart.setXRange(x_range[0], x_range[1], padding=0)

        # 设置X轴为时间格式
        x_axis = self.chart.getAxis('bottom')
        ticks = []

        if len(self.data) <= 20:
            interval = 5
        elif len(self.data) <= 40:
            interval = 10
        else:
            interval = 15

        for i in range(0, len(self.data), interval):
            if i < len(self.timestamps):
                time_str = self.timestamps[i].strftime("%H:%M:%S")
                ticks.append((i, time_str))

        x_axis.setTicks([ticks])

        # 自适应Y轴（如果需要）
        if self.y_axis_config.get('min') == 'dataMin' or self.y_axis_config.get('max') == 'dataMax':
            min_val = min(self.data)
            max_val = max(self.data)
            # 添加一些边距
            if self.y_axis_config.get('min') == 'dataMin':
                min_val = max(0, min_val - 5)
            if self.y_axis_config.get('max') == 'dataMax':
                max_val += 5
            self.chart.setYRange(min_val, max_val, padding=0)
        elif self.y_axis_config.get('max') is None:
            # 完全自适应
            min_val = min(self.data)
            max_val = max(self.data)
            if min_val > 0:
                min_val = 0
            self.chart.setYRange(min_val, max_val * 1.1, padding=0)

    def _update_stats(self):
        """更新统计信息（完全复刻HTML：Max | Min | Avg）- 统一保留2位小数"""
        if not self.data:
            return

        max_val = max(self.data)
        min_val = min(self.data)
        avg_val = sum(self.data) / len(self.data)

        # 格式化（参考HTML：toLocaleString）
        # 统一使用2位小数，避免小数点溢出
        unit = self.y_axis_config.get('unit', '')
        decimals = self.y_axis_config.get('decimals', 0)

        if decimals == 0:
            # 千分位格式，保留2位小数
            format_val = lambda x: f"{x:,.2f}"
        else:
            format_val = lambda x: f"{x:,.{decimals}f}"

        stats_text = f"Max: {format_val(max_val)}{unit} | Min: {format_val(min_val)}{unit} | Avg: {format_val(avg_val)}{unit}"
        self.stats_label.setText(stats_text)

    def _cleanup_hover(self):
        """清理悬停相关资源，防止内存泄漏"""
        if hasattr(self, 'chart') and self.chart.scene():
            try:
                self.chart.scene().sigMouseMoved.disconnect(self._on_mouse_moved)
            except:
                pass
        if hasattr(self, 'tooltip') and self.tooltip:
            self.tooltip.hide_tooltip()

    def clear_data(self):
        """清除所有图表数据"""
        self.data.clear()
        self.timestamps.clear()
        self._update_curve()
        self._update_stats()
        # 清理悬停资源
        self._cleanup_hover()

    def _on_mouse_moved(self, pos):
        """鼠标移动事件处理"""
        if not self.chart.plotItem.vb.sceneBoundingRect().contains(pos):
            self.vLine.hide()
            self.hover_point.hide()
            if self.tooltip:
                self.tooltip.hide_tooltip()
            return

        # 转换为图表坐标
        mouse_point = self.chart.plotItem.vb.mapSceneToView(pos)
        x_pos = mouse_point.x()

        # 找到最近的数据点
        if not self.data:
            return

        idx = int(round(x_pos))
        if 0 <= idx < len(self.data):
            # 显示垂直线
            self.vLine.setPos(idx)
            self.vLine.show()

            # 显示数据点
            self.hover_point.setData([{'pos': (idx, self.data[idx])}])
            self.hover_point.show()

            # 创建并显示提示框
            if self.tooltip is None:
                from insight_eyes.desktop.ui.widgets.tooltip_widget import ChartTooltip
                self.tooltip = ChartTooltip(self.chart)

            # 获取全局坐标
            global_pos = self.chart.mapToGlobal(self.chart.pos())
            tooltip_pos = global_pos + QPoint(int(pos.x()), int(pos.y()))

            tooltip_data = {
                'title': self.title,
                'time': self.timestamps[idx].strftime("%H:%M:%S"),
                'value': f"{self.data[idx]:.2f}",
                'unit': self.y_axis_config.get('unit', '')
            }
            self.tooltip.show_tooltip(tooltip_pos, tooltip_data)


class MonitorPanelV2(QWidget):
    """监控面板 V2 - 动态卡片布局"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.device_id = None
        self.package_name = None
        self.app_name = None
        self._title_label = None

        # 动态卡片存储
        self.cards = {}  # {metric_id: NeonChartCard}
        self.grid_layout = None

        # 延迟初始化配置管理器（避免在 __init__ 中触发配置加载）
        self._config_mgr = None

        self._init_ui()

        # 延迟初始化配置管理器和卡片（使用较长延迟确保窗口完全显示）
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, self._delayed_init)

    def _init_ui(self):
        """初始化UI"""
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {DesignTokens.BG_COLOR};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 5, 20, 10)  # 减少顶部和底部margin，标题置顶
        layout.setSpacing(8)  # 减少整体spacing

        # 标题（上移居中置顶）
        self._title_label = QLabel("REAL-TIME SYSTEM MONITOR")
        self._title_label.setStyleSheet(f"""
            QLabel {{
                font-size: 1.2rem;
                font-weight: 600;
                color: {DesignTokens.TEXT_PRIMARY};
                background: transparent;
                text-align: center;
                padding: 0px 10px;
                letter-spacing: 2px;
                text-transform: uppercase;
            }}
        """)
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._title_label)

        # 动态网格布局
        self.grid_layout = QGridLayout()
        self.grid_layout.setHorizontalSpacing(15)
        self.grid_layout.setVerticalSpacing(12)
        layout.addLayout(self.grid_layout, 1)  # 让网格布局占据所有剩余空间

    def _delayed_init(self):
        """延迟初始化（在 UI 完全构建后调用）"""
        try:
            from insight_eyes.desktop.ui.utils.models import CollectionConfig

            # 使用默认配置而不是 ConfigManager（避免单例初始化问题）
            config = CollectionConfig()

            # 初始化卡片
            self._rebuild_cards_with_config(config)
        except Exception as e:
            import traceback
            print(f"[MonitorPanelV2] 延迟初始化失败: {e}")
            traceback.print_exc()

    def _rebuild_cards_with_config(self, config):
        """根据配置重建卡片（使用提供的配置对象）- 限制最多6个"""
        try:
            from insight_eyes.desktop.ui.utils.card_configs import ALL_METRIC_CARDS, get_card_config

            enabled_metrics = config.get_enabled_metrics()
            logger.info(f"准备重建卡片，启用的指标: {enabled_metrics}")

            # 清除现有卡片
            self._clear_cards()

            # 强制更新布局，确保旧卡片被移除
            self.grid_layout.update()

            # 限制最多6个卡片（2×3布局）
            MAX_CARDS = 6
            if len(enabled_metrics) > MAX_CARDS:
                logger.warning(f"启用的指标数量({len(enabled_metrics)})超过最大限制({MAX_CARDS})，将只显示前{MAX_CARDS}个")
                enabled_metrics = enabled_metrics[:MAX_CARDS]

            # 创建新卡片 - 使用 ALL_METRIC_CARDS 而不是 get_enabled_cards()
            # 这样可以确保 gpu 也能被创建（如果启用了的话）
            row, col = 0, 0
            max_cols = self._calculate_columns(len(enabled_metrics))

            logger.info(f"网格列数: {max_cols}")

            for card_config in ALL_METRIC_CARDS:
                if card_config.metric_id not in enabled_metrics:
                    continue

                logger.info(f"创建卡片: {card_config.metric_id}")
                try:
                    card = NeonChartCard(
                        card_config.title,
                        card_config.color,
                        y_axis_config={
                            'min': card_config.y_min,
                            'max': card_config.y_max,
                            'width': card_config.y_width,
                            'decimals': card_config.decimals,
                            'unit': card_config.unit
                        }
                    )
                    self.cards[card_config.metric_id] = card
                    self.grid_layout.addWidget(card, row, col)
                    logger.info(f"成功添加卡片 {card_config.metric_id} 到位置 ({row}, {col})")

                    # 计算下一个位置
                    col += 1
                    if col >= max_cols:
                        col = 0
                        row += 1
                except Exception as e:
                    logger.error(f"创建卡片 {card_config.metric_id} 失败: {e}")
                    import traceback
                    traceback.print_exc()

            logger.info(f"卡片创建完成，共创建 {len(self.cards)} 个卡片")

            # 设置等分布局 - 始终保持2列3行的网格结构，确保布局稳定
            # 列stretch：固定2列
            for i in range(2):  # 固定2列
                self.grid_layout.setColumnStretch(i, 1)

            # 行stretch：固定3行（即使某些行没有卡片，也设置stretch以保持布局稳定）
            for i in range(3):  # 固定3行
                self.grid_layout.setRowStretch(i, 1)

            # 强制刷新界面
            self.grid_layout.activate()
            self.update()

            logger.info("卡片重建完成")

        except Exception as e:
            logger.error(f"重建卡片失败: {e}")
            import traceback
            traceback.print_exc()

    def _calculate_columns(self, card_count: int) -> int:
        """计算网格列数 - 固定2列布局"""
        return 2  # 固定2列布局，最多6个卡片（2×3）

    def _clear_cards(self):
        """清除所有卡片"""
        try:
            # 复制一份键列表，避免在迭代时修改字典
            card_keys = list(self.cards.keys())
            for key in card_keys:
                card = self.cards.get(key)
                if card:
                    try:
                        card._cleanup_hover()  # 先清理悬停资源
                        self.grid_layout.removeWidget(card)
                        card.deleteLater()
                    except Exception as e:
                        logger.warning(f"清理卡片 {key} 时出错: {e}")
            self.cards.clear()
            logger.info("卡片清理完成")
        except Exception as e:
            logger.error(f"清除卡片失败: {e}")
            import traceback
            traceback.print_exc()

    def add_data_point(self, cpu: float, ram: float, fps: float, upload: float, download: float, battery: float = 0.0, gpu: float = 0.0):
        """
        添加数据点（动态更新所有启用的卡片）

        Args:
            cpu: CPU使用率（%）
            ram: 内存使用（MB）
            fps: 帧率
            upload: 上传速度（KB/s）
            download: 下载速度（KB/s）
            battery: 电池温度（℃）
            gpu: GPU使用率（%）
        """
        if 'cpu' in self.cards:
            self.cards['cpu'].add_data_point(cpu)

        if 'memory' in self.cards:
            self.cards['memory'].add_data_point(ram)

        if 'fps' in self.cards:
            self.cards['fps'].add_data_point(fps)

        if 'network_up' in self.cards:
            self.cards['network_up'].add_data_point(upload)

        if 'network_down' in self.cards:
            self.cards['network_down'].add_data_point(download)

        if 'battery' in self.cards:
            self.cards['battery'].add_data_point(battery)

        if 'gpu' in self.cards:
            self.cards['gpu'].add_data_point(gpu)

    def set_monitoring_target(self, device_id: str, package_name: str, app_name: str):
        """
        设置监控目标

        Args:
            device_id: 设备ID
            package_name: 包名
            app_name: 应用名称
        """
        self.device_id = device_id
        self.package_name = package_name
        self.app_name = app_name
        # 更新标题显示监控目标
        if self._title_label:
            self._title_label.setText(f"Monitoring: {app_name}")

    def clear_data(self):
        """清除所有图表数据"""
        for chart in self.cards.values():
            chart.clear_data()

    def refresh_cards(self, config_dict=None):
        """
        刷新卡片配置（当配置变更时调用）- 接收配置字典参数

        Args:
            config_dict: 配置字典（可选），如果提供则使用它来刷新卡片

        这个方法会：
        1. 根据配置字典创建临时配置对象
        2. 清除现有卡片
        3. 根据新配置创建卡片
        4. 自动计算布局

        Note:
            不再使用 ConfigManager，直接从配置字典创建临时配置对象。
            这避免了多线程访问 ConfigManager 单例的潜在问题。
        """
        try:
            import sys
            import traceback

            logger.info("[MONITOR-DEBUG-1] >>> refresh_cards 开始执行")
            logger.info(f"[MONITOR-DEBUG-2] 收到的配置字典: {config_dict}")

            # 如果没有提供配置字典，返回
            if config_dict is None:
                logger.warning("[MONITOR-DEBUG-WARNING] 没有提供配置字典，无法刷新卡片")
                return

            # 从配置字典创建临时配置对象
            logger.info("[MONITOR-DEBUG-3] 创建临时配置对象...")
            from insight_eyes.desktop.ui.utils.models import CollectionConfig

            temp_config = CollectionConfig()

            # 根据配置字典更新临时配置
            if 'enable_cpu' in config_dict:
                temp_config.enable_cpu = config_dict['enable_cpu']
            if 'enable_memory' in config_dict:
                temp_config.enable_memory = config_dict['enable_memory']
            if 'enable_fps' in config_dict:
                temp_config.enable_fps = config_dict['enable_fps']
            if 'enable_network_up' in config_dict:
                temp_config.enable_network_up = config_dict['enable_network_up']
            if 'enable_network_down' in config_dict:
                temp_config.enable_network_down = config_dict['enable_network_down']
            if 'enable_gpu' in config_dict:
                temp_config.enable_gpu = config_dict['enable_gpu']

            logger.info(f"[MONITOR-DEBUG-4] 临时配置对象创建成功: {temp_config}")
            logger.info(f"[MONITOR-DEBUG-5] 启用的指标: {temp_config.get_enabled_metrics()}")
            logger.info(f"[MONITOR-DEBUG-6] 当前卡片数量: {len(self.cards)}")
            logger.info(f"[MONITOR-DEBUG-7] 当前卡片列表: {list(self.cards.keys())}")

            # 强制刷新日志
            sys.stdout.flush()
            sys.stderr.flush()

            # 重建卡片
            logger.info("[MONITOR-DEBUG-8] *** 即将调用 _rebuild_cards_with_config ***")
            self._rebuild_cards_with_config(temp_config)
            logger.info("[MONITOR-DEBUG-9] *** _rebuild_cards_with_config 调用完成 ***")

            logger.info(f"[MONITOR-DEBUG-10] 新卡片数量: {len(self.cards)}")
            logger.info(f"[MONITOR-DEBUG-11] 新卡片列表: {list(self.cards.keys())}")

            sys.stdout.flush()
            sys.stderr.flush()

            logger.info("[MONITOR-DEBUG-12] >>> refresh_cards 执行成功")

        except Exception as e:
            logger.error(f"[MONITOR-DEBUG-EXCEPTION] refresh_cards 异常: {e}")
            logger.error(f"[MONITOR-DEBUG-EXCEPTION] 异常类型: {type(e).__name__}")
            logger.error(f"[MONITOR-DEBUG-EXCEPTION] 堆栈:\n{''.join(traceback.format_exc())}")

    def start_monitoring(self):
        """开始监控（占位方法，V2面板不需要特殊处理）"""
        pass

    def stop_monitoring(self):
        """停止监控（占位方法，V2面板不需要特殊处理）"""
        pass

    def reset_monitoring(self):
        """重置监控（清除数据）"""
        self.clear_data()
        if self._title_label:
            self._title_label.setText("Real-time System Monitor")
        self.device_id = None
        self.package_name = None
        self.app_name = None

    def mark_scenario(self, scenario_name: str):
        """
        标记场景（占位方法）

        Args:
            scenario_name: 场景名称
        """
        # V2 面板暂时不实现场景标记可视化
        pass

    def update_duration(self, duration_seconds: float):
        """
        更新监控时长（占位方法）

        Args:
            duration_seconds: 时长（秒）
        """
        # V2 面板暂不显示时长
        pass

    # 兼容旧面板接口（虽然不会被调用，但为了安全添加）
    def update_metrics(self, ui_metrics):
        """
        兼容旧面板接口（实际上使用 add_data_point）

        Args:
            ui_metrics: 旧格式的指标数据
        """
        # 此方法不会被调用，main_window.py 会使用 add_data_point
        pass
