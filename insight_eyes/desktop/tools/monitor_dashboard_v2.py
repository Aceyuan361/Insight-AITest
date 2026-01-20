"""
监控面板测试 - 完全复刻HTML设计 V2
参考：C:\\Users\\86132\\Desktop\\图表.html (最新版本)

运行此文件查看效果：
python monitor_dashboard_v2.py
"""
import sys
import os

# 添加项目路径
project_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, project_root)

from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import QTimer
from datetime import datetime
import random

# 直接导入，绕过 __init__.py 中的相对导入问题
import importlib.util

def import_module_from_file(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# 导入 monitor_panel_v2
panels_dir = os.path.join(os.path.dirname(__file__), 'ui', 'panels')
monitor_panel_module = import_module_from_file(
    "monitor_panel_v2",
    os.path.join(panels_dir, "monitor_panel_v2.py")
)
MonitorPanelV2 = monitor_panel_module.MonitorPanelV2


class MonitorDashboardWindow(QMainWindow):
    """监控仪表板窗口 - 完全复刻HTML V2"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Real-time System Monitor - 复刻HTML")
        self.setMinimumSize(1100, 700)

        # 创建监控面板
        self.monitor_panel = MonitorPanelV2()
        self.setCentralWidget(self.monitor_panel)

        # 初始化数据容器（参考HTML）
        self.data_cpu = []
        self.data_ram = []
        self.data_fps = []
        self.data_net_up = []
        self.data_net_down = []

        # 模拟状态变量（参考HTML）
        self.ram_base = 64  # 内存从64MB开始模拟
        self.ram_trend_step = 0.2  # 模拟缓慢的线性增长趋势

        # 预填充初始数据（参考HTML）
        self._init_data()

        # 定时器：每秒更新（参考HTML：1000ms）
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_data)
        self.timer.start(1000)

    def _init_data(self):
        """预填充初始数据（完全复刻HTML逻辑）"""
        now = datetime.now()
        for i in range(60, 0, -1):
            # 初始化数据，保持低位（参考HTML）
            self.data_cpu.append(random.random() * 10 + 5)  # 5-15
            self.data_ram.append(self.ram_base + random.random() * 5)  # 64MB附近
            self.data_fps.append(60)  # 稳定60
            self.data_net_up.append(0)
            self.data_net_down.append(0)

        # 添加到图表
        self._add_to_charts()

    def _update_data(self):
        """更新数据（完全复刻HTML的数据生成逻辑）"""
        # 1. CPU: 大部分时间低负载，偶尔尖峰（参考HTML）
        new_cpu = (random.random() * 40 + 30) if random.random() > 0.9 else random.random() * 15 + 5

        # 2. RAM: 模拟线性增长和波动（参考HTML）
        self.ram_base += self.ram_trend_step + (random.random() - 0.4)
        new_ram = max(10, self.ram_base + (random.random() - 0.5) * 8)

        # 3. FPS: 模拟偶尔掉帧（参考HTML）
        new_fps = (random.random() * 10 + 45) if random.random() > 0.85 else 60 + (random.random() - 0.5) * 2

        # 4. Network: 偶尔突发（参考HTML）
        new_net_up = (random.random() * 500 + 50) if random.random() > 0.95 else random.random() * 20
        new_net_down = (random.random() * 1000 + 100) if random.random() > 0.92 else random.random() * 50

        # 更新数据队列（参考HTML：updateQueue）
        self.data_cpu.pop(0)
        self.data_cpu.append(new_cpu)

        self.data_ram.pop(0)
        self.data_ram.append(new_ram)

        self.data_fps.pop(0)
        self.data_fps.append(new_fps)

        self.data_net_up.pop(0)
        self.data_net_up.append(new_net_up)

        self.data_net_down.pop(0)
        self.data_net_down.append(new_net_down)

        # 添加到图表
        self._add_to_charts()

    def _add_to_charts(self):
        """添加数据到图表"""
        self.monitor_panel.add_data_point(
            cpu=self.data_cpu[-1],
            ram=self.data_ram[-1],
            fps=self.data_fps[-1],
            upload=self.data_net_up[-1],
            download=self.data_net_down[-1]
        )


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    window = MonitorDashboardWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
