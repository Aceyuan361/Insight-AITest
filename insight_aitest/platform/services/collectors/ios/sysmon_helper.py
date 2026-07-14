# -*- coding: utf-8 -*-
"""
iOS Sysmon 辅助类

封装 pymobiledevice3 developer dvt sysmon 命令行调用，
用于获取 iOS 进程的真实性能数据。

注意：需要 Developer Mode 已启用且 DeveloperDiskImage 已挂载。
"""

import subprocess
import json
from typing import Dict, Optional
from logzero import logger


class SysmonHelper:
    """iOS Sysmon 辅助类"""

    def __init__(self, udid: Optional[str] = None):
        """
        初始化 Sysmon 辅助类

        Args:
            udid: iOS 设备唯一标识符
        """
        self.udid = udid
        self._available = self._check_availability()

    def _check_availability(self) -> bool:
        """检查 sysmon 服务是否可用"""
        try:
            logger.info("===== SysmonHelper: 检查可用性 =====")
            logger.info("命令: pymobiledevice3 developer dvt sysmon process single")

            result = subprocess.run(
                ["pymobiledevice3", "developer", "dvt", "sysmon", "process", "single"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            logger.debug(f"返回码: {result.returncode}")
            logger.debug(f"STDOUT 长度: {len(result.stdout) if result.stdout else 0}")
            logger.debug(f"STDERR: {result.stderr[:200] if result.stderr else 'None'}")

            if result.returncode == 0:
                try:
                    processes = json.loads(result.stdout)
                    logger.info(f"✓ Sysmon 服务可用，检测到 {len(processes)} 个进程")

                    # 打印前3个进程用于调试
                    for i, proc in enumerate(processes[:3]):
                        logger.debug(
                            f"  进程 {i+1}: PID={proc.get('pid')}, name={proc.get('name', 'N/A')}, execName={proc.get('execName', 'N/A')[:50]}"
                        )

                    return True
                except json.JSONDecodeError as e:
                    logger.error(f"✓ JSON 解析失败: {e}")
                    logger.debug(f"原始输出前500字符: {result.stdout[:500]}")
                    return False
            else:
                logger.warning(f"✗ Sysmon 服务不可用: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("✗ Sysmon 检查超时（10秒）")
            return False
        except FileNotFoundError:
            logger.error("✗ pymobiledevice3 未安装或不在 PATH 中")
            return False
        except Exception as e:
            logger.error(f"✗ 检查 Sysmon 服务失败: {type(e).__name__}: {e}")
            return False

    def get_process_by_bundle_id(self, bundle_id: str) -> Optional[Dict]:
        """
        根据 Bundle ID 获取进程信息

        Args:
            bundle_id: 应用的 Bundle ID (如 com.example.app)

        Returns:
            进程信息字典，如果未找到则返回 None
        """
        if not self._available:
            logger.warning(f"Sysmon 服务不可用，无法获取进程: {bundle_id}")
            return None

        try:
            logger.info("===== SysmonHelper: 查找进程 =====")
            logger.info(f"Bundle ID: {bundle_id}")
            logger.info("命令: pymobiledevice3 developer dvt sysmon process single")

            result = subprocess.run(
                ["pymobiledevice3", "developer", "dvt", "sysmon", "process", "single"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            logger.debug(f"返回码: {result.returncode}")

            if result.returncode != 0:
                logger.error(f"获取进程列表失败: {result.stderr}")
                return None

            # 解析 JSON
            try:
                processes = json.loads(result.stdout)
                logger.info(f"✓ 解析成功，共 {len(processes)} 个进程")
            except json.JSONDecodeError as e:
                logger.error(f"✗ JSON 解析失败: {e}")
                logger.debug(f"原始输出: {result.stdout[:500]}")
                return None

            # 查找匹配的进程
            logger.debug(f"正在搜索匹配 '{bundle_id}' 的进程...")

            # 提取应用名（智能处理 Bundle ID）
            # 例如: Sango.Sango.com -> Sango (不是 com)
            #       com.ubercab.UberClient -> UberClient
            #       com.example.app -> app
            parts = bundle_id.split(".")
            if len(parts) > 1:
                # 常见的 TLD 后缀，如果最后一部分是这些，则取倒数第二部分
                common_tlds = {"com", "net", "org", "io", "co", "app"}
                if parts[-1].lower() in common_tlds and len(parts) >= 2:
                    app_name = parts[-2]
                else:
                    app_name = parts[-1]
            else:
                app_name = bundle_id

            logger.debug(f"提取应用名: {app_name} (从 Bundle ID: {bundle_id})")

            for i, process in enumerate(processes):
                # 匹配 execName 或 comm 字段
                exec_name = process.get("execName", "")
                comm = process.get("comm", "")
                name = process.get("name", "")

                # 调试：每10个进程打印一次
                if i % 10 == 0:
                    logger.debug(
                        f"  检查进程 {i}: name='{name}', execName='{exec_name[:50] if exec_name else ''}'"
                    )

                # 使用应用名进行匹配（更灵活）
                if app_name in exec_name or app_name in comm or app_name in name:

                    logger.info("✓ 找到进程!")
                    logger.info(f"  PID: {process.get('pid')}")
                    logger.info(f"  Name: {name}")
                    logger.info(f"  execName: {exec_name[:80]}")
                    logger.info(f"  cpuUsage: {process.get('cpuUsage', 'N/A')}")
                    logger.info(f"  physFootprint: {process.get('physFootprint', 'N/A')}")
                    logger.info(f"  memResidentSize: {process.get('memResidentSize', 'N/A')}")

                    return process

            logger.warning(f"✗ 未找到 Bundle ID 为 '{bundle_id}' 的进程")
            logger.debug(f"搜索了 {len(processes)} 个进程，无匹配")

            # 打印所有进程名用于调试
            process_names = [p.get("name", p.get("execName", "N/A"))[:50] for p in processes[:10]]
            logger.debug(f"前10个进程名: {process_names}")

            return None

        except subprocess.TimeoutExpired:
            logger.error("✗ 获取进程超时（10秒）")
            return None
        except Exception as e:
            logger.error(f"✗ 获取进程信息失败: {type(e).__name__}: {e}")
            return None

    def get_process_by_pid(self, pid: int) -> Optional[Dict]:
        """
        根据 PID 获取进程信息

        Args:
            pid: 进程 ID

        Returns:
            进程信息字典，如果未找到则返回 None
        """
        if not self._available:
            return None

        try:
            logger.debug(f"根据 PID 查找进程: {pid}")

            result = subprocess.run(
                ["pymobiledevice3", "developer", "dvt", "sysmon", "process", "single"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                logger.debug(f"获取进程列表失败: {result.stderr}")
                return None

            processes = json.loads(result.stdout)

            for process in processes:
                if process.get("pid") == pid:
                    logger.debug(f"✓ 找到 PID {pid}: {process.get('name')}")
                    return process

            logger.debug(f"✗ 未找到 PID {pid}")
            return None

        except Exception as e:
            logger.error(f"✗ 根据 PID 获取进程失败: {e}")
            return None

    def get_energy_stats(self, pid: int) -> Optional[Dict]:
        """
        获取进程的能耗统计

        Args:
            pid: 进程 ID

        Returns:
            能耗数据字典，如果失败则返回 None
        """
        if not self._available:
            logger.debug(f"Sysmon 不可用，无法获取能耗: PID {pid}")
            return None

        try:
            logger.info("===== SysmonHelper: 获取能耗 =====")
            logger.info(f"PID: {pid}")
            logger.info(f"命令: pymobiledevice3 developer dvt energy {pid}")

            result = subprocess.run(
                ["pymobiledevice3", "developer", "dvt", "energy", str(pid)],
                capture_output=True,
                text=True,
                timeout=15,
            )

            logger.debug(f"返回码: {result.returncode}")
            logger.debug(f"STDOUT 长度: {len(result.stdout) if result.stdout else 0}")

            if result.returncode != 0:
                logger.debug(f"获取能耗数据失败: {result.stderr}")
                return None

            # 能耗监控会持续输出，读取最后一行
            lines = result.stdout.strip().split("\n")
            logger.debug(f"输出行数: {len(lines)}")

            if lines:
                last_line = lines[-1]
                logger.debug(f"最后一行: {last_line[:200]}")

                if "{" in last_line:
                    start = last_line.find("{")
                    energy_data = json.loads(last_line[start:])
                    logger.debug(f"解析的能耗数据: {energy_data}")

                    if str(pid) in energy_data:
                        stats = energy_data[str(pid)]
                        logger.info(f"✓ 获取到能耗数据: {stats}")
                        return stats
                    else:
                        logger.warning(f"能耗数据中没有 PID {pid}")
                else:
                    logger.debug("最后一行不包含 JSON 数据")
            else:
                logger.debug("能耗输出为空")

            return None

        except subprocess.TimeoutExpired:
            logger.warning("✗ 获取能耗超时（15秒）")
            return None
        except json.JSONDecodeError as e:
            logger.debug(f"✗ 解析能耗 JSON 失败: {e}")
            return None
        except Exception as e:
            logger.debug(f"✗ 获取能耗统计失败: {type(e).__name__}: {e}")
            return None

    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self._available

    @staticmethod
    def parse_cpu_usage(process: Dict) -> float:
        """
        从进程信息中解析 CPU 使用率

        Args:
            process: 进程信息字典

        Returns:
            CPU 使用率（百分比）
        """
        cpu_usage = process.get("cpuUsage", 0.0)

        # pymobiledevice3 返回的 cpuUsage 可能是小数（0-1）或百分比（0-100）
        # 根据实际值进行转换
        if cpu_usage <= 1.0:
            cpu_usage = cpu_usage * 100

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
        # 优先使用 physFootprint（物理足迹）
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
