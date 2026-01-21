# -*- coding: utf-8 -*-
"""
iOS PyiOSDevice 采集器

基于 py-ios-device 的 PyiOSDevice API 实现性能数据采集。

设计：
- 持久连接：监控会话期间保持连接开启
- 回调缓存：数据持续推送到回调，缓存最新数据
- 同步查询：提供 collect*() 方法从缓存获取数据
"""
import time
import threading
from typing import Optional, Dict, Any
from logzero import logger


class IOSPyDeviceCollector:
    """
    iOS PyiOSDevice 采集器

    使用 py-ios-device 的 PyiOSDevice API 实现性能数据采集。

    使用示例：
    ```python
    collector = IOSPyDeviceCollector(udid='device_udid', bundle_id='com.app')

    # 启动监控
    collector.start()

    # 采集数据
    cpu = collector.collect_cpu()
    memory = collector.collect_memory()

    # 停止监控
    collector.stop()
    ```
    """

    def __init__(self, udid: str, bundle_id: str):
        """
        初始化采集器

        Args:
            udid: iOS 设备 UDID
            bundle_id: 应用 Bundle ID
        """
        self.udid = udid
        self.bundle_id = bundle_id
        self._device = None
        self._is_started = False
        self._data_lock = threading.RLock()

        # 数据缓存
        self._cached_data = {}
        self._last_update = {}

        logger.info(f"[iOS采集器] 初始化: UDID={udid}, BundleID={bundle_id}")

    def start(self) -> bool:
        """
        启动监控（建立连接并启动服务）

        Returns:
            bool: 是否启动成功
        """
        with self._data_lock:
            if self._is_started:
                logger.debug("[iOS采集器] 已经启动，跳过")
                return True

            try:
                from ios_device.py_ios_device import PyiOSDevice

                logger.info(f"[iOS采集器] 正在连接设备: {self.udid}")
                self._device = PyiOSDevice(device_id=self.udid)

                # 启动系统监控（CPU、Memory、Network）
                self._device.start_get_system(callback=self._on_system_data)
                logger.info("[iOS采集器] ✓ 系统监控已启动")

                # 启动 FPS 监控
                self._device.start_get_fps(callback=self._on_fps_data)
                logger.info("[iOS采集器] ✓ FPS 监控已启动")

                self._is_started = True
                logger.info("[iOS采集器] ✓ 监控已启动")

                # 等待首次数据
                self._wait_for_initial_data()

                return True

            except ImportError:
                logger.error("[iOS采集器] ✗ 依赖库缺失: 请安装 py-ios-device")
                return False
            except Exception as e:
                logger.error(f"[iOS采集器] ✗ 启动失败: {e}")
                import traceback
                logger.debug(traceback.format_exc())
                return False

    def _wait_for_initial_data(self, timeout: float = 5.0):
        """等待初始数据生成"""
        logger.debug(f"[iOS采集器] 等待初始数据... (超时={timeout}秒)")
        start = time.time()

        while time.time() - start < timeout:
            with self._data_lock:
                if 'system' in self._cached_data:
                    logger.info("[iOS采集器] ✓ 初始数据已生成")
                    return

            time.sleep(0.2)

        logger.warning(f"[iOS采集器] 等待初始数据超时 ({timeout}秒)")

    def _on_system_data(self, res):
        """
        系统数据回调

        Args:
            res: py-ios-device 返回的数据对象
                res.selector 是列表，包含系统性能数据
        """
        try:
            if hasattr(res, 'selector') and isinstance(res.selector, list):
                with self._data_lock:
                    self._cached_data['system'] = res.selector
                    self._last_update['system'] = time.time()

                    # 打印调试信息（首次）
                    elem0 = res.selector[0] if len(res.selector) > 0 else {}
                    if 'Processes' in elem0:
                        proc_count = len(elem0['Processes'])
                        logger.debug(f"[iOS采集器] ✓ 收到系统数据 (进程数: {proc_count})")
        except Exception as e:
            logger.debug(f"[iOS采集器] 处理系统数据回调失败: {e}")

    def _on_fps_data(self, res):
        """
        FPS 数据回调

        Args:
            res: py-ios-device 返回的数据对象
        """
        try:
            if hasattr(res, 'selector'):
                with self._data_lock:
                    self._cached_data['fps'] = res.selector
                    self._last_update['fps'] = time.time()

                    if res.selector:
                        fps = res.selector.get('fps', 0)
                        logger.debug(f"[iOS采集器] ✓ 收到 FPS 数据: {fps}")
        except Exception as e:
            logger.debug(f"[iOS采集器] 处理 FPS 数据回调失败: {e}")

    def stop(self):
        """停止监控（停止服务并关闭连接）"""
        with self._data_lock:
            if not self._is_started:
                return

            if self._device:
                try:
                    logger.info("[iOS采集器] 正在停止监控...")

                    # 停止 FPS 监控
                    try:
                        self._device.stop_get_fps()
                    except Exception as e:
                        logger.debug(f"[iOS采集器] 停止 FPS 监控失败: {e}")

                    # 停止系统监控
                    try:
                        self._device.stop_get_system()
                    except Exception as e:
                        logger.debug(f"[iOS采集器] 停止系统监控失败: {e}")

                    # 停止设备
                    self._device.stop()

                    logger.info("[iOS采集器] ✓ 监控已停止")
                except Exception as e:
                    logger.warning(f"[iOS采集器] 停止监控失败: {e}")

            self._is_started = False
            self._device = None

            # 清除缓存
            self._cached_data.clear()
            self._last_update.clear()

    def _get_cached_data(self, key: str, max_age: float = 3.0) -> Optional[Any]:
        """
        获取缓存数据（带超时检查）

        Args:
            key: 数据键 ('system', 'fps')
            max_age: 最大有效时间（秒）

        Returns:
            缓存的数据，过期或无效返回 None
        """
        with self._data_lock:
            data = self._cached_data.get(key)
            last_time = self._last_update.get(key, 0)
            age = time.time() - last_time

            if age > max_age:
                logger.debug(f"[iOS采集器] 数据过期 [{key}]: age={age:.1f}s > max={max_age}s")
                return None

            return data

    def collect_cpu(self) -> Optional[Dict[str, float]]:
        """
        采集 CPU 数据

        Returns:
            dict: {'appCpuRate': float, 'sysCpuRate': float} 或 None
        """
        try:
            data = self._get_cached_data('system', max_age=3.0)
            if not data:
                return None

            return self._extract_cpu(data, self.bundle_id)
        except Exception as e:
            logger.error(f"[iOS采集器] CPU 采集失败: {e}")
            return None

    def _extract_cpu(self, data: list, bundle_id: str) -> Dict[str, float]:
        """
        从系统数据中提取 CPU 信息

        Args:
            data: 系统数据列表
            bundle_id: 应用 Bundle ID

        Returns:
            dict: {'appCpuRate': float, 'sysCpuRate': float}
        """
        app_cpu = 0.0
        sys_cpu = 0.0

        try:
            if isinstance(data, list) and len(data) > 0:
                elem0 = data[0]

                # 获取应用 CPU 使用率
                if 'Processes' in elem0:
                    processes = elem0['Processes']
                    for pid, proc_data in processes.items():
                        if isinstance(proc_data, list):
                            # proc_data 格式: [pid, name, cpuUsage, physFootprint, ...]
                            if len(proc_data) >= 3:
                                proc_name = proc_data[1]  # name
                                cpu_usage = proc_data[2]   # cpuUsage

                                # 匹配应用名称
                                if bundle_id.split('.')[0].lower() in str(proc_name).lower():
                                    # cpuUsage 是小数（0-1），转换为百分比
                                    app_cpu = float(cpu_usage) * 100
                                    break

        except Exception as e:
            logger.debug(f"[iOS采集器] 解析 CPU 数据失败: {e}")

        return {
            'appCpuRate': round(app_cpu, 2),
            'sysCpuRate': round(sys_cpu, 2)
        }

    def collect_memory(self) -> Optional[Dict[str, float]]:
        """
        采集内存数据

        Returns:
            dict: {'totalPass': float, 'nativePass': float, 'dalvikPass': float}
        """
        try:
            data = self._get_cached_data('system', max_age=3.0)
            if not data:
                return None

            return self._extract_memory(data, self.bundle_id)
        except Exception as e:
            logger.error(f"[iOS采集器] Memory 采集失败: {e}")
            return None

    def _extract_memory(self, data: list, bundle_id: str) -> Dict[str, float]:
        """
        从系统数据中提取内存信息

        Args:
            data: 系统数据列表
            bundle_id: 应用 Bundle ID

        Returns:
            dict: {'totalPass': float, 'nativePass': float, 'dalvikPass': float}
        """
        total_mb = 0.0
        native_mb = 0.0

        try:
            if isinstance(data, list) and len(data) > 0:
                elem0 = data[0]

                if 'Processes' in elem0:
                    processes = elem0['Processes']
                    for pid, proc_data in processes.items():
                        if isinstance(proc_data, list):
                            # proc_data 格式: [pid, name, cpuUsage, physFootprint, ...]
                            if len(proc_data) >= 5:
                                proc_name = proc_data[1]  # name
                                footprint = proc_data[4]   # physFootprint (bytes)

                                # 匹配应用名称
                                if bundle_id.split('.')[0].lower() in str(proc_name).lower():
                                    # 转换为 MB
                                    total_mb = float(footprint) / (1024 * 1024)
                                    native_mb = total_mb
                                    break

        except Exception as e:
            logger.debug(f"[iOS采集器] 解析 Memory 数据失败: {e}")

        return {
            'totalPass': round(total_mb, 2),
            'nativePass': round(native_mb, 2),
            'dalvikPass': 0.0  # iOS 没有 Dalvik
        }

    def collect_fps(self) -> Optional[Dict[str, Any]]:
        """
        采集 FPS 数据

        Returns:
            dict: {'fps': int} 或 None
        """
        try:
            data = self._get_cached_data('fps', max_age=3.0)
            if not data:
                return None

            # FPS 数据格式: {'currentTime': str, 'fps': int}
            fps = data.get('fps', 0)
            return {'fps': int(fps)}
        except Exception as e:
            logger.error(f"[iOS采集器] FPS 采集失败: {e}")
            return None

    def collect_network(self) -> Optional[Dict[str, float]]:
        """
        采集网络数据

        Returns:
            dict: {'upFlow': float, 'downFlow': float}
        """
        try:
            # iOS 网络数据需要单独监控（暂时返回默认值）
            return {'upFlow': 0.0, 'downFlow': 0.0}
        except Exception as e:
            logger.error(f"[iOS采集器] Network 采集失败: {e}")
            return None

    def collect_battery(self) -> Optional[Dict[str, Any]]:
        """
        采集电池数据

        Returns:
            dict: {'level': int, 'temperature': float, 'current': float}
        """
        try:
            # iOS 电池数据需要单独获取（暂时返回默认值）
            return {'level': 100, 'temperature': 25.0, 'current': 0.0}
        except Exception as e:
            logger.error(f"[iOS采集器] Battery 采集失败: {e}")
            return None
