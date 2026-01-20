# -*- coding: utf-8 -*-
"""
iOS CPU 采集器
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
    iOS CPU 使用率采集器

    使用 tidevice perf 命令获取应用的 CPU 使用率
    """

    def __init__(self, udid: str):
        """
        初始化 CPU 采集器

        Args:
            udid: iOS 设备唯一标识符
        """
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

        使用 Popen 持续读取输出，在获取数据或超时后终止进程

        Args:
            cmd: 完整的命令列表
            timeout: 超时时间（秒）

        Returns:
            str: 捕获的输出
        """
        import threading
        import time

        output_buffer = []
        process = None
        stop_reading = threading.Event()

        def read_output():
            nonlocal output_buffer
            try:
                for line in process.stdout:
                    if stop_reading.is_set():
                        break
                    line = line.decode('utf-8', errors='ignore').strip()
                    if line:
                        output_buffer.append(line)
                        # 获取到数据后通知主线程
                        if len(output_buffer) >= 1:
                            break
            except Exception:
                pass  # 线程退出时忽略错误

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,  # 忽略 stderr
                text=False
            )

            # 启动线程读取输出
            reader_thread = threading.Thread(target=read_output, daemon=True)
            reader_thread.start()

            # 等待获取数据或超时
            start_time = time.time()
            while time.time() - start_time < timeout:
                if output_buffer:
                    break
                time.sleep(0.1)

            # 清理进程
            stop_reading.set()  # 通知线程停止读取

            # 先关闭管道，让进程能够正常退出
            try:
                if process.stdout:
                    process.stdout.close()
            except:
                pass

            # 强制终止进程（Windows 上需要 kill）
            try:
                process.kill()
                process.wait(timeout=2)
            except:
                pass

            if output_buffer:
                output = '\n'.join(output_buffer)
                logger.debug(f"tidevice perf 成功获取 {len(output_buffer)} 行数据")
                return output
            else:
                logger.warning(f"tidevice perf 超时未获取到数据")
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
            # 使用 5 秒超时确保至少捕获一个数据点（tidevice perf 约每秒输出一次）
            output = self._run_tidevice(['perf', '-B', bundle_id, '-o', 'cpu'], timeout=5)

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
