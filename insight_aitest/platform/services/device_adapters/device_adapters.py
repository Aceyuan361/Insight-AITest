# -*- coding: utf-8 -*-
"""
设备连接适配器（支持 Android 和 iOS）
"""

import re
import threading
from typing import Optional, Dict, Any
from logzero import logger

from .models import DeviceInfo, Platform, DeviceStatus
from .base import BaseDeviceAdapter

# 导入 iOS 适配器（如果文件存在）
try:
    from .ios_device_adapter import IOSDeviceAdapter

    _IOS_ADAPTER_AVAILABLE = True
except ImportError:
    _IOS_ADAPTER_AVAILABLE = False
    logger.debug("IOSDeviceAdapter 不可用（这是正常的，如果使用骨架实现）")


class AndroidDeviceAdapter(BaseDeviceAdapter):
    """
    Android设备适配器
    通过ADB与Android设备通信
    """

    def __init__(self, device_id: str):
        """
        初始化Android设备适配器

        Args:
            device_id: Android设备ID
        """
        super().__init__(device_id)
        self._adb = None
        self._apm = None  # AndroidAPM 实例
        self._apm_lock = threading.Lock()  # 保护 APM 实例创建的锁
        self._init_adb()

    def _init_adb(self):
        """初始化ADB连接"""
        try:
            from insight_aitest.platform.services.collectors.adb import adb

            self._adb = adb
            logger.info(f"Android设备适配器初始化成功: {self.device_id}")
        except Exception as e:
            logger.error(f"初始化ADB失败: {e}")
            self._adb = None

    def connect(self) -> bool:
        """
        连接Android设备

        Returns:
            bool: 是否连接成功
        """
        logger.info(f"[设备连接] 尝试连接 Android 设备: {self.device_id}")
        try:
            if not self._adb:
                logger.info("[设备连接] 初始化 ADB...")
                self._init_adb()
                if not self._adb:
                    logger.error(f"[设备连接] ADB 初始化失败: {self.device_id}")
                    return False

            # 检查设备是否在线
            logger.info(f"[设备连接] 检查设备在线状态: {self.device_id}")
            result = self._adb.shell_noDevice("devices")
            if result != 0:
                logger.error(f"[设备连接] ADB设备列表获取失败: {self.device_id}")
                return False

            # 尝试执行简单命令验证连接
            logger.info(f"[设备连接] 验证设备连接: {self.device_id}")
            output = self._adb.shell("echo test", self.device_id, timeout=5)
            if "test" in output:
                logger.info(f"[设备连接] Android设备连接成功: {self.device_id}")
                return True
            else:
                logger.error(
                    f"[设备连接] Android设备连接验证失败: {self.device_id}, 输出: {output}"
                )
                return False

        except Exception as e:
            logger.error(f"Android设备连接异常: {e}")
            return False

    def disconnect(self) -> bool:
        """
        断开Android设备连接

        Returns:
            bool: 是否断开成功
        """
        # Android设备通过USB/Wi-Fi连接，ADB层面无需显式断开
        logger.info(f"Android设备已断开: {self.device_id}")
        return True

    def is_connected(self) -> bool:
        """
        检查Android设备是否连接

        Returns:
            bool: 是否已连接
        """
        try:
            if not self._adb:
                return False

            devices = self._adb.devices()
            return self.device_id in devices

        except Exception as e:
            logger.error(f"检查Android设备连接状态失败: {e}")
            return False

    def get_device_info(self) -> Optional[DeviceInfo]:
        """
        获取Android设备详细信息

        Returns:
            DeviceInfo: 设备信息
        """
        try:
            if not self._adb:
                return None

            # 获取设备属性
            model = self._adb.get_device_property("ro.product.model", self.device_id) or "Unknown"
            manufacturer = (
                self._adb.get_device_property("ro.product.manufacturer", self.device_id)
                or "Unknown"
            )
            os_version = (
                self._adb.get_device_property("ro.build.version.release", self.device_id)
                or "Unknown"
            )
            serial = self._adb.get_device_property("ro.serialno", self.device_id) or self.device_id

            # 获取设备名称（品牌 + 型号）
            name = f"{manufacturer} {model}".strip()

            # 获取Android API级别
            api_level = self._adb.get_device_property("ro.build.version.sdk", self.device_id)

            device_info = DeviceInfo(
                device_id=self.device_id,
                name=name,
                platform=Platform.ANDROID,
                model=model,
                os_version=f"Android {os_version} (API {api_level})",
                serial_number=serial,
                manufacturer=manufacturer,
                status=DeviceStatus.CONNECTED,
            )

            # 获取电池电量
            battery_level = self._get_battery_info()
            if battery_level is not None:
                device_info.battery_level = battery_level

            # 获取网络类型
            device_info.network_type = self.get_network_type()

            # 获取温度
            device_info.temperature = self.get_device_temperature()

            self._device_info = device_info
            return device_info

        except Exception as e:
            logger.error(f"获取Android设备信息失败: {e}")
            return None

    def _get_battery_info(self) -> Optional[int]:
        """
        获取电池电量信息

        Returns:
            int: 电池电量百分比
        """
        try:
            output = self._adb.shell("dumpsys battery", self.device_id, timeout=10)
            if not output:
                return None

            # 解析电池电量
            for line in output.split("\n"):
                if "level:" in line.lower():
                    match = re.search(r"level:\s*(\d+)", line)
                    if match:
                        return int(match.group(1))

            return None

        except Exception as e:
            logger.error(f"获取电池信息失败: {e}")
            return None

    def execute_command(self, command: str, timeout: int = 30) -> str:
        """
        在Android设备上执行shell命令

        Args:
            command: shell命令
            timeout: 超时时间（秒）

        Returns:
            str: 命令输出
        """
        if not self._adb:
            return ""

        return self._adb.shell(command, self.device_id, timeout)

    def install_app(self, app_path: str) -> bool:
        """
        安装APK应用

        Args:
            app_path: APK文件路径

        Returns:
            bool: 是否安装成功
        """
        if not self._adb:
            return False

        return self._adb.install(app_path, self.device_id, reinstall=True)

    def uninstall_app(self, package_name: str) -> bool:
        """
        卸载Android应用

        Args:
            package_name: 包名

        Returns:
            bool: 是否卸载成功
        """
        try:
            if not self._adb:
                return False

            result = self._adb.shell(f"pm uninstall {package_name}", self.device_id, timeout=60)
            return "Success" in result

        except Exception as e:
            logger.error(f"卸载应用失败: {e}")
            return False

    def start_app(self, package_name: str, activity: str = None) -> bool:
        """
        启动Android应用

        Args:
            package_name: 包名
            activity: Activity名称（可选）

        Returns:
            bool: 是否启动成功
        """
        try:
            if not self._adb:
                return False

            if activity:
                cmd = f"am start -n {package_name}/{activity}"
            else:
                # 使用monkey命令启动应用
                cmd = f"monkey -p {package_name} -c android.intent.category.LAUNCHER 1"

            result = self._adb.shell(cmd, self.device_id, timeout=10)
            return result != "" or "No activities found" not in result

        except Exception as e:
            logger.error(f"启动应用失败: {e}")
            return False

    def stop_app(self, package_name: str) -> bool:
        """
        停止Android应用

        Args:
            package_name: 包名

        Returns:
            bool: 是否停止成功
        """
        try:
            if not self._adb:
                return False

            self._adb.shell(f"am force-stop {package_name}", self.device_id, timeout=10)
            return True

        except Exception as e:
            logger.error(f"停止应用失败: {e}")
            return False

    def get_device_temperature(self) -> float:
        """
        获取Android设备温度

        Returns:
            float: 温度（摄氏度）
        """
        try:
            if not self._adb:
                return 0.0

            output = self._adb.shell("dumpsys battery", self.device_id, timeout=10)
            if not output:
                return 0.0

            # 尝试获取温度
            for line in output.split("\n"):
                if "temperature:" in line.lower():
                    match = re.search(r"temperature:\s*(\d+\.?\d*)", line)
                    if match:
                        # Android返回的是温度的10倍（摄氏度）
                        temp = float(match.group(1)) / 10.0
                        return temp

            return 0.0

        except Exception as e:
            logger.error(f"获取设备温度失败: {e}")
            return 0.0

    def get_network_type(self) -> str:
        """
        获取Android设备网络类型

        Returns:
            str: 网络类型
        """
        try:
            if not self._adb:
                return "Unknown"

            # 检查网络类型
            output = self._adb.shell("dumpsys connectivity", self.device_id, timeout=10)
            if not output:
                return "Unknown"

            # 解析网络类型
            if "WIFI" in output.upper():
                return "Wi-Fi"
            elif "MOBILE" in output.upper() or "CELLULAR" in output.upper():
                # 检查是4G还是5G
                nr_output = self._adb.shell("getprop gsm.network.type", self.device_id, timeout=5)
                if "NR" in nr_output or "5G" in nr_output:
                    return "5G"
                else:
                    return "4G"

            return "Unknown"

        except Exception as e:
            logger.error(f"获取网络类型失败: {e}")
            return "Unknown"

    # ========== 性能指标采集实现 ==========

    def _get_apm(self, package_name: str):
        """
        获取或初始化 APM 实例 - 线程安全版本

        使用双重检查锁定模式（Double-Checked Locking）：
        1. 快速检查（无锁）：如果已有匹配的 APM 实例，直接返回
        2. 锁保护检查：在锁内再次检查，防止竞态条件
        3. 创建新实例：仅在需要时创建，避免重复初始化

        注意：Python GIL 保证对象引用读取的原子性，此实现在 CPython 中是安全的。

        Args:
            package_name: 应用包名（使用 "__battery__" 表示电池采集）

        Returns:
            AndroidAPM: APM 实例
        """
        # 特殊处理：电池采集不需要包名，使用现有的 APM 实例（如果有）
        if package_name == "__battery__":
            with self._apm_lock:
                # 如果已有 APM 实例，直接复用（不需要包名）
                if self._apm:
                    return self._apm
                # 如果没有 APM 实例，创建一个不带包名的实例用于电池采集
                from insight_aitest.platform.services.collectors.android.android_apm import AndroidAPM

                logger.debug(f"[APM管理] 创建电池专用 APM 实例: device={self.device_id}")
                self._apm = AndroidAPM("", self.device_id)
                return self._apm

        # 快速路径：如果已有匹配的 APM 实例，直接返回（无锁，利用 Python GIL）
        # 注意：在 GIL 下，简单的对象引用读取是原子操作
        if self._apm is not None and self._apm.package_name == package_name:
            return self._apm

        # 慢速路径：需要创建或更换 APM，使用锁保护
        with self._apm_lock:
            # 双重检查：可能在等待锁时已被其他线程创建
            if self._apm is not None and self._apm.package_name == package_name:
                return self._apm

            from insight_aitest.platform.services.collectors.android.android_apm import AndroidAPM

            # 如果之前的 APM 存在且包名不同，先停止旧实例
            if self._apm is not None:
                try:
                    logger.debug(f"[APM管理] 停止旧 APM 实例: {self._apm.package_name}")
                    self._apm.stop()
                except Exception as e:
                    logger.warning(f"[APM管理] 停止旧 APM 失败: {e}")

            # 创建新的 APM 实例
            logger.debug(
                f"[APM管理] 创建新 APM 实例: package={package_name}, device={self.device_id}"
            )
            self._apm = AndroidAPM(package_name, self.device_id)
            # 启动 FPS 监控（会在内部创建 FPSMonitor）
            self._apm.start()

        return self._apm

    def collect_fps(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        采集Android应用的FPS数据

        Args:
            package_name: 应用包名

        Returns:
            dict: FPS数据
        """
        try:
            if not self._adb:
                return None

            # 使用 APM 实例采集FPS
            apm = self._get_apm(package_name)
            fps_data = apm.collectFps()

            if fps_data:
                logger.debug(f"FPS采集成功: {fps_data.get('fps', 0)}")
                return fps_data
            else:
                logger.warning(f"FPS采集返回空数据: {package_name}")
                return None

        except Exception as e:
            logger.error(f"采集FPS数据失败: {e}")
            return None

    def collect_memory(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        采集Android应用的内存数据

        Args:
            package_name: 应用包名

        Returns:
            dict: 内存数据（单位MB）
        """
        try:
            if not self._adb:
                return None

            # 使用 APM 实例采集内存
            apm = self._get_apm(package_name)
            memory_data = apm.collectMemory()

            if memory_data:
                logger.debug(f"内存采集成功: {memory_data.get('totalPass', 0)} MB")
                return memory_data
            else:
                logger.warning(f"内存采集返回空数据: {package_name}")
                return None

        except Exception as e:
            logger.error(f"采集内存数据失败: {e}")
            return None

    def collect_cpu(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        采集Android应用的CPU数据

        Args:
            package_name: 应用包名

        Returns:
            dict: CPU数据（百分比）
        """
        try:
            if not self._adb:
                return None

            # 使用 APM 实例采集CPU
            apm = self._get_apm(package_name)
            cpu_data = apm.collectCpu()

            if cpu_data:
                logger.debug(f"CPU采集成功: {cpu_data.get('appCpuRate', 0)}%")
                return cpu_data
            else:
                logger.warning(f"CPU采集返回空数据: {package_name}")
                return None

        except Exception as e:
            logger.error(f"采集CPU数据失败: {e}")
            return None

    def collect_network(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        采集Android应用的网络数据

        Args:
            package_name: 应用包名

        Returns:
            dict: 网络数据（KB/s）
        """
        try:
            if not self._adb:
                return None

            # 使用 APM 实例采集网络
            apm = self._get_apm(package_name)
            network_data = apm.collectFlow()

            if network_data:
                logger.debug(f"网络采集成功: 上行{network_data.get('upFlow', 0)} KB/s")
                return network_data
            else:
                logger.warning(f"网络采集返回空数据: {package_name}")
                return None

        except Exception as e:
            logger.error(f"采集网络数据失败: {e}")
            return None

    def collect_battery(self) -> Optional[Dict[str, Any]]:
        """
        采集Android设备的电池数据

        Returns:
            dict: 电池数据
        """
        try:
            if not self._adb:
                return None

            # 关键修复：使用共享的 APM 实例，而不是创建新实例
            # 电池采集不需要包名，但为了复用 APM 实例，传入一个特殊的标记
            # 这样可以避免创建多个 APM 实例导致的线程安全问题
            apm = self._get_apm("__battery__")  # 使用特殊标记表示电池采集
            battery_data = apm.collectBattery()

            if battery_data:
                logger.debug(f"电池采集成功: {battery_data.get('level', 0)}%")
                return battery_data
            else:
                logger.warning("电池采集返回空数据")
                return None

        except Exception as e:
            logger.error(f"采集电池数据失败: {e}")
            return None

    def cleanup(self):
        """
        清理设备适配器资源 - 增强修复版（确保线程安全停止）

        关键修复：
        1. 停止APM实例（包括FPS监控线程）
        2. 等待所有线程完全停止（增加超时时间）
        3. 验证线程状态后再清空APM实例
        4. 如果线程未能停止，提前返回避免崩溃
        """
        logger.info(f"开始清理Android设备适配器: {self.device_id}")

        try:
            # 步骤 1: 停止APM实例（包括FPS监控线程）
            if self._apm:
                try:
                    logger.debug("停止APM实例")
                    self._apm.stop()

                    # 步骤 2: 等待FPS线程完全停止（增强修复 - 增加超时和验证）
                    if hasattr(self._apm, "fps_monitor") and self._apm.fps_monitor:
                        fps_monitor = self._apm.fps_monitor
                        if hasattr(fps_monitor, "fpscollector"):
                            collector = fps_monitor.fpscollector

                            # 等待采集线程停止（超时从5秒增加到10秒）
                            if (
                                hasattr(collector, "collector_thread")
                                and collector.collector_thread
                            ):
                                if collector.collector_thread.is_alive():
                                    logger.debug("等待FPS采集线程停止...")
                                    collector.collector_thread.join(timeout=10.0)
                                    if collector.collector_thread.is_alive():
                                        # 关键修复：如果线程仍未停止，提前返回避免崩溃
                                        logger.error(
                                            "FPS采集线程未能在10秒内停止，中止清理以避免崩溃"
                                        )
                                        return

                            # 等待计算线程停止（超时从5秒增加到10秒）
                            if (
                                hasattr(collector, "calculator_thread")
                                and collector.calculator_thread
                            ):
                                if collector.calculator_thread.is_alive():
                                    logger.debug("等待FPS计算线程停止...")
                                    collector.calculator_thread.join(timeout=10.0)
                                    if collector.calculator_thread.is_alive():
                                        logger.error(
                                            "FPS计算线程未能在10秒内停止，中止清理以避免崩溃"
                                        )
                                        return

                    logger.info("APM实例已停止，所有线程已停止")
                except Exception as e:
                    logger.warning(f"停止APM实例时出错: {e}")

            # 步骤 3: 只有在所有线程停止后才清空APM实例
            self._apm = None

            logger.info(f"Android设备适配器已清理: {self.device_id}")

        except Exception as e:
            logger.error(f"清理Android设备适配器时出错: {e}", exc_info=True)


class DeviceAdapterFactory:
    """
    设备适配器工厂
    """

    @staticmethod
    def create_adapter(device_id: str, platform: Platform) -> Optional[BaseDeviceAdapter]:
        """
        创建设备适配器

        Args:
            device_id: 设备ID
            platform: 平台类型

        Returns:
            BaseDeviceAdapter: 设备适配器实例
        """
        # 调试日志
        logger.info(
            f"[设备适配器] 创建适配器: device_id={device_id}, platform={platform}, platform类型={type(platform)}, platform值={platform.value if hasattr(platform, 'value') else platform}"
        )

        # 比较枚举值而不是枚举本身
        if hasattr(platform, "value"):
            platform_value = platform.value
        else:
            platform_value = str(platform)

        if platform_value == "Android":
            logger.info("[设备适配器] 创建 AndroidDeviceAdapter")
            adapter = AndroidDeviceAdapter(device_id)
        elif platform_value == "iOS":
            # 使用已导入的 iOS 适配器（在文件顶部导入）
            if _IOS_ADAPTER_AVAILABLE:
                logger.info("[设备适配器] 创建 IOSDeviceAdapter")
                adapter = IOSDeviceAdapter(device_id)
            else:
                logger.error("[设备适配器] iOS 适配器不可用")
                return None
        else:
            logger.error(f"[设备适配器] 不支持的平台: {platform} (值: {platform_value})")
            return None

        # 设置 platform 属性，供 main_window.py 检测平台类型
        adapter.platform = platform
        logger.info(f"[设备适配器] 适配器创建成功: {type(adapter).__name__}")
        return adapter
