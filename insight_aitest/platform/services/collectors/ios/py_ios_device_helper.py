# -*- coding: utf-8 -*-
"""
py-ios-device 辅助类

封装 py-ios-device 的 Instruments API，
作为 pymobiledevice3 developer dvt 的降级方案。

优势：
- 使用 instruments 协议，更稳定可靠
- 不需要 Developer Mode（仅需要信任）
- 支持 iOS 12+ 版本

依赖：
- pip install py-ios-device
"""

import threading
from typing import Dict, Optional
from logzero import logger


class PyiOSDeviceHelper:
    """py-ios-device 辅助类"""

    def __init__(self, udid: Optional[str] = None):
        """
        初始化 py-ios-device 辅助类

        Args:
            udid: iOS 设备唯一标识符
        """
        self.udid = udid
        self._available = self._check_availability()
        self._lock = threading.Lock()

    def _check_availability(self) -> bool:
        """检查 py-ios-device 是否可用"""
        try:
            from ios_device.cli.base import InstrumentsBase

            # 尝试连接设备
            with InstrumentsBase(udid=self.udid) as _:
                logger.info("py-ios-device 可用，instruments 协议连接成功")
                return True

        except ImportError:
            logger.warning("py-ios-device 未安装，请运行: pip install py-ios-device")
            return False

        except Exception as e:
            logger.warning(f"py-ios-device 不可用: {e}")
            return False

    def get_process_cpu_memory(self, bundle_id: str, timeout: float = 5.0) -> Optional[Dict]:
        """
        获取进程的 CPU 和内存使用情况

        Args:
            bundle_id: 应用的 Bundle ID (如 com.example.app)
            timeout: 超时时间（秒）

        Returns:
            {'pid': int, 'name': str, 'cpu_usage': float, 'memory_mb': float}
            如果失败则返回 None
        """
        if not self._available:
            return None

        with self._lock:
            try:
                from ios_device.cli.base import InstrumentsBase

                result = {"found": False}
                callback_called = threading.Event()

                def callback(res):
                    """回调函数处理 sysmontap 数据"""
                    try:
                        # res 是 DTXMessage 对象
                        if hasattr(res, "auxiliaries") and res.auxiliaries:
                            # 解析进程列表
                            for item in res.auxiliaries:
                                if isinstance(item, dict):
                                    # 检查是否匹配 Bundle ID
                                    item_name = item.get("name", "")
                                    item_exec_name = item.get("execName", "")

                                    if bundle_id in item_name or bundle_id in item_exec_name:

                                        result["found"] = True
                                        result["pid"] = item.get("pid")
                                        result["name"] = item.get("name", "")

                                        # CPU 使用率（可能是百分比或小数）
                                        cpu_usage = item.get("cpuUsage", 0.0)
                                        if cpu_usage <= 1.0:
                                            cpu_usage *= 100  # 转换为百分比
                                        result["cpu_usage"] = float(cpu_usage)

                                        # 内存使用（字节转换为 MB）
                                        phys_footprint = item.get("physFootprint", 0)
                                        mem_resident = item.get("memResidentSize", 0)
                                        memory_bytes = (
                                            phys_footprint if phys_footprint > 0 else mem_resident
                                        )
                                        result["memory_mb"] = round(memory_bytes / 1024 / 1024, 2)

                                        logger.debug(f"py-ios-device 获取到进程数据: {result}")
                                        callback_called.set()
                                        break

                    except Exception as e:
                        logger.debug(f"解析 py-ios-device 数据失败: {e}")
                        callback_called.set()

                try:
                    with InstrumentsBase(udid=self.udid) as rpc:
                        # 设置要采集的进程属性
                        rpc.process_attributes = [
                            "name",
                            "pid",
                            "execName",
                            "cpuUsage",
                            "physFootprint",
                            "memResidentSize",
                        ]

                        # 启动 sysmontap
                        rpc.sysmontap(callback)

                        # 等待回调或超时
                        callback_called.wait(timeout=timeout)

                        if result["found"]:
                            return result
                        else:
                            logger.warning(f"py-ios-device 未找到进程: {bundle_id}")
                            return None

                except Exception as e:
                    logger.error(f"py-ios-device 采集失败: {e}")
                    return None

            except ImportError:
                logger.warning("py-ios-device 未安装")
                return None

            except Exception as e:
                logger.error(f"获取进程数据失败: {e}")
                return None

    def get_system_memory(self) -> Optional[Dict[str, float]]:
        """
        获取系统内存使用情况

        Returns:
            {'used_mb': float, 'total_mb': float, 'percentage': float}
            如果失败则返回 None
        """
        if not self._available:
            return None

        with self._lock:
            try:
                from ios_device.cli.base import InstrumentsBase

                result = {"found": False}
                callback_called = threading.Event()

                def callback(res):
                    """回调函数处理系统数据"""
                    try:
                        if hasattr(res, "auxiliaries") and res.auxiliaries:
                            for item in res.auxiliaries:
                                if isinstance(item, dict):
                                    # 系统内存数据
                                    if "MemUsed" in item or "PhysMem" in item:
                                        # 提取内存数据（字符串格式如 "1.42 GiB"）
                                        mem_used = item.get("MemUsed", item.get("PhysMem", "0"))
                                        mem_total = item.get("MemSize", "4 GB")

                                        # 解析内存大小
                                        def parse_memory(mem_str):
                                            if isinstance(mem_str, (int, float)):
                                                return float(mem_str)
                                            if isinstance(mem_str, str):
                                                mem_str = mem_str.strip().upper()
                                                if "GB" in mem_str or "GIB" in mem_str:
                                                    return (
                                                        float(
                                                            mem_str.replace("GB", "")
                                                            .replace("GIB", "")
                                                            .strip()
                                                        )
                                                        * 1024
                                                    )
                                                elif "MB" in mem_str or "MIB" in mem_str:
                                                    return float(
                                                        mem_str.replace("MB", "")
                                                        .replace("MIB", "")
                                                        .strip()
                                                    )
                                            return 0.0

                                        used_mb = parse_memory(mem_used)
                                        total_mb = parse_memory(mem_total)

                                        if total_mb > 0:
                                            result["used_mb"] = used_mb
                                            result["total_mb"] = total_mb
                                            result["percentage"] = round(
                                                (used_mb / total_mb * 100), 2
                                            )
                                            result["found"] = True
                                            logger.debug(f"py-ios-device 系统内存: {result}")
                                            callback_called.set()
                                            break

                    except Exception as e:
                        logger.debug(f"解析系统内存数据失败: {e}")
                        callback_called.set()

                try:
                    with InstrumentsBase(udid=self.udid) as rpc:
                        rpc.system_attributes = rpc.device_info.sysmonSystemAttributes()
                        rpc.sysmontap(callback)

                        callback_called.wait(timeout=3.0)

                        if result["found"]:
                            return result
                        else:
                            return None

                except Exception as e:
                    logger.error(f"获取系统内存失败: {e}")
                    return None

            except Exception as e:
                logger.error(f"获取系统内存失败: {e}")
                return None

    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self._available

    @staticmethod
    def parse_cpu_usage(process: Dict) -> float:
        """从进程信息中解析 CPU 使用率"""
        return process.get("cpu_usage", 0.0)

    @staticmethod
    def parse_memory_usage(process: Dict) -> Dict[str, float]:
        """从进程信息中解析内存使用情况"""
        used_mb = process.get("memory_mb", 0.0)
        total_mb = 4 * 1024  # 默认 4GB
        percentage = (used_mb / total_mb * 100) if total_mb > 0 else 0

        return {
            "used_mb": round(used_mb, 2),
            "total_mb": float(total_mb),
            "percentage": round(percentage, 2),
        }
