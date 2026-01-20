# -*- coding: utf-8 -*-
"""
数据验证器模块

负责验证从设备采集的原始性能数据，确保数据有效性和完整性。

主要功能:
- 验证 FPS 数据的有效性
- 验证内存数据的有效性
- 验证 CPU 数据的有效性
- 验证网络数据的有效性
- 提供详细的验证错误报告

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum


class ValidationErrorSeverity(str, Enum):
    """验证错误严重程度"""
    WARNING = "warning"      # 警告：数据可能有问题但可以使用
    ERROR = "error"          # 错误：数据无效，需要修复或丢弃
    CRITICAL = "critical"    # 严重：数据完全无效，必须丢弃


@dataclass
class ValidationError:
    """验证错误记录"""
    field_name: str                    # 字段名
    expected: str                      # 期望值/范围
    actual: Any                        # 实际值
    severity: ValidationErrorSeverity   # 严重程度
    message: str                       # 错误消息
    suggestion: Optional[str] = None   # 修复建议

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'field_name': self.field_name,
            'expected': self.expected,
            'actual': str(self.actual),
            'severity': self.severity.value,
            'message': self.message,
            'suggestion': self.suggestion
        }


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool                     # 是否通过验证
    metric_type: str                   # 指标类型 (fps/memory/cpu/network)
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """是否有错误"""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """是否有警告"""
        return len(self.warnings) > 0

    @property
    def error_count(self) -> int:
        """错误数量"""
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        """警告数量"""
        return len(self.warnings)

    def get_all_messages(self) -> List[str]:
        """获取所有验证消息"""
        messages = []
        for error in self.errors:
            messages.append(f"[ERROR] {error.field_name}: {error.message}")
        for warning in self.warnings:
            messages.append(f"[WARNING] {warning.field_name}: {warning.message}")
        return messages

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'is_valid': self.is_valid,
            'metric_type': self.metric_type,
            'error_count': self.error_count,
            'warning_count': self.warning_count,
            'errors': [e.to_dict() for e in self.errors],
            'warnings': [w.to_dict() for w in self.warnings]
        }


class DataValidator:
    """
    数据验证器

    验证从设备采集的原始性能数据，确保数据有效性和完整性。
    支持链式调用，可批量验证多个指标。

    使用示例:
        validator = DataValidator()

        # 验证单个指标
        result = validator.validate_fps({'fps': 60, 'jank': 0})
        if not result.is_valid:
            print(result.get_all_messages())

        # 验证原始数据
        result = validator.validate_raw_data({
            'fps': {'fps': 60},
            'memory': {'totalPass': 100},
            'cpu': {'appCpuRate': 50}
        })
    """

    # FPS 数据的有效范围
    FPS_MIN = 0.0
    FPS_MAX = 240.0      # 支持高刷新率设备
    FPS_TYPICAL_MIN = 10.0  # 低于此值可能有问题

    # 帧时间有效范围 (毫秒)
    FRAME_TIME_MIN = 0.0
    FRAME_TIME_MAX = 5000.0   # 5秒已经是极端卡顿

    # 内存有效范围 (MB)
    MEMORY_MIN = 0.0
    MEMORY_MAX = 16384.0      # 16GB，对于移动应用已经足够大
    MEMORY_WARNING_THRESHOLD = 1024.0   # 1GB

    # CPU 有效范围 (%)
    CPU_MIN = 0.0
    CPU_MAX = 100.0

    # 网络速度有效范围 (KB/s)
    NETWORK_SPEED_MIN = 0.0
    NETWORK_SPEED_MAX = 102400.0  # 100 MB/s

    # 网络总量有效范围 (MB)
    NETWORK_TOTAL_MIN = 0.0
    NETWORK_TOTAL_MAX = 1048576.0  # 1 TB

    def __init__(self, strict_mode: bool = False):
        """
        初始化数据验证器

        Args:
            strict_mode: 严格模式，在严格模式下更多警告会被视为错误
        """
        self._strict_mode = strict_mode
        self._validation_history: List[ValidationResult] = []

    def validate_raw_data(self, raw_data: Dict[str, Any]) -> ValidationResult:
        """
        验证完整的原始数据

        Args:
            raw_data: 原始数据字典，包含 fps/memory/cpu/network 等键

        Returns:
            ValidationResult: 验证结果
        """
        all_errors = []
        all_warnings = []

        # 验证各个指标
        metric_types = ['fps', 'memory', 'cpu', 'network']

        for metric_type in metric_types:
            if metric_type in raw_data and raw_data[metric_type]:
                result = self._validate_by_type(metric_type, raw_data[metric_type])
                all_errors.extend(result.errors)
                all_warnings.extend(result.warnings)

        # 创建综合结果
        is_valid = len(all_errors) == 0

        result = ValidationResult(
            is_valid=is_valid,
            metric_type='raw_data',
            errors=all_errors,
            warnings=all_warnings
        )

        self._validation_history.append(result)
        return result

    def validate_fps(self, fps_data: Dict[str, Any]) -> ValidationResult:
        """
        验证 FPS 数据

        Args:
            fps_data: FPS 数据字典，可能的键:
                - fps: 帧率
                - jank: 卡顿次数
                - bigJank: 大卡顿次数
                - ftime_avg: 平均帧时间
                - ftime_max: 最大帧时间

        Returns:
            ValidationResult: 验证结果
        """
        errors = []
        warnings = []

        # 验证 fps
        fps = fps_data.get('fps')
        if fps is not None:
            try:
                fps_value = float(fps)
                if fps_value < self.FPS_MIN:
                    errors.append(ValidationError(
                        field_name='fps',
                        expected=f'>= {self.FPS_MIN}',
                        actual=fps_value,
                        severity=ValidationErrorSeverity.CRITICAL,
                        message='FPS 不能为负数',
                        suggestion='设置为 0 或丢弃此数据'
                    ))
                elif fps_value < self.FPS_TYPICAL_MIN:
                    warnings.append(ValidationError(
                        field_name='fps',
                        expected=f'>= {self.FPS_TYPICAL_MIN}',
                        actual=fps_value,
                        severity=ValidationErrorSeverity.WARNING,
                        message='FPS 异常低，可能存在严重性能问题',
                        suggestion='检查应用性能状态'
                    ))
                elif fps_value > self.FPS_MAX:
                    warnings.append(ValidationError(
                        field_name='fps',
                        expected=f'<= {self.FPS_MAX}',
                        actual=fps_value,
                        severity=ValidationErrorSeverity.WARNING,
                        message='FPS 异常高，超过典型设备范围',
                        suggestion='确认设备刷新率设置'
                    ))
            except (ValueError, TypeError):
                errors.append(ValidationError(
                    field_name='fps',
                    expected='numeric value',
                    actual=fps,
                    severity=ValidationErrorSeverity.ERROR,
                    message='FPS 必须是数字',
                    suggestion='转换为数字或丢弃此数据'
                ))
        else:
            warnings.append(ValidationError(
                field_name='fps',
                expected='存在 fps 字段',
                actual='None',
                severity=ValidationErrorSeverity.WARNING,
                message='FPS 数据缺失',
                suggestion='检查采集器是否正常工作'
            ))

        # 验证卡顿次数
        for field in ['jank', 'bigJank', 'jank_count', 'big_jank_count']:
            jank_value = fps_data.get(field)
            if jank_value is not None:
                try:
                    jank_int = int(jank_value)
                    if jank_int < 0:
                        errors.append(ValidationError(
                            field_name=field,
                            expected='>= 0',
                            actual=jank_int,
                            severity=ValidationErrorSeverity.ERROR,
                            message=f'{field} 不能为负数',
                            suggestion='使用绝对值或设置为 0'
                        ))
                except (ValueError, TypeError):
                    errors.append(ValidationError(
                        field_name=field,
                        expected='integer',
                        actual=jank_value,
                        severity=ValidationErrorSeverity.ERROR,
                        message=f'{field} 必须是整数',
                        suggestion='转换为整数'
                    ))

        # 验证帧时间
        for field in ['ftime_avg', 'ftime_max', 'frame_time_avg', 'frame_time_max']:
            frame_time = fps_data.get(field)
            if frame_time is not None:
                try:
                    frame_time_value = float(frame_time)
                    if frame_time_value < self.FRAME_TIME_MIN:
                        errors.append(ValidationError(
                            field_name=field,
                            expected=f'>= {self.FRAME_TIME_MIN}',
                            actual=frame_time_value,
                            severity=ValidationErrorSeverity.ERROR,
                            message=f'{field} 不能为负数',
                            suggestion='设置为 0'
                        ))
                    elif frame_time_value > self.FRAME_TIME_MAX:
                        errors.append(ValidationError(
                            field_name=field,
                            expected=f'<= {self.FRAME_TIME_MAX}',
                            actual=frame_time_value,
                            severity=ValidationErrorSeverity.ERROR,
                            message=f'{field} 超出合理范围',
                            suggestion='检查数据来源'
                        ))
                except (ValueError, TypeError):
                    errors.append(ValidationError(
                        field_name=field,
                        expected='numeric value',
                        actual=frame_time,
                        severity=ValidationErrorSeverity.ERROR,
                        message=f'{field} 必须是数字',
                        suggestion='转换为数字'
                    ))

        is_valid = len(errors) == 0 or (not self._strict_mode and len(errors) == 0)

        result = ValidationResult(
            is_valid=is_valid,
            metric_type='fps',
            errors=errors,
            warnings=warnings
        )

        self._validation_history.append(result)
        return result

    def validate_memory(self, memory_data: Dict[str, Any]) -> ValidationResult:
        """
        验证内存数据

        Args:
            memory_data: 内存数据字典，可能的键:
                - totalPass/total: 总内存 (KB)
                - nativePass/native: Native 堆内存 (KB)
                - dalvikPass/dalvik: Dalvik 堆内存 (KB)

        Returns:
            ValidationResult: 验证结果
        """
        errors = []
        warnings = []

        # 内存字段映射 (可能的键名)
        memory_fields = {
            'totalPass': 'total',
            'nativePass': 'native',
            'dalvikPass': 'dalvik',
            'total': 'total',
            'native': 'native',
            'dalvik': 'dalvik'
        }

        for field, metric_name in memory_fields.items():
            if field in memory_data and memory_data[field] is not None:
                value = memory_data[field]
                try:
                    value_mb = float(value) / 1024.0  # 转换为 MB

                    if value_mb < self.MEMORY_MIN:
                        errors.append(ValidationError(
                            field_name=field,
                            expected=f'>= {self.MEMORY_MIN} MB',
                            actual=f'{value_mb} MB',
                            severity=ValidationErrorSeverity.ERROR,
                            message=f'{metric_name} 内存不能为负数',
                            suggestion='使用绝对值'
                        ))
                    elif value_mb > self.MEMORY_MAX:
                        errors.append(ValidationError(
                            field_name=field,
                            expected=f'<= {self.MEMORY_MAX} MB',
                            actual=f'{value_mb} MB',
                            severity=ValidationErrorSeverity.ERROR,
                            message=f'{metric_name} 内存超出合理范围',
                            suggestion='检查数据单位，可能需要转换为 MB'
                        ))
                    elif value_mb > self.MEMORY_WARNING_THRESHOLD and metric_name == 'total':
                        warnings.append(ValidationError(
                            field_name=field,
                            expected=f'<= {self.MEMORY_WARNING_THRESHOLD} MB',
                            actual=f'{value_mb} MB',
                            severity=ValidationErrorSeverity.WARNING,
                            message='总内存占用较高',
                            suggestion='检查是否存在内存泄漏'
                        ))
                except (ValueError, TypeError):
                    errors.append(ValidationError(
                        field_name=field,
                        expected='numeric value (KB)',
                        actual=value,
                        severity=ValidationErrorSeverity.ERROR,
                        message=f'{field} 必须是数字',
                        suggestion='转换为数字'
                    ))

        is_valid = len(errors) == 0

        result = ValidationResult(
            is_valid=is_valid,
            metric_type='memory',
            errors=errors,
            warnings=warnings
        )

        self._validation_history.append(result)
        return result

    def validate_cpu(self, cpu_data: Dict[str, Any]) -> ValidationResult:
        """
        验证 CPU 数据

        Args:
            cpu_data: CPU 数据字典，可能的键:
                - appCpuRate: 应用 CPU 占用率 (%)
                - sysCpuRate: 系统 CPU 占用率 (%)

        Returns:
            ValidationResult: 验证结果
        """
        errors = []
        warnings = []

        # CPU 字段映射
        cpu_fields = {
            'appCpuRate': 'app_cpu',
            'sysCpuRate': 'sys_cpu',
            'app_cpu': 'app_cpu',
            'sys_cpu': 'sys_cpu'
        }

        for field, metric_name in cpu_fields.items():
            if field in cpu_data and cpu_data[field] is not None:
                value = cpu_data[field]
                try:
                    cpu_value = float(value)

                    if cpu_value < self.CPU_MIN:
                        errors.append(ValidationError(
                            field_name=field,
                            expected=f'>= {self.CPU_MIN}%',
                            actual=f'{cpu_value}%',
                            severity=ValidationErrorSeverity.ERROR,
                            message=f'{metric_name} 不能为负数',
                            suggestion='使用绝对值或设置为 0'
                        ))
                    elif cpu_value > self.CPU_MAX:
                        errors.append(ValidationError(
                            field_name=field,
                            expected=f'<= {self.CPU_MAX}%',
                            actual=f'{cpu_value}%',
                            severity=ValidationErrorSeverity.ERROR,
                            message=f'{metric_name} 超出 100%',
                            suggestion='检查数据计算方式'
                        ))
                    elif cpu_value > 90.0 and metric_name == 'app_cpu':
                        warnings.append(ValidationError(
                            field_name=field,
                            expected='<= 90%',
                            actual=f'{cpu_value}%',
                            severity=ValidationErrorSeverity.WARNING,
                            message='应用 CPU 占用率很高',
                            suggestion='检查是否存在性能瓶颈'
                        ))
                except (ValueError, TypeError):
                    errors.append(ValidationError(
                        field_name=field,
                        expected='percentage (0-100)',
                        actual=value,
                        severity=ValidationErrorSeverity.ERROR,
                        message=f'{field} 必须是数字',
                        suggestion='转换为数字'
                    ))

        is_valid = len(errors) == 0

        result = ValidationResult(
            is_valid=is_valid,
            metric_type='cpu',
            errors=errors,
            warnings=warnings
        )

        self._validation_history.append(result)
        return result

    def validate_network(self, network_data: Dict[str, Any]) -> ValidationResult:
        """
        验证网络数据

        Args:
            network_data: 网络数据字典，可能的键:
                - upFlow: 上行流量 (KB)
                - downFlow: 下行流量 (KB)

        Returns:
            ValidationResult: 验证结果
        """
        errors = []
        warnings = []

        # 网络字段映射
        network_fields = {
            'upFlow': 'upload',
            'downFlow': 'download',
            'upload': 'upload',
            'download': 'download'
        }

        for field, metric_name in network_fields.items():
            if field in network_data and network_data[field] is not None:
                value = network_data[field]
                try:
                    network_value = float(value)

                    if network_value < self.NETWORK_SPEED_MIN:
                        errors.append(ValidationError(
                            field_name=field,
                            expected=f'>= {self.NETWORK_SPEED_MIN}',
                            actual=network_value,
                            severity=ValidationErrorSeverity.ERROR,
                            message=f'{metric_name} 不能为负数',
                            suggestion='使用绝对值或设置为 0'
                        ))
                except (ValueError, TypeError):
                    errors.append(ValidationError(
                        field_name=field,
                        expected='numeric value',
                        actual=value,
                        severity=ValidationErrorSeverity.ERROR,
                        message=f'{field} 必须是数字',
                        suggestion='转换为数字'
                    ))

        is_valid = len(errors) == 0

        result = ValidationResult(
            is_valid=is_valid,
            metric_type='network',
            errors=errors,
            warnings=warnings
        )

        self._validation_history.append(result)
        return result

    def _validate_by_type(self, metric_type: str, data: Dict[str, Any]) -> ValidationResult:
        """根据类型调用相应的验证方法"""
        validators = {
            'fps': self.validate_fps,
            'memory': self.validate_memory,
            'cpu': self.validate_cpu,
            'network': self.validate_network
        }

        validator = validators.get(metric_type)
        if validator:
            return validator(data)
        else:
            return ValidationResult(
                is_valid=False,
                metric_type=metric_type,
                errors=[ValidationError(
                    field_name='metric_type',
                    expected='fps/memory/cpu/network',
                    actual=metric_type,
                    severity=ValidationErrorSeverity.ERROR,
                    message=f'未知的指标类型: {metric_type}',
                    suggestion='使用有效的指标类型'
                )]
            )

    def get_validation_summary(self) -> Dict[str, Any]:
        """
        获取验证历史摘要

        Returns:
            验证统计信息
        """
        total = len(self._validation_history)
        valid = sum(1 for r in self._validation_history if r.is_valid)
        invalid = total - valid
        total_errors = sum(r.error_count for r in self._validation_history)
        total_warnings = sum(r.warning_count for r in self._validation_history)

        return {
            'total_validations': total,
            'valid_count': valid,
            'invalid_count': invalid,
            'success_rate': (valid / total * 100) if total > 0 else 0,
            'total_errors': total_errors,
            'total_warnings': total_warnings
        }

    def clear_history(self) -> None:
        """清空验证历史"""
        self._validation_history.clear()


# 便捷函数
def validate_raw_data(raw_data: Dict[str, Any], strict_mode: bool = False) -> ValidationResult:
    """
    验证原始数据的便捷函数

    Args:
        raw_data: 原始数据字典
        strict_mode: 是否使用严格模式

    Returns:
        ValidationResult: 验证结果
    """
    validator = DataValidator(strict_mode=strict_mode)
    return validator.validate_raw_data(raw_data)


def validate_fps(fps_data: Dict[str, Any]) -> ValidationResult:
    """验证 FPS 数据的便捷函数"""
    validator = DataValidator()
    return validator.validate_fps(fps_data)


def validate_memory(memory_data: Dict[str, Any]) -> ValidationResult:
    """验证内存数据的便捷函数"""
    validator = DataValidator()
    return validator.validate_memory(memory_data)


def validate_cpu(cpu_data: Dict[str, Any]) -> ValidationResult:
    """验证 CPU 数据的便捷函数"""
    validator = DataValidator()
    return validator.validate_cpu(cpu_data)


def validate_network(network_data: Dict[str, Any]) -> ValidationResult:
    """验证网络数据的便捷函数"""
    validator = DataValidator()
    return validator.validate_network(network_data)
