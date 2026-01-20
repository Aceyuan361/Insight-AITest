# -*- coding: utf-8 -*-
"""
iOS 数据格式规范化器
统一不同采集方案的数据格式

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License

Author: Aceyuan361
"""
from typing import Any, Dict, Optional
from logzero import logger


class IOSDataNormalizer:
    """
    iOS 数据格式规范化器

    职责：
    1. 统一 py-ios-device 和 tidevice 的数据格式
    2. 确保返回格式与 Android 采集器一致
    3. 处理数据缺失或异常情况

    支持的采集方案：
    - py-ios-device: 原始格式需要转换
    - tidevice: 已是标准格式，直接返回
    """

    @staticmethod
    def normalize_cpu(raw_data: Any) -> Dict[str, float]:
        """
        统一 CPU 数据格式

        Tidevice 返回: {'appCpuRate': 15.2, 'sysCpuRate': 35.8}
        PyIOS 原始: {'cpuUsage': 15.2, 'sysCpuRate': 35.8, ...}

        统一输出: {'appCpuRate': float, 'sysCpuRate': float}

        Args:
            raw_data: 原始 CPU 数据

        Returns:
            dict: {'appCpuRate': float, 'sysCpuRate': float}
        """
        try:
            if not raw_data:
                return {'appCpuRate': 0.0, 'sysCpuRate': 0.0}

            # 已经是标准格式（tidevice 或已规范化）
            if isinstance(raw_data, dict):
                if 'appCpuRate' in raw_data:
                    app_cpu = float(raw_data.get('appCpuRate', 0))
                    sys_cpu = float(raw_data.get('sysCpuRate', app_cpu))
                    return {
                        'appCpuRate': round(app_cpu, 2),
                        'sysCpuRate': round(sys_cpu, 2)
                    }

                # py-ios-device 原始格式
                elif 'cpuUsage' in raw_data:
                    app_cpu = float(raw_data.get('cpuUsage', 0))
                    sys_cpu = float(raw_data.get('sysCpuRate', raw_data.get('cpuTotal', app_cpu)))
                    return {
                        'appCpuRate': round(app_cpu, 2),
                        'sysCpuRate': round(sys_cpu, 2)
                    }

            # 无法解析，返回默认值
            logger.debug(f"[数据规范化] CPU 数据格式未知: {type(raw_data)}")
            return {'appCpuRate': 0.0, 'sysCpuRate': 0.0}

        except (ValueError, TypeError) as e:
            logger.warning(f"[数据规范化] CPU 数据转换失败: {e}")
            return {'appCpuRate': 0.0, 'sysCpuRate': 0.0}

    @staticmethod
    def normalize_memory(raw_data: Any) -> Dict[str, float]:
        """
        统一 Memory 数据格式

        Tidevice 返回: {'totalPass': 120.5, 'nativePass': 120.5, 'dalvikPass': 0}
        PyIOS 原始: {'Memory': 120.5, 'memVirtualSize': 150000, ...}

        统一输出: {
            'totalPass': float,    # 总内存 (MB)
            'nativePass': float,   # Native 内存 (MB)
            'dalvikPass': float    # Dalvik 内存 (MB，iOS 上为 0)
        }

        Args:
            raw_data: 原始 Memory 数据

        Returns:
            dict: {'totalPass': float, 'nativePass': float, 'dalvikPass': float}
        """
        try:
            if not raw_data:
                return {'totalPass': 0, 'nativePass': 0, 'dalvikPass': 0}

            # 已经是标准格式
            if isinstance(raw_data, dict):
                if 'totalPass' in raw_data:
                    total = float(raw_data.get('totalPass', 0))
                    native = float(raw_data.get('nativePass', total))
                    dalvik = float(raw_data.get('dalvikPass', 0))
                    return {
                        'totalPass': round(total, 2),
                        'nativePass': round(native, 2),
                        'dalvikPass': round(dalvik, 2)
                    }

                # py-ios-device 原始格式
                elif 'Memory' in raw_data or 'memVirtualSize' in raw_data:
                    # 提取内存值（可能是 MB 或 KB）
                    if 'Memory' in raw_data:
                        mem_value = float(raw_data['Memory'])
                        # 尝试识别单位
                        if 'MemoryUnit' in raw_data:
                            unit = raw_data['MemoryUnit'].upper()
                            if unit == 'KB':
                                mem_value = mem_value / 1024
                        return {
                            'totalPass': round(mem_value, 2),
                            'nativePass': round(mem_value, 2),
                            'dalvikPass': 0.0
                        }
                    elif 'memVirtualSize' in raw_data:
                        mem_value = float(raw_data['memVirtualSize'])
                        # 通常 memVirtualSize 单位是字节
                        mem_mb = mem_value / (1024 * 1024)
                        return {
                            'totalPass': round(mem_mb, 2),
                            'nativePass': round(mem_mb, 2),
                            'dalvikPass': 0.0
                        }

            # 无法解析
            logger.debug(f"[数据规范化] Memory 数据格式未知")
            return {'totalPass': 0, 'nativePass': 0, 'dalvikPass': 0}

        except (ValueError, TypeError) as e:
            logger.warning(f"[数据规范化] Memory 数据转换失败: {e}")
            return {'totalPass': 0, 'nativePass': 0, 'dalvikPass': 0}

    @staticmethod
    def normalize_fps(raw_data: Any) -> Dict[str, Any]:
        """
        统一 FPS 数据格式

        Tidevice 返回: {'fps': 60, 'jank': 0, 'bigJank': 0, 'ftime_avg': 16.67, ...}
        PyIOS 原始: {'FPS': 60, 'frameRate': 60, ...}

        统一输出: {
            'fps': int,             # 帧率
            'jank': int,            # 普通卡顿次数
            'bigJank': int,         # 严重卡顿次数
            'ftime_avg': float,     # 平均帧时间 (ms)
            'ftime_max': float,     # 最大帧时间 (ms)
            'ftime_min': float      # 最小帧时间 (ms)
        }

        Args:
            raw_data: 原始 FPS 数据

        Returns:
            dict: 标准化的 FPS 数据
        """
        try:
            if not raw_data:
                return IOSDataNormalizer._default_fps_data()

            # 已经是标准格式
            if isinstance(raw_data, dict):
                if 'fps' in raw_data:
                    fps = int(raw_data.get('fps', 60))
                    return {
                        'fps': fps,
                        'jank': int(raw_data.get('jank', 0)),
                        'bigJank': int(raw_data.get('bigJank', 0)),
                        'ftime_avg': float(raw_data.get('ftime_avg', 1000.0 / fps if fps > 0 else 0)),
                        'ftime_max': float(raw_data.get('ftime_max', 0)),
                        'ftime_min': float(raw_data.get('ftime_min', 0))
                    }

                # py-ios-device 原始格式
                elif 'FPS' in raw_data or 'fps' in raw_data or 'frameRate' in raw_data:
                    fps = int(raw_data.get('FPS', raw_data.get('fps', raw_data.get('frameRate', 60))))
                    ftime_avg = round(1000.0 / fps, 2) if fps > 0 else 0

                    # py-ios-device 基础实现，暂不提供卡顿检测
                    return {
                        'fps': fps,
                        'jank': 0,
                        'bigJank': 0,
                        'ftime_avg': ftime_avg,
                        'ftime_max': round(ftime_avg * 1.2, 2),  # 估算最大帧时间
                        'ftime_min': round(ftime_avg * 0.8, 2)   # 估算最小帧时间
                    }

            # 无法解析，返回 iOS 标准帧率
            logger.debug(f"[数据规范化] FPS 数据格式未知，使用默认值")
            return IOSDataNormalizer._default_fps_data()

        except (ValueError, TypeError) as e:
            logger.warning(f"[数据规范化] FPS 数据转换失败: {e}")
            return IOSDataNormalizer._default_fps_data()

    @staticmethod
    def _default_fps_data() -> Dict[str, Any]:
        """返回 iOS 标准帧率数据"""
        return {
            'fps': 60,
            'jank': 0,
            'bigJank': 0,
            'ftime_avg': 16.67,  # 60fps 对应的帧时间
            'ftime_max': 20.0,
            'ftime_min': 16.0
        }

    @staticmethod
    def normalize_network(raw_data: Any) -> Dict[str, float]:
        """
        统一 Network 数据格式

        Tidevice 返回: {'upFlow': 0, 'downFlow': 0}
        PyIOS 原始: {'networkIn': 1024, 'networkOut': 512, ...}

        统一输出: {'upFlow': float, 'downFlow': float}  # 单位 KB/s

        Args:
            raw_data: 原始 Network 数据

        Returns:
            dict: {'upFlow': float, 'downFlow': float}
        """
        try:
            if not raw_data:
                return {'upFlow': 0, 'downFlow': 0}

            # 已经是标准格式
            if isinstance(raw_data, dict):
                if 'upFlow' in raw_data:
                    up = float(raw_data.get('upFlow', 0))
                    down = float(raw_data.get('downFlow', 0))
                    return {'upFlow': round(up, 2), 'downFlow': round(down, 2)}

                # py-ios-device 原始格式
                elif 'networkIn' in raw_data or 'networkOut' in raw_data:
                    # networkIn 是下行，networkOut 是上行
                    down = float(raw_data.get('networkIn', 0))
                    up = float(raw_data.get('networkOut', 0))

                    # 单位转换（通常是字节，转换为 KB）
                    down_kb = down / 1024
                    up_kb = up / 1024

                    return {'upFlow': round(up_kb, 2), 'downFlow': round(down_kb, 2)}

            # 无法解析
            return {'upFlow': 0, 'downFlow': 0}

        except (ValueError, TypeError) as e:
            logger.warning(f"[数据规范化] Network 数据转换失败: {e}")
            return {'upFlow': 0, 'downFlow': 0}

    @staticmethod
    def normalize_battery(raw_data: Any) -> Dict[str, Any]:
        """
        统一 Battery 数据格式

        Tidevice 返回: {'level': 85, 'temperature': 0, 'current': 0, ...}
        PyIOS 原始: {'BatteryLevel': 85, 'BatteryTemperature': 28.5, ...}

        统一输出: {
            'level': int,           # 电量百分比
            'temperature': float,   # 温度 (°C)
            'current': float,       # 电流 (mA)
            'voltage': float,       # 电压 (V)
            'power': float,         # 功率 (W)
            'status': str           # 充电状态
        }

        Args:
            raw_data: 原始 Battery 数据

        Returns:
            dict: 标准化的 Battery 数据
        """
        try:
            if not raw_data:
                return IOSDataNormalizer._default_battery_data()

            # 已经是标准格式
            if isinstance(raw_data, dict):
                if 'level' in raw_data:
                    return {
                        'level': int(raw_data.get('level', 0)),
                        'temperature': float(raw_data.get('temperature', 0)),
                        'current': float(raw_data.get('current', 0)),
                        'voltage': float(raw_data.get('voltage', 0)),
                        'power': float(raw_data.get('power', 0)),
                        'status': raw_data.get('status', 'unknown')
                    }

                # py-ios-device 原始格式
                elif 'BatteryLevel' in raw_data or 'BatteryCurrent' in raw_data:
                    level = int(raw_data.get('BatteryLevel', raw_data.get('level', 0)))
                    temp = float(raw_data.get('BatteryTemperature', raw_data.get('temperature', 0)))
                    current = float(raw_data.get('BatteryCurrent', raw_data.get('current', 0)))
                    voltage = float(raw_data.get('BatteryVoltage', raw_data.get('voltage', 0)))

                    # 计算功率 (W = V * A)
                    power = round(abs(voltage * current / 1000), 3) if voltage > 0 and current != 0 else 0

                    return {
                        'level': level,
                        'temperature': round(temp, 1),
                        'current': round(current, 2),
                        'voltage': round(voltage, 2),
                        'power': power,
                        'status': raw_data.get('BatteryStatus', raw_data.get('status', 'unknown'))
                    }

            # 无法解析
            return IOSDataNormalizer._default_battery_data()

        except (ValueError, TypeError) as e:
            logger.warning(f"[数据规范化] Battery 数据转换失败: {e}")
            return IOSDataNormalizer._default_battery_data()

    @staticmethod
    def _default_battery_data() -> Dict[str, Any]:
        """返回默认电池数据"""
        return {
            'level': 0,
            'temperature': 0,
            'current': 0,
            'voltage': 0,
            'power': 0,
            'status': 'unknown'
        }

    @staticmethod
    def normalize_gpu(raw_data: Any) -> Dict[str, Any]:
        """
        统一 GPU 数据格式

        统一输出: {
            'gpu': int,             # GPU 使用率
            'gpu_freq': int,        # GPU 频率 (MHz)
            'gpu_vendor': str,      # GPU 厂商
            'gpu_model': str        # GPU 型号
        }

        Args:
            raw_data: 原始 GPU 数据

        Returns:
            dict: 标准化的 GPU 数据
        """
        try:
            if not raw_data:
                return IOSDataNormalizer._default_gpu_data()

            # 已经是标准格式
            if isinstance(raw_data, dict):
                if 'gpu' in raw_data:
                    return {
                        'gpu': int(raw_data.get('gpu', 0)),
                        'gpu_freq': int(raw_data.get('gpu_freq', 0)),
                        'gpu_vendor': raw_data.get('gpu_vendor', 'apple'),
                        'gpu_model': raw_data.get('gpu_model', 'Apple GPU')
                    }

                # py-ios-device 原始格式
                elif 'GPUUtilization' in raw_data or 'gpuUsage' in raw_data:
                    gpu = int(raw_data.get('GPUUtilization', raw_data.get('gpuUsage', 0)))
                    return {
                        'gpu': gpu,
                        'gpu_freq': 0,  # iOS 一般不提供频率信息
                        'gpu_vendor': 'apple',
                        'gpu_model': 'Apple GPU'
                    }

            # 无法解析
            return IOSDataNormalizer._default_gpu_data()

        except (ValueError, TypeError) as e:
            logger.warning(f"[数据规范化] GPU 数据转换失败: {e}")
            return IOSDataNormalizer._default_gpu_data()

    @staticmethod
    def _default_gpu_data() -> Dict[str, Any]:
        """返回默认 GPU 数据"""
        return {
            'gpu': 0,
            'gpu_freq': 0,
            'gpu_vendor': 'apple',
            'gpu_model': 'Apple GPU'
        }
