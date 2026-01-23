# -*- coding: utf-8 -*-
"""
设备管理器使用示例
演示如何使用设备连接与App枚举筛选模块
"""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QListWidget, QPushButton, QLabel
from PyQt6.QtCore import Qt

from insight_eyes.desktop.core import (
    DeviceManager, DeviceFilter, AppFilter, Platform, DeviceInfo, AppInfo
)


class DeviceManagerDemo(QMainWindow):
    """设备管理器演示窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("设备管理器演示")
        self.setGeometry(100, 100, 800, 600)

        # 创建设备管理器
        self.device_manager = DeviceManager()

        # 连接信号
        self.device_manager.device_discovered.connect(self.on_device_discovered)
        self.device_manager.device_lost.connect(self.on_device_lost)
        self.device_manager.device_updated.connect(self.on_device_updated)
        self.device_manager.app_list_updated.connect(self.on_app_list_updated)

        # 创建UI
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()

        # 设备列表
        layout.addWidget(QLabel("设备列表:"))
        self.device_list = QListWidget()
        layout.addWidget(self.device_list)

        # 应用列表
        layout.addWidget(QLabel("应用列表:"))
        self.app_list = QListWidget()
        layout.addWidget(self.app_list)

        # 按钮
        self.btn_scan = QPushButton("开始扫描")
        self.btn_scan.clicked.connect(self.start_scan)
        layout.addWidget(self.btn_scan)

        self.btn_refresh_apps = QPushButton("刷新应用列表")
        self.btn_refresh_apps.clicked.connect(self.refresh_apps)
        layout.addWidget(self.btn_refresh_apps)

        central_widget.setLayout(layout)

    def start_scan(self):
        """开始扫描设备"""
        self.device_manager.start_scan()
        self.btn_scan.setText("扫描中...")

    def refresh_apps(self):
        """刷新应用列表"""
        current_device = self.get_selected_device()
        if current_device:
            apps = self.device_manager.get_device_apps(current_device.device_id, force_refresh=True)
            self._update_app_list(apps)

    def get_selected_device(self) -> DeviceInfo:
        """获取选中的设备"""
        row = self.device_list.currentRow()
        if row >= 0:
            devices = self.device_manager.get_devices()
            if row < len(devices):
                return devices[row]
        return None

    def on_device_discovered(self, device: DeviceInfo):
        """设备发现事件处理"""
        item_text = f"[{device.platform.value}] {device.name} ({device.device_id})"
        self.device_list.addItem(item_text)
        print(f"发现设备: {device.name} - {device.platform.value}")

        # 自动开始监控
        self.device_manager.monitor_device(device.device_id)

    def on_device_lost(self, device_id: str):
        """设备断开事件处理"""
        print(f"设备断开: {device_id}")
        # 刷新列表
        self.device_list.clear()
        devices = self.device_manager.get_devices()
        for device in devices:
            item_text = f"[{device.platform.value}] {device.name} ({device.device_id})"
            self.device_list.addItem(item_text)

    def on_device_updated(self, device: DeviceInfo):
        """设备信息更新事件处理"""
        print(f"设备状态更新: {device.name} - 电量: {device.battery_level}%")

    def on_app_list_updated(self, device_id: str, apps: list):
        """应用列表更新事件处理"""
        current_device = self.get_selected_device()
        if current_device and current_device.device_id == device_id:
            self._update_app_list(apps)

    def _update_app_list(self, apps: list):
        """更新应用列表显示"""
        self.app_list.clear()
        for app in apps:
            status = "运行中" if app.is_running else "已停止"
            item_text = f"{app.app_name} ({app.package_name}) - {status}"
            self.app_list.addItem(item_text)


def example_basic_usage():
    """示例1：基本使用"""
    print("\n=== 示例1：基本使用 ===\n")

    from insight_eyes.desktop.core import DeviceManager

    # 创建设备管理器
    manager = DeviceManager()

    # 开始扫描设备
    manager.start_scan()

    print("正在扫描设备...")

    # 等待设备发现（实际应用中使用Qt事件循环）
    import time
    time.sleep(5)

    # 获取所有设备
    devices = manager.get_devices()
    print(f"发现 {len(devices)} 个设备")

    for device in devices:
        print(f"  - {device.name} ({device.platform.value})")
        print(f"    型号: {device.model}")
        print(f"    系统版本: {device.os_version}")
        print(f"    电池电量: {device.battery_level}%")

    # 清理
    manager.cleanup()


def example_device_filter():
    """示例2：使用设备过滤器"""
    print("\n=== 示例2：使用设备过滤器 ===\n")

    from insight_eyes.desktop.core import DeviceManager, DeviceFilter, Platform

    manager = DeviceManager()
    manager.start_scan()

    # 等待设备发现
    import time
    time.sleep(5)

    # 只获取Android设备
    android_filter = DeviceFilter(platform=Platform.ANDROID)
    android_devices = manager.get_devices(android_filter)
    print(f"Android设备数量: {len(android_devices)}")

    # 搜索特定设备
    search_filter = DeviceFilter(search_text="Samsung")
    samsung_devices = manager.get_devices(search_filter)
    print(f"Samsung设备数量: {len(samsung_devices)}")

    # 按系统版本过滤
    version_filter = DeviceFilter(min_os_version="Android 10")
    new_devices = manager.get_devices(version_filter)
    print(f"Android 10+设备数量: {len(new_devices)}")

    manager.cleanup()


def example_app_enumeration():
    """示例3：应用枚举"""
    print("\n=== 示例3：应用枚举 ===\n")

    from insight_eyes.desktop.core import DeviceManager, AppFilter

    manager = DeviceManager()
    manager.start_scan()

    import time
    time.sleep(5)

    devices = manager.get_devices()
    if not devices:
        print("没有发现设备")
        return

    device = devices[0]
    print(f"设备: {device.name}")

    # 获取所有应用
    all_apps = manager.get_device_apps(device.device_id)
    print(f"总应用数: {len(all_apps)}")

    # 只获取运行中的应用
    running_filter = AppFilter(running_only=True)
    running_apps = manager.get_device_apps(device.device_id, running_filter)
    print(f"运行中的应用数: {len(running_apps)}")

    for app in running_apps[:5]:  # 只显示前5个
        print(f"  - {app.app_name} (PID: {app.pid})")

    # 搜索应用
    search_filter = AppFilter(search_text="WeChat")
    wechat_apps = manager.get_device_apps(device.device_id, search_filter)
    print(f"WeChat相关应用: {len(wechat_apps)}")

    manager.cleanup()


def example_device_monitoring():
    """示例4：设备监控"""
    print("\n=== 示例4：设备监控 ===\n")

    from insight_eyes.desktop.core import DeviceManager

    manager = DeviceManager()

    # 连接信号
    def on_device_updated(device):
        print(f"设备更新: {device.name} - 电量: {device.battery_level}% - 温度: {device.temperature}°C")

    def on_app_list_updated(device_id, apps):
        print(f"应用列表更新: {len(apps)}个应用")

    manager.device_updated.connect(on_device_updated)
    manager.app_list_updated.connect(on_app_list_updated)

    manager.start_scan()

    import time
    time.sleep(5)

    devices = manager.get_devices()
    if devices:
        device = devices[0]
        print(f"开始监控设备: {device.name}")
        manager.monitor_device(device.device_id)

        # 监控10秒
        time.sleep(10)

        # 停止监控
        manager.stop_monitoring(device.device_id)
        print("停止监控")

    manager.cleanup()


def example_search():
    """示例5：搜索功能"""
    print("\n=== 示例5：搜索功能 ===\n")

    from insight_eyes.desktop.core import DeviceManager

    manager = DeviceManager()
    manager.start_scan()

    import time
    time.sleep(5)

    # 搜索设备
    devices = manager.search_devices("Galaxy")
    print(f"搜索'Galaxy'找到 {len(devices)} 个设备")

    if devices:
        device = devices[0]

        # 搜索应用
        apps = manager.search_apps(device.device_id, "WeChat", running_only=True)
        print(f"在{device.name}上搜索'WeChat'运行中的应用: {len(apps)}个")

    manager.cleanup()


def example_direct_adapter():
    """示例6：直接使用设备适配器"""
    print("\n=== 示例6：直接使用设备适配器 ===\n")

    from insight_eyes.desktop.core import DeviceAdapterFactory, Platform

    device_id = "emulator-5554"  # 替换为实际设备ID

    # 创建Android适配器
    adapter = DeviceAdapterFactory.create_adapter(device_id, Platform.ANDROID)
    if adapter and adapter.connect():
        print("设备连接成功")

        # 获取设备信息
        device_info = adapter.get_device_info()
        if device_info:
            print(f"设备名称: {device_info.name}")
            print(f"设备型号: {device_info.model}")
            print(f"系统版本: {device_info.os_version}")

        # 执行命令
        output = adapter.execute_command("getprop ro.build.version.release")
        print(f"系统版本: {output}")

        # 断开连接
        adapter.disconnect()
        print("设备已断开")
    else:
        print("设备连接失败")


def example_direct_enumerator():
    """示例7：直接使用应用枚举器"""
    print("\n=== 示例7：直接使用应用枚举器 ===\n")

    from insight_eyes.desktop.core import AppEnumeratorFactory, Platform

    device_id = "emulator-5554"  # 替换为实际设备ID

    # 创建枚举器
    enumerator = AppEnumeratorFactory.create_enumerator(device_id, Platform.ANDROID)
    if enumerator:
        # 枚举应用
        apps = enumerator.enumerate_apps(include_system_apps=False)
        print(f"发现 {len(apps)} 个第三方应用")

        # 获取运行中的应用
        running_apps = enumerator.get_running_apps()
        print(f"运行中的应用: {len(running_apps)}")

        for app in running_apps[:3]:
            print(f"  - {app.app_name} (PID: {app.pid})")


def main():
    """主函数"""
    print("设备管理器使用示例")
    print("=" * 50)

    # 运行示例
    example_basic_usage()
    example_device_filter()
    example_app_enumeration()
    example_device_monitoring()
    example_search()
    example_direct_adapter()
    example_direct_enumerator()

    print("\n" + "=" * 50)
    print("示例运行完成")

    # 如果需要运行GUI演示
    # app = QApplication(sys.argv)
    # demo = DeviceManagerDemo()
    # demo.show()
    # sys.exit(app.exec())


if __name__ == '__main__':
    main()
