# -*- coding: utf-8 -*-
"""
Android APM (Application Performance Monitor) 性能监控主类
提供 Android 应用的性能数据采集功能

改进：
- 集成设备配置系统（DeviceProfile）
- 根据设备厂商/ROM 自动选择最佳采集策略
- 支持 CPU/Memory/Network/FPS/Battery 各指标的智能采集
- 添加输入验证（P3-21）
"""

import re
import time
from logzero import logger

from insight_aitest.platform.services.collectors.android.cpu_collector import CPUCollector
from insight_aitest.platform.services.collectors.android.memory_collector import MemoryCollector
from insight_aitest.platform.services.collectors.android.fps_collector import FPSMonitor
from insight_aitest.platform.services.collectors.android.network_collector import NetworkCollector
from insight_aitest.platform.services.collectors.android.battery_collector import BatteryCollector
from insight_aitest.platform.services.collectors.android.device_profile import (
    get_device_profile,
    DeviceProfile,
)

# 包名验证正则表达式（P3-21）
# Android 包名格式: 至少两级，如 com.example.app
# 每部分以字母开头，只能包含字母、数字、下划线
_PACKAGE_NAME_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)+$")


def _validate_package_name(package_name: str) -> bool:
    """
    验证 Android 包名格式是否有效（P3-21）

    Args:
        package_name: 应用包名

    Returns:
        bool: 包名是否有效

    Examples:
        有效: com.example.app, com.company.myapp
        无效: example, com..app, 123.example, com.example
    """
    if not package_name or not isinstance(package_name, str):
        return False

    # 检查长度限制（Android 包名最长 200 字符）
    if len(package_name) > 200:
        logger.warning(f"包名过长: {len(package_name)} > 200 字符")
        return False

    # 使用正则表达式验证格式
    if not _PACKAGE_NAME_PATTERN.match(package_name):
        logger.warning(f"包名格式无效: {package_name}")
        return False

    return True


class AndroidAPM:
    """
    Android 应用性能监控器 - 集成设备配置系统

    支持采集的指标:
    - CPU 使用率（根据设备选择 dumpsys_cpuinfo 或 top）
    - 内存使用（根据设备选择最佳解析方式）
    - FPS 帧率（根据设备选择 gfxinfo 或 SurfaceFlinger）
    - 网络流量（根据设备选择 shell 包装）
    - 电池状态
    - GPU 使用率（暂不支持）

    设备适配：
    - 小米设备：优先使用 top，需要 ANSI 过滤
    - 华为设备：优先使用 dumpsys_cpuinfo
    - OPPO/vivo：优先使用 top
    - 三星/Google：优先使用 dumpsys_cpuinfo
    """

    def __init__(
        self,
        package_name,
        device_id,
        frequency=1.0,
        surfaceview=True,
        device_profile=None,
        **kwargs,
    ):
        """
        初始化 Android APM 监控器

        Args:
            package_name: 应用包名 (如 com.example.app)
            device_id: Android 设备 ID
            frequency: 采集频率（秒），范围 0.1-60
            surfaceview: 是否使用 SurfaceView FPS 采集方式
            device_profile: 设备配置档案（可选，为 None 时自动创建）
            **kwargs: 其他参数

        Raises:
            ValueError: 当包名格式无效或频率超出范围时
        """
        # 输入验证（P3-21）
        if not _validate_package_name(package_name):
            raise ValueError(
                f"无效的包名格式: {package_name}。包名应遵循 Android 命名规范，如 com.example.app"
            )

        if not isinstance(frequency, (int, float)) or frequency <= 0 or frequency > 60:
            raise ValueError(f"无效的采集频率: {frequency}。频率应在 0.1-60 秒之间")

        if not device_id or not isinstance(device_id, str):
            raise ValueError(f"无效的设备 ID: {device_id}")

        self.package_name = package_name
        self.device_id = device_id
        self.frequency = frequency
        self.surfaceview = surfaceview
        self.kwargs = kwargs

        # ============ 设备配置系统 ============
        # 获取或创建设备配置档案（自动检测厂商、ROM、Android 版本）
        self.device_profile: DeviceProfile = (
            device_profile if device_profile else get_device_profile(device_id)
        )
        self.strategy = self.device_profile.get_strategy()

        # 记录设备配置和采集策略
        logger.info(
            f"[设备配置] 厂商={self.device_profile.vendor.value}, "
            f"ROM={self.device_profile.rom_type.value}, "
            f"Android={self.device_profile.android_version}, "
            f"型号={self.device_profile.model}"
        )
        logger.info(
            f"[采集策略] FPS={self.strategy.fps_primary_method}, "
            f"CPU={self.strategy.cpu_primary_method}, "
            f"Memory={self.strategy.memory_primary_method}, "
            f"Network={self.strategy.network_method}"
        )

        # 初始化各采集器（传入设备配置）
        self.cpu_collector = CPUCollector(device_id, device_profile=self.device_profile)
        self.memory_collector = MemoryCollector(device_id, device_profile=self.device_profile)
        self.network_collector = NetworkCollector(device_id, device_profile=self.device_profile)
        self.battery_collector = BatteryCollector(device_id, device_profile=self.device_profile)

        # FPS 监控器使用已有的 FPSMonitor 类（传入设备配置）
        self.fps_monitor = None  # 延迟初始化，因为需要传递 fps_queue

        logger.info(
            f"初始化 Android APM: package={package_name}, device={device_id}, 采集频率={frequency}秒"
        )

    def start(self):
        """启动监控"""
        # 启动 FPS 监控（传入设备配置）
        if not self.fps_monitor:
            self.fps_monitor = FPSMonitor(
                device_id=self.device_id,
                package_name=self.package_name,
                frequency=self.frequency,
                surfaceview=self.surfaceview,
                device_profile=self.device_profile,  # 传入设备配置
                **self.kwargs,
            )
            self.fps_monitor.start()
            # 性能优化：移除阻塞等待，让 FPS 监控在后台异步初始化
            # 首次采集可能返回默认值(0)，但后续采集会获取真实数据
            logger.info("FPS 监控已在后台启动，异步初始化中...")

        # 重置网络流量统计
        self.network_collector.reset(self.package_name)

        logger.info(f"Android 性能监控已启动: package={self.package_name}")

    def stop(self):
        """停止监控 - 支持安全重复调用"""
        if self.fps_monitor:
            self.fps_monitor.stop()
            self.fps_monitor = None  # 防止重复调用

        logger.info(f"Android 性能监控已停止: package={self.package_name}")

    def collectCpu(self):
        """
        采集 CPU 使用率

        Returns:
            dict: {'appCpuRate': float, 'sysCpuRate': float} 或 None
        """
        return self.cpu_collector.collect(self.package_name)

    def collectMemory(self):
        """
        采集内存使用情况

        Returns:
            dict: {
                'totalPass': float,     # 总内存 (MB)
                'nativePass': float,    # Native 内存 (MB)
                'dalvikPass': float,    # Dalvik 内存 (MB)
            } 或 None
        """
        return self.memory_collector.collect(self.package_name)

    def collectFps(self):
        """
        采集 FPS 帧率数据 - 从缓存读取（持续运行模式）

        设计说明：
        - 首次调用时启动 FPS 监控后台线程（只启动一次，持续运行）
        - 后续调用从内部缓存读取最新数据（不停止监控）
        - 确保线程在监控结束时通过 stop() 方法正确停止

        Returns:
            dict: {
                'fps': int,             # 帧率
                'jank': int,            # 普通卡顿次数
                'bigJank': int,         # 严重卡顿次数
                'ftime_avg': float,     # 平均帧时间 (ms)
                'ftime_max': float,     # 最大帧时间 (ms)
                'ftime_min': float,     # 最小帧时间 (ms)
            } 或 None
        """
        logger.info(f"[collectFps] 开始采集 FPS: fps_monitor存在={self.fps_monitor is not None}")

        # 关键修复：从 FPSMonitor 的内部状态读取数据，而不是停止监控
        if not self.fps_monitor:
            # 首次调用时启动 FPS 监控（只启动一次，持续运行）
            logger.info("[collectFps] 首次启动 FPS 监控（持续运行模式）")
            self.fps_monitor = FPSMonitor(
                device_id=self.device_id,
                package_name=self.package_name,
                frequency=self.frequency,
                surfaceview=self.surfaceview,
                start_time=time.time(),
                **self.kwargs,
            )
            self.fps_monitor.start()
            # 等待初始数据积累（只等待一次）
            logger.info("[collectFps] 等待 FPS 初始数据积累...")
            time.sleep(1.0)  # 减少到1秒，避免首次采集延迟过长
            logger.info("[collectFps] FPS 初始数据积累完成")

        # 从 fpscollector 的内部状态读取最新数据（不停止监控）
        try:
            # 直接读取缓存数据，不等待（避免阻塞数据采集循环）
            fps_data = self.fps_monitor.fpscollector.get_latest_fps_data()
            if fps_data:
                current_fps = fps_data.get("fps", 0)
                logger.debug(f"[collectFps] 从缓存读取 FPS: {current_fps}")
                return fps_data
            else:
                # 缓存无数据，返回默认值（不阻塞等待）
                logger.debug("[collectFps] FPS 缓存暂无数据，返回默认值")
                return {
                    "fps": 0,
                    "jank": 0,
                    "bigJank": 0,
                    "ftime_avg": 0,
                    "ftime_max": 0,
                    "ftime_min": 0,
                }
        except Exception as e:
            logger.error(f"[collectFps] 读取 FPS 缓存失败: {e}")
            import traceback

            logger.error(traceback.format_exc())
            return {
                "fps": 0,
                "jank": 0,
                "bigJank": 0,
                "ftime_avg": 0,
                "ftime_max": 0,
                "ftime_min": 0,
            }

    def collectFlow(self):
        """
        采集网络流量

        Returns:
            dict: {'upFlow': float, 'downFlow': float} 单位 KB/s 或 None
        """
        return self.network_collector.collect(self.package_name)

    def collectBattery(self):
        """
        采集电池状态

        Returns:
            dict: {
                'level': int,           # 电量百分比
                'temperature': float,   # 温度 (°C)
                'current': float,       # 电流 (mA)
                'voltage': float,       # 电压 (V)
                'power': float,         # 功率 (W)
                'status': str,          # 充电状态
            } 或 None
        """
        return self.battery_collector.collect()

    def collectGpu(self):
        """
        采集 GPU 使用率

        Returns:
            dict: {
                'gpu': int,             # GPU 使用率
                'gpu_freq': int,        # GPU 频率 (MHz)
                'gpu_vendor': str,      # GPU 厂商
                'gpu_model': str,       # GPU 型号
            }

        注意：Android GPU 采集需要 root 权限或特定设备支持
        """
        # Android GPU 采集需要 root 或 dumpsys gfxinfo，暂不支持
        # 返回默认值
        return {"gpu": 0, "gpu_freq": 0, "gpu_vendor": "unknown", "gpu_model": "unknown"}

    def getAllMetrics(self):
        """
        获取所有性能指标

        Returns:
            dict: 包含所有指标的字典
        """
        return {
            "cpu": self.collectCpu(),
            "memory": self.collectMemory(),
            "fps": self.collectFps(),
            "network": self.collectFlow(),
            "battery": self.collectBattery(),
            "gpu": self.collectGpu(),
        }

    def diagnoseFpsCollection(self):
        """
        诊断 FPS 采集问题

        当 FPS 采集失败或返回 0 时，可以使用此方法进行故障排查。
        该方法会尝试多种 FPS 采集命令并报告结果，帮助定位问题。

        Returns:
            dict: 诊断报告，包含：
                - package_name: 应用包名
                - device_id: 设备 ID
                - tests: 测试结果列表
                - recommendations: 建议/解决方案列表

        Example:
            >>> apm = AndroidAPM('com.example.app', 'device_id')
            >>> report = apm.diagnoseFpsCollection()
            >>> print(f"执行了 {len(report['tests'])} 个测试")
            >>> for rec in report['recommendations']:
            >>>     print(f"建议: {rec}")
        """
        if not self.fps_monitor:
            # 创建临时 FPSMonitor 用于诊断
            from insight_aitest.platform.services.collectors.android.fps_collector import FPSMonitor

            temp_monitor = FPSMonitor(
                device_id=self.device_id,
                package_name=self.package_name,
                frequency=self.frequency,
                surfaceview=self.surfaceview,
                **self.kwargs,
            )
            return temp_monitor.fpscollector.diagnose_fps_collection()
        else:
            return self.fps_monitor.fpscollector.diagnose_fps_collection()
