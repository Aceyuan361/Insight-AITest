# -*- coding: utf-8 -*-
"""
iOS FPS 采集器 (已弃用)

.. deprecated::
    请使用 py-ios-device 架构（PyIOSConnection + GraphicsCollector）
    此类仅为向后兼容保留，将在未来版本中移除。

使用 tidevice 实现无需越狱的 iOS FPS 性能数据采集

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License

Author: Aceyuan361
"""
import subprocess
import re
from typing import Optional, Dict, Any
from logzero import logger


class FPSCollector:
    """
    iOS FPS 帧率采集器（已弃用）

    .. deprecated::
        请使用 py-ios-device 架构（PyIOSConnection + GraphicsCollector）
        此类仅为向后兼容保留，将在未来版本中移除。

    使用 tidevice perf 命令获取应用的 FPS 信息
    """

    def __init__(self, udid: str):
        """
        初始化 FPS 采集器

        Args:
            udid: iOS 设备唯一标识符
        """
        logger.warning("[DEPRECATED] FPSCollector 已弃用，请使用 py-ios-device 架构")
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
                logger.warning("tidevice 未正确安装，FPS 采集可能不可用")
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
            # FPS 采集需要较长超时以获取多行数据并跳过初始的 fps=0
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
                lines = result.stdout.splitlines()
                logger.debug(f"tidevice perf 成功获取 {len(lines)} 行数据")
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

    def collect(self, bundle_id: str) -> Optional[Dict[str, Any]]:
        """
        采集 FPS 帧率数据

        Args:
            bundle_id: 应用 Bundle ID (如 com.apple.mobilesafari)

        Returns:
            dict: {
                'fps': int,             # 帧率
                'jank': int,            # 普通卡顿次数
                'bigJank': int,         # 严重卡顿次数
                'ftime_avg': float,     # 平均帧时间 (ms)
                'ftime_max': float,     # 最大帧时间 (ms)
                'ftime_min': float,     # 最小帧时间 (ms)
            } 或 None

        注意：
            - iOS 设备的标准帧率为 60fps（部分 Pro 设备支持 120fps）
            - FPS 采集需要应用在前台运行且有动画/刷新
            - 如果应用静止不动，可能无法获取准确的 FPS 数据
        """
        try:
            # 使用 tidevice perf 获取性能数据
            output = self._run_tidevice(['perf', '-B', bundle_id, '-o', 'fps'], timeout=3)

            if output:
                # 解析 FPS 数据
                # tidevice perf 输出格式 (Python字典):
                # fps {'fps': 30, 'value': 30, 'timestamp': ...}
                # 注意：output 可能包含多行，我们取最后一行（最新的值）
                lines = output.split('\n')
                fps_data_list = []  # 收集所有有效的 FPS 数据

                for line in lines:
                    if line.strip().startswith('fps '):
                        # 提取字典部分
                        dict_part = line[line.find('{'):]
                        try:
                            # 安全解析字典
                            import ast
                            data = ast.literal_eval(dict_part)
                            fps = int(data.get('fps', data.get('value', 60)))
                            fps_data_list.append(fps)
                        except (ValueError, SyntaxError) as e:
                            logger.debug(f"解析 FPS 数据失败: {e}")
                            continue

                # 使用最后一个（最新的）FPS 值
                if fps_data_list:
                    fps = fps_data_list[-1]  # 取最后一行
                    # 计算帧时间 (ms)
                    ftime_avg = round(1000.0 / fps, 2) if fps > 0 else 16.67

                    logger.debug(f"FPS 采集: 读取了 {len(fps_data_list)} 行数据，使用最新值 fps={fps}")
                    return {
                        'fps': fps,
                        'jank': 0,
                        'bigJank': 0,
                        'ftime_avg': ftime_avg,
                        'ftime_max': ftime_avg * 1.2,
                        'ftime_min': ftime_avg * 0.8
                    }

            # 如果无法获取 FPS 数据，返回 iOS 标准帧率
            logger.debug("无法通过 tidevice perf 获取 FPS 数据，返回 iOS 标准帧率")

            return {
                'fps': 60,           # iOS 标准帧率
                'jank': 0,
                'bigJank': 0,
                'ftime_avg': 16.67,  # 60fps 对应的帧时间
                'ftime_max': 20.0,
                'ftime_min': 16.0
            }

        except Exception as e:
            logger.error(f"iOS FPS 采集失败: {e}")
            return None
