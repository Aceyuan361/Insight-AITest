# -*- coding: utf-8 -*-
"""
iOS CPU 采集器 (已弃用)

.. deprecated::
    请使用 py-ios-device 架构（PyIOSConnection + SysMontapCollector）
    此类仅为向后兼容保留，将在未来版本中移除。

    推荐迁移方式：
    from insight_eyes.public.ios.pyios_connect import PyIOSConnection
    from insight_eyes.public.ios.pyios_collectors.sysmontap import SysMontapCollector
    from insight_eyes.public.ios.data_normalizer import IOSDataNormalizer

    connection = PyIOSConnection(udid)
    connection.connect()
    collector = SysMontapCollector(connection.rpc, bundle_id)
    collector.configure()
    collector.start()
    raw_data = collector.collect_cpu()
    normalized_data = IOSDataNormalizer.normalize_cpu(raw_data)

使用 tidevice 实现无需越狱的 iOS CPU 性能数据采集

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License

Author: Aceyuan361
"""
import subprocess
import re
from typing import Optional, Dict
from logzero import logger


class CPUCollector:
    """
    iOS CPU 使用率采集器（已弃用）

    .. deprecated::
        请使用 py-ios-device 架构（PyIOSConnection + SysMontapCollector）
        此类仅为向后兼容保留，将在未来版本中移除。

    使用 tidevice perf 命令获取应用的 CPU 使用率
    """

    def __init__(self, udid: str):
        """
        初始化 CPU 采集器

        Args:
            udid: iOS 设备唯一标识符
        """
        logger.warning("[DEPRECATED] CPUCollector 已弃用，请使用 py-ios-device 架构")
        self.udid = udid
        self._check_tidevice()

    def _check_tidevice(self):
        """检查 tidevice 是否可用"""
        try:
            result = subprocess.run(
                ['tidevice', 'version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info(f"tidevice 可用: {result.stdout.strip()}")
            else:
                logger.warning("tidevice 未正确安装，CPU 采集可能不可用")
        except FileNotFoundError:
            logger.warning("未找到 tidevice 命令，请安装: pip install tidevice")

    def _run_tidevice(self, args: list, timeout: int = 30) -> Optional[str]:
        """
        执行 tidevice 命令

        Args:
            args: 命令参数列表
            timeout: 超时时间（秒）

        Returns:
            str: 命令输出，失败返回 None
        """
        cmd = ['tidevice', '--udid', self.udid] + args

        # 对于 perf 命令，使用 Popen 持续读取输出
        if 'perf' in args:
            return self._run_tidevice_perf(cmd, timeout)

        # 其他命令使用 run
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode != 0:
                logger.error(f"tidevice 命令失败: {result.stderr}")
                return None

            return result.stdout

        except subprocess.TimeoutExpired:
            logger.warning(f"tidevice 命令超时: {' '.join(args)}")
            return None
        except FileNotFoundError:
            logger.error("未找到 tidevice 命令，请安装: pip install tidevice")
            return None
        except Exception as e:
            logger.error(f"tidevice 执行异常: {e}")
            return None

    def _run_tidevice_perf(self, cmd: list, timeout: int) -> Optional[str]:
        """
        执行 tidevice perf 命令（持续输出型）

        使用 subprocess.run() 等待固定时间后获取所有输出

        Args:
            cmd: 完整的命令列表
            timeout: 超时时间（秒）

        Returns:
            str: 捕获的输出
        """
        try:
            # 修复：使用 shell=True 否则 tidevice perf 会检测到输出重定向而抑制输出
            cmd_str = ' '.join(cmd)
            logger.debug(f"[_run_tidevice_perf] 启动进程: {cmd_str}")

            # 使用 run() 等待固定时间后获取输出
            result = subprocess.run(
                cmd_str,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # 合并 stderr 到 stdout
                text=True,
                shell=True,  # 关键修复：使用 shell=True
                encoding='utf-8',
                errors='ignore',
                timeout=timeout  # run() 原生支持超时
            )

            if result.stdout:
                logger.debug(f"tidevice perf 成功获取 {len(result.stdout.splitlines())} 行数据")
                return result.stdout
            else:
                logger.warning(f"tidevice perf 未获取到数据")
                return None

        except subprocess.TimeoutExpired:
            # 超时是正常的，因为 tidevice perf 会持续输出
            # 我们只关心是否获取到了数据
            logger.debug(f"tidevice perf 超时（这是正常的）")
            return None
        except Exception as e:
            logger.error(f"tidevice perf 执行异常: {e}")
            return None

    def collect(self, bundle_id: str) -> Optional[Dict[str, float]]:
        """
        采集 CPU 使用率

        Args:
            bundle_id: 应用 Bundle ID (如 com.apple.mobilesafari)

        Returns:
            dict: {'appCpuRate': float, 'sysCpuRate': float} 或 None

        注意：
            - tidevice perf --io 需要应用在前台运行
            - CPU 使用率以百分比形式返回
            - 如果应用未运行或设备未连接，返回 None
        """
        try:
            # 使用 tidevice perf 获取性能数据
            # tidevice perf 命令会持续输出应用的性能指标
            # 使用 3 秒超时确保至少捕获一个数据点（tidevice perf 约每秒输出一次）
            output = self._run_tidevice(['perf', '-B', bundle_id, '-o', 'cpu'], timeout=3)

            if output:
                # 解析 CPU 数据
                # tidevice perf 输出格式 (Python字典):
                # cpu {'timestamp': ..., 'value': 0.0, 'sys_value': 67.85, ...}
                for line in output.split('\n'):
                    if line.strip().startswith('cpu '):
                        # 提取字典部分
                        dict_part = line[line.find('{'):]
                        try:
                            # 安全解析字典
                            import ast
                            data = ast.literal_eval(dict_part)
                            app_cpu = float(data.get('value', 0))
                            sys_cpu = float(data.get('sys_value', app_cpu))
                            return {
                                'appCpuRate': round(app_cpu, 2),
                                'sysCpuRate': round(sys_cpu, 2)
                            }
                        except (ValueError, SyntaxError) as e:
                            logger.debug(f"解析 CPU 数据失败: {e}")
                            continue

            # 如果无法获取数据，返回默认值
            logger.debug("无法通过 tidevice perf 获取 CPU 数据，可能应用未在前台运行")

            return {
                'appCpuRate': 0.0,
                'sysCpuRate': 0.0
            }

        except Exception as e:
            logger.error(f"iOS CPU 采集失败: {e}")
            return None
