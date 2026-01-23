# -*- coding: utf-8 -*-
"""
iOS Sysmon 服务（使用 pymobiledevice3 Python API）

直接使用 pymobiledevice3 的 DVT 协议，而不是通过 CLI 调用。
这样可以建立持久连接，大幅提升性能。
"""

import threading
import time
from typing import Dict, List, Optional
from logzero import logger


class SysmonService:
    """
    iOS Sysmon 服务

    使用 pymobiledevice3 Python API 直接连接 DVT 协议，
    提供高性能的进程监控数据采集。
    """

    _instance_lock = threading.Lock()
    _instances: Dict[str, 'SysmonService'] = {}

    def __init__(self, udid: Optional[str] = None):
        """
        初始化 Sysmon 服务

        Args:
            udid: iOS 设备唯一标识符
        """
        self.udid = udid
        self._lock = threading.Lock()
        self._dvt = None
        self._sysmon = None
        self._sysmon_tap = None  # 保存 sysmon tap 实例
        self._process_cache: Optional[List[Dict]] = None
        self._cache_time: Optional[float] = None
        self._cache_ttl = 0.5  # 0.5秒缓存（平衡性能和实时性）
        self._connected = False

    @classmethod
    def get_instance(cls, udid: Optional[str] = None) -> 'SysmonService':
        """
        获取 Sysmon 服务实例（单例模式）

        Args:
            udid: iOS 设备唯一标识符

        Returns:
            SysmonService 实例
        """
        device_key = udid or 'default'

        with cls._instance_lock:
            if device_key not in cls._instances:
                cls._instances[device_key] = cls(udid)
            return cls._instances[device_key]

    def connect(self) -> bool:
        """
        建立到设备的 DVT 连接

        Returns:
            bool: 是否连接成功
        """
        with self._lock:
            if self._connected:
                return True

            try:
                from pymobiledevice3.lockdown import create_using_usbmux
                from pymobiledevice3.services.dvt.dvt_secure_socket_proxy import DvtSecureSocketProxyService

                logger.debug("===== SysmonService: 建立 DVT 连接 =====")
                logger.debug(f"设备 UDID: {self.udid or '默认'}")

                # 创建 lockdown 连接
                if self.udid:
                    lockdown = create_using_usbmux(self.udid)
                else:
                    lockdown = create_using_usbmux()

                # 创建 DVT 服务
                self._dvt = DvtSecureSocketProxyService(lockdown)
                self._dvt.perform_handshake()

                self._connected = True
                logger.debug("✓ DVT 连接建立成功")

                return True

            except ImportError as e:
                logger.error(f"✗ 导入 pymobiledevice3 失败: {e}")
                return False
            except Exception as e:
                logger.error(f"✗ 建立 DVT 连接失败: {type(e).__name__}: {e}")
                self._cleanup()
                return False

    def _cleanup(self):
        """清理资源"""
        try:
            if self._sysmon_tap:
                # Sysmontap 使用 context manager，会自动清理
                self._sysmon_tap = None
            if self._dvt:
                self._dvt.close()
                self._dvt = None
        except Exception as e:
            logger.debug(f"清理资源时出错: {e}")
        finally:
            self._connected = False
            self._process_cache = None
            self._cache_time = None

    def disconnect(self):
        """断开连接"""
        with self._lock:
            self._cleanup()
            logger.debug("SysmonService 连接已断开")

    def get_processes(self, force_refresh: bool = False) -> Optional[List[Dict]]:
        """
        获取所有进程列表

        Args:
            force_refresh: 是否强制刷新缓存

        Returns:
            进程列表，每个进程包含 pid, name, cpuUsage, physFootprint 等字段
        """
        # 检查缓存
        current_time = time.time()
        if (not force_refresh and
            self._process_cache is not None and
            self._cache_time is not None and
            current_time - self._cache_time < self._cache_ttl):
            return self._process_cache

        with self._lock:
            try:
                # 确保已连接
                if not self._connected:
                    logger.debug("[get_processes] 尝试连接...")
                    if not self.connect():
                        logger.warning("[get_processes] 连接失败，使用缓存")
                        return self._process_cache

                logger.debug("===== SysmonService: 获取进程列表 =====")

                # 从 sysmon 流中读取一次数据
                processes = []
                try:
                    from pymobiledevice3.services.dvt.instruments.sysmontap import Sysmontap

                    # 设置 socket 超时避免阻塞
                    import socket
                    old_timeout = socket.getdefaulttimeout()
                    socket.setdefaulttimeout(3)  # 3 秒超时
                    
                    try:
                        with Sysmontap(self._dvt) as sysmon_tap:
                            # 使用 iter_processes 获取进程
                            for process_list in sysmon_tap.iter_processes():
                                processes.extend(process_list)
                                # 只读取第一批数据就退出（避免阻塞）
                                break
                    finally:
                        socket.setdefaulttimeout(old_timeout)  # 恢复默认超时

                except socket.timeout:
                    logger.warning("[get_processes] Socket 超时，使用缓存")
                    return self._process_cache if self._process_cache else None
                except Exception as iter_error:
                    error_str = str(iter_error)
                    if "10054" in error_str or "连接" in error_str:
                        logger.warning(f"[get_processes] 连接断开: {iter_error}，标记为未连接")
                        self._connected = False
                    logger.warning(f"从 DVT 流读取进程失败: {iter_error}")
                    # 如果有缓存，返回缓存（即使过期）
                    if self._process_cache:
                        logger.info("[get_processes] 使用过期缓存")
                        return self._process_cache
                    return None

                if processes:
                    # 转换为统一格式
                    result = []
                    for proc in processes:
                        result.append({
                            'pid': proc.get('pid'),
                            'name': proc.get('name', ''),
                            'cpuUsage': proc.get('cpuUsage', 0.0),
                            'physFootprint': proc.get('physFootprint', 0),
                            'memResidentSize': proc.get('memResidentSize', 0),
                            'execName': proc.get('execName', ''),
                            'comm': proc.get('comm', '')
                        })

                    # 更新缓存
                    self._process_cache = result
                    self._cache_time = current_time

                    logger.debug(f"✓ 获取到 {len(result)} 个进程")
                    return result
                else:
                    logger.warning("未获取到进程数据")
                    # 返回缓存（如果存在）
                    return self._process_cache if self._process_cache else None

            except Exception as e:
                logger.error(f"✗ 获取进程列表失败: {type(e).__name__}: {e}")
                # 连接可能已断开，标记为未连接
                self._connected = False
                # 返回缓存（如果存在）
                return self._process_cache if self._process_cache else None

    def get_process_by_bundle_id(self, bundle_id: str) -> Optional[Dict]:
        """
        根据 Bundle ID 获取进程信息

        Args:
            bundle_id: 应用的 Bundle ID (如 com.example.app)

        Returns:
            进程信息字典，如果未找到则返回 None
        """
        processes = self.get_processes()
        if not processes:
            return None

        # 提取应用名（智能处理 Bundle ID）
        parts = bundle_id.split('.')
        if len(parts) > 1:
            common_tlds = {'com', 'net', 'org', 'io', 'co', 'app'}
            if parts[-1].lower() in common_tlds and len(parts) >= 2:
                app_name = parts[-2]
            else:
                app_name = parts[-1]
        else:
            app_name = bundle_id

        logger.debug(f"查找进程: Bundle ID='{bundle_id}', 提取应用名='{app_name}'")

        for process in processes:
            exec_name = process.get('execName', '')
            comm = process.get('comm', '')
            name = process.get('name', '')

            # 使用应用名进行匹配
            if (app_name in exec_name or
                app_name in comm or
                app_name in name):

                logger.info(f"✓ 找到进程!")
                logger.info(f"  PID: {process.get('pid')}")
                logger.info(f"  Name: {name}")
                logger.info(f"  cpuUsage: {process.get('cpuUsage', 'N/A')}")
                logger.info(f"  physFootprint: {process.get('physFootprint', 'N/A')}")
                logger.info(f"  memResidentSize: {process.get('memResidentSize', 'N/A')}")

                return process

        logger.warning(f"✗ 未找到 Bundle ID 为 '{bundle_id}' 的进程")
        return None

    def get_process_by_pid(self, pid: int) -> Optional[Dict]:
        """
        根据 PID 获取进程信息

        Args:
            pid: 进程 ID

        Returns:
            进程信息字典，如果未找到则返回 None
        """
        processes = self.get_processes()
        if not processes:
            return None

        for process in processes:
            if process.get('pid') == pid:
                logger.debug(f"✓ 找到 PID {pid}: {process.get('name')}")
                return process

        logger.debug(f"✗ 未找到 PID {pid}")
        return None

    @staticmethod
    def parse_cpu_usage(process: Dict) -> float:
        """
        从进程信息中解析 CPU 使用率

        Args:
            process: 进程信息字典

        Returns:
            CPU 使用率（百分比）
        """
        cpu_usage = process.get('cpuUsage', 0.0)

        # 处理 None 值（即使 dict.get 有默认值，如果值是 None 仍会返回 None）
        if cpu_usage is None:
            logger.debug(f"CPU 使用率为 None，返回 0.0")
            return 0.0

        # pymobiledevice3 返回的 cpuUsage 已经是百分比值
        # 例如：0.4598 = 0.4598%，不需要任何转换
        result = float(cpu_usage) if cpu_usage else 0.0
        logger.debug(f"解析 CPU 使用率: {result}% (原始值: {process.get('cpuUsage')})")

        return result

    @staticmethod
    def parse_memory_usage(process: Dict) -> Dict[str, float]:
        """
        从进程信息中解析内存使用情况

        Args:
            process: 进程信息字典

        Returns:
            {'used_mb': float, 'total_mb': float, 'percentage': float}
        """
        phys_footprint = process.get('physFootprint', 0)
        resident_size = process.get('memResidentSize', 0)

        logger.debug(f"解析内存: physFootprint={phys_footprint}, memResidentSize={resident_size}")

        # 以字节为单位的内存使用量
        used_bytes = phys_footprint if phys_footprint > 0 else resident_size

        used_mb = used_bytes / 1024 / 1024

        # 总内存 - 使用固定值 4GB，因为 iOS 不提供真实总量
        total_mb = 4 * 1024

        percentage = (used_mb / total_mb * 100) if total_mb > 0 else 0

        result = {
            'used_mb': round(used_mb, 2),
            'total_mb': float(total_mb),
            'percentage': round(percentage, 2)
        }

        logger.debug(f"解析内存结果: {result}")
        return result

    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self._connected

    def __del__(self):
        """析构函数，确保资源清理"""
        self.disconnect()
