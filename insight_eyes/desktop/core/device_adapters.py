# -*- coding: utf-8 -*-
"""
设备连接适配器
为Android和iOS设备提供统一的连接接口

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License

Author: Aceyuan361
"""

import subprocess
import json
import re
import threading
from typing import Optional, Dict, Any, List, Literal, Tuple
from abc import ABC, abstractmethod
from logzero import logger

from .models import DeviceInfo, Platform, DeviceStatus, AppInfo, AppStatus


class BaseDeviceAdapter(ABC):
    """
    设备适配器基类
    定义所有设备适配器必须实现的接口
    """

    def __init__(self, device_id: str):
        """
        初始化设备适配器

        Args:
            device_id: 设备ID
        """
        self.device_id = device_id
        self._device_info: Optional[DeviceInfo] = None

    @abstractmethod
    def connect(self) -> bool:
        """
        连接设备

        Returns:
            bool: 是否连接成功
        """
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """
        断开设备连接

        Returns:
            bool: 是否断开成功
        """
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """
        检查设备是否连接

        Returns:
            bool: 是否已连接
        """
        pass

    @abstractmethod
    def get_device_info(self) -> Optional[DeviceInfo]:
        """
        获取设备信息

        Returns:
            DeviceInfo: 设备信息，获取失败返回None
        """
        pass

    @abstractmethod
    def execute_command(self, command: str, timeout: int = 30) -> str:
        """
        在设备上执行命令

        Args:
            command: 要执行的命令
            timeout: 超时时间（秒）

        Returns:
            str: 命令输出
        """
        pass

    @abstractmethod
    def install_app(self, app_path: str) -> bool:
        """
        安装应用

        Args:
            app_path: 应用文件路径

        Returns:
            bool: 是否安装成功
        """
        pass

    @abstractmethod
    def uninstall_app(self, package_name: str) -> bool:
        """
        卸载应用

        Args:
            package_name: 包名

        Returns:
            bool: 是否卸载成功
        """
        pass

    @abstractmethod
    def start_app(self, package_name: str, activity: str = None) -> bool:
        """
        启动应用

        Args:
            package_name: 包名
            activity: Activity名称（Android）

        Returns:
            bool: 是否启动成功
        """
        pass

    @abstractmethod
    def stop_app(self, package_name: str) -> bool:
        """
        停止应用

        Args:
            package_name: 包名

        Returns:
            bool: 是否停止成功
        """
        pass

    def get_battery_level(self) -> int:
        """
        获取电池电量

        Returns:
            int: 电池电量百分比
        """
        return 100

    def get_device_temperature(self) -> float:
        """
        获取设备温度

        Returns:
            float: 温度（摄氏度）
        """
        return 0.0

    def get_network_type(self) -> str:
        """
        获取网络类型

        Returns:
            str: 网络类型（4G/5G/Wi-Fi/Unknown）
        """
        return "Unknown"

    # ========== 性能指标采集接口 ==========

    def collect_fps(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        采集FPS数据

        Args:
            package_name: 应用包名

        Returns:
            dict: FPS数据，包含fps, jank, big_jank, ftime_avg等字段
        """
        return None

    def collect_memory(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        采集内存数据

        Args:
            package_name: 应用包名

        Returns:
            dict: 内存数据，包含totalPass, nativePass, dalvikPass等字段（单位KB）
        """
        return None

    def collect_cpu(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        采集CPU数据

        Args:
            package_name: 应用包名

        Returns:
            dict: CPU数据，包含appCpuRate, sysCpuRate等字段（百分比）
        """
        return None

    def collect_network(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        采集网络数据

        Args:
            package_name: 应用包名

        Returns:
            dict: 网络数据，包含upFlow, downFlow等字段（KB/s）
        """
        return None

    def collect_battery(self) -> Optional[Dict[str, Any]]:
        """
        采集电池数据

        Returns:
            dict: 电池数据，包含level, temperature等字段
        """
        return None


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
            from insight_eyes.public.adb import adb
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
        try:
            if not self._adb:
                self._init_adb()
                if not self._adb:
                    return False

            # 检查设备是否在线
            result = self._adb.shell_noDevice('devices')
            if result != 0:
                logger.error("ADB设备列表获取失败")
                return False

            # 尝试执行简单命令验证连接
            output = self._adb.shell('echo test', self.device_id, timeout=5)
            if 'test' in output:
                logger.info(f"Android设备连接成功: {self.device_id}")
                return True
            else:
                logger.error(f"Android设备连接验证失败: {self.device_id}")
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
            model = self._adb.get_device_property('ro.product.model', self.device_id) or "Unknown"
            manufacturer = self._adb.get_device_property('ro.product.manufacturer', self.device_id) or "Unknown"
            os_version = self._adb.get_device_property('ro.build.version.release', self.device_id) or "Unknown"
            serial = self._adb.get_device_property('ro.serialno', self.device_id) or self.device_id

            # 获取设备名称（品牌 + 型号）
            name = f"{manufacturer} {model}".strip()

            # 获取Android API级别
            api_level = self._adb.get_device_property('ro.build.version.sdk', self.device_id)

            device_info = DeviceInfo(
                device_id=self.device_id,
                name=name,
                platform=Platform.ANDROID,
                model=model,
                os_version=f"Android {os_version} (API {api_level})",
                serial_number=serial,
                manufacturer=manufacturer,
                status=DeviceStatus.CONNECTED
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
            output = self._adb.shell('dumpsys battery', self.device_id, timeout=10)
            if not output:
                return None

            # 解析电池电量
            for line in output.split('\n'):
                if 'level:' in line.lower():
                    match = re.search(r'level:\s*(\d+)', line)
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

            result = self._adb.shell(f'pm uninstall {package_name}', self.device_id, timeout=60)
            return 'Success' in result

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
                cmd = f'am start -n {package_name}/{activity}'
            else:
                # 使用monkey命令启动应用
                cmd = f'monkey -p {package_name} -c android.intent.category.LAUNCHER 1'

            result = self._adb.shell(cmd, self.device_id, timeout=10)
            return result != "" or 'No activities found' not in result

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

            result = self._adb.shell(f'am force-stop {package_name}', self.device_id, timeout=10)
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

            output = self._adb.shell('dumpsys battery', self.device_id, timeout=10)
            if not output:
                return 0.0

            # 尝试获取温度
            for line in output.split('\n'):
                if 'temperature:' in line.lower():
                    match = re.search(r'temperature:\s*(\d+\.?\d*)', line)
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
            output = self._adb.shell('dumpsys connectivity', self.device_id, timeout=10)
            if not output:
                return "Unknown"

            # 解析网络类型
            if 'WIFI' in output.upper():
                return "Wi-Fi"
            elif 'MOBILE' in output.upper() or 'CELLULAR' in output.upper():
                # 检查是4G还是5G
                nr_output = self._adb.shell('getprop gsm.network.type', self.device_id, timeout=5)
                if 'NR' in nr_output or '5G' in nr_output:
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
                from insight_eyes.public.android.android_apm import AndroidAPM
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

            from insight_eyes.public.android.android_apm import AndroidAPM

            # 如果之前的 APM 存在且包名不同，先停止旧实例
            if self._apm is not None:
                try:
                    logger.debug(f"[APM管理] 停止旧 APM 实例: {self._apm.package_name}")
                    self._apm.stop()
                except Exception as e:
                    logger.warning(f"[APM管理] 停止旧 APM 失败: {e}")

            # 创建新的 APM 实例
            logger.debug(f"[APM管理] 创建新 APM 实例: package={package_name}, device={self.device_id}")
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
                logger.warning(f"电池采集返回空数据")
                return None

        except Exception as e:
            logger.error(f"采集电池数据失败: {e}")
            return None

    def cleanup(self):
        """
        清理设备适配器资源 - 修复版（正确等待APM线程停止）

        关键修复：
        1. 停止APM实例（包括FPS监控线程）
        2. 等待所有线程完全停止
        3. 清空APM实例
        """
        logger.info(f"开始清理Android设备适配器: {self.device_id}")

        try:
            # 步骤 1: 停止APM实例（包括FPS监控线程）
            if self._apm:
                try:
                    logger.debug("停止APM实例")
                    self._apm.stop()

                    # 步骤 2: 等待FPS线程完全停止（关键修复）
                    if hasattr(self._apm, 'fps_monitor') and self._apm.fps_monitor:
                        fps_monitor = self._apm.fps_monitor
                        if hasattr(fps_monitor, 'fpscollector'):
                            collector = fps_monitor.fpscollector

                            # 等待采集线程停止
                            if hasattr(collector, 'collector_thread') and collector.collector_thread:
                                if collector.collector_thread.is_alive():
                                    logger.debug("等待FPS采集线程停止...")
                                    collector.collector_thread.join(timeout=5.0)
                                    if collector.collector_thread.is_alive():
                                        logger.warning("FPS采集线程未能在5秒内停止")

                            # 等待计算线程停止
                            if hasattr(collector, 'calculator_thread') and collector.calculator_thread:
                                if collector.calculator_thread.is_alive():
                                    logger.debug("等待FPS计算线程停止...")
                                    collector.calculator_thread.join(timeout=5.0)
                                    if collector.calculator_thread.is_alive():
                                        logger.warning("FPS计算线程未能在5秒内停止")

                    logger.info("APM实例已停止")
                except Exception as e:
                    logger.warning(f"停止APM实例时出错: {e}")

            # 步骤 3: 清空APM实例
            self._apm = None

            logger.info(f"Android设备适配器已清理: {self.device_id}")

        except Exception as e:
            logger.error(f"清理Android设备适配器时出错: {e}")


class IOSDeviceAdapter(BaseDeviceAdapter):
    """
    iOS设备适配器
    通过tidevice与iOS设备通信

    性能优化（P2-20）：
    - 缓存 IOSAPM 实例，避免每次采集都创建新实例
    - 使用双重检查锁定模式管理 APM 实例
    """

    def __init__(self, device_id: str):
        """
        初始化iOS设备适配器（增强版）

        新增功能：
        - iOS 版本自动检测
        - 采集方案自动选择（py-ios-device / tidevice）
        - 连接生命周期管理
        - 优雅降级机制

        Args:
            device_id: iOS设备UDID
        """
        super().__init__(device_id)
        self._device_info_cache: Optional[Dict[str, Any]] = None

        # 新增：iOS 版本检测
        self._ios_version: Optional[str] = None

        # 新增：采集方案选择（自动检测）
        # 'tidevice': 使用 tidevice 采集（iOS < 17 或降级方案）
        # 'pyios': 使用 py-ios-device 采集（iOS 17+ 优化方案）
        self._collector_type: Literal['tidevice', 'pyios'] = 'tidevice'

        # APM 实例缓存（性能优化：避免每次采集都创建新实例）
        self._apm: Optional['IOSAPM'] = None
        self._apm_lock = threading.Lock()

        # 新增：py-ios-device 连接管理
        self._pyios_connection: Optional['PyIOSConnection'] = None
        self._pyios_lock = threading.Lock()
        self._pyios_remote_address: Optional[Tuple[str, int]] = None

        # 新增：隧道管理器（用于 iOS 17+）
        self._tunnel_manager: Optional['IOSTunnelManager'] = None

        # 新增：缓存当前监控的包名（用于 Battery/GPU 等系统级采集）
        self._current_package_name: Optional[str] = None

        self._check_tidevice()
        self._detect_ios_version_and_select_collector()

    def _get_apm(self, package_name: str) -> 'IOSAPM':
        """
        获取或创建 IOSAPM 实例（带缓存）

        性能优化（P2-20）：
        - 使用双重检查锁定模式
        - 复用同一包名的 APM 实例，避免重复初始化开销

        Args:
            package_name: Bundle ID

        Returns:
            IOSAPM: APM 实例
        """
        # 快速检查（无锁）：如果已有匹配的 APM 实例，直接返回
        if self._apm is not None and self._apm.bundleId == package_name:
            return self._apm

        # 慢速路径：创建新实例（带锁保护）
        with self._apm_lock:
            # 双重检查：在锁内再次检查，防止竞态条件
            if self._apm is not None and self._apm.bundleId == package_name:
                return self._apm

            # 创建新实例
            from insight_eyes.public.ios.ios_apm import IOSAPM
            logger.debug(f"[APM缓存] 创建新 IOSAPM 实例: bundle={package_name}, device={self.device_id}")
            self._apm = IOSAPM(package_name, self.device_id)
            return self._apm

    def _check_tidevice(self):
        """检查tidevice是否可用"""
        try:
            result = subprocess.run(
                ['tidevice', 'version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info(f"iOS设备适配器初始化成功: {self.device_id}")
            else:
                logger.warning("tidevice不可用")
        except Exception as e:
            logger.error(f"检查tidevice失败: {e}")

    def _detect_ios_version_and_select_collector(self):
        """
        检测 iOS 版本并选择最佳采集方案

        决策逻辑：
        1. 检测 iOS 版本（从设备信息获取）
        2. 检测 py-ios-device 可用性
        3. 如果 iOS >= 17 且有依赖 → 使用 py-ios-device
        4. 否则 → 使用 tidevice

        支持版本：
        - iOS 15-16: tidevice 方案
        - iOS 17-26: py-ios-device 方案（优先），tidevice（降级）
        """
        try:
            # 1. 获取 iOS 版本
            self._ios_version = self._get_ios_version()

            # 2. 检测依赖可用性
            has_pyios = self._check_pyios_device()

            # 3. 决策逻辑
            if self._ios_version and has_pyios:
                # 解析版本号
                try:
                    version_parts = self._ios_version.split('.')
                    major_version = int(version_parts[0])

                    # iOS 17+ 使用 py-ios-device
                    if major_version >= 17:
                        self._collector_type = 'pyios'
                        logger.info(f"[iOS适配器] ✓ iOS {self._ios_version} 检测到，使用 PyIOSDevice 方案（优化）")
                        return

                except (ValueError, IndexError):
                    logger.warning(f"[iOS适配器] 无法解析版本号: {self._ios_version}")

            # 默认使用 tidevice
            self._collector_type = 'tidevice'
            if self._ios_version:
                logger.info(f"[iOS适配器] iOS {self._ios_version} 检测到，使用 Tidevice 方案（标准）")
            else:
                logger.info(f"[iOS适配器] 无法检测版本，使用 Tidevice 方案（默认）")

        except Exception as e:
            logger.warning(f"[iOS适配器] 版本检测失败，使用 Tidevice 方案: {e}")
            self._collector_type = 'tidevice'

    def _get_ios_version(self) -> Optional[str]:
        """
        获取 iOS 设备版本号（带缓存优化）

        性能优化：避免重复调用 subprocess 命令

        Returns:
            str: iOS 版本号（如 "17.0"），失败返回 None
        """
        # 优先返回缓存值（避免重复调用外部命令）
        if self._ios_version:
            logger.debug(f"[iOS适配器] 使用缓存的 iOS 版本: {self._ios_version}")
            return self._ios_version

        try:
            # 从设备信息缓存获取
            if self._device_info_cache and 'version' in self._device_info_cache:
                version = self._device_info_cache['version']
                self._ios_version = version  # 更新缓存
                logger.debug(f"[iOS适配器] 从设备信息缓存获取 iOS 版本: {version}")
                return version

            # 通过 tidevice info 获取（仅当缓存为空时）
            logger.debug("[iOS适配器] 缓存未命中，调用 tidevice info 获取版本")
            result = subprocess.run(
                ['tidevice', '--udid', self.device_id, 'info'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                # 解析版本号（tidevice info 输出格式：ProductVersion: 17.0）
                for line in result.stdout.split('\n'):
                    if 'ProductVersion' in line or 'Version' in line:
                        match = re.search(r'(\d+\.\d+(?:\.\d+)?)', line)
                        if match:
                            version = match.group(1)
                            self._ios_version = version  # 更新缓存
                            logger.debug(f"[iOS适配器] 检测到 iOS 版本: {version} (已缓存)")
                            return version

            logger.debug("[iOS适配器] 无法从 tidevice info 获取版本")
            return None

        except Exception as e:
            logger.warning(f"[iOS适配器] 获取 iOS 版本失败: {e}")
            return None

    def _check_pyios_device(self) -> bool:
        """
        检查 py-ios-device 是否可用

        Returns:
            bool: py-ios-device 是否可用
        """
        try:
            from insight_eyes.public.ios.dependency_checker import IOSDependencyChecker
            return IOSDependencyChecker.check_pyios_device()
        except Exception as e:
            logger.debug(f"[iOS适配器] py-ios-device 检测失败: {e}")
            return False

    def _validate_data(self, data: Optional[Dict], data_type: str) -> bool:
        """
        验证数据有效性

        Args:
            data: 待验证的数据
            data_type: 数据类型（用于日志）

        Returns:
            bool: 数据是否有效
        """
        if not data:
            logger.debug(f"[iOS适配器] {data_type} 数据为空")
            return False

        if not isinstance(data, dict):
            logger.warning(f"[iOS适配器] {data_type} 数据格式错误: {type(data)}")
            return False

        # 根据数据类型进行特定验证
        if data_type == 'CPU':
            app_cpu = data.get('appCpuRate', 0)
            if app_cpu < 0 or app_cpu > 100:
                logger.warning(f"[iOS适配器] CPU 数据异常: appCpuRate={app_cpu}")
                return False

        elif data_type == 'Memory':
            total = data.get('totalPass', 0)
            if total < 0:
                logger.warning(f"[iOS适配器] Memory 数据异常: totalPass={total}")
                return False

        elif data_type == 'FPS':
            fps = data.get('fps', 0)
            if fps < 0 or fps > 120:
                logger.warning(f"[iOS适配器] FPS 数据异常: fps={fps}")
                return False

        return True

    def _execute_tidevice(self, args: List[str], timeout: int = 30) -> str:
        """
        执行tidevice命令

        Args:
            args: 命令参数列表
            timeout: 超时时间（秒）

        Returns:
            str: 命令输出
        """
        try:
            cmd = ['tidevice', '--udid', self.device_id] + args
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode == 0:
                return result.stdout
            else:
                logger.error(f"tidevice命令执行失败: {result.stderr}")
                return ""

        except subprocess.TimeoutExpired:
            logger.error(f"tidevice命令超时: {' '.join(args)}")
            return ""
        except Exception as e:
            logger.error(f"tidevice命令执行异常: {e}")
            return ""

    def connect(self) -> bool:
        """
        连接iOS设备

        Returns:
            bool: 是否连接成功
        """
        try:
            # 检查设备是否在列表中
            result = subprocess.run(
                ['tidevice', 'list', '--json'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                logger.error("获取iOS设备列表失败")
                return False

            devices = json.loads(result.stdout)
            for device in devices:
                if device.get('udid') == self.device_id:
                    self._device_info_cache = device
                    logger.info(f"iOS设备连接成功: {self.device_id}")
                    return True

            logger.error(f"未找到iOS设备: {self.device_id}")
            return False

        except Exception as e:
            logger.error(f"iOS设备连接异常: {e}")
            return False

    def disconnect(self) -> bool:
        """
        断开iOS设备连接

        Returns:
            bool: 是否断开成功
        """
        logger.info(f"iOS设备已断开: {self.device_id}")
        return True

    def is_connected(self) -> bool:
        """
        检查iOS设备是否连接

        Returns:
            bool: 是否已连接
        """
        try:
            result = subprocess.run(
                ['tidevice', 'list', '--json'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return False

            devices = json.loads(result.stdout)
            for device in devices:
                if device.get('udid') == self.device_id:
                    return True

            return False

        except Exception as e:
            logger.error(f"检查iOS设备连接状态失败: {e}")
            return False

    def get_device_info(self) -> Optional[DeviceInfo]:
        """
        获取iOS设备详细信息

        Returns:
            DeviceInfo: 设备信息
        """
        try:
            if not self._device_info_cache:
                if not self.connect():
                    return None

            info = self._device_info_cache

            device_info = DeviceInfo(
                device_id=self.device_id,
                name=info.get('name', 'Unknown iOS Device'),
                platform=Platform.IOS,
                model=info.get('model', 'Unknown'),
                os_version=info.get('version', 'Unknown'),
                serial_number=self.device_id,
                status=DeviceStatus.CONNECTED
            )

            # 获取电池电量
            battery_level = self._get_battery_info()
            if battery_level is not None:
                device_info.battery_level = battery_level

            self._device_info = device_info
            return device_info

        except Exception as e:
            logger.error(f"获取iOS设备信息失败: {e}")
            return None

    def _get_battery_info(self) -> Optional[int]:
        """
        获取iOS设备电池电量

        Returns:
            int: 电池电量百分比
        """
        try:
            # tidevice不直接提供电池信息，返回None
            # 可以通过其他方式获取，如安装instrument helpers
            return None

        except Exception as e:
            logger.error(f"获取iOS电池信息失败: {e}")
            return None

    def execute_command(self, command: str, timeout: int = 30) -> str:
        """
        在iOS设备上执行命令

        Args:
            command: 命令（iOS支持有限）
            timeout: 超时时间（秒）

        Returns:
            str: 命令输出
        """
        # iOS对命令执行限制较多，大多数命令不可用
        logger.warning("iOS设备不支持执行自定义命令")
        return ""

    def install_app(self, app_path: str) -> bool:
        """
        安装iOS应用（.ipa文件）

        Args:
            app_path: .ipa文件路径

        Returns:
            bool: 是否安装成功
        """
        try:
            result = self._execute_tidevice(['install', app_path], timeout=120)
            return 'Install' in result or 'Complete' in result

        except Exception as e:
            logger.error(f"安装iOS应用失败: {e}")
            return False

    def uninstall_app(self, package_name: str) -> bool:
        """
        卸载iOS应用

        Args:
            package_name: Bundle ID

        Returns:
            bool: 是否卸载成功
        """
        try:
            result = self._execute_tidevice(['uninstall', package_name], timeout=60)
            return 'Uninstall' in result or 'Complete' in result or result == ""

        except Exception as e:
            logger.error(f"卸载iOS应用失败: {e}")
            return False

    def start_app(self, package_name: str, activity: str = None) -> bool:
        """
        启动iOS应用

        Args:
            package_name: Bundle ID
            activity: 忽略（iOS不需要）

        Returns:
            bool: 是否启动成功
        """
        try:
            result = self._execute_tidevice(['launch', package_name], timeout=10)
            return result != "" or 'PID' in result

        except Exception as e:
            logger.error(f"启动iOS应用失败: {e}")
            return False

    def stop_app(self, package_name: str) -> bool:
        """
        停止iOS应用

        Args:
            package_name: Bundle ID

        Returns:
            bool: 是否停止成功
        """
        try:
            result = self._execute_tidevice(['kill', package_name], timeout=10)
            return True

        except Exception as e:
            logger.error(f"停止iOS应用失败: {e}")
            return False

    # ========== 性能指标采集实现 ==========

    def collect_fps(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        采集iOS应用的FPS数据（增强版：支持降级）

        Args:
            package_name: Bundle ID

        Returns:
            dict: FPS数据
        """
        # 缓存当前监控的包名（用于 Battery/GPU 等系统级采集）
        self._current_package_name = package_name

        # 尝试主方案
        if self._collector_type == 'pyios':
            try:
                data = self._collect_fps_pyios(package_name)
                if data and self._validate_data(data, 'FPS'):
                    return data
                logger.warning("[iOS适配器] PyIOS FPS 采集失败或数据无效，降级到 Tidevice")
            except Exception as e:
                logger.error(f"[iOS适配器] PyIOS FPS 采集异常: {e}，降级到 Tidevice")

        # 降级到 tidevice
        try:
            if self._collector_type == 'pyios':
                logger.info("[iOS适配器] → 降级到 Tidevice FPS 采集")
                self._collector_type = 'tidevice'

            data = self._collect_fps_tidevice(package_name)
            if data and self._validate_data(data, 'FPS'):
                return data

            logger.warning(f"[iOS适配器] Tidevice FPS 采集返回空数据: {package_name}")
            return None

        except Exception as e:
            logger.error(f"[iOS适配器] Tidevice FPS 采集失败: {e}")
            return None

    def _collect_fps_pyios(self, package_name: str) -> Optional[Dict[str, Any]]:
        """使用 py-ios-device 采集 FPS 数据"""
        try:
            if not self._pyios_connection or not self._pyios_connection.is_alive():
                logger.debug("[iOS适配器] PyIOS 连接不存在")
                return {'fps': 60, 'jank': 0, 'bigJank': 0, 'ftime_avg': 16.67, 'ftime_max': 20.0, 'ftime_min': 16.0}

            fps_data = self._pyios_connection.collect_fps(package_name)
            return fps_data

        except Exception as e:
            logger.error(f"[iOS适配器] PyIOS FPS 采集异常: {e}")
            return None

    def _collect_fps_tidevice(self, package_name: str) -> Optional[Dict[str, Any]]:
        """使用 tidevice 采集 FPS 数据"""
        try:
            apm = self._get_apm(package_name)
            fps_data = apm.collectFps()

            if fps_data:
                logger.debug(f"[Tidevice采集] FPS 采集成功: {fps_data.get('fps', 0)}")
                return fps_data
            else:
                logger.warning(f"[Tidevice采集] FPS 采集返回空数据: {package_name}")
                return None

        except Exception as e:
            logger.error(f"[Tidevice采集] FPS 采集失败: {e}")
            return None

    def collect_memory(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        采集iOS应用的内存数据（增强版：支持降级）

        Args:
            package_name: Bundle ID

        Returns:
            dict: 内存数据（单位MB）{'totalPass': float, 'nativePass': float, 'dalvikPass': float}
        """
        # 缓存当前监控的包名（用于 Battery/GPU 等系统级采集）
        self._current_package_name = package_name

        # 尝试主方案
        if self._collector_type == 'pyios':
            try:
                data = self._collect_memory_pyios(package_name)
                if data and self._validate_data(data, 'Memory'):
                    return data
                logger.warning("[iOS适配器] PyIOS Memory 采集失败或数据无效，降级到 Tidevice")
            except Exception as e:
                logger.error(f"[iOS适配器] PyIOS Memory 采集异常: {e}，降级到 Tidevice")

        # 降级到 tidevice
        try:
            if self._collector_type == 'pyios':
                logger.info("[iOS适配器] → 降级到 Tidevice Memory 采集")
                self._collector_type = 'tidevice'

            data = self._collect_memory_tidevice(package_name)
            if data and self._validate_data(data, 'Memory'):
                return data

            logger.warning(f"[iOS适配器] Tidevice Memory 采集返回空数据: {package_name}")
            return None

        except Exception as e:
            logger.error(f"[iOS适配器] Tidevice Memory 采集失败: {e}")
            return None

    def _collect_memory_pyios(self, package_name: str) -> Optional[Dict[str, Any]]:
        """使用 py-ios-device 采集 Memory 数据"""
        try:
            if not self._pyios_connection or not self._pyios_connection.is_alive():
                logger.debug("[iOS适配器] PyIOS 连接不存在")
                return {'totalPass': 0, 'nativePass': 0, 'dalvikPass': 0}

            mem_data = self._pyios_connection.collect_memory(package_name)
            return mem_data

        except Exception as e:
            logger.error(f"[iOS适配器] PyIOS Memory 采集异常: {e}")
            return None

    def _collect_memory_tidevice(self, package_name: str) -> Optional[Dict[str, Any]]:
        """使用 tidevice 采集 Memory 数据"""
        try:
            apm = self._get_apm(package_name)
            memory_data = apm.collectMemory()

            if memory_data:
                logger.debug(f"[Tidevice采集] Memory 采集成功: {memory_data.get('totalPass', 0)} MB")
                return memory_data
            else:
                logger.warning(f"[Tidevice采集] Memory 采集返回空数据: {package_name}")
                return None

        except Exception as e:
            logger.error(f"[Tidevice采集] Memory 采集失败: {e}")
            return None

    def collect_cpu(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        采集iOS应用的CPU数据（增强版：支持降级）

        采集流程：
        1. 如果选择 pyios 方案，尝试使用 py-ios-device
        2. 如果失败或数据无效，自动降级到 tidevice
        3. 验证数据有效性后返回

        Args:
            package_name: Bundle ID

        Returns:
            dict: CPU数据（百分比）{'appCpuRate': float, 'sysCpuRate': float}
        """
        # 缓存当前监控的包名（用于 Battery/GPU 等系统级采集）
        self._current_package_name = package_name

        # 尝试主方案
        if self._collector_type == 'pyios':
            try:
                data = self._collect_cpu_pyios(package_name)
                if data and self._validate_data(data, 'CPU'):
                    return data
                logger.warning("[iOS适配器] PyIOS CPU 采集失败或数据无效，降级到 Tidevice")
            except Exception as e:
                logger.error(f"[iOS适配器] PyIOS CPU 采集异常: {e}，降级到 Tidevice")

        # 降级到 tidevice（如果 pyios 失败或本身就是 tidevice）
        try:
            # 标记降级（如果是从 pyios 降级）
            if self._collector_type == 'pyios':
                logger.info("[iOS适配器] → 降级到 Tidevice CPU 采集")
                self._collector_type = 'tidevice'  # 持久化降级决策

            data = self._collect_cpu_tidevice(package_name)
            if data and self._validate_data(data, 'CPU'):
                return data

            logger.warning(f"[iOS适配器] Tidevice CPU 采集返回空数据: {package_name}")
            return None

        except Exception as e:
            logger.error(f"[iOS适配器] Tidevice CPU 采集失败: {e}")
            return None

    def _collect_cpu_pyios(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        使用 py-ios-device 采集 CPU 数据

        Args:
            package_name: Bundle ID

        Returns:
            dict: CPU 数据
        """
        try:
            # 确保隧道启动（iOS 17+ 需要）
            if not self._ensure_tunnel():
                logger.warning("[iOS适配器] 隧道启动失败，无法采集数据")
                return {'appCpuRate': 0.0, 'sysCpuRate': 0.0}

            # 确保连接存在
            if not self._pyios_connection or not self._pyios_connection.is_alive():
                logger.debug("[iOS适配器] PyIOS 连接不存在，需要建立连接")

                # 创建新的连接（使用隧道地址）
                if not self._pyios_remote_address:
                    logger.warning("[iOS适配器] 无法获取隧道地址")
                    return {'appCpuRate': 0.0, 'sysCpuRate': 0.0}

                from insight_eyes.public.ios.pyios_connect import PyIOSConnection
                self._pyios_connection = PyIOSConnection(
                    self.device_id,
                    self._pyios_remote_address
                )

                if not self._pyios_connection.connect():
                    logger.warning("[iOS适配器] PyIOS 连接建立失败")
                    return {'appCpuRate': 0.0, 'sysCpuRate': 0.0}

            # 使用连接采集数据
            cpu_data = self._pyios_connection.collect_cpu(package_name)
            return cpu_data

        except Exception as e:
            logger.error(f"[iOS适配器] PyIOS CPU 采集异常: {e}")
            return None

    def _collect_cpu_tidevice(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        使用 tidevice 采集 CPU 数据（原有实现）

        Args:
            package_name: Bundle ID

        Returns:
            dict: CPU 数据
        """
        try:
            # 使用缓存的 IOSAPM 实例（性能优化）
            apm = self._get_apm(package_name)
            cpu_data = apm.collectCpu()

            if cpu_data:
                logger.debug(f"[Tidevice采集] CPU 采集成功: {cpu_data.get('appCpuRate', 0)}%")
                return cpu_data
            else:
                logger.warning(f"[Tidevice采集] CPU 采集返回空数据: {package_name}")
                return None

        except Exception as e:
            logger.error(f"[Tidevice采集] CPU 采集失败: {e}")
            return None

    def collect_network(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        采集iOS应用的网络数据（增强版：支持降级）
        注意：iOS网络采集支持有限

        Args:
            package_name: Bundle ID

        Returns:
            dict: 网络数据（可能返回空或0）{'upFlow': float, 'downFlow': float}
        """
        # 缓存当前监控的包名（用于 Battery/GPU 等系统级采集）
        self._current_package_name = package_name

        # 尝试主方案
        if self._collector_type == 'pyios':
            try:
                data = self._collect_network_pyios(package_name)
                if data is not None:  # Network 可能为 0，所以用 is not None
                    return data
                logger.warning("[iOS适配器] PyIOS Network 采集失败，降级到 Tidevice")
            except Exception as e:
                logger.error(f"[iOS适配器] PyIOS Network 采集异常: {e}，降级到 Tidevice")

        # 降级到 tidevice
        try:
            if self._collector_type == 'pyios':
                logger.info("[iOS适配器] → 降级到 Tidevice Network 采集")
                self._collector_type = 'tidevice'

            data = self._collect_network_tidevice(package_name)
            return data

        except Exception as e:
            logger.error(f"[iOS适配器] Tidevice Network 采集失败: {e}")
            return None

    def _collect_network_pyios(self, package_name: str) -> Optional[Dict[str, Any]]:
        """使用 py-ios-device 采集 Network 数据"""
        try:
            if not self._pyios_connection or not self._pyios_connection.is_alive():
                logger.debug("[iOS适配器] PyIOS 连接不存在")
                return {'upFlow': 0, 'downFlow': 0}

            net_data = self._pyios_connection.collect_network(package_name)
            return net_data

        except Exception as e:
            logger.error(f"[iOS适配器] PyIOS Network 采集异常: {e}")
            return None

    def _collect_network_tidevice(self, package_name: str) -> Optional[Dict[str, Any]]:
        """使用 tidevice 采集 Network 数据"""
        try:
            apm = self._get_apm(package_name)
            network_data = apm.collectFlow()

            if network_data:
                logger.debug(f"[Tidevice采集] Network 采集成功")
                return network_data
            else:
                logger.warning(f"[Tidevice采集] Network 采集返回空数据: {package_name}")
                return None

        except Exception as e:
            logger.error(f"[Tidevice采集] Network 采集失败: {e}")
            return None

    def collect_battery(self) -> Optional[Dict[str, Any]]:
        """
        采集iOS设备的电池数据（增强版：支持降级）
        注意：iOS电池采集支持有限

        Returns:
            dict: 电池数据
        """
        # 尝试主方案
        if self._collector_type == 'pyios':
            try:
                data = self._collect_battery_pyios()
                if data is not None:
                    return data
                logger.warning("[iOS适配器] PyIOS Battery 采集失败，降级到 Tidevice")
            except Exception as e:
                logger.error(f"[iOS适配器] PyIOS Battery 采集异常: {e}，降级到 Tidevice")

        # 降级到 tidevice
        try:
            if self._collector_type == 'pyios':
                logger.info("[iOS适配器] → 降级到 Tidevice Battery 采集")
                self._collector_type = 'tidevice'

            data = self._collect_battery_tidevice()
            return data

        except Exception as e:
            logger.error(f"[iOS适配器] Tidevice Battery 采集失败: {e}")
            return None

    def _collect_battery_pyios(self) -> Optional[Dict[str, Any]]:
        """使用 py-ios-device 采集 Battery 数据"""
        try:
            if not self._pyios_connection or not self._pyios_connection.is_alive():
                logger.debug("[iOS适配器] PyIOS 连接不存在")
                return {'level': 0, 'temperature': 0, 'current': 0, 'voltage': 0, 'power': 0, 'status': 'unknown'}

            # 使用缓存的包名（如果有的话）
            bundle_id = self._current_package_name or "com.apple.Preferences"

            battery_data = self._pyios_connection.collect_battery(bundle_id)
            return battery_data if battery_data else {'level': 0, 'temperature': 0, 'current': 0, 'voltage': 0, 'power': 0, 'status': 'unknown'}

        except Exception as e:
            logger.error(f"[iOS适配器] PyIOS Battery 采集异常: {e}")
            return None

    def _collect_battery_tidevice(self) -> Optional[Dict[str, Any]]:
        """使用 tidevice 采集 Battery 数据"""
        try:
            # 电池采集不需要包名，使用现有的缓存实例或创建新实例
            if self._apm is None:
                from insight_eyes.public.ios.ios_apm import IOSAPM
                self._apm = IOSAPM("", self.device_id)

            battery_data = self._apm.collectBattery()

            if battery_data:
                logger.debug(f"[Tidevice采集] Battery 采集成功: {battery_data.get('level', 0)}%")
                return battery_data
            else:
                logger.warning(f"[Tidevice采集] Battery 采集返回空数据")
                return None

        except Exception as e:
            logger.error(f"[Tidevice采集] Battery 采集失败: {e}")
            return None

    def collect_gpu(self) -> Optional[Dict[str, Any]]:
        """
        采集iOS设备的GPU数据

        注意：iOS GPU 采集支持有限，通常返回默认值

        Returns:
            dict: GPU数据 {'gpu': int, 'gpu_freq': int, 'gpu_vendor': str, 'gpu_model': str}
        """
        # 尝试使用 py-ios-device
        if self._collector_type == 'pyios':
            try:
                data = self._collect_gpu_pyios()
                if data is not None:
                    return data
                logger.warning("[iOS适配器] PyIOS GPU 采集失败，使用默认值")
            except Exception as e:
                logger.error(f"[iOS适配器] PyIOS GPU 采集异常: {e}")

        # 返回默认值（iOS GPU 采集支持有限）
        return {'gpu': 0, 'gpu_freq': 0, 'gpu_vendor': 'apple', 'gpu_model': 'Apple GPU'}

    def _collect_gpu_pyios(self) -> Optional[Dict[str, Any]]:
        """使用 py-ios-device 采集 GPU 数据"""
        try:
            if not self._pyios_connection or not self._pyios_connection.is_alive():
                logger.debug("[iOS适配器] PyIOS 连接不存在")
                return {'gpu': 0, 'gpu_freq': 0, 'gpu_vendor': 'apple', 'gpu_model': 'Apple GPU'}

            # 使用缓存的包名（如果有的话）
            bundle_id = self._current_package_name or "com.apple.Preferences"

            gpu_data = self._pyios_connection.collect_gpu(bundle_id)
            return gpu_data if gpu_data else {'gpu': 0, 'gpu_freq': 0, 'gpu_vendor': 'apple', 'gpu_model': 'Apple GPU'}

        except Exception as e:
            logger.error(f"[iOS适配器] PyIOS GPU 采集异常: {e}")
            return None

    def _ensure_tunnel(self) -> bool:
        """
        确保隧道启动（iOS 17+ 需要）

        Returns:
            bool: 隧道是否可用
        """
        # 只有 iOS 17+ 且使用 py-ios-device 时才需要隧道
        if not self._ios_version:
            return True  # 无法检测版本，假设不需要

        try:
            major_version = int(self._ios_version.split('.')[0])
            if major_version < 17:
                return True  # iOS 17 以下不需要隧道
        except:
            return True

        # 检查是否已有运行中的隧道
        if self._tunnel_manager and self._tunnel_manager.is_running():
            return True

        # 启动新隧道
        logger.info(f"[iOS隧道] 正在启动隧道: {self.device_id}")
        return self._start_tunnel()

    def _start_tunnel(self) -> bool:
        """
        启动远程隧道

        Returns:
            bool: 是否启动成功
        """
        try:
            from insight_eyes.public.ios.tunnel_manager import IOSTunnelManager

            self._tunnel_manager = IOSTunnelManager(self.device_id)

            if self._tunnel_manager.start_tunnel():
                remote_address = self._tunnel_manager.get_remote_address()
                if remote_address:
                    self._pyios_remote_address = remote_address
                    logger.info(f"[iOS隧道] ✓ 隧道启动成功: {remote_address}")
                    return True

            logger.error("[iOS隧道] ✗ 隧道启动失败")
            return False

        except Exception as e:
            logger.error(f"[iOS隧道] 启动隧道异常: {e}")
            return False

    def _stop_tunnel(self):
        """停止远程隧道"""
        if self._tunnel_manager:
            try:
                self._tunnel_manager.stop_tunnel()
                logger.debug("[iOS隧道] 隧道已停止")
            except Exception as e:
                logger.warning(f"[iOS隧道] 停止隧道失败: {e}")
            finally:
                self._tunnel_manager = None
                self._pyios_remote_address = None

    def cleanup(self):
        """
        清理iOS设备适配器资源（增强版）

        清理内容：
        1. 停止 APM 实例
        2. 停止远程隧道
        3. 断开 py-ios-device 连接
        4. 清理所有缓存
        """
        logger.info(f"[iOS适配器] 开始清理资源: {self.device_id}")

        try:
            # 1. 清理 APM 实例
            if self._apm:
                try:
                    self._apm.stop()
                    logger.debug("[iOS适配器] APM 实例已停止")
                except Exception as e:
                    logger.warning(f"[iOS适配器] 停止 APM 失败: {e}")
                finally:
                    self._apm = None

            # 2. 停止远程隧道
            self._stop_tunnel()

            # 3. 清理 py-ios-device 连接
            if self._pyios_connection:
                try:
                    self._pyios_connection.disconnect()
                    logger.debug("[iOS适配器] PyIOS 连接已断开")
                except Exception as e:
                    logger.warning(f"[iOS适配器] 断开 PyIOS 连接失败: {e}")
                finally:
                    self._pyios_connection = None

            logger.info(f"[iOS适配器] ✓ 资源清理完成: {self.device_id}")

        except Exception as e:
            logger.error(f"[iOS适配器] 清理资源时出错: {e}")


class DeviceAdapterFactory:
    """
    设备适配器工厂
    根据平台创建对应的设备适配器
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
        logger.debug(f"create_adapter 被调用: device_id={device_id}, platform={platform}, platform类型={type(platform)}, platform值={platform.value if hasattr(platform, 'value') else platform}")

        # 比较枚举值而不是枚举本身
        if hasattr(platform, 'value'):
            platform_value = platform.value
        else:
            platform_value = str(platform)

        if platform_value == "Android":
            return AndroidDeviceAdapter(device_id)
        elif platform_value == "iOS":
            return IOSDeviceAdapter(device_id)
        else:
            logger.error(f"不支持的平台: {platform} (值: {platform_value})")
            return None
