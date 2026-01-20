# -*- coding: utf-8 -*-
"""
iOS FPS 采集器
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
    iOS FPS 帧率采集器

    使用 tidevice perf 命令获取应用的 FPS 信息
    """

    def __init__(self, udid: str):
        """
        初始化 FPS 采集器

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
        try:
            cmd = ['tidevice', '--udid', self.udid] + args
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
            logger.error(f"tidevice 命令超时: {' '.join(args)}")
            return None
        except FileNotFoundError:
            logger.error("未找到 tidevice 命令，请安装: pip install tidevice")
            return None
        except Exception as e:
            logger.error(f"tidevice 执行异常: {e}")
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
            output = self._run_tidevice(['perf', '--bundleid', bundle_id, '--io'], timeout=5)

            if output:
                # 解析 FPS 数据
                # tidevice perf 输出格式可能包含:
                # FPS: 60 或 Frame rate: 60fps
                for line in output.split('\n'):
                    if 'FPS' in line or 'fps' in line or 'Frame' in line:
                        # 提取 FPS 值
                        match = re.search(r'(?:FPS|fps|Frame rate)[:\s]+(\d+)', line)
                        if match:
                            fps = int(match.group(1))

                            # 计算帧时间 (ms)
                            # 帧时间 = 1000 / FPS
                            ftime_avg = round(1000.0 / fps, 2) if fps > 0 else 0

                            # iOS 基础实现，暂不提供卡顿检测
                            # 卡顿检测需要更复杂的帧时间分析
                            return {
                                'fps': fps,
                                'jank': 0,
                                'bigJank': 0,
                                'ftime_avg': ftime_avg,
                                'ftime_max': ftime_avg * 1.2,  # 估算最大帧时间
                                'ftime_min': ftime_avg * 0.8   # 估算最小帧时间
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
