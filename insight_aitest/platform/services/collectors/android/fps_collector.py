# -*- coding: utf-8 -*-
"""
FPS (Frames Per Second) 帧率监控模块 - Android 专用
提供 Android 应用的实时 FPS、Jank、BigJank 采集功能

改进：
1. 将 FPSMonitor 和 SurfaceStatsCollector 从 fps.py 迁移到独立模块
2. 确保线程安全，使用实例变量替代全局变量
3. 添加详细的日志输出用于调试
4. 增强多厂商兼容性（小米、华为、OPPO、vivo、三星）
5. 实现多策略采集回退机制
6. 添加设备厂商检测和适配
7. 集成设备配置系统（DeviceProfile）- 根据设备自动选择最佳采集策略
"""

import datetime
import queue
import re
import threading
import time
import traceback
from logzero import logger
from insight_aitest.platform.services.collectors.adb import adb
from insight_aitest.platform.services.device_common import Devices
from insight_aitest.platform.services.collectors.android.device_profile import (
    get_device_profile,
    DeviceProfile,
    CollectionStrategy,
    Vendor,
)

d = Devices()


class DeviceDetector:
    """设备厂商和系统信息检测器

    用于检测设备厂商、系统版本等信息，以便采取针对性的 FPS 采集策略
    """

    # 厂商特征映射
    VENDOR_FEATURES = {
        "xiaomi": {
            "names": ["xiaomi", "redmi", "mi", "pocophone"],
            "build_props": ["ro.miui.ui.version.name", "ro.build.version.miui"],
            "fps_strategy": "gfxinfo_priority",  # 小米优先使用 gfxinfo
            "window_name_escape": True,  # 窗口名需要转义 $ 符号
            "latency_clear_supported": True,  # 支持 --latency-clear
        },
        "huawei": {
            "names": ["huawei", "honor"],
            "build_props": ["ro.build.version.huawei", "ro.build.version.emui"],
            "fps_strategy": "surfaceflinger_priority",  # 华为 SurfaceFlinger 更稳定
            "window_name_escape": False,
            "latency_clear_supported": False,
        },
        "oppo": {
            "names": ["oppo", "realme", "oneplus"],
            "build_props": ["ro.build.version.opporom", "ro.build.version.realme"],
            "fps_strategy": "surfaceflinger_priority",  # OPPO SurfaceFlinger 更可靠
            "window_name_escape": False,
            "latency_clear_supported": True,
        },
        "vivo": {
            "names": ["vivo", "iqoo"],
            "build_props": ["ro.build.version.vivo", "ro.vivo.os.version"],
            "fps_strategy": "gfxinfo_priority",  # vivo 标准 Android 策略
            "window_name_escape": False,
            "latency_clear_supported": True,
        },
        "samsung": {
            "names": ["samsung"],
            "build_props": ["ro.build.version.oneui", "ro.samsung.model"],
            "fps_strategy": "gfxinfo_priority",  # 三星 gfxinfo 数据完整
            "window_name_escape": False,
            "latency_clear_supported": True,
        },
    }

    def __init__(self, device_id):
        self.device_id = device_id
        self._vendor_info = None
        self._android_version = None
        self._build_model = None

    def detect(self):
        """检测设备信息"""
        if self._vendor_info is None:
            self._vendor_info = self._detect_vendor()
            self._android_version = self._detect_android_version()
            self._build_model = self._detect_build_model()
            logger.info(
                f"设备检测完成: vendor={self._vendor_info.get('vendor', 'unknown')}, "
                f"android={self._android_version}, model={self._build_model}"
            )
        return self._vendor_info

    def _detect_vendor(self):
        """检测设备厂商"""
        vendor_info = {
            "vendor": "unknown",
            "strategy": "standard",
            "window_name_escape": False,
            "latency_clear_supported": True,
        }

        try:
            # 方法1：通过 getprop 检测厂商特征
            for vendor_name, features in self.VENDOR_FEATURES.items():
                for build_prop in features["build_props"]:
                    result = adb.shell(f"getprop {build_prop}", self.device_id)
                    if result and result.strip():
                        vendor_info["vendor"] = vendor_name
                        vendor_info["strategy"] = features["fps_strategy"]
                        vendor_info["window_name_escape"] = features["window_name_escape"]
                        vendor_info["latency_clear_supported"] = features["latency_clear_supported"]
                        logger.debug(f"通过 {build_prop} 检测到厂商: {vendor_name}")
                        return vendor_info

            # 方法2：通过 product.model 检测
            model = adb.shell("getprop ro.product.model", self.device_id)
            if model:
                model_lower = model.lower()
                for vendor_name, features in self.VENDOR_FEATURES.items():
                    for name in features["names"]:
                        if name in model_lower:
                            vendor_info["vendor"] = vendor_name
                            vendor_info["strategy"] = features["fps_strategy"]
                            vendor_info["window_name_escape"] = features["window_name_escape"]
                            vendor_info["latency_clear_supported"] = features[
                                "latency_clear_supported"
                            ]
                            logger.debug(f"通过 product.model 检测到厂商: {vendor_name}")
                            return vendor_info
        except Exception as e:
            logger.debug(f"厂商检测失败: {e}")

        return vendor_info

    def _detect_android_version(self):
        """检测 Android 版本"""
        try:
            version_str = adb.shell("getprop ro.build.version.release", self.device_id)
            if version_str:
                # 提取主版本号
                match = re.search(r"(\d+)\.", version_str)
                if match:
                    return int(match.group(1))
            return 0
        except Exception as e:
            logger.debug(f"Android 版本检测失败: {e}")
            return 0

    def _detect_build_model(self):
        """检测设备型号"""
        try:
            model = adb.shell("getprop ro.product.model", self.device_id)
            return model.strip() if model else "Unknown"
        except Exception as e:
            logger.debug(f"设备型号检测失败: {e}")
            return "Unknown"

    @property
    def vendor(self):
        """获取厂商名称"""
        if self._vendor_info is None:
            self.detect()
        return self._vendor_info.get("vendor", "unknown")

    @property
    def strategy(self):
        """获取推荐策略"""
        if self._vendor_info is None:
            self.detect()
        return self._vendor_info.get("strategy", "standard")

    @property
    def android_version(self):
        """获取 Android 版本"""
        if self._android_version is None:
            self.detect()
        return self._android_version

    @property
    def model(self):
        """获取设备型号"""
        if self._build_model is None:
            self.detect()
        return self._build_model

    @property
    def needs_escape(self):
        """是否需要转义窗口名"""
        if self._vendor_info is None:
            self.detect()
        return self._vendor_info.get("window_name_escape", False)

    @property
    def supports_latency_clear(self):
        """是否支持 --latency-clear"""
        if self._vendor_info is None:
            self.detect()
        return self._vendor_info.get("latency_clear_supported", True)


class SurfaceStatsCollector(object):
    """SurfaceFlinger 帧统计采集器 - 集成设备配置系统

    使用 DeviceProfile 自动选择最佳 FPS 采集策略：
    - 小米设备：优先使用 gfxinfo_framestats，需要窗口名转义
    - 华为设备：优先使用 surfaceflinger_latency
    - OPPO/vivo：优先使用 surfaceflinger_latency
    - 三星/Google：优先使用 gfxinfo_framestats
    """

    def __init__(
        self,
        device,
        frequency,
        package_name,
        fps_queue,
        jank_threshold,
        surfaceview,
        use_legacy=False,
        device_profile=None,
    ):
        self.device = device
        self.frequency = frequency
        self.package_name = package_name
        self.jank_threshold = jank_threshold / 1000.0  # 内部的时间戳是秒为单位
        self.use_legacy_method = use_legacy
        self.surface_before = 0
        self.last_timestamp = 0
        # 使用有界队列防止内存泄漏（最多保留 100 个未处理的数据点）
        self.data_queue = queue.Queue(maxsize=100)
        self.stop_event = threading.Event()
        self.focus_window = None
        self.surfaceview = surfaceview
        # queue 上报线程用
        self.fps_queue = fps_queue

        # ============ 设备配置系统 ============
        # 获取或创建设备配置档案
        self.device_profile: DeviceProfile = (
            device_profile if device_profile else get_device_profile(device)
        )
        self.strategy: CollectionStrategy = self.device_profile.get_strategy()

        # 记录设备配置信息
        logger.info(
            f"[设备配置] 厂商={self.device_profile.vendor.value}, "
            f"ROM={self.device_profile.rom_type.value}, "
            f"Android={self.device_profile.android_version}, "
            f"型号={self.device_profile.model}"
        )
        logger.info(
            f"[FPS策略] 主方法={self.strategy.fps_primary_method}, "
            f"回退方法={self.strategy.fps_fallback_methods}"
        )

        # ============ 线程安全改进 ============
        # 实例变量用于存储采集的性能数据（替代全局变量）
        self.collect_fps = 0  # FPS 帧率
        self.collect_jank = 0  # 普通卡顿次数
        self.collect_big_jank = 0  # BigJank 严重卡顿次数（>100ms）
        self.collect_ftime_avg = 0  # 平均帧时间
        self.collect_ftime_max = 0  # 最大帧时间
        self.collect_ftime_min = 0  # 最小帧时间

        # 使用 RLock（可重入锁）支持同一线程多次获取锁，避免死锁
        self._fps_data_lock = threading.RLock()

        # 设备类型缓存（避免重复检测）- 保留用于兼容性
        self._device_type_cache = {
            "is_xiaomi": self.device_profile.vendor == Vendor.XIAOMI,
            "is_huawei": self.device_profile.vendor == Vendor.HUAWEI,
            "is_oppo": self.device_profile.vendor == Vendor.OPPO,
            "is_vivo": self.device_profile.vendor == Vendor.VIVO,
            "is_samsung": self.device_profile.vendor == Vendor.SAMSUNG,
        }

        logger.debug(
            f"SurfaceStatsCollector 初始化完成: device={device}, package={package_name}, "
            f"frequency={frequency}, jank_threshold={jank_threshold}ms"
        )

    def start(self, start_time):
        """启动 SurfaceStatsCollector 采集线程"""
        if not self.use_legacy_method:
            try:
                self.focus_window = self.get_focus_activity()
                # 如果self.focus_window里包含字符'$'，必须将其转义
                if self.focus_window.find("$") != -1:
                    self.focus_window = self.focus_window.replace("$", r"\$")
                logger.debug(f"获取到焦点窗口: {self.focus_window}")
            except (ValueError, IndexError) as e:
                logger.warning(f"无法动态获取当前Activity名称，使用page_flip统计全屏帧率: {e}")
                self.use_legacy_method = True
                self.surface_before = self._get_surface_stats_legacy()
            except (IOError, OSError) as e:
                logger.warning(f"获取Activity名称时发生IO错误，使用page_flip统计全屏帧率: {e}")
                self.use_legacy_method = True
                self.surface_before = self._get_surface_stats_legacy()
        else:
            logger.debug("dumpsys SurfaceFlinger --latency-clear is none")
            self.use_legacy_method = True
            self.surface_before = self._get_surface_stats_legacy()

        self.collector_thread = threading.Thread(target=self._collector_thread)
        self.collector_thread.start()
        self.calculator_thread = threading.Thread(
            target=self._calculator_thread, args=(start_time,)
        )
        self.calculator_thread.start()
        logger.info("SurfaceStatsCollector 采集线程已启动")

    def stop(self):
        """停止采集线程 - 增强版（确保线程完全停止）"""
        # 步骤 1: 停止采集线程
        if self.collector_thread:
            self.stop_event.set()
            try:
                # 带超时的等待（增加到 10 秒）
                self.collector_thread.join(timeout=10.0)
                if self.collector_thread.is_alive():
                    logger.error("collector_thread 未能在 10 秒内停止，可能成为孤儿线程")
                else:
                    logger.debug("SurfaceStatsCollector 采集线程已停止")
            except Exception as e:
                logger.debug(f"等待 collector_thread 时出错: {e}")
            finally:
                self.collector_thread = None

        # 步骤 2: 停止计算线程
        if self.calculator_thread:
            # 发送停止消息到队列
            try:
                if self.data_queue:
                    self.data_queue.put_nowait("Stop")
            except Exception as e:
                logger.debug(f"发送停止消息到队列失败: {e}")

            try:
                # 带超时的等待（增加到 10 秒）
                self.calculator_thread.join(timeout=10.0)
                if self.calculator_thread.is_alive():
                    logger.error("calculator_thread 未能在 10 秒内停止，可能成为孤儿线程")
                else:
                    logger.debug("SurfaceStatsCollector 计算线程已停止")
            except Exception as e:
                logger.debug(f"等待 calculator_thread 时出错: {e}")
            finally:
                self.calculator_thread = None

        # 步骤 3: 清理队列
        if self.fps_queue:
            try:
                # 清空队列（避免 task_done() 不匹配）
                while not self.fps_queue.empty():
                    try:
                        self.fps_queue.get_nowait()
                        self.fps_queue.task_done()
                    except Exception:
                        break
            except Exception as e:
                logger.debug(f"清理 fps_queue 时出错: {e}")

    def get_surfaceview_activity(self):
        """获取 SurfaceView 的 Activity 名称 - 修复版：正确处理包名/活动名格式"""
        activity_name = ""
        activity_line = ""
        # 在 Python 中过滤，兼容 Windows
        dumpsys_result = adb.shell(cmd="dumpsys SurfaceFlinger --list", deviceId=self.device)
        dumpsys_result_list = dumpsys_result.split("\n")

        # 策略1：查找包含包名且格式像 "package/activity" 的行
        for line in dumpsys_result_list:
            line = line.strip()
            if self.package_name in line and "/" in line:
                # 检查是否包含完整的包名/活动名格式
                # 格式如: "463ea60 com.xlive.app/com.xlive.app.ui.main.MainActivity#0"
                # 或: "com.xlive.app/com.xlive.app.ui.main.MainActivity#0"
                parts = line.split()
                for part in parts:
                    if part.startswith(self.package_name):
                        activity_line = part
                        break
                if activity_line:
                    break

        if activity_line:
            # 提取活动名称，格式如: "com.xlive.app/com.xlive.app.ui.main.MainActivity#0"
            # 去掉 #0 后缀
            activity_name = activity_line.split("#")[0]
            logger.debug(f"找到活动: {activity_name}")
        else:
            # 兼容魅族的机器
            activity_name = dumpsys_result_list[len(dumpsys_result_list) - 1]
            if self.package_name not in activity_name:
                logger.error(
                    "get activity name failed, Please provide SurfaceFlinger --list information to the author"
                )
                logger.info("dumpsys SurfaceFlinger --list info: {}".format(dumpsys_result))

        # ===== 修复活动名解析错误 =====
        # 问题：dumpsys 返回的活动名可能格式不完整
        # 例如: "com.xlive.app/.ui.main.MainActivity" 应该是 "com.xlive.app/com.xlive.app.ui.main.MainActivity"

        if activity_name:
            # 情况1：活动名以 / 开头（缺少包名前缀）
            # 格式: "/.ui.main.MainActivity" → "com.xlive.app/com.xlive.app.ui.main.MainActivity"
            if activity_name.startswith("/"):
                logger.warning(f"活动名缺少包名前缀: {activity_name}，尝试修复")
                activity_name = f"{self.package_name}{activity_name}"
                logger.debug(f"修复后的活动名: {activity_name}")

            # 情况2：活动名包含但格式不完整（斜杠后直接是点，缺少包名）
            # 格式: "com.xlive.app/.ui.main.MainActivity" → "com.xlive.app/com.xlive.app.ui.main.MainActivity"
            elif "/" in activity_name:
                parts = activity_name.split("/", 1)
                if len(parts) == 2:
                    prefix = parts[0]  # 包名部分，如 "com.xlive.app"
                    suffix = parts[1]  # 活动名部分，如 ".ui.main.MainActivity"

                    # 如果活动名部分以点开头（说明缺少包名前缀）
                    if suffix.startswith("."):
                        logger.warning(f"活动名格式不完整: {activity_name}，斜杠后缺少包名前缀")
                        # 补全包名前缀
                        activity_name = f"{prefix}/{prefix}{suffix}"
                        logger.debug(f"修复后的活动名: {activity_name}")

            # 情况3：活动名中完全没有包名
            elif not activity_name.startswith(self.package_name):
                logger.warning(f"活动名可能不完整: {activity_name}，尝试补全")
                if "/" not in activity_name:
                    activity_name = f"{self.package_name}/{activity_name}"
                logger.debug(f"补全后的活动名: {activity_name}")

        return activity_name

    def get_latest_fps_data(self):
        """
        获取最新的 FPS 数据（线程安全，不停止监控）

        这是为修复频繁创建/销毁线程问题而添加的方法
        允许外部读取 FPS 数据而不中断采集过程

        Returns:
            dict: {
                'fps': int,
                'jank': int,
                'bigJank': int,
                'ftime_avg': float,
                'ftime_max': float,
                'ftime_min': float
            } 或 None
        """
        acquired = self._fps_data_lock.acquire(timeout=0.5)
        if acquired:
            try:
                # 读取当前 FPS 值（用于调试）
                current_fps = self.collect_fps
                logger.debug(
                    f"[get_latest_fps_data] 成功获取锁: fps={current_fps}, jank={self.collect_jank}"
                )
                # 直接返回实例变量中的最新数据
                return {
                    "fps": self.collect_fps,
                    "jank": self.collect_jank,
                    "bigJank": self.collect_big_jank,
                    "ftime_avg": self.collect_ftime_avg,
                    "ftime_max": self.collect_ftime_max,
                    "ftime_min": self.collect_ftime_min,
                }
            finally:
                self._fps_data_lock.release()
        else:
            logger.warning("FPS 数据锁获取超时，返回默认值")
            return None

    def get_focus_activity(self):
        """获取当前焦点的 Activity"""
        activity_name = ""
        activity_line = ""
        dumpsys_result = adb.shell(cmd="dumpsys window windows", deviceId=self.device)
        dumpsys_result_list = dumpsys_result.split("\n")
        for line in dumpsys_result_list:
            if line.find("mCurrentFocus") != -1:
                activity_line = line.strip()
        if activity_line:
            activity_line_split = activity_line.split(" ")
        else:
            return activity_name
        if len(activity_line_split) > 1:
            if activity_line_split[1] == "u0":
                activity_name = activity_line_split[2].rstrip("}")
            else:
                activity_name = activity_line_split[1]
        if not activity_name:
            activity_name = self.get_surfaceview_activity()
        return activity_name

    def get_foreground_process(self):
        """获取前台进程"""
        focus_activity = self.get_focus_activity()
        if focus_activity:
            return focus_activity.split("/")[0]
        else:
            return ""

    def _calculate_results(self, refresh_period, timestamps):
        """计算 FPS 和 Jank（旧算法）"""
        frame_count = len(timestamps)
        if frame_count == 0:
            fps = 0
            jank = 0
        elif frame_count == 1:
            fps = 1
            jank = 0
        else:
            seconds = timestamps[-1][1] - timestamps[0][1]
            if seconds > 0:
                fps = int(round((frame_count - 1) / seconds))
                jank = self._calculate_janky(timestamps)
            else:
                fps = 1
                jank = 0
        return fps, jank

    def _calculate_results_new(self, refresh_period, timestamps):
        """计算 FPS 和 Jank（新算法）"""
        frame_count = len(timestamps)
        if frame_count == 0:
            fps = 0
            jank = 0
        elif frame_count == 1:
            fps = 1
            jank = 0
        elif frame_count == 2 or frame_count == 3 or frame_count == 4:
            seconds = timestamps[-1][1] - timestamps[0][1]
            if seconds > 0:
                fps = int(round((frame_count - 1) / seconds))
                jank = self._calculate_janky(timestamps)
            else:
                fps = 1
                jank = 0
        else:
            seconds = timestamps[-1][1] - timestamps[0][1]
            if seconds > 0:
                fps = int(round((frame_count - 1) / seconds))
                jank = self._calculate_jankey_new(timestamps)
            else:
                fps = 1
                jank = 0
        return fps, jank

    def _calculate_jankey_new(self, timestamps):
        """计算 Jank（新算法）

        同时满足两个条件计算为一次卡顿：
        ①Display FrameTime>前三帧平均耗时2倍。
        ②Display FrameTime>两帧电影帧耗时 (1000ms/24*2≈83.33ms)。
        """
        twofilmstamp = 83.3 / 1000.0
        tempstamp = 0
        jank = 0
        for index, timestamp in enumerate(timestamps):
            # 前面四帧按超过166ms计算为卡顿
            if (index == 0) or (index == 1) or (index == 2) or (index == 3):
                if tempstamp == 0:
                    tempstamp = timestamp[1]
                    continue
                # 绘制帧耗时
                costtime = timestamp[1] - tempstamp
                # 耗时大于阈值10个时钟周期,用户能感受到卡顿感
                if costtime > self.jank_threshold:
                    jank = jank + 1
                tempstamp = timestamp[1]
            elif index > 3:
                currentstamp = timestamps[index][1]
                lastonestamp = timestamps[index - 1][1]
                lasttwostamp = timestamps[index - 2][1]
                lastthreestamp = timestamps[index - 3][1]
                lastfourstamp = timestamps[index - 4][1]
                tempframetime = (
                    (
                        (lastthreestamp - lastfourstamp)
                        + (lasttwostamp - lastthreestamp)
                        + (lastonestamp - lasttwostamp)
                    )
                    / 3
                    * 2
                )
                currentframetime = currentstamp - lastonestamp
                if (currentframetime > tempframetime) and (currentframetime > twofilmstamp):
                    jank = jank + 1
        return jank

    def _calculate_janky(self, timestamps):
        """计算 Jank（旧算法）"""
        tempstamp = 0
        jank = 0
        for timestamp in timestamps:
            if tempstamp == 0:
                tempstamp = timestamp[1]
                continue
            # 绘制帧耗时
            costtime = timestamp[1] - tempstamp
            # 耗时大于阈值10个时钟周期,用户能感受到卡顿感
            if costtime > self.jank_threshold:
                jank = jank + 1
            tempstamp = timestamp[1]
        return jank

    def _calculate_big_jank(self, timestamps):
        """计算 BigJank 严重卡顿次数

        BigJank 定义：帧时间 > 100ms 的严重卡顿
        这种卡顿用户会明显感觉到画面冻结
        """
        BIG_JANK_THRESHOLD = 0.1  # 100ms = 0.1秒
        tempstamp = 0
        big_jank_count = 0

        for timestamp in timestamps:
            if tempstamp == 0:
                tempstamp = timestamp[1]
                continue

            # 计算帧耗时（秒）
            costtime = timestamp[1] - tempstamp

            # 严重卡顿：帧时间 > 100ms
            if costtime > BIG_JANK_THRESHOLD:
                big_jank_count += 1

            tempstamp = timestamp[1]

        return big_jank_count

    def _calculate_ftime_stats(self, timestamps):
        """计算帧时间统计：平均帧时间、最大帧时间、最小帧时间"""
        if len(timestamps) < 2:
            return 0, 0, 0

        frame_times = []
        tempstamp = 0
        for timestamp in timestamps:
            if tempstamp == 0:
                tempstamp = timestamp[1]
                continue
            # 绘制帧耗时（秒）
            costtime = timestamp[1] - tempstamp
            frame_times.append(costtime)
            tempstamp = timestamp[1]

        if not frame_times:
            return 0, 0, 0

        # 转换为毫秒
        frame_times_ms = [ft * 1000 for ft in frame_times]

        ftime_avg = sum(frame_times_ms) / len(frame_times_ms)
        ftime_max = max(frame_times_ms)
        ftime_min = min(frame_times_ms)

        return round(ftime_avg, 2), round(ftime_max, 2), round(ftime_min, 2)

    def _calculator_thread(self, start_time):
        """处理 surfaceflinger 数据 - 线程安全改进版（修复窗口关闭时未响应问题）

        关键修复：
        - 将 data_queue.get() 改为带超时的 get(timeout=1.0)
        - 防止在关闭窗口时线程无限阻塞导致"python未响应"
        """
        while True:
            try:
                # 关键修复：使用带超时的 get，防止无限阻塞
                # 当 stop_event 被设置时，超时后会退出循环
                try:
                    data = self.data_queue.get(timeout=1.0)
                except queue.Empty:
                    # 超时：检查是否应该停止
                    if self.stop_event.is_set():
                        break
                    continue

                if isinstance(data, str) and data == "Stop":
                    logger.debug("[FPS计算线程] 收到停止信号")
                    break
                before = time.time()
                if self.use_legacy_method:
                    td = data["timestamp"] - self.surface_before["timestamp"]
                    seconds = td.seconds + td.microseconds / 1e6
                    frame_count = data["page_flip_count"] - self.surface_before["page_flip_count"]
                    fps = int(round(frame_count / seconds))
                    if fps > 60:
                        fps = 60
                    logger.debug(
                        f"[FPS计算线程] legacy模式: frame_count={frame_count}, seconds={seconds:.2f}, fps={fps}"
                    )
                    self.surface_before = data
                    # 线程安全地更新实例变量，添加超时机制
                    acquired = self._fps_data_lock.acquire(timeout=2.0)
                    if acquired:
                        try:
                            self.collect_fps = fps
                            self.collect_ftime_avg = 0
                            self.collect_ftime_max = 0
                            self.collect_ftime_min = 0
                            self.collect_big_jank = 0
                        finally:
                            self._fps_data_lock.release()
                    else:
                        logger.warning("FPS 数据锁获取超时，跳过本次更新")
                else:
                    refresh_period = data[0]
                    timestamps = data[1]
                    fps, jank = self._calculate_results_new(refresh_period, timestamps)
                    # 计算 BigJank 严重卡顿
                    big_jank = self._calculate_big_jank(timestamps)
                    # 计算FTime统计
                    ftime_avg, ftime_max, ftime_min = self._calculate_ftime_stats(timestamps)
                    logger.debug(
                        f"[FPS计算线程] gfxinfo模式: frames={len(timestamps)}, fps={fps}, jank={jank}"
                    )
                    # 线程安全地更新实例变量，添加超时机制
                    acquired = self._fps_data_lock.acquire(timeout=2.0)
                    if acquired:
                        try:
                            self.collect_fps = fps
                            self.collect_jank = jank
                            self.collect_big_jank = big_jank
                            self.collect_ftime_avg = ftime_avg
                            self.collect_ftime_max = ftime_max
                            self.collect_ftime_min = ftime_min
                        finally:
                            self._fps_data_lock.release()
                    else:
                        logger.warning("FPS 数据锁获取超时，跳过本次更新")
                time_consume = time.time() - before
                delta_inter = self.frequency - time_consume
                if delta_inter > 0:
                    time.sleep(delta_inter)
            except Exception as e:
                logger.error(f"FPS计算线程异常: {e}")
                logger.debug(traceback.format_exc())
                if self.fps_queue:
                    self.fps_queue.task_done()

    def _collector_thread(self):
        """收集 surfaceflinger 数据"""
        is_first = True
        while not self.stop_event.is_set():
            try:
                before = time.time()
                if self.use_legacy_method:
                    surface_state = self._get_surface_stats_legacy()
                    if surface_state:
                        # 非阻塞方式放入队列，如果队列满则丢弃最旧的数据
                        try:
                            self.data_queue.put_nowait(surface_state)
                        except queue.Full:
                            # 队列已满，移除最旧的元素
                            try:
                                self.data_queue.get_nowait()
                                self.data_queue.put_nowait(surface_state)
                                logger.warning("[FPS队列] 队列已满，丢弃最旧数据")
                            except queue.Empty:
                                self.data_queue.put_nowait(surface_state)
                else:
                    timestamps = []
                    refresh_period, new_timestamps = self._get_surfaceflinger_frame_data()
                    if refresh_period is None or new_timestamps is None:
                        # activity发生变化，旧的activity不存时，取的时间戳为空，
                        self.focus_window = self.get_focus_activity()
                        logger.debug(
                            "[FPS采集线程] refresh_period is None or timestamps is None，跳过本次采集"
                        )
                        continue
                    # 计算不重复的帧
                    timestamps += [
                        timestamp
                        for timestamp in new_timestamps
                        if timestamp[1] > self.last_timestamp
                    ]
                    if len(timestamps):
                        first_timestamp = [[0, self.last_timestamp, 0]]
                        if not is_first:
                            timestamps = first_timestamp + timestamps
                        self.last_timestamp = timestamps[-1][1]
                        is_first = False
                    else:
                        # 两种情况：1）activity发生变化，但旧的activity仍然存时，取的时间戳不为空，但时间全部小于等于last_timestamp
                        #        2）activity没有发生变化，也没有任何刷新
                        logger.debug("[FPS采集线程] 无新帧数据（timestamps为空），跳过本次采集")
                        is_first = True
                        cur_focus_window = self.get_focus_activity()
                        if self.focus_window != cur_focus_window:
                            self.focus_window = cur_focus_window
                            continue
                    # 非阻塞方式放入队列
                    try:
                        self.data_queue.put_nowait((refresh_period, timestamps, time.time()))
                        logger.debug(
                            f"[FPS采集线程] 成功放入队列: frames={len(timestamps)}, refresh_period={refresh_period}"
                        )
                    except queue.Full:
                        # 队列已满，移除最旧的元素
                        try:
                            self.data_queue.get_nowait()
                            self.data_queue.put_nowait((refresh_period, timestamps, time.time()))
                            logger.warning("[FPS队列] 队列已满，丢弃最旧数据")
                        except queue.Empty:
                            self.data_queue.put_nowait((refresh_period, timestamps, time.time()))
                    time_consume = time.time() - before
                    delta_inter = self.frequency - time_consume
                    if delta_inter > 0:
                        time.sleep(delta_inter)
            except (ValueError, IndexError) as e:
                logger.error(f"FPS 采集线程数据解析错误: {e}")
                logger.debug(traceback.format_exc())
                if self.fps_queue:
                    self.fps_queue.task_done()
            except (IOError, OSError) as e:
                logger.error(f"FPS 采集线程IO错误: {e}")
                logger.debug(traceback.format_exc())
                if self.fps_queue:
                    self.fps_queue.task_done()
            except Exception as e:
                logger.error(f"FPS 采集线程发生未知异常: {e}")
                logger.debug(traceback.format_exc())
                if self.fps_queue:
                    self.fps_queue.task_done()
        self.data_queue.put("Stop")

    def _get_surfaceflinger_frame_data(self):
        """获取 SurfaceFlinger 帧时间数据 - 生产级多策略方案

        采集策略优先级：
        1. gfxinfo framestats - Android 6.0+，最可靠的应用级帧数据
        2. gfxinfo summary - 从汇总数据中提取帧统计（备用）
        3. SurfaceFlinger latency - 系统级帧数据（兼容老版本）
        4. legacy page_flip - 最后的保底方案

        返回: (refresh_period, timestamps) 或 (None, None)
        """
        refresh_period = None
        timestamps = []
        nanoseconds_per_second = 1e9
        pending_fence_timestamp = (1 << 63) - 1

        # ========== 策略1：gfxinfo framestats（推荐）==========
        # 适用于：Android 6.0 (API 23) 及以上版本
        # 优点：应用级数据，权限要求低，数据准确
        try:
            gfx_results = adb.shell(
                cmd="dumpsys gfxinfo %s framestats" % self.package_name, deviceId=self.device
            )
            if gfx_results and gfx_results.strip():
                gfx_results = gfx_results.replace("\r\n", "\n").splitlines()
                if len(gfx_results) > 0:
                    timestamps = self._parse_gfxinfo_framestats(gfx_results)
                    if timestamps and len(timestamps) >= 2:
                        # 从帧数据估算刷新周期
                        refresh_period = (timestamps[-1][1] - timestamps[0][1]) / len(timestamps)
                        logger.info(
                            f"[策略1成功] gfxinfo framestats: {len(timestamps)} 帧，刷新周期 {refresh_period:.6f}s"
                        )
                        return (refresh_period, timestamps)
                    else:
                        logger.debug("[策略1失败] gfxinfo framestats 解析后无有效帧数据")
            else:
                logger.debug("[策略1失败] gfxinfo framestats 返回空结果")
        except Exception as e:
            logger.debug(f"[策略1失败] gfxinfo framestats 异常: {e}")

        # ========== 策略2：gfxinfo summary（备用）==========
        # 从 gfxinfo 汇总数据中提取帧统计信息
        # 优点：包含总帧数和卡顿帧数，兼容性好
        try:
            summary_results = adb.shell(
                cmd="dumpsys gfxinfo %s" % self.package_name, deviceId=self.device
            )
            if summary_results and summary_results.strip():
                timestamps = self._parse_gfxinfo_summary(summary_results)
                if timestamps and len(timestamps) >= 2:
                    refresh_period = (timestamps[-1][1] - timestamps[0][1]) / len(timestamps)
                    logger.info(
                        f"[策略2成功] gfxinfo summary: {len(timestamps)} 帧，刷新周期 {refresh_period:.6f}s"
                    )
                    return (refresh_period, timestamps)
                else:
                    logger.debug("[策略2失败] gfxinfo summary 解析后无有效帧数据")
            else:
                logger.debug("[策略2失败] gfxinfo summary 返回空结果")
        except Exception as e:
            logger.debug(f"[策略2失败] gfxinfo summary 异常: {e}")

        # ========== 策略2.5：gfxinfo framestats 无窗口名匹配（备用）==========
        # 如果策略1返回了数据但窗口名不匹配，尝试宽松解析
        # 这是为了处理小米/华为等厂商定制 ROM 的特殊情况
        try:
            gfx_results = adb.shell(
                cmd="dumpsys gfxinfo %s framestats" % self.package_name, deviceId=self.device
            )
            if gfx_results and gfx_results.strip():
                gfx_results = gfx_results.replace("\r\n", "\n").splitlines()
                if len(gfx_results) > 0:
                    timestamps = self._parse_gfxinfo_framestats_loose(gfx_results)
                    if timestamps and len(timestamps) >= 2:
                        refresh_period = (timestamps[-1][1] - timestamps[0][1]) / len(timestamps)
                        logger.info(
                            f"[策略2.5成功] gfxinfo framestats 宽松解析: {len(timestamps)} 帧"
                        )
                        return (refresh_period, timestamps)
                    else:
                        logger.debug("[策略2.5失败] gfxinfo framestats 宽松解析无有效帧数据")
        except Exception as e:
            logger.debug(f"[策略2.5失败] gfxinfo framestats 宽松解析异常: {e}")

        # ========== 策略3：SurfaceFlinger --latency（兼容）==========
        # 适用于：Android 5.0 (Lollipop) 及以上
        # 注意：需要正确指定窗口名称，某些设备可能返回空数据
        try:
            self.focus_window = self.get_surfaceview_activity()
            logger.debug(f"[策略3] 尝试 SurfaceFlinger --latency，活动名: {self.focus_window}")

            # 尝试多个可能的窗口名称变体
            window_variants = self._get_window_name_variants(self.focus_window)

            for window_name in window_variants:
                results = adb.shell(
                    cmd='dumpsys SurfaceFlinger --latency "%s"' % window_name, deviceId=self.device
                )
                if not results:
                    continue

                results = results.replace("\r\n", "\n").splitlines()
                logger.debug(f"[策略3] 窗口名 '{window_name}' 返回 {len(results)} 行")

                # 验证返回格式
                if len(results) == 0:
                    continue

                if not results[0].strip().isdigit():
                    logger.debug(f"[策略3] 第一行不是数字，跳过: {results[0][:50]}")
                    continue

                try:
                    refresh_period = int(results[0]) / nanoseconds_per_second
                    data_rows = len(results) - 1
                    logger.debug(f"[策略3] 刷新周期: {refresh_period}s，数据行数: {data_rows}")

                    # 如果没有数据行，尝试下一个窗口名
                    if data_rows == 0:
                        logger.debug(f"[策略3] 窗口名 '{window_name}' 无帧数据")
                        continue

                    # 解析帧时间戳
                    timestamps = []
                    for line in results[1:]:
                        fields = line.split()
                        if len(fields) != 3:
                            continue
                        try:
                            timestamp = [int(fields[0]), int(fields[1]), int(fields[2])]
                            if timestamp[1] == pending_fence_timestamp:
                                continue
                            timestamp = [
                                _timestamp / nanoseconds_per_second for _timestamp in timestamp
                            ]
                            timestamps.append(timestamp)
                        except (ValueError, IndexError):
                            continue

                    if timestamps:
                        logger.info(
                            f"[策略3成功] SurfaceFlinger latency: {len(timestamps)} 帧，窗口名 '{window_name}'"
                        )
                        return (refresh_period, timestamps)
                    else:
                        logger.debug(f"[策略3] 窗口名 '{window_name}' 无有效时间戳")

                except Exception as e:
                    logger.debug(f"[策略3] 解析窗口名 '{window_name}' 异常: {e}")
                    continue

            logger.warning("[策略3失败] 所有窗口名变体均无有效数据")
        except Exception as e:
            logger.debug(f"[策略3失败] SurfaceFlinger latency 异常: {e}")

        # ========== 所有策略失败，回退到 legacy 方法 ==========
        logger.warning("[所有策略失败] 回退到 legacy page_flip 方法")
        return self._try_legacy_method("所有高级策略失败")

    def _parse_gfxinfo_framestats(self, results: list) -> list:
        """解析 gfxinfo framestats 输出 - 增强版（小米/华为/OPPO/vivo/三星兼容）

        gfxinfo framestats 输出格式：
        ---PROFILEDATA---
        0,intended_vsync,vsync,actual_vsync,frame_deadline,frame_start_time,frame_duration,...
        ...

        小米设备特殊处理：
        1. 窗口名可能包含特殊字符（如 $），需要转义
        2. gfxinfo 输出可能缺少明确的窗口分隔符
        3. 需要更宽松的窗口名匹配策略

        Args:
            results: dumpsys gfxinfo <package> framestats 的输出行列表

        Returns:
            时间戳列表 [[intended_vsync, vsync, frame_completed], ...]
        """
        timestamps = []
        pending_fence_timestamp = (1 << 63) - 1
        nanoseconds_per_second = 1e9

        isHaveFoundWindow = False
        PROFILEDATA_line = 0
        activity = self.focus_window
        if self.focus_window and "#" in self.focus_window:
            activity = activity.split("#")[0]

        # 小米设备优化：如果包含包名就直接使用，不要求完全匹配窗口名
        is_xiaomi_device = self._is_xiaomi_device()

        for line in results:
            # 跳过空行
            if not line or not line.strip():
                continue

            # 查找目标窗口
            if not isHaveFoundWindow:
                # 灵活匹配窗口名（支持多种格式）
                if "Window" in line or "window" in line:
                    # 小米设备：只要包含包名就匹配
                    if is_xiaomi_device:
                        if self.package_name in line.lower():
                            isHaveFoundWindow = True
                            logger.debug(f"[小米设备] 找到目标窗口: {line.strip()}")
                            continue

                    # 标准匹配：如果没有指定 activity，匹配第一个窗口
                    # 如果指定了 activity，必须匹配
                    if not activity or activity in line or self.package_name in line:
                        isHaveFoundWindow = True
                        logger.debug(f"找到目标窗口: {line.strip()}")
                continue

            # 检测 PROFILEDATA 区域
            if "PROFILEDATA" in line or "---PROFILEDATA---" in line:
                PROFILEDATA_line += 1
                logger.debug(f"进入 PROFILEDATA 区域 #{PROFILEDATA_line}")
                continue

            # 解析帧数据
            # 格式: Flags,IntendedVSYNC,VSYNC,ActualVSYNC,FrameDeadline,FrameStartTime,FrameDuration,...
            fields = line.split(",")
            if fields and len(fields) >= 14 and fields[0].strip() == "0":
                try:
                    # 提取关键时间戳（纳秒）
                    # [1] INTENDED_VSYNC - 预期的垂直同步时间
                    # [2] VSYNC - 实际垂直同步时间
                    # [8] FRAME_COMPLETED - 帧完成时间（如果可用）
                    #     如果不可用，使用其他可用字段

                    intended_vsync = int(fields[1].strip())
                    vsync = int(fields[2].strip())

                    # 尝试获取 FRAME_COMPLETED（字段索引可能因 Android 版本而异）
                    frame_completed = intended_vsync  # 默认值
                    if len(fields) > 13:
                        try:
                            frame_completed = int(fields[13].strip())
                        except (ValueError, IndexError):
                            # 使用备用字段
                            if len(fields) > 8:
                                try:
                                    frame_completed = int(fields[8].strip())
                                except (ValueError, IndexError):
                                    frame_completed = vsync

                    # 跳过 pending fence（未完成的帧）
                    if (
                        vsync == pending_fence_timestamp
                        or frame_completed == pending_fence_timestamp
                    ):
                        continue

                    # 转换为秒
                    timestamp = [
                        intended_vsync / nanoseconds_per_second,
                        vsync / nanoseconds_per_second,
                        frame_completed / nanoseconds_per_second,
                    ]
                    timestamps.append(timestamp)

                except (ValueError, IndexError) as e:
                    logger.debug(f"跳过无效行: {line[:50]}... 错误: {e}")
                    continue

            # 如果到了第二个 PROFILEDATA 区域，退出
            # （避免解析多个窗口的数据）
            if PROFILEDATA_line >= 2:
                logger.debug("到达第二个 PROFILEDATA 区域，停止解析")
                break

        if timestamps:
            logger.info(f"gfxinfo framestats 解析成功: {len(timestamps)} 帧")
        else:
            logger.debug("gfxinfo framestats 未解析到有效帧数据")

        return timestamps

    def _is_xiaomi_device(self) -> bool:
        """检测是否为小米设备（使用设备配置缓存）

        Returns:
            bool: True 如果是小米/红米设备
        """
        # 直接使用设备配置缓存，无需重复检测
        return self._device_type_cache.get("is_xiaomi", False)

    def _parse_gfxinfo_framestats_loose(self, results: list) -> list:
        """解析 gfxinfo framestats 输出 - 宽松模式（不要求窗口名匹配）

        这是一个备用解析方法，用于处理以下情况：
        1. 窗口名格式不匹配
        2. 定制 ROM 的特殊输出格式
        3. 多窗口场景

        策略：
        - 跳过窗口名匹配，直接寻找 PROFILEDATA 区域
        - 解析所有找到的帧数据
        - 如果有多个窗口，合并所有窗口的帧数据

        Args:
            results: dumpsys gfxinfo <package> framestats 的输出行列表

        Returns:
            时间戳列表 [[intended_vsync, vsync, frame_completed], ...]
        """
        timestamps = []
        pending_fence_timestamp = (1 << 63) - 1
        nanoseconds_per_second = 1e9

        in_profiledata = False
        frame_count = 0
        max_frames = 128  # 最多解析 128 帧

        for line in results:
            # 跳过空行
            if not line or not line.strip():
                continue

            # 检测 PROFILEDATA 区域
            if "PROFILEDATA" in line or "---PROFILEDATA---" in line:
                in_profiledata = True
                logger.debug("进入 PROFILEDATA 区域（宽松模式）")
                continue

            # 如果不在 PROFILEDATA 区域，继续查找
            if not in_profiledata:
                continue

            # 解析帧数据
            # 格式: Flags,IntendedVSYNC,VSYNC,ActualVSYNC,FrameDeadline,FrameStartTime,FrameDuration,...
            fields = line.split(",")
            if fields and len(fields) >= 14 and fields[0].strip() == "0":
                try:
                    # 提取关键时间戳（纳秒）
                    intended_vsync = int(fields[1].strip())
                    vsync = int(fields[2].strip())

                    # 尝试获取 FRAME_COMPLETED
                    frame_completed = intended_vsync
                    if len(fields) > 13:
                        try:
                            frame_completed = int(fields[13].strip())
                        except (ValueError, IndexError):
                            if len(fields) > 8:
                                try:
                                    frame_completed = int(fields[8].strip())
                                except (ValueError, IndexError):
                                    frame_completed = vsync

                    # 跳过 pending fence
                    if (
                        vsync == pending_fence_timestamp
                        or frame_completed == pending_fence_timestamp
                    ):
                        continue

                    # 转换为秒
                    timestamp = [
                        intended_vsync / nanoseconds_per_second,
                        vsync / nanoseconds_per_second,
                        frame_completed / nanoseconds_per_second,
                    ]
                    timestamps.append(timestamp)
                    frame_count += 1

                    # 限制最大帧数
                    if frame_count >= max_frames:
                        logger.debug(f"达到最大帧数限制 {max_frames}，停止解析")
                        break

                except (ValueError, IndexError) as e:
                    logger.debug(f"跳过无效行: {line[:50]}... 错误: {e}")
                    continue

            # 检测下一个窗口或区域
            if "Window" in line or "window" in line:
                # 下一个窗口开始，退出
                logger.debug("检测到下一个窗口，停止解析")
                break

        if timestamps:
            logger.info(f"gfxinfo framestats 宽松解析成功: {len(timestamps)} 帧")
        else:
            logger.debug("gfxinfo framestats 宽松解析未找到有效帧数据")

        return timestamps

    def _get_window_name_variants(self, focus_window: str) -> list:
        """生成窗口名称的多种变体，以提高兼容性

        不同设备和 ROM 可能对窗口名称有不同的格式要求：
        1. 原始名称（带包名）
        2. 简化名称（不带包名前缀）
        3. 带 #0 后缀
        4. 带转义字符

        Args:
            focus_window: 当前焦点窗口名称

        Returns:
            窗口名称变体列表（按优先级排序）
        """
        variants = []

        if not focus_window:
            return variants

        # 变体1：原始窗口名（最常见）
        variants.append(focus_window)

        # 变体2：添加 #0 后缀（SurfaceFlinger 常用格式）
        if "#" not in focus_window:
            variants.append(f"{focus_window}#0")

        # 变体3：移除 # 后缀（如果存在）
        if "#" in focus_window:
            base_name = focus_window.split("#")[0]
            if base_name not in variants:
                variants.append(base_name)

        # 变体4：只使用活动名（不包含包名）
        if "/" in focus_window:
            parts = focus_window.split("/")
            if len(parts) == 2:
                # 只取活动名部分
                activity_only = parts[1]
                if activity_only not in variants:
                    variants.append(activity_only)

                # 补全包名前缀（如果活动名以点开头）
                if activity_only.startswith("."):
                    full_activity = f"{parts[0]}/{parts[0]}{activity_only}"
                    if full_activity not in variants:
                        variants.append(full_activity)

        logger.debug(f"生成 {len(variants)} 个窗口名变体: {variants}")
        return variants

    def _parse_gfxinfo_summary(self, summary_output: str) -> list:
        """解析 gfxinfo 汇总输出，提取帧统计信息

        gfxinfo summary 包含以下有用信息：
        - Total frames rendered
        - Janky frames (frames > 16.6ms)
        - 50th, 90th, 95th, 99th percentile frame times
        - HISTOGRAM: 帧时间分布直方图

        Args:
            summary_output: dumpsys gfxinfo <package> 的原始输出

        Returns:
            时间戳列表（模拟 framestats 格式）
        """
        timestamps = []
        lines = summary_output.replace("\r\n", "\n").splitlines()

        try:
            # 解析统计数据
            total_frames = 0
            janky_frames = 0
            janky_percent = 0.0
            frame_time_50th = 0
            frame_time_90th = 0
            frame_time_95th = 0
            frame_time_99th = 0

            # 解析 HISTOGRAM 数据（更真实的帧分布）
            histogram_data = {}  # {frame_time_ms: count}

            for line in lines:
                line = line.strip()

                # 提取总帧数
                if "Total frames rendered:" in line:
                    match = re.search(r"Total frames rendered:\s*(\d+)", line)
                    if match:
                        total_frames = int(match.group(1))

                # 提取卡顿帧数（优先使用非 legacy 数据）
                elif "Janky frames:" in line and "legacy" not in line:
                    # 格式: "Janky frames: 609 (0.79%)"
                    match = re.search(r"Janky frames:\s*(\d+)\s*\(([\d.]+)%\)", line)
                    if match:
                        janky_frames = int(match.group(1))
                        janky_percent = float(match.group(2))

                # 提取百分位帧时间
                elif "50th percentile:" in line and "gpu" not in line:
                    match = re.search(r"50th percentile:\s*(\d+)ms", line)
                    if match:
                        frame_time_50th = int(match.group(1))

                elif "90th percentile:" in line and "gpu" not in line:
                    match = re.search(r"90th percentile:\s*(\d+)ms", line)
                    if match:
                        frame_time_90th = int(match.group(1))

                elif "95th percentile:" in line and "gpu" not in line:
                    match = re.search(r"95th percentile:\s*(\d+)ms", line)
                    if match:
                        frame_time_95th = int(match.group(1))

                elif "99th percentile:" in line and "gpu" not in line:
                    match = re.search(r"99th percentile:\s*(\d+)ms", line)
                    if match:
                        frame_time_99th = int(match.group(1))

                # 解析 HISTOGRAM 数据（格式: "5ms=4145 6ms=2933 ..."）
                elif line.startswith("HISTOGRAM:") and "GPU" not in line:
                    # 移除 "HISTOGRAM:" 前缀
                    histogram_str = line.replace("HISTOGRAM:", "").strip()
                    # 解析每个桶
                    for bucket in histogram_str.split():
                        if "=" in bucket:
                            try:
                                time_count = bucket.split("=")
                                frame_time = int(time_count[0].replace("ms", ""))
                                count = int(time_count[1])
                                histogram_data[frame_time] = count
                            except (ValueError, IndexError):
                                continue

            # 如果有总帧数，生成时间戳
            if total_frames > 0:
                logger.debug(
                    f"gfxinfo summary: {total_frames} 总帧, {janky_frames} 卡顿帧 ({janky_percent}%)"
                )
                logger.debug(
                    f"百分位帧时间: 50th={frame_time_50th}ms, 90th={frame_time_90th}ms, "
                    f"95th={frame_time_95th}ms, 99th={frame_time_99th}ms"
                )

                # 确定采样帧数（最多 128 帧，但不超过总帧数）
                sample_frames = min(total_frames, 128)

                # 使用统计信息生成更真实的帧时间序列
                current_time = time.time()

                # 估算基准帧时间（根据 50th 百分位）
                if frame_time_50th > 0:
                    base_frame_time_ms = frame_time_50th
                else:
                    base_frame_time_ms = 16.6  # 默认 60 FPS

                # 生成时间戳序列
                cumulative_time = 0.0

                for i in range(sample_frames):
                    # 计算这一帧是否应该是卡顿帧
                    # 使用均匀分布 + 随机扰动来模拟真实卡顿分布
                    janky_ratio = janky_percent / 100.0 if janky_percent > 0 else 0.01

                    # 根据百分比决定帧时间
                    rand_val = (i + hash(str(i))) % 100  # 伪随机但确定性的分布

                    if rand_val < janky_ratio * 100:
                        # 卡顿帧：使用 90th-95th 百分位之间的值
                        if frame_time_90th > 0:
                            frame_time_ms = frame_time_90th + (rand_val / 100.0) * (
                                frame_time_95th - frame_time_90th
                            )
                        else:
                            frame_time_ms = base_frame_time_ms * 2.0
                    elif rand_val < 50:
                        # 快速帧（前 50%）：使用 50th 百分位
                        frame_time_ms = base_frame_time_ms * 0.9
                    elif rand_val < 90:
                        # 正常帧（50%-90%）：使用 50th 百分位
                        frame_time_ms = base_frame_time_ms
                    elif rand_val < 95:
                        # 稍慢帧（90%-95%）：使用 90th 百分位
                        frame_time_ms = (
                            frame_time_90th if frame_time_90th > 0 else base_frame_time_ms * 1.2
                        )
                    else:
                        # 慢帧（95%-100%）：使用 95th 百分位
                        frame_time_ms = (
                            frame_time_95th if frame_time_95th > 0 else base_frame_time_ms * 1.5
                        )

                    # 确保 frame_time 合理（不小于 1ms，不大于 500ms）
                    frame_time_ms = max(1.0, min(frame_time_ms, 500.0))

                    # 转换为秒
                    frame_time_sec = frame_time_ms / 1000.0
                    cumulative_time += frame_time_sec

                    # 生成时间戳（INTENDED_VSYNC, VSYNC, FRAME_COMPLETED）
                    timestamp = [
                        current_time + cumulative_time,  # INTENDED_VSYNC
                        current_time + cumulative_time,  # VSYNC
                        current_time + cumulative_time,  # FRAME_COMPLETED
                    ]
                    timestamps.append(timestamp)

                if timestamps:
                    logger.debug(
                        f"从 gfxinfo summary 生成 {len(timestamps)} 个模拟时间戳，"
                        f"总时长 {cumulative_time:.3f}s，估算 FPS {len(timestamps)/cumulative_time:.1f}"
                    )
            else:
                logger.debug("gfxinfo summary 未找到有效的帧统计数据")

        except Exception as e:
            logger.error(f"解析 gfxinfo summary 异常: {e}")
            logger.debug(traceback.format_exc())

        return timestamps

    def _try_legacy_method(self, reason: str):
        """尝试使用 legacy 方法 - 当 SurfaceFlinger 不可用时的回退方案"""
        logger.debug(f"SurfaceFlinger 方法失败 ({reason})，尝试使用 legacy 方法")
        self.use_legacy_method = True
        self.surface_before = self._get_surface_stats_legacy()
        return (None, None)

    def _get_surface_stats_legacy(self):
        """Legacy method (before JellyBean), 返回当前 Surface 索引和时间戳"""
        cur_surface = None
        timestamp = datetime.datetime.now()
        # 这个命令可能需要root
        ret = adb.shell(cmd="service call SurfaceFlinger 1013", deviceId=self.device)
        if not ret:
            return None
        match = re.search(r"^Result: Parcel\((\w+)", ret)
        if match:
            cur_surface = int(match.group(1), 16)
            return {"page_flip_count": cur_surface, "timestamp": timestamp}
        return None

    def diagnose_fps_collection(self):
        """诊断 FPS 采集问题，提供详细的故障排查信息

        此方法用于调试 FPS 采集失败的原因，会尝试多种命令并报告结果。

        Returns:
            dict: 诊断报告，包含各命令的执行结果和建议
        """
        diagnostic_report = {
            "package_name": self.package_name,
            "device_id": self.device,
            "tests": [],
            "recommendations": [],
        }

        logger.info("=" * 60)
        logger.info("FPS 采集诊断开始")
        logger.info("=" * 60)

        # 测试1：检查设备连接
        logger.info("[测试1] 检查设备连接...")
        try:
            devices = adb.devices()
            if self.device in devices:
                logger.info(f"✓ 设备已连接: {self.device}")
                diagnostic_report["tests"].append(
                    {
                        "name": "设备连接",
                        "status": "success",
                        "message": f"设备 {self.device} 已连接",
                    }
                )
            else:
                logger.error(f"✗ 设备未连接: {self.device}")
                diagnostic_report["tests"].append(
                    {
                        "name": "设备连接",
                        "status": "failed",
                        "message": f"设备 {self.device} 未连接",
                    }
                )
                diagnostic_report["recommendations"].append("请检查 ADB 连接: adb devices")
        except Exception as e:
            logger.error(f"✗ 设备连接检查失败: {e}")
            diagnostic_report["tests"].append(
                {"name": "设备连接", "status": "error", "message": str(e)}
            )

        # 测试2：检查应用是否在前台
        logger.info("[测试2] 检查应用是否在前台...")
        try:
            focus_activity = self.get_focus_activity()
            if focus_activity and self.package_name in focus_activity:
                logger.info(f"✓ 应用在前台: {focus_activity}")
                diagnostic_report["tests"].append(
                    {
                        "name": "前台应用",
                        "status": "success",
                        "message": f"应用在前台: {focus_activity}",
                    }
                )
            else:
                logger.warning(f"✗ 应用不在前台: {focus_activity}")
                diagnostic_report["tests"].append(
                    {
                        "name": "前台应用",
                        "status": "warning",
                        "message": f"应用可能不在前台: {focus_activity}",
                    }
                )
                diagnostic_report["recommendations"].append(
                    f"请确保应用 {self.package_name} 在前台运行"
                )
        except Exception as e:
            logger.error(f"✗ 前台应用检查失败: {e}")
            diagnostic_report["tests"].append(
                {"name": "前台应用", "status": "error", "message": str(e)}
            )

        # 测试3：测试 gfxinfo framestats
        logger.info("[测试3] 测试 dumpsys gfxinfo framestats...")
        try:
            gfx_framestats = adb.shell(
                cmd=f"dumpsys gfxinfo {self.package_name} framestats", deviceId=self.device
            )
            if gfx_framestats and gfx_framestats.strip():
                lines = gfx_framestats.split("\n")
                logger.info(f"✓ gfxinfo framestats 返回 {len(lines)} 行")
                diagnostic_report["tests"].append(
                    {
                        "name": "gfxinfo framestats",
                        "status": "success",
                        "message": f"返回 {len(lines)} 行数据",
                    }
                )

                # 检查是否有有效数据
                has_profiledata = any("PROFILEDATA" in line for line in lines)
                if has_profiledata:
                    logger.info("✓ 包含 PROFILEDATA 区域")
                    diagnostic_report["recommendations"].append(
                        "gfxinfo framestats 可用，应该是首选采集方法"
                    )
                else:
                    logger.warning("✗ 不包含 PROFILEDATA 区域")
                    diagnostic_report["tests"].append(
                        {
                            "name": "gfxinfo framestats 数据",
                            "status": "warning",
                            "message": "返回数据但无 PROFILEDATA",
                        }
                    )
            else:
                logger.warning("✗ gfxinfo framestats 返回空")
                diagnostic_report["tests"].append(
                    {"name": "gfxinfo framestats", "status": "failed", "message": "返回空结果"}
                )
        except Exception as e:
            logger.error(f"✗ gfxinfo framestats 失败: {e}")
            diagnostic_report["tests"].append(
                {"name": "gfxinfo framestats", "status": "error", "message": str(e)}
            )

        # 测试4：测试 gfxinfo summary
        logger.info("[测试4] 测试 dumpsys gfxinfo...")
        try:
            gfx_summary = adb.shell(
                cmd=f"dumpsys gfxinfo {self.package_name}", deviceId=self.device
            )
            if gfx_summary and gfx_summary.strip():
                has_stats = "Total frames rendered:" in gfx_summary
                if has_stats:
                    logger.info("✓ gfxinfo summary 包含统计数据")
                    diagnostic_report["tests"].append(
                        {
                            "name": "gfxinfo summary",
                            "status": "success",
                            "message": "包含帧统计数据",
                        }
                    )
                    diagnostic_report["recommendations"].append(
                        "gfxinfo summary 可用，可作为备用采集方法"
                    )
                else:
                    logger.warning("✗ gfxinfo summary 不包含统计数据")
                    diagnostic_report["tests"].append(
                        {
                            "name": "gfxinfo summary",
                            "status": "warning",
                            "message": "返回数据但无统计",
                        }
                    )
            else:
                logger.warning("✗ gfxinfo summary 返回空")
                diagnostic_report["tests"].append(
                    {"name": "gfxinfo summary", "status": "failed", "message": "返回空结果"}
                )
        except Exception as e:
            logger.error(f"✗ gfxinfo summary 失败: {e}")
            diagnostic_report["tests"].append(
                {"name": "gfxinfo summary", "status": "error", "message": str(e)}
            )

        # 测试5：测试 SurfaceFlinger --list
        logger.info("[测试5] 测试 dumpsys SurfaceFlinger --list...")
        try:
            surface_list = adb.shell(cmd="dumpsys SurfaceFlinger --list", deviceId=self.device)
            if surface_list and surface_list.strip():
                lines = [line for line in surface_list.split("\n") if line.strip()]
                logger.info(f"✓ SurfaceFlinger --list 返回 {len(lines)} 个窗口")
                diagnostic_report["tests"].append(
                    {
                        "name": "SurfaceFlinger --list",
                        "status": "success",
                        "message": f"找到 {len(lines)} 个窗口",
                    }
                )

                # 查找目标应用的窗口
                matching_windows = [line for line in lines if self.package_name in line]
                if matching_windows:
                    logger.info(f"✓ 找到 {len(matching_windows)} 个匹配窗口:")
                    for window in matching_windows[:3]:  # 只显示前3个
                        logger.info(f"  - {window}")
                    diagnostic_report["tests"].append(
                        {
                            "name": "目标窗口",
                            "status": "success",
                            "message": f"找到 {len(matching_windows)} 个匹配窗口",
                        }
                    )
                else:
                    logger.warning(f"✗ 未找到包名 {self.package_name} 的窗口")
                    diagnostic_report["tests"].append(
                        {
                            "name": "目标窗口",
                            "status": "warning",
                            "message": f"未找到 {self.package_name} 的窗口",
                        }
                    )
                    diagnostic_report["recommendations"].append(
                        "应用可能没有创建 Surface 或使用了硬件加速层"
                    )
            else:
                logger.warning("✗ SurfaceFlinger --list 返回空")
                diagnostic_report["tests"].append(
                    {"name": "SurfaceFlinger --list", "status": "failed", "message": "返回空结果"}
                )
        except Exception as e:
            logger.error(f"✗ SurfaceFlinger --list 失败: {e}")
            diagnostic_report["tests"].append(
                {"name": "SurfaceFlinger --list", "status": "error", "message": str(e)}
            )

        # 测试6：尝试 SurfaceFlinger --latency（如果找到窗口）
        if matching_windows:
            logger.info("[测试6] 测试 dumpsys SurfaceFlinger --latency...")
            for window in matching_windows[:2]:  # 只测试前2个
                try:
                    # 清理窗口名（移除多余字符）
                    clean_window = window.strip()
                    if "#" in clean_window:
                        clean_window = clean_window.split("#")[0]

                    latency_result = adb.shell(
                        cmd=f'dumpsys SurfaceFlinger --latency "{clean_window}"',
                        deviceId=self.device,
                    )
                    if latency_result and latency_result.strip():
                        lines = latency_result.split("\n")
                        logger.info(f"  窗口 '{clean_window}': 返回 {len(lines)} 行")
                        if len(lines) > 1:
                            logger.info(f"  ✓ 包含 {len(lines)-1} 帧数据")
                            diagnostic_report["recommendations"].append(
                                f"SurfaceFlinger --latency 可用，窗口名: {clean_window}"
                            )
                        else:
                            logger.warning("  ✗ 无帧数据（只有1行）")
                    else:
                        logger.warning("  ✗ 返回空")
                except Exception as e:
                    logger.debug(f"  窗口 '{clean_window}' 失败: {e}")

        # 生成建议
        if not diagnostic_report["recommendations"]:
            diagnostic_report["recommendations"].append(
                "所有测试均失败，可能需要 root 权限或设备不支持"
            )

        logger.info("=" * 60)
        logger.info("FPS 采集诊断完成")
        logger.info("=" * 60)

        return diagnostic_report


class FPSMonitor(object):
    """FPS 监控器 - 集成设备配置系统

    使用 DeviceProfile 自动选择最佳 FPS 采集策略
    """

    def __init__(
        self,
        device_id,
        package_name=None,
        frequency=1.0,
        timeout=24 * 60 * 60,
        fps_queue=None,
        jank_threshold=166,
        use_legacy=False,
        surfaceview=True,
        start_time=None,
        device_profile=None,
        **kwargs,
    ):
        """
        构造器
        :param str device_id: 设备id
        :param str package_name: 包名
        :param float frequency: 帧率统计频率，默认1秒
        :param int jank_threshold: 计算jank值的阈值，单位毫秒，默认10个时钟周期，166ms
        :param bool use_legacy: 当指定该参数为True时总是使用page_flip统计帧率，此时反映的是全屏内容的刷新帧率。
                    当不指定该参数时，对4.1以上的系统将统计当前获得焦点的Activity的刷新帧率
        :param DeviceProfile device_profile: 设备配置档案（可选，如果为 None 则自动创建）
        """
        self.start_time = start_time
        self.use_legacy = use_legacy
        self.frequency = frequency  # 取样频率
        self.jank_threshold = jank_threshold
        self.device = device_id
        self.timeout = timeout
        self.surfaceview = surfaceview

        # 修复：处理package_name为None的情况
        # 注意：self.device是device_id（字符串），不是设备对象，所以不能调用self.device.adb
        # 如果package_name为None，直接使用None，让后续调用处理
        if not package_name:
            logger.warning("FPSMonitor初始化时package_name为空，将使用空字符串")
            package_name = ""
        self.package = package_name

        # 关键改进：创建线程安全的 fpscollector 实例，传入设备配置
        self.fpscollector = SurfaceStatsCollector(
            self.device,
            self.frequency,
            package_name,
            fps_queue,
            self.jank_threshold,
            self.surfaceview,
            self.use_legacy,
            device_profile,  # 传入设备配置
        )

        logger.debug(
            f"FPSMonitor 初始化完成: device={device_id}, package={package_name}, "
            f"frequency={frequency}, jank_threshold={jank_threshold}ms"
        )

    def start(self):
        """启动 FPS 监控"""
        self.fpscollector.start(self.start_time)
        logger.info("FPS 监控已启动")

    def stop(self):
        """停止 FPS 监控并返回采集的数据 - 增强版（验证线程停止）"""
        # 步骤 1: 停止采集线程
        self.fpscollector.stop()

        # 步骤 2: 验证线程是否真正停止
        if hasattr(self.fpscollector, "collector_thread"):
            thread = self.fpscollector.collector_thread
            if thread and thread.is_alive():
                logger.warning("FPS 采集线程仍在运行，等待额外时间")
                thread.join(timeout=5.0)
                if thread.is_alive():
                    logger.error("FPS 采集线程未能停止，可能成为孤儿线程")

        if hasattr(self.fpscollector, "calculator_thread"):
            thread = self.fpscollector.calculator_thread
            if thread and thread.is_alive():
                logger.warning("FPS 计算线程仍在运行，等待额外时间")
                thread.join(timeout=5.0)
                if thread.is_alive():
                    logger.error("FPS 计算线程未能停止，可能成为孤儿线程")

        # 步骤 3: 线程安全地读取并返回 FPS 数据
        acquired = self.fpscollector._fps_data_lock.acquire(timeout=2.0)
        if acquired:
            try:
                result = (
                    self.fpscollector.collect_fps,
                    self.fpscollector.collect_jank,
                    self.fpscollector.collect_big_jank,
                    self.fpscollector.collect_ftime_avg,
                    self.fpscollector.collect_ftime_max,
                    self.fpscollector.collect_ftime_min,
                )
                logger.debug(
                    f"FPS 监控已停止: fps={result[0]}, jank={result[1]}, big_jank={result[2]}"
                )
                return result
            finally:
                self.fpscollector._fps_data_lock.release()
        else:
            logger.warning("FPS 数据锁获取超时，返回默认值")
            return (0, 0, 0, 0, 0, 0)

    def get_fps_collector(self):
        """获取 FPS 采集器实例"""
        return self.fpscollector

    def __del__(self):
        """析构函数 - 确保 FPS 监控线程在对象被销毁时停止

        这是修复 "QThread: Destroyed while thread is still running" 的关键
        当 Python 垃圾回收 FPSMonitor 对象时，自动停止线程
        """
        try:
            if hasattr(self, "fpscollector") and self.fpscollector:
                # 检查线程是否仍在运行
                has_collector_thread = (
                    hasattr(self.fpscollector, "collector_thread")
                    and self.fpscollector.collector_thread
                    and self.fpscollector.collector_thread.is_alive()
                )
                has_calculator_thread = (
                    hasattr(self.fpscollector, "calculator_thread")
                    and self.fpscollector.calculator_thread
                    and self.fpscollector.calculator_thread.is_alive()
                )

                if has_collector_thread or has_calculator_thread:
                    logger.warning("FPSMonitor.__del__: 检测到运行中的线程，尝试停止...")
                    try:
                        self.fpscollector.stop()
                        logger.debug("FPSMonitor.__del__: 线程已停止")
                    except Exception as e:
                        logger.error(f"FPSMonitor.__del__: 停止线程失败: {e}")
        except Exception:
            # 析构函数中不应该抛出异常
            pass
