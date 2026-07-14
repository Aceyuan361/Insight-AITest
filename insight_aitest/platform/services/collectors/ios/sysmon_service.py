# -*- coding: utf-8 -*-
"""
iOS Sysmon 服务（使用 pymobiledevice3 v9.x async Python API）

通过 IOSConnectionManager 获取 LockdownServiceProvider，使用 DvtProvider +
Sysmontap 的 async API 进行高性能进程监控数据采集。

兼容 iOS 11-16 (usbmux 路径) 和 iOS 17+ (tunnel 路径)。
"""

import threading
import time
from typing import Dict, List, Optional
from logzero import logger

from .connection_manager import IOSConnectionManager


class SysmonService:
    """
    iOS Sysmon 服务

    使用 pymobiledevice3 v9.x async API 连接 DVT 协议，
    提供高性能的进程监控数据采集。
    """

    _instance_lock = threading.Lock()
    _instances: Dict[str, "SysmonService"] = {}

    def __init__(self, udid: Optional[str] = None):
        """
        初始化 Sysmon 服务

        Args:
            udid: iOS 设备唯一标识符
        """
        self.udid = udid
        self._lock = threading.Lock()
        self._process_cache: Optional[List[Dict]] = None
        self._cache_time: Optional[float] = None
        self._cache_ttl = 0.5  # 0.5秒缓存（平衡性能和实时性）
        self._connected = False

    @classmethod
    def get_instance(cls, udid: Optional[str] = None) -> "SysmonService":
        """
        获取 Sysmon 服务实例（单例模式）

        Args:
            udid: iOS 设备唯一标识符

        Returns:
            SysmonService 实例
        """
        device_key = udid or "default"

        with cls._instance_lock:
            if device_key not in cls._instances:
                cls._instances[device_key] = cls(udid)
            return cls._instances[device_key]

    def connect(self) -> bool:
        """
        验证设备连接可用性（实际连接由 IOSConnectionManager 管理）

        Returns:
            bool: 是否连接成功
        """
        with self._lock:
            if self._connected:
                return True

            try:
                if self.udid:
                    mgr = IOSConnectionManager.get_instance(self.udid)
                else:
                    # 无 UDID 时尝试默认设备
                    logger.warning("SysmonService: 无 UDID，无法连接")
                    return False

                if not mgr.is_connected:
                    mgr.connect()

                self._connected = True
                logger.debug("✓ SysmonService 连接就绪")
                return True

            except Exception as e:
                logger.error(f"✗ SysmonService 连接失败: {type(e).__name__}: {e}")
                return False

    def disconnect(self):
        """断开连接（仅清理本地缓存，实际连接由 ConnectionManager 管理）"""
        with self._lock:
            self._connected = False
            self._process_cache = None
            self._cache_time = None
            logger.debug("SysmonService 连接已断开")

    def get_processes(self, force_refresh: bool = False) -> Optional[List[Dict]]:
        """
        获取所有进程列表（通过 async DVT API）

        Args:
            force_refresh: 是否强制刷新缓存

        Returns:
            进程列表，每个进程包含 pid, name, cpuUsage, physFootprint 等字段
        """
        # 检查缓存
        current_time = time.time()
        if (
            not force_refresh
            and self._process_cache is not None
            and self._cache_time is not None
            and current_time - self._cache_time < self._cache_ttl
        ):
            return self._process_cache

        with self._lock:
            try:
                # 确保已连接
                if not self._connected:
                    if not self.connect():
                        logger.warning("[get_processes] 连接失败，使用缓存")
                        return self._process_cache

                logger.debug("===== SysmonService: 获取进程列表 =====")

                # 通过 ConnectionManager 的事件循环执行 async DVT 查询
                mgr = IOSConnectionManager.get_instance(self.udid)
                processes = mgr.run_async(self._fetch_processes_async(), timeout=10)

                if processes:
                    # 转换为统一格式
                    result = []
                    for proc in processes:
                        result.append(
                            {
                                "pid": proc.get("pid"),
                                "name": proc.get("name", ""),
                                "cpuUsage": proc.get("cpuUsage", 0.0),
                                "physFootprint": proc.get("physFootprint", 0),
                                "memResidentSize": proc.get("memResidentSize", 0),
                                "execName": proc.get("execName", ""),
                                "comm": proc.get("comm", ""),
                            }
                        )

                    # 更新缓存
                    self._process_cache = result
                    self._cache_time = current_time

                    logger.debug(f"✓ 获取到 {len(result)} 个进程")
                    return result
                else:
                    logger.warning("未获取到进程数据")
                    return self._process_cache if self._process_cache else None

            except Exception as e:
                logger.error(f"✗ 获取进程列表失败: {type(e).__name__}: {e}")
                self._connected = False
                return self._process_cache if self._process_cache else None

    async def _fetch_processes_async(self) -> List[Dict]:
        """异步获取进程列表（通过 DvtProvider + Sysmontap）"""
        from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
        from pymobiledevice3.services.dvt.instruments.sysmontap import Sysmontap

        mgr = IOSConnectionManager.get_instance(self.udid)
        lockdown = mgr.get_async_lockdown()

        async with DvtProvider(lockdown) as dvt:
            tap = await Sysmontap.create(dvt)
            async with tap:
                async for process_list in tap.iter_processes():
                    # 只读取第一批数据
                    return process_list

        return []

    def get_process_by_bundle_id(self, bundle_id: str) -> Optional[Dict]:
        """
        根据 Bundle ID 获取进程信息

        通过 AppLookup 查找该 Bundle ID 对应的可执行文件名（CFBundleExecutable，
        即 DVT 进程的 name 字段），然后在进程列表中精确匹配。

        Args:
            bundle_id: 应用的 Bundle ID (如 com.example.app)

        Returns:
            进程信息字典，如果未找到则返回 None
        """
        from insight_aitest.platform.services.collectors.ios.app_lookup import AppLookup

        processes = self.get_processes()
        if not processes:
            return None

        if not self.udid:
            logger.warning("无法查找进程：缺少 UDID")
            return None

        # 通过 AppLookup 查找该 Bundle ID 对应的可执行文件名
        executable_name = AppLookup.find_executable_for_bundle(self.udid, bundle_id)

        if not executable_name:
            logger.warning(
                f"未找到 Bundle ID '{bundle_id}' 对应的可执行文件名，"
                "可能应用未安装"
            )
            return None

        logger.debug(
            f"查找进程: Bundle ID='{bundle_id}', 可执行文件名='{executable_name}'"
        )

        # 精确匹配进程 name（大小写不敏感）
        target_lower = executable_name.lower()
        for process in processes:
            name = process.get("name", "")

            if name and name.lower() == target_lower:
                logger.info("✓ 找到进程!")
                logger.info(f"  PID: {process.get('pid')}")
                logger.info(f"  Name: {name}")
                logger.info(f"  cpuUsage: {process.get('cpuUsage', 'N/A')}")
                logger.info(
                    f"  physFootprint: {process.get('physFootprint', 'N/A')}"
                )
                logger.info(
                    f"  memResidentSize: {process.get('memResidentSize', 'N/A')}"
                )
                return process

        logger.warning(
            f"✗ 未找到 Bundle ID 为 '{bundle_id}' 的进程"
            f"（可执行文件名 '{executable_name}' 不在运行中）"
        )
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
            if process.get("pid") == pid:
                logger.debug(f"✓ 找到 PID {pid}: {process.get('name')}")
                return process

        logger.debug(f"✗ 未找到 PID {pid}")
        return None

    @staticmethod
    def parse_cpu_usage(process: Dict) -> float:
        """
        从进程信息中解析 CPU 使用率

        Args:
            process: 进程信息

        Returns:
            CPU 使用率（百分比）
        """
        cpu_usage = process.get("cpuUsage", 0.0)

        if cpu_usage is None:
            logger.debug("CPU 使用率为 None，返回 0.0")
            return 0.0

        # pymobiledevice3 返回的 cpuUsage 已经是百分比值
        result = float(cpu_usage) if cpu_usage else 0.0
        logger.debug(f"解析 CPU 使用率: {result}% (原始值: {process.get('cpuUsage')})")

        return result

    @staticmethod
    def parse_memory_usage(process: Dict) -> Dict[str, float]:
        """
        从进程信息中解析内存使用情况

        Args:
            process: 进程信息

        Returns:
            {'used_mb': float, 'total_mb': float, 'percentage': float}
        """
        phys_footprint = process.get("physFootprint", 0)
        resident_size = process.get("memResidentSize", 0)

        logger.debug(f"解析内存: physFootprint={phys_footprint}, memResidentSize={resident_size}")

        # 以字节为单位的内存使用量
        used_bytes = phys_footprint if phys_footprint > 0 else resident_size

        used_mb = used_bytes / 1024 / 1024

        # 总内存 - 使用固定值 4GB，因为 iOS 不提供真实总量
        total_mb = 4 * 1024

        percentage = (used_mb / total_mb * 100) if total_mb > 0 else 0

        result = {
            "used_mb": round(used_mb, 2),
            "total_mb": float(total_mb),
            "percentage": round(percentage, 2),
        }

        logger.debug(f"解析内存结果: {result}")
        return result

    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self._connected

    def __del__(self):
        """析构函数，确保资源清理"""
        self.disconnect()
