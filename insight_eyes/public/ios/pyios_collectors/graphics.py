# -*- coding: utf-8 -*-
"""
Graphics 数据采集器
基于 Apple Instruments Graphics 服务的 FPS 和 GPU 数据采集

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License

Author: Aceyuan361
"""
from typing import Optional, Dict, Any
from logzero import logger

from .base import PyIOSCollectorBase


class GraphicsCollector(PyIOSCollectorBase):
    """
    Graphics 采集器

    Apple Instruments Graphics 服务提供：
    - FPS（帧率）
    - GPU 使用率
    - 图形渲染性能指标

    支持版本：iOS 17-26
    """

    def __init__(self, rpc_connection, bundle_id: str):
        """
        初始化 Graphics 采集器

        Args:
            rpc_connection: InstrumentServer RPC 连接
            bundle_id: 目标应用的 Bundle ID
        """
        super().__init__(rpc_connection)
        self.bundle_id = bundle_id
        self._service_name = "com.apple.instruments.server.services.graphics.opengl"

        # 配置参数
        self._sampling_interval = 1.0  # 采样间隔（秒）

        # FPS 统计
        self._frame_times = []  # 用于计算平均/最小/最大帧时间

    def configure(self) -> bool:
        """
        配置 Graphics 服务

        Returns:
            bool: 配置是否成功
        """
        try:
            # Graphics 服务通常使用默认配置
            logger.debug(f"[Graphics] ✓ 使用默认配置")
            return True

        except Exception as e:
            logger.error(f"[Graphics] ✗ 配置失败: {e}")
            return False

    def start(self) -> bool:
        """
        启动 Graphics 服务

        Returns:
            bool: 启动是否成功
        """
        try:
            self._rpc.call(
                self._service_name,
                "startSamplingAtTimeInterval:",
                self._sampling_interval
            )
            logger.info(f"[Graphics] ✓ 服务已启动: {self.bundle_id}")
            return True

        except Exception as e:
            logger.error(f"[Graphics] ✗ 启动失败: {e}")
            return False

    def stop(self) -> bool:
        """
        停止 Graphics 服务

        Returns:
            bool: 停止是否成功
        """
        try:
            self._rpc.call(self._service_name, "stop")
            logger.info(f"[Graphics] ✓ 服务已停止")
            return True

        except Exception as e:
            logger.error(f"[Graphics] ✗ 停止失败: {e}")
            return False

    def parse_message(self, message: Any) -> Optional[Dict[str, Any]]:
        """
        解析 Graphics 消息

        Graphics 消息格式可能包含：
        {
            'fps': 60,
            'frameRate': 60,
            'frameTimes': [16.5, 16.7, 16.3, ...],
            'gpuUtilization': 45,
            'renderer': 'Apple GPU'
        }

        Args:
            message: 原始 DTX 消息

        Returns:
            dict: {
                'fps': {...},
                'gpu': {...}
            }
        """
        try:
            if not message:
                return None

            # 提取所有数据
            result = {
                'fps': self._extract_fps_data(message),
                'gpu': self._extract_gpu_data(message)
            }

            return result

        except Exception as e:
            logger.error(f"[Graphics] 解析消息失败: {e}")
            return None

    def _extract_fps_data(self, message: Dict) -> Dict[str, Any]:
        """
        提取 FPS 数据

        卡顿检测说明：
        - jank（卡顿）：单帧时间 > 16.67ms（低于 60fps）
        - bigJank（严重卡顿）：单帧时间 > 100ms

        注意：与 Android FPS 采集器可能存在差异
        - Android: 基于 SurfaceFlinger 的帧时间戳，精确到纳秒级
        - iOS: 基于 Instruments Graphics 服务的帧时间数组（如果可用）
        - 卡顿次数为 frame_times 数组中的绝对次数，非百分比

        Args:
            message: Graphics 消息，可能包含以下字段：
                - fps/frameRate/FPS: 帧率值
                - frameTimes: 帧时间数组（单位：毫秒）

        Returns:
            dict: {
                'fps': int,          # 帧率
                'jank': int,         # 卡顿次数（>16.67ms）
                'bigJank': int,      # 严重卡顿次数（>100ms）
                'ftime_avg': float,  # 平均帧时间（ms）
                'ftime_max': float,  # 最大帧时间（ms）
                'ftime_min': float   # 最小帧时间（ms）
            }
        """
        try:
            # 尝试从消息中提取 FPS
            fps = 60  # iOS 标准帧率

            if isinstance(message, dict):
                # 尝试多种可能的字段名
                if 'fps' in message:
                    fps = int(message['fps'])
                elif 'frameRate' in message:
                    fps = int(message['frameRate'])
                elif 'FPS' in message:
                    fps = int(message['FPS'])

            # 计算帧时间
            ftime_avg = round(1000.0 / fps, 2) if fps > 0 else 0

            # 提取帧时间统计（如果有）
            frame_times = message.get('frameTimes', []) if isinstance(message, dict) else []
            if frame_times and len(frame_times) > 0:
                ftime_min = round(min(frame_times), 2)
                ftime_max = round(max(frame_times), 2)
                ftime_avg = round(sum(frame_times) / len(frame_times), 2)

                # 计算卡顿次数（基于帧时间数组中的样本）
                # 注意：这是绝对次数，不是百分比
                # 如果 frame_times 包含最近 1 秒的 60 个帧样本，则 jank=2 表示 2/60=3.3% 的帧卡顿
                jank = sum(1 for ft in frame_times if ft > 16.67)
                big_jank = sum(1 for ft in frame_times if ft > 100)
            else:
                # 如果没有帧时间数组，根据 FPS 估算
                ftime_min = round(ftime_avg * 0.8, 2)
                ftime_max = round(ftime_avg * 1.2, 2)
                jank = 0
                big_jank = 0

            return {
                'fps': fps,
                'jank': jank,
                'bigJank': big_jank,
                'ftime_avg': ftime_avg,
                'ftime_max': ftime_max,
                'ftime_min': ftime_min
            }

        except (KeyError, AttributeError, TypeError) as e:
            logger.warning(f"[Graphics] FPS 数据格式错误: {type(e).__name__}: {e}")
            # 返回 iOS 标准默认值
            return {
                'fps': 60,
                'jank': 0,
                'bigJank': 0,
                'ftime_avg': 16.67,
                'ftime_max': 20.0,
                'ftime_min': 16.0
            }
        except (ValueError, ArithmeticError) as e:
            logger.warning(f"[Graphics] FPS 数值转换失败: {e}")
            return {
                'fps': 60,
                'jank': 0,
                'bigJank': 0,
                'ftime_avg': 16.67,
                'ftime_max': 20.0,
                'ftime_min': 16.0
            }

    def _extract_gpu_data(self, message: Dict) -> Dict[str, Any]:
        """
        提取 GPU 数据

        Args:
            message: Graphics 消息

        Returns:
            dict: {
                'gpu': int,
                'gpu_freq': int,
                'gpu_vendor': str,
                'gpu_model': str
            }
        """
        try:
            gpu_usage = 0

            if isinstance(message, dict):
                # 尝试多种可能的字段名
                if 'gpuUtilization' in message:
                    gpu_usage = int(message['gpuUtilization'])
                elif 'gpuUsage' in message:
                    gpu_usage = int(message['gpuUsage'])
                elif 'gpu' in message:
                    gpu_usage = int(message['gpu'])

            return {
                'gpu': gpu_usage,
                'gpu_freq': 0,  # iOS 一般不提供频率信息
                'gpu_vendor': 'apple',
                'gpu_model': 'Apple GPU'
            }

        except (KeyError, AttributeError, TypeError) as e:
            logger.warning(f"[Graphics] GPU 数据格式错误: {type(e).__name__}: {e}")
            return {
                'gpu': 0,
                'gpu_freq': 0,
                'gpu_vendor': 'apple',
                'gpu_model': 'Apple GPU'
            }
        except (ValueError, ArithmeticError) as e:
            logger.warning(f"[Graphics] GPU 数值转换失败: {e}")
            return {
                'gpu': 0,
                'gpu_freq': 0,
                'gpu_vendor': 'apple',
                'gpu_model': 'Apple GPU'
            }

    def collect_fps(self) -> Optional[Dict[str, Any]]:
        """
        单次 FPS 采集（便捷方法）

        Returns:
            dict: FPS 数据
        """
        message = self.receive_message()
        if message:
            fps_data = self._extract_fps_data(message)
            return fps_data
        return None

    def collect_gpu(self) -> Optional[Dict[str, Any]]:
        """
        单次 GPU 采集（便捷方法）

        Returns:
            dict: GPU 数据
        """
        message = self.receive_message()
        if message:
            gpu_data = self._extract_gpu_data(message)
            return gpu_data
        return None
