# -*- coding: utf-8 -*-
"""
Android CPU 采集器
使用 ADB 实现 Android 应用的 CPU 使用率采集

改进：
- 集成设备配置系统（DeviceProfile）
- 根据设备厂商选择最佳 CPU 采集方法
- 小米设备：优先使用 top，需要 ANSI 过滤
- 华为设备：优先使用 dumpsys_cpuinfo
- 精确计算模式：基于 /proc/stat 和 /proc/[pid]/stat（与 Android Studio 一致）
"""

import re
import time
from typing import Optional, Dict, Tuple
from logzero import logger
from insight_aitest.platform.services.collectors.adb import adb


class CPUCollector:
    """
    Android CPU 使用率采集器 - 集成设备配置系统

    根据设备配置自动选择最佳采集方法：
    - 小米设备：优先使用 top（需要 ANSI 过滤）
    - 华为/三星/Google：优先使用 dumpsys_cpuinfo

    性能优化（P2-18）：
    - 预编译正则表达式，避免重复编译开销
    """

    # 预编译正则表达式（性能优化：避免每次调用时重新编译）
    _ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-9;]*m")

    def __init__(self, device_id: str, device_profile=None):
        """
        初始化 CPU 采集器

        Args:
            device_id: Android 设备 ID
            device_profile: 设备配置档案（可选）
        """
        self.device_id = device_id
        self.device_profile = device_profile
        self.strategy = device_profile.get_strategy() if device_profile else None

        # 获取CPU核心数（用于将多核累计值转换为单核占用百分比）
        self.cpu_cores = self._get_cpu_cores()

        # 精确计算模式：存储上一次采样的 CPU 时间
        self._last_cpu_data = {}  # {pid: (last_proc_time, last_total_time, last_timestamp)}

        if self.strategy:
            logger.debug(
                f"[CPU采集器] 使用策略: {self.strategy.cpu_primary_method}, "
                f"解析模式: {self.strategy.cpu_parse_mode}, "
                f"ANSI过滤: {self.strategy.cpu_ansi_filter}, "
                f"CPU核心数: {self.cpu_cores}"
            )

    def _get_cpu_cores(self) -> int:
        """获取设备CPU核心数"""
        try:
            cpuinfo = adb.shell("cat /proc/cpuinfo", self.device_id)
            if cpuinfo:
                core_count = cpuinfo.count("processor")
                if core_count > 0:
                    logger.info(f"[CPU采集器] 检测到CPU核心数: {core_count}")
                    return core_count
        except Exception as e:
            logger.warning(f"获取CPU核心数失败: {e}")

        # 默认返回8核
        logger.info("[CPU采集器] 使用默认CPU核心数: 8")
        return 8

    def _get_app_cpu_time_from_proc(self, pid: str) -> Optional[int]:
        """
        获取进程的 CPU 时间（Jiffies）- 直接读取 /proc/[pid]/stat
        按照专业文档的算法：读取 utime, stime, cutime, cstime

        Args:
            pid: 进程 ID

        Returns:
            int: 总 CPU 时间（jiffies）= utime + stime + cutime + cstime
        """
        try:
            # 直接读取 /proc/[pid]/stat
            stat_result = adb.shell(f"cat /proc/{pid}/stat", self.device_id)
            if not stat_result:
                return None

            # /proc/[pid]/stat 格式：字段间用空格分隔，但命令名可能包含空格和括号
            # 需要从右边解析，因为命令名格式不确定
            # utime(14), stime(15), cutime(16), cstime(17)
            parts = stat_result.strip().split()
            if len(parts) < 17:
                logger.warning(f"[CPU精确算法] /proc/{pid}/stat 字段不足: {len(parts)} < 17")
                return None

            try:
                utime = int(parts[13])
                stime = int(parts[14])
                cutime = int(parts[15])
                cstime = int(parts[16])

                # 总应用时间 = 用户态 + 内核态 + 子进程用户态 + 子进程内核态
                total_app_time = utime + stime + cutime + cstime
                return total_app_time

            except (ValueError, IndexError) as e:
                logger.warning(f"[CPU精确算法] 解析 /proc/{pid}/stat 失败: {e}")
                return None

        except Exception as e:
            logger.warning(f"[CPU精确算法] 读取 /proc/{pid}/stat 失败: {e}")
            return None

    def _get_cpu_data_atomic(self, pid: str) -> Optional[Tuple[int, int]]:
        """
        原子性采集：一次性读取系统和进程的 CPU 数据
        按照文档建议：使用合并命令减少 ADB 通信 RTT（往返延迟）

        Args:
            pid: 进程 ID

        Returns:
            tuple: (total_cpu_time, app_cpu_time) 或 None
        """
        try:
            # 构造原子性采集命令：一次性读取 System 和 App 的 stat 文件
            # 减少 ADB 通信往返耗时 (RTT)
            cmd = f'cat /proc/stat ; echo "---SEPARATOR---" ; cat /proc/{pid}/stat'
            result = adb.shell(cmd, self.device_id)

            if not result:
                logger.warning("[CPU精确算法] 合并命令返回空结果")
                return None

            # 分隔系统和进程数据
            parts = result.split("---SEPARATOR---")
            if len(parts) != 2:
                logger.warning(f"[CPU精确算法] 分隔符解析失败，部分数量: {len(parts)}")
                return None

            stat_output = parts[0].strip()
            proc_stat_output = parts[1].strip()

            # 解析 /proc/stat
            lines = stat_output.split("\n")
            total_cpu_time = 0
            for line in lines:
                if line.startswith("cpu "):
                    parts_stat = line.split()
                    # 累加所有字段（必须包含 idle 和 iowait）
                    total_cpu_time = sum(int(parts_stat[i]) for i in range(1, len(parts_stat)))
                    break

            if total_cpu_time == 0:
                logger.warning("[CPU精确算法] /proc/stat 解析失败")
                return None

            # 解析 /proc/[pid]/stat
            proc_parts = proc_stat_output.split()
            if len(proc_parts) < 17:
                logger.warning(f"[CPU精确算法] /proc/{pid}/stat 字段不足: {len(proc_parts)} < 17")
                return None

            try:
                utime = int(proc_parts[13])
                stime = int(proc_parts[14])
                cutime = int(proc_parts[15])
                cstime = int(proc_parts[16])

                # 总应用时间 = 用户态 + 内核态 + 子进程用户态 + 子进程内核态
                app_cpu_time = utime + stime + cutime + cstime

                return (total_cpu_time, app_cpu_time)

            except (ValueError, IndexError) as e:
                logger.warning(f"[CPU精确算法] 解析 /proc/{pid}/stat 失败: {e}")
                return None

        except Exception as e:
            logger.warning(f"[CPU精确算法] 原子性采集失败: {e}")
            return None

    def _parse_cpu_from_proc_stat(self, pid: str) -> Optional[float]:
        """
        精确算法：基于 /proc/stat 和 /proc/[pid]/stat 计算 CPU 使用率
        按照专业文档的差值算法实现：
        1. 读取 /proc/stat 获取系统总时间（包含所有字段）
        2. 读取 /proc/[pid]/stat 获取应用时间（utime+stime+cutime+cstime）
        3. 使用差值法：CPU% = (AppTime_T2 - AppTime_T1) / (TotalTime_T2 - TotalTime_T1) × 100%

        Args:
            pid: 进程 ID

        Returns:
            float: CPU 使用率百分比 (0-100)，失败返回 None

        注意：
            - 必须包含 idle 和 iowait，这是分母的关键部分
            - 返回的是应用占当前设备整体算力资源的百分比（0% - 100%）
            - 使用原子性采集命令减少 ADB 通信 RTT
        """
        try:
            current_time = time.time()

            # 使用原子性采集命令一次性读取系统和进程数据
            cpu_data = self._get_cpu_data_atomic(pid)
            if cpu_data is None:
                # 回退到分别采集的方式
                logger.debug("[CPU精确算法] 原子性采集失败，尝试分别采集")
                stat_result = adb.shell("cat /proc/stat", self.device_id)
                if not stat_result:
                    logger.warning("[CPU精确算法] 无法读取 /proc/stat")
                    return None

                lines = stat_result.strip().split("\n")
                total_cpu_time = 0
                for line in lines:
                    if line.startswith("cpu "):
                        parts = line.split()
                        total_cpu_time = sum(int(parts[i]) for i in range(1, len(parts)))
                        break

                app_cpu_time = self._get_app_cpu_time_from_proc(pid)
                if app_cpu_time is None:
                    logger.warning(f"[CPU精确算法] 无法获取进程 {pid} 的 CPU 时间")
                    return None
            else:
                total_cpu_time, app_cpu_time = cpu_data
                logger.debug("[CPU精确算法] 使用原子性采集成功")

            if total_cpu_time == 0:
                logger.warning("[CPU精确算法] /proc/stat 解析失败，总时间为 0")
                return None

            # 检查是否有上一次的采样数据
            if pid not in self._last_cpu_data:
                # 首次采样，只记录数据不计算
                self._last_cpu_data[pid] = {
                    "app_time": app_cpu_time,
                    "total_time": total_cpu_time,
                    "timestamp": current_time,
                }
                logger.info(
                    f"[CPU精确算法] 首次采样: pid={pid}, "
                    f"app_time={app_cpu_time}, total_time={total_cpu_time}"
                )
                return None

            # 计算增量
            last_data = self._last_cpu_data[pid]

            # 更新缓存
            self._last_cpu_data[pid] = {
                "app_time": app_cpu_time,
                "total_time": total_cpu_time,
                "timestamp": current_time,
            }

            delta_app_time = app_cpu_time - last_data["app_time"]
            delta_total_time = total_cpu_time - last_data["total_time"]
            time_delta = current_time - last_data["timestamp"]

            # 验证数据有效性
            if delta_total_time <= 0:
                logger.warning(f"[CPU精确算法] 总 CPU 时间无变化: delta_total={delta_total_time}")
                return None

            if delta_app_time < 0:
                logger.warning(
                    f"[CPU精确算法] 进程 CPU 时间异常: delta_app={delta_app_time} "
                    f"(可能是进程重启)"
                )
                # 进程可能重启了，清除缓存重新采样
                del self._last_cpu_data[pid]
                return None

            # 计算精确的 CPU 使用率（差值法）
            # Rate = (AppTime_T2 - AppTime_T1) / (TotalTime_T2 - TotalTime_T1) × 100%
            cpu_usage = (delta_app_time / delta_total_time) * 100.0

            # 限制最大值为 100%（理论上不应该超过，但为了安全）
            cpu_usage = min(max(cpu_usage, 0.0), 100.0)

            logger.info(
                f"[CPU精确算法] pid={pid}: "
                f"Δapp={delta_app_time}, Δtotal={delta_total_time}, "
                f"CPU={cpu_usage:.2f}%, 间隔={time_delta:.3f}s"
            )

            return round(cpu_usage, 2)

        except ValueError as e:
            logger.error(f"[CPU精确算法] 数值解析错误: {e}")
            return None
        except Exception as e:
            logger.error(f"[CPU精确算法] 采样失败: {e}")
            return None

    def _get_app_pid(self, package_name: str) -> Optional[str]:
        """
        获取应用的进程 ID

        Args:
            package_name: 应用包名

        Returns:
            str: 进程 ID，失败返回 None
        """
        try:
            result = adb.shell(f"pidof {package_name}", self.device_id)
            if result:
                # pidof 可能返回多个 PID（空格分隔），取第一个
                pids = result.strip().split()
                if pids:
                    return pids[0]

            # 备选方法: 使用 ps 命令（在Python中过滤，兼容Windows）
            result = adb.shell("ps", self.device_id)
            if result:
                lines = result.strip().split("\n")
                for line in lines:
                    if package_name in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            return parts[1]

            return None

        except Exception as e:
            logger.error(f"获取应用 PID 失败: {e}")
            return None

    def _parse_cpu_from_top(self, package_name: str) -> Optional[Dict[str, float]]:
        """
        使用 top 命令解析 CPU 使用率 - 增强版：支持多种 Android 版本格式

        Args:
            package_name: 应用包名

        Returns:
            dict: {'appCpuRate': float, 'sysCpuRate': float} 或 None
        """
        try:
            # 使用 top 命令获取 CPU 使用率
            # Android top 命令格式因版本而异：
            # - Android 7-8: PID USER     PR  NI  VIRT  RES  %CPU  %MEM  COMMAND
            # - Android 9+: PID USER      PR  NI VIRT  RES CPU %MEM  TIME+ COMMAND
            # - Android 10+: 可能使用不同的列顺序
            result = adb.shell("top -n 1", self.device_id)

            if not result:
                logger.warning("top 命令返回空结果")
                return None

            # ===== 调试日志：记录原始输出（前500字符） =====
            logger.info(f"[CPU调试] top原始输出(前500字符): {result[:500]}")

            # 清理 ANSI 转义序列（颜色代码）
            # 性能优化：使用预编译的正则表达式
            result = self._ANSI_ESCAPE_PATTERN.sub("", result)

            # ===== 调试日志：记录清理后的输出 =====
            logger.info(f"[CPU调试] top清理后输出(前500字符): {result[:500]}")

            lines = result.strip().split("\n")
            logger.info(f"[CPU调试] top 命令返回 {len(lines)} 行数据")

            # ===== 策略1：智能列匹配 - 找到表头并记录列位置 =====
            cpu_column_index = -1
            column_count = 0

            for i, line in enumerate(lines):
                if "%CPU" in line or "CPU%" in line:
                    parts = line.split()
                    column_count = len(parts)
                    logger.info(f"[CPU调试] 找到表头行 (行{i}): {line}")
                    logger.info(f"[CPU调试] 表头列数: {column_count}, 列内容: {parts}")

                    # 查找 CPU 列索引
                    for j, part in enumerate(parts):
                        if "%CPU" in part or "CPU%" in part:
                            cpu_column_index = j
                            logger.info(
                                f"[CPU调试] 找到 CPU 列索引: {cpu_column_index}, 列名: {part}"
                            )
                            # 特殊处理：如果表头是 S[%CPU] 格式，数据行会分成两列（S列 + CPU列）
                            # 需要将 CPU 列索引 +1
                            if "S[%CPU]" in part or "[%CPU]" in part:
                                cpu_column_index += 1
                                logger.info(
                                    f"[CPU调试] 检测到 S[%CPU] 格式，CPU 列索引调整为: {cpu_column_index}"
                                )
                            break
                    break

            # ===== 策略2：查找包含包名的数据行并尝试多种解析方式 =====
            for i, line in enumerate(lines):
                if package_name in line:
                    logger.info(f"[CPU调试] 找到包含包名的数据行 (行{i}): {line}")
                    parts = line.split()
                    logger.info(f"[CPU调试] 数据行分割为 {len(parts)} 列: {parts}")

                    # 尝试1：使用表头列索引（如果有）
                    if cpu_column_index >= 0:
                        if cpu_column_index < len(parts):
                            cpu_part = parts[cpu_column_index]
                            logger.info(
                                f"[CPU调试] 尝试1: 从列 {cpu_column_index} 提取: '{cpu_part}'"
                            )

                            result = self._try_extract_cpu(cpu_part, package_name, "按表头列")
                            if result:
                                logger.info(
                                    f"[CPU调试] ✓ 尝试1成功: 按表头列{cpu_column_index} -> {result['appCpuRate']}%"
                                )
                                return result
                        else:
                            logger.warning(
                                f"[CPU调试] CPU 列索引 {cpu_column_index} 超出数据行范围 (数据行只有 {len(parts)} 列)"
                            )
                            logger.info(
                                f"[CPU调试] 列数不匹配: 表头 {column_count} 列 vs 数据行 {len(parts)} 列，尝试智能搜索"
                            )

                    # 尝试2：智能搜索包含 % 的列（从右向左搜索，跳过最后一列的命令名）
                    # 从倒数第 2 列开始，向前搜索包含 % 的列
                    for idx in range(len(parts) - 2, 0, -1):
                        if "%" in parts[idx]:
                            logger.info(f"[CPU调试] 尝试2: 智能搜索找到 % 列 {idx}: '{parts[idx]}'")
                            result = self._try_extract_cpu(
                                parts[idx], package_name, f"智能搜索列{idx}"
                            )
                            if result:
                                logger.info(
                                    f"[CPU调试] ✓ 尝试2成功: 智能搜索列{idx} -> {result['appCpuRate']}%"
                                )
                                return result

                    # 尝试2.5：智能搜索数值列（从右向左搜索，寻找0-100之间的浮点数）
                    # 某些 top 输出中 CPU 值不带 % 符号
                    for idx in range(len(parts) - 2, 0, -1):
                        part = parts[idx]
                        # 检查是否是纯数值或数值格式（如 79.3）
                        try:
                            # 移除可能的 % 符号
                            cleaned = part.replace("%", "").replace(",", ".").strip()
                            value = float(cleaned)
                            # 检查是否在合理的 CPU 范围内（0-100）
                            if 0 <= value <= 100:
                                logger.info(
                                    f"[CPU调试] 尝试2.5: 智能搜索找到数值列 {idx}: '{part}' -> {value}%"
                                )
                                result = self._try_extract_cpu(
                                    part, package_name, f"智能搜索数值列{idx}"
                                )
                                if result:
                                    logger.info(
                                        f"[CPU调试] ✓ 尝试2.5成功: 智能搜索数值列{idx} -> {result['appCpuRate']}%"
                                    )
                                    return result
                        except (ValueError, IndexError):
                            continue

                    # 尝试3：基于列位置的启发式方法（兼容各种 top 格式）
                    # Android top 的常见列位置：
                    # - 格式1: PID USER PR NI VIRT RES %CPU %MEM TIME+ COMMAND
                    # - 格式2: PID USER PR NI VIRT RES S %CPU %MEM TIME+ COMMAND (带状态列)
                    # 通常 CPU 在倒数第 3 或第 4 列
                    if len(parts) >= 10:
                        # 尝试倒数第 3 列（通常是 %CPU）
                        logger.info(f"[CPU调试] 尝试3: 倒数第3列: '{parts[-3]}'")
                        result = self._try_extract_cpu(parts[-3], package_name, "倒数第3列")
                        if result:
                            logger.info(
                                f"[CPU调试] ✓ 尝试3成功: 倒数第3列 -> {result['appCpuRate']}%"
                            )
                            return result

                        # 尝试倒数第 4 列（如果有状态列）
                        logger.info(f"[CPU调试] 尝试3b: 倒数第4列: '{parts[-4]}'")
                        result = self._try_extract_cpu(parts[-4], package_name, "倒数第4列")
                        if result:
                            logger.info(
                                f"[CPU调试] ✓ 尝试3b成功: 倒数第4列 -> {result['appCpuRate']}%"
                            )
                            return result

                    logger.error(
                        f"[CPU调试] ❌ 所有尝试失败，无法从数据行解析 CPU 值: {line[:100]}"
                    )

            logger.warning(f"未找到包名 {package_name} 的 CPU 数据")
            return None

        except Exception as e:
            logger.error(f"使用 top 命令获取 CPU 失败: {e}")
            return None

    def _try_extract_cpu(
        self, cpu_part: str, package_name: str, method: str
    ) -> Optional[Dict[str, float]]:
        """
        尝试从字符串中提取 CPU 使用率值

        Args:
            cpu_part: 包含 CPU 值的字符串（如 "47.0%", "47.0", "S" 等）
            package_name: 包名（用于日志）
            method: 解析方法描述（用于日志）

        Returns:
            dict: {'appCpuRate': float, 'sysCpuRate': float} 或 None
        """
        if not cpu_part:
            return None

        # 移除常见的非数字字符
        cleaned = cpu_part.replace("%", "").replace(",", ".").strip()

        # 跳过明显的非数值（如线程状态 "S", "R", "D" 等）
        if cleaned in ["S", "R", "D", "Z", "T", "W", "x", "+", "l"]:
            logger.debug(f"跳过非数值 CPU 部分: '{cpu_part}' (可能是线程状态)")
            return None

        try:
            raw_cpu_value = float(cleaned)

            # top 命令显示的是多核累积值（所有核心的CPU%总和）
            # 需要除以核心数得到实际CPU占用率
            # 例如：143% ÷ 8核 = 17.875%（这是实际占用系统CPU的百分比）
            if raw_cpu_value > 0:
                normalized_cpu = raw_cpu_value / self.cpu_cores
                sys_cpu = min(100.0, normalized_cpu * 1.5)
                logger.info(
                    f"[✓] top命令: 原始值={raw_cpu_value}% ÷ {self.cpu_cores}核 = {normalized_cpu:.2f}%"
                )
                return {"appCpuRate": round(normalized_cpu, 2), "sysCpuRate": round(sys_cpu, 2)}
            else:
                logger.debug(f"CPU 值 <= 0: {raw_cpu_value} (来源: '{cpu_part}')")
                return None
        except ValueError as e:
            logger.debug(f"无法解析 CPU 值: '{cpu_part}' -> '{cleaned}' ({method}): {e}")
            return None

    def _parse_cpu_from_dumpsys(self, package_name: str) -> Optional[Dict[str, float]]:
        """
        使用 dumpsys cpuinfo 解析 CPU 使用率

        Args:
            package_name: 应用包名

        Returns:
            dict: {'appCpuRate': float, 'sysCpuRate': float} 或 None
        """
        try:
            result = adb.shell("dumpsys cpuinfo", self.device_id)

            if not result:
                return None

            lines = result.strip().split("\n")
            app_cpu = 0.0
            total_cpu = 0.0

            for line in lines:
                # dumpsys cpuinfo 输出格式:
                # 86% 5623/com.xlive.app: 68% user + 18% kernel
                # 注意：第一个百分比是总 CPU（user + kernel）
                if package_name in line:
                    # 优先匹配格式: "XX% PID/com.xlive.app: YY% user + ZZ% kernel"
                    # 提取行首的总CPU百分比（user + kernel的总和）
                    match = re.search(r"^\s*(\d+\.?\d*)%\s+[\d]+/" + re.escape(package_name), line)
                    if match:
                        try:
                            raw_cpu_value = float(match.group(1))
                            # 直接使用 dumpsys 的原始值，不做归一化处理
                            # dumpsys 已经显示了应用的实际 CPU 占用百分比
                            app_cpu = max(app_cpu, raw_cpu_value)
                            logger.info(f"[CPU调试] dumpsys: 原始值={raw_cpu_value}% (直接使用)")
                        except ValueError:
                            continue
                    else:
                        # 备选方案：如果找不到行首的总CPU，尝试匹配 user 部分
                        match = re.search(
                            re.escape(package_name) + r":\s*(\d+\.?\d*)%\s+user", line
                        )
                        if match:
                            try:
                                cpu_value = float(match.group(1))
                                app_cpu = max(app_cpu, cpu_value)
                                logger.info(
                                    f"[CPU调试] dumpsys提取user部分: {cpu_value}% (行: {line[:100]})"
                                )
                            except ValueError:
                                continue

                # 累计总 CPU 使用率
                if "Load:" in line or "CPU usage" in line:
                    try:
                        for part in line.split():
                            if "%" in part:
                                value = float(part.replace("%", "").replace(",", ""))
                                total_cpu += value
                    except ValueError:
                        continue

            if app_cpu > 0:
                sys_cpu = min(100.0, max(total_cpu / 10, app_cpu * 1.5))
                return {"appCpuRate": round(app_cpu, 2), "sysCpuRate": round(sys_cpu, 2)}

            return None

        except Exception as e:
            logger.error(f"使用 dumpsys 获取 CPU 失败: {e}")
            return None

    def collect(self, package_name: str) -> Optional[Dict[str, float]]:
        """
        采集 CPU 使用率

        Args:
            package_name: 应用包名 (如 com.example.app)

        Returns:
            dict: {'appCpuRate': float, 'sysCpuRate': float} 或 None

        注意：
            - appCpuRate: 应用 CPU 使用率（百分比，0-100）
            - sysCpuRate: 系统 CPU 使用率（百分比，估算值）
            - 优先级（重新调整，使用实时值）：
              1. 精确算法（主要方法，基于 /proc/stat 的差值法，实时值）
              2. top 命令（备选，实时采样值）
              3. dumpsys cpuinfo（最后，累计平均值，不推荐）
        """
        try:
            # 方法1: 精确算法（主要方法，基于 /proc/stat 的差值法，实时值）
            # 首次采样返回 None 是正常的，需要两次采样计算差值
            pid = self._get_app_pid(package_name)
            if pid:
                precise_cpu = self._parse_cpu_from_proc_stat(pid)
                if precise_cpu is not None and precise_cpu > 0:
                    sys_cpu = min(100.0, precise_cpu * 1.5)
                    logger.info(f"[✓] 精确算法成功: CPU={precise_cpu}%")
                    return {"appCpuRate": precise_cpu, "sysCpuRate": round(sys_cpu, 2)}

            # 方法2: 使用 top 命令（备选，实时采样值）
            result = self._parse_cpu_from_top(package_name)
            if result and result.get("appCpuRate", 0) >= 0:
                logger.info(f"[✓] top 命令: CPU={result['appCpuRate']}%")
                return result

            # 方法3: 使用 dumpsys cpuinfo（最后，累计平均值，不推荐）
            result = self._parse_cpu_from_dumpsys(package_name)
            if result and result.get("appCpuRate", 0) >= 0:
                logger.info(f"[✓] dumpsys cpuinfo: CPU={result['appCpuRate']}%")
                return result

            # 如果都失败，返回默认值
            logger.debug(f"无法获取 {package_name} 的 CPU 使用率")
            return {"appCpuRate": 0.0, "sysCpuRate": 0.0}

        except Exception as e:
            logger.error(f"Android CPU 采集失败: {e}")
            # 返回默认值而非 None，避免后续处理失败
            return {"appCpuRate": 0.0, "sysCpuRate": 0.0}
