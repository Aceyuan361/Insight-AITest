# -*- coding: utf-8 -*-
"""
设备适配系统 - 为不同厂商/ROM/Android 版本选择最佳采集策略

核心思想：
1. 在设备连接时检测设备特征（厂商、Android 版本、ROM 类型）
2. 根据特征选择最佳采集策略
3. 所有采集器（CPU、Memory、Network、FPS）共享设备配置

设计模式：
- 策略模式：不同设备使用不同采集策略
- 工厂模式：根据设备信息创建对应的配置
- 单例模式：每个设备只检测一次，缓存配置
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
from logzero import logger

from insight_aitest.platform.services.collectors.adb import adb


class Vendor(Enum):
    """设备厂商枚举"""

    UNKNOWN = "unknown"
    XIAOMI = "xiaomi"  # 小米/红米/POCO
    HUAWEI = "huawei"  # 华为/荣耀
    OPPO = "oppo"  # OPPO/realme/一加
    VIVO = "vivo"  # vivo/iQOO
    SAMSUNG = "samsung"  # 三星
    GOOGLE = "google"  # Google Pixel
    MEIZU = "meizu"  # 魅族
    OTHER = "other"  # 其他厂商


class ROMType(Enum):
    """ROM 类型枚举"""

    STOCK = "stock"  # 原生 Android
    MIUI = "miui"  # 小米 MIUI
    EMUI = "emui"  # 华为 EMUI/HarmonyOS
    COLOROS = "coloros"  # OPPO ColorOS
    FUNTOUCH = "funtouch"  # vivo FuntouchOS/OriginOS
    ONEUI = "oneui"  # 三星 OneUI
    OTHER = "other"  # 其他定制 ROM


@dataclass
class CollectionStrategy:
    """采集策略配置

    定义了如何采集各项性能指标的最佳方式
    """

    # === FPS 采集策略 ===
    fps_primary_method: str = "gfxinfo_framestats"  # gfxinfo_framestats, surfaceflinger_latency
    fps_fallback_methods: List[str] = field(
        default_factory=lambda: ["gfxinfo_summary", "surfaceflinger_latency", "legacy_page_flip"]
    )
    fps_window_name_escape: bool = False  # 窗口名是否需要转义 $ 符号
    fps_require_foreground: bool = True  # 是否要求应用在前台

    # === CPU 采集策略 ===
    cpu_primary_method: str = "dumpsys_cpuinfo"  # dumpsys_cpuinfo, top
    cpu_fallback_methods: List[str] = field(default_factory=lambda: ["top"])
    cpu_parse_mode: str = "standard"  # standard, xiaomi_compat, huawei_compat
    cpu_ansi_filter: bool = True  # 是否过滤 ANSI 转义序列

    # === 内存采集策略 ===
    memory_primary_method: str = "dumpsys_meminfo"  # dumpsys_meminfo, procrank
    memory_unit: str = "MB"  # MB, KB
    memory_detail_level: str = "summary"  # summary, detail, full

    # === 网络采集策略 ===
    network_method: str = "proc_uid_stat"  # proc_uid_stat, dumpsys_network
    network_shell_wrap: bool = False  # 是否使用 sh -c 包装命令
    network_uid_cache: bool = True  # 是否缓存 UID 映射

    # === 电池采集策略 ===
    battery_method: str = "dumpsys_battery"  # dumpsys_battery, dumpsys_batterystats
    battery_temperature_unit: str = "celsius"  # celsius, fahrenheit

    # === 通用配置 ===
    collection_timeout: int = 5  # 采集超时时间（秒）
    retry_on_failure: bool = True  # 失败是否重试
    max_retries: int = 2  # 最大重试次数

    def get_fps_methods(self) -> List[str]:
        """获取 FPS 采集方法列表（按优先级）"""
        return [self.fps_primary_method] + self.fps_fallback_methods

    def get_cpu_methods(self) -> List[str]:
        """获取 CPU 采集方法列表（按优先级）"""
        return [self.cpu_primary_method] + self.cpu_fallback_methods


@dataclass
class DeviceProfile:
    """设备配置档案

    存储设备的特征信息和对应的采集策略
    """

    device_id: str
    vendor: Vendor = Vendor.UNKNOWN
    rom_type: ROMType = ROMType.STOCK
    android_version: int = 0
    android_api_level: int = 0
    model: str = ""
    manufacturer: str = ""
    is_rooted: bool = False
    strategy: CollectionStrategy = field(default_factory=CollectionStrategy)

    # 缓存的信息
    _package_uid_cache: Dict[str, int] = field(default_factory=dict)

    def get_strategy(self) -> CollectionStrategy:
        """获取采集策略"""
        return self.strategy

    def cache_package_uid(self, package_name: str, uid: int):
        """缓存包名的 UID"""
        self._package_uid_cache[package_name] = uid

    def get_package_uid(self, package_name: str) -> Optional[int]:
        """获取缓存的 UID"""
        return self._package_uid_cache.get(package_name)


class DeviceProfileFactory:
    """设备配置工厂

    根据设备信息创建最佳的配置档案
    """

    # === 厂商标识特征 ===
    VENDOR_PATTERNS = {
        Vendor.XIAOMI: {
            "manufacturer": ["xiaomi", "redmi", "poco"],
            "build_props": ["ro.miui.ui.version.name", "ro.build.version.miui"],
            "product_keywords": ["redmi", "poco", "mi "],
        },
        Vendor.HUAWEI: {
            "manufacturer": ["huawei", "honor"],
            "build_props": [
                "ro.build.version.huawei",
                "ro.build.version.emui",
                "ro.build.version.harmonyos",
            ],
            "product_keywords": ["honor", "huawei", "mate", "p", "nova", "yoy"],
        },
        Vendor.OPPO: {
            "manufacturer": ["oppo", "realme", "oneplus"],
            "build_props": [
                "ro.build.version.opporom",
                "ro.build.version.realme",
                "ro.build.version.oneui",
            ],
            "product_keywords": ["oppo", "realme", "oneplus", "rmx", "cph", "p", "a"],
        },
        Vendor.VIVO: {
            "manufacturer": ["vivo", "iqoo"],
            "build_props": ["ro.build.version.vivo", "ro.vivo.os.version"],
            "product_keywords": ["vivo", "iqoo", "v", "y", "x", "z"],
        },
        Vendor.SAMSUNG: {
            "manufacturer": ["samsung"],
            "build_props": ["ro.build.version.oneui"],
            "product_keywords": ["samsung", "sm-", "gt-"],
        },
        Vendor.GOOGLE: {
            "manufacturer": ["google"],
            "build_props": [],
            "product_keywords": ["pixel", "pixel "],  # Pixel 2, 3, 4...
        },
        Vendor.MEIZU: {
            "manufacturer": ["meizu", "meizu"],
            "build_props": ["ro.build.version.flyme"],
            "product_keywords": ["meizu", "meizu", "mx", "16", "17", "18", "20", "30"],
        },
    }

    # === ROM 类型特征 ===
    ROM_PATTERNS = {
        ROMType.MIUI: ["ro.miui.ui.version.name"],
        ROMType.EMUI: ["ro.build.version.emui", "ro.build.version.harmonyos"],
        ROMType.COLOROS: ["ro.build.version.opporom"],
        ROMType.FUNTOUCH: ["ro.build.version.vivo"],
        ROMType.ONEUI: ["ro.build.version.oneui"],
    }

    # === 预定义的厂商策略配置 ===
    VENDOR_STRATEGIES = {
        Vendor.XIAOMI: CollectionStrategy(
            fps_primary_method="gfxinfo_framestats",
            fps_window_name_escape=True,
            fps_require_foreground=True,
            cpu_primary_method="top",  # 小米设备的 top 输出更稳定
            cpu_parse_mode="xiaomi_compat",
            cpu_ansi_filter=True,
            memory_primary_method="dumpsys_meminfo",
            memory_unit="MB",
            network_shell_wrap=True,  # 小米设备需要 sh -c 包装
            network_uid_cache=True,
        ),
        Vendor.HUAWEI: CollectionStrategy(
            fps_primary_method="surfaceflinger_latency",  # 华为 SurfaceFlinger 更稳定
            fps_window_name_escape=False,
            fps_require_foreground=True,
            cpu_primary_method="dumpsys_cpuinfo",
            cpu_parse_mode="huawei_compat",
            memory_primary_method="dumpsys_meminfo",
            memory_unit="MB",
            network_shell_wrap=False,
            network_uid_cache=True,
        ),
        Vendor.OPPO: CollectionStrategy(
            fps_primary_method="surfaceflinger_latency",
            fps_window_name_escape=False,
            fps_require_foreground=True,
            cpu_primary_method="top",
            cpu_parse_mode="standard",
            memory_primary_method="dumpsys_meminfo",
            memory_unit="MB",
            network_shell_wrap=False,
            network_uid_cache=True,
        ),
        Vendor.VIVO: CollectionStrategy(
            fps_primary_method="gfxinfo_framestats",
            fps_window_name_escape=False,
            fps_require_foreground=True,
            cpu_primary_method="top",
            cpu_parse_mode="standard",
            memory_primary_method="dumpsys_meminfo",
            memory_unit="MB",
            network_shell_wrap=False,
            network_uid_cache=True,
        ),
        Vendor.SAMSUNG: CollectionStrategy(
            fps_primary_method="gfxinfo_framestats",
            fps_window_name_escape=False,
            fps_require_foreground=True,
            cpu_primary_method="dumpsys_cpuinfo",
            cpu_parse_mode="standard",
            memory_primary_method="dumpsys_meminfo",
            memory_unit="MB",
            network_shell_wrap=False,
            network_uid_cache=True,
        ),
        Vendor.GOOGLE: CollectionStrategy(
            fps_primary_method="gfxinfo_framestats",
            fps_window_name_escape=False,
            fps_require_foreground=True,
            cpu_primary_method="dumpsys_cpuinfo",
            cpu_parse_mode="standard",
            memory_primary_method="dumpsys_meminfo",
            memory_unit="MB",
            network_shell_wrap=False,
            network_uid_cache=True,
        ),
        Vendor.MEIZU: CollectionStrategy(
            fps_primary_method="gfxinfo_framestats",
            fps_window_name_escape=False,
            fps_require_foreground=True,
            cpu_primary_method="top",
            cpu_parse_mode="standard",
            memory_primary_method="dumpsys_meminfo",
            memory_unit="MB",
            network_shell_wrap=False,
            network_uid_cache=True,
        ),
    }

    # === Android 版本特定配置 ===
    @staticmethod
    def get_android_version_config(android_version: int) -> Dict[str, Any]:
        """根据 Android 版本获取配置"""
        config = {}

        if android_version >= 11:  # Android 11+
            config["fps_gfxinfo_reliable"] = True
            config["cpu_dumpsys_reliable"] = True
        elif android_version >= 8:  # Android 8-10
            config["fps_gfxinfo_reliable"] = True
            config["cpu_dumpsys_reliable"] = False
        elif android_version >= 6:  # Android 6-7
            config["fps_gfxinfo_reliable"] = True
            config["cpu_dumpsys_reliable"] = False
        else:  # Android 5 及以下
            config["fps_gfxinfo_reliable"] = False
            config["cpu_dumpsys_reliable"] = False

        return config

    # 使用 OrderedDict 实现 LRU 缓存（防止内存泄漏）
    from collections import OrderedDict

    _device_profile_cache: OrderedDict = OrderedDict()
    _max_cache_size = 100  # 最多缓存 100 个设备配置

    @classmethod
    def create(cls, device_id: str) -> DeviceProfile:
        """创建设备配置档案（带 LRU 缓存）

        Args:
            device_id: 设备 ID

        Returns:
            DeviceProfile: 设备配置档案
        """
        # 检查缓存
        if device_id in cls._device_profile_cache:
            # 移到末尾（标记为最近使用）
            profile = cls._device_profile_cache.pop(device_id)
            cls._device_profile_cache[device_id] = profile
            logger.debug(f"使用缓存的设备配置: {device_id}")
            return profile

        logger.info(f"[设备适配] 开始检测设备配置: {device_id}")

        # 检测设备信息
        vendor = cls._detect_vendor(device_id)
        rom_type = cls._detect_rom_type(device_id)
        android_version = cls._detect_android_version(device_id)
        android_api_level = cls._detect_android_api_level(device_id)
        model = cls._detect_model(device_id)
        manufacturer = cls._detect_manufacturer(device_id)
        is_rooted = cls._detect_root(device_id)

        # 选择最佳策略
        strategy = cls._select_strategy(vendor, android_version)

        # 创建配置档案
        profile = DeviceProfile(
            device_id=device_id,
            vendor=vendor,
            rom_type=rom_type,
            android_version=android_version,
            android_api_level=android_api_level,
            model=model,
            manufacturer=manufacturer,
            is_rooted=is_rooted,
            strategy=strategy,
        )

        # 缓存配置（带 LRU 淘汰）
        if len(cls._device_profile_cache) >= cls._max_cache_size:
            # 删除最旧的缓存项（第一个）
            oldest_device_id = next(iter(cls._device_profile_cache))
            cls._device_profile_cache.pop(oldest_device_id)
            logger.debug(f"[设备缓存] 淘汰最旧的配置: {oldest_device_id}")
        cls._device_profile_cache[device_id] = profile

        logger.info(
            f"[设备适配] 检测完成: "
            f"厂商={vendor.value}, ROM={rom_type.value}, "
            f"Android={android_version}, 型号={model}"
        )
        logger.info(
            f"[设备适配] 采集策略: FPS={strategy.fps_primary_method}, "
            f"CPU={strategy.cpu_primary_method}"
        )

        return profile

    @classmethod
    def _detect_vendor(cls, device_id: str) -> Vendor:
        """检测设备厂商"""
        try:
            # 方法1：检查 manufacturer 属性
            manufacturer = adb.shell("getprop ro.product.manufacturer", device_id)
            if manufacturer:
                manufacturer_lower = manufacturer.lower().strip()
                for vendor, patterns in cls.VENDOR_PATTERNS.items():
                    if any(m in manufacturer_lower for m in patterns["manufacturer"]):
                        return vendor

            # 方法2：检查 build.prop 特征
            for vendor, patterns in cls.VENDOR_PATTERNS.items():
                for build_prop in patterns["build_props"]:
                    value = adb.shell(f"getprop {build_prop}", device_id)
                    if value and value.strip():
                        return vendor

            # 方法3：检查产品型号关键词
            model = adb.shell("getprop ro.product.model", device_id)
            if model:
                model_lower = model.lower().strip()
                for vendor, patterns in cls.VENDOR_PATTERNS.items():
                    if any(kw in model_lower for kw in patterns["product_keywords"]):
                        return vendor

        except Exception as e:
            logger.debug(f"检测设备厂商失败: {e}")

        return Vendor.UNKNOWN

    @classmethod
    def _detect_rom_type(cls, device_id: str) -> ROMType:
        """检测 ROM 类型"""
        try:
            for rom_type, props in cls.ROM_PATTERNS.items():
                for prop in props:
                    value = adb.shell(f"getprop {prop}", device_id)
                    if value and value.strip():
                        return rom_type
        except Exception as e:
            logger.debug(f"检测 ROM 类型失败: {e}")

        return ROMType.STOCK

    @classmethod
    def _detect_android_version(cls, device_id: str) -> int:
        """检测 Android 版本（增强版：支持更多格式）"""
        try:
            version_str = adb.shell("getprop ro.build.version.release", device_id)
            if version_str:
                version_str = version_str.strip()
                logger.debug(f"Android 版本字符串: '{version_str}'")

                # 尝试多种匹配模式
                import re

                # 模式1: "12" 或 "12.0"
                match = re.match(r"^(\d+)", version_str)
                if match:
                    version = int(match.group(1))
                    logger.debug(f"从模式1匹配到 Android 版本: {version}")
                    return version

                # 模式2: 带字母的版本 (如 "12R")
                match = re.match(r"^(\d+)[A-Za-z]", version_str)
                if match:
                    version = int(match.group(1))
                    logger.debug(f"从模式2匹配到 Android 版本: {version}")
                    return version

            # 备用方法：使用 SDK 推断版本
            api_level = cls._detect_android_api_level(device_id)
            if api_level > 0:
                # API Level 映射到 Android 版本
                version_map = {
                    33: 13,
                    32: 12,
                    31: 12,
                    30: 11,
                    29: 10,
                    28: 9,
                    27: 8,
                    26: 8,
                    25: 7,
                    24: 7,
                }
                for api, ver in version_map.items():
                    if api_level >= api:
                        logger.debug(f"从 API Level {api_level} 推断 Android 版本: {ver}")
                        return ver

        except Exception as e:
            logger.debug(f"检测 Android 版本失败: {e}")

        return 0

    @classmethod
    def _detect_android_api_level(cls, device_id: str) -> int:
        """检测 Android API Level"""
        try:
            api_str = adb.shell("getprop ro.build.version.sdk", device_id)
            if api_str:
                return int(api_str.strip())
        except Exception as e:
            logger.debug(f"检测 API Level 失败: {e}")

        return 0

    @classmethod
    def _detect_model(cls, device_id: str) -> str:
        """检测设备型号"""
        try:
            model = adb.shell("getprop ro.product.model", device_id)
            return model.strip() if model else "Unknown"
        except Exception as e:
            logger.debug(f"检测设备型号失败: {e}")
            return "Unknown"

    @classmethod
    def _detect_manufacturer(cls, device_id: str) -> str:
        """检测制造商"""
        try:
            manufacturer = adb.shell("getprop ro.product.manufacturer", device_id)
            return manufacturer.strip() if manufacturer else "Unknown"
        except Exception as e:
            logger.debug(f"检测制造商失败: {e}")
            return "Unknown"

    @classmethod
    def _detect_root(cls, device_id: str) -> bool:
        """检测设备是否 root"""
        try:
            # 检查 su 命令是否可用
            result = adb.shell("which su", device_id)
            if result and "su" in result:
                return True

            # 检查 Magisk
            result = adb.shell("ls /system/app/Magisk", device_id)
            if result and not result.startswith("No such file"):
                return True

        except Exception as e:
            logger.debug(f"检测 root 状态失败: {e}")

        return False

    @classmethod
    def _select_strategy(cls, vendor: Vendor, android_version: int) -> CollectionStrategy:
        """选择最佳采集策略"""
        # 优先使用厂商预设策略
        if vendor in cls.VENDOR_STRATEGIES:
            base_strategy = cls.VENDOR_STRATEGIES[vendor]
        else:
            base_strategy = CollectionStrategy()

        # 根据 Android 版本调整策略
        version_config = cls.get_android_version_config(android_version)

        # 如果 gfxinfo 不可靠，调整 FPS 策略
        if not version_config.get("fps_gfxinfo_reliable", True):
            base_strategy.fps_primary_method = "surfaceflinger_latency"

        # 如果 dumpsys cpuinfo 不可靠，调整 CPU 策略
        if not version_config.get("cpu_dumpsys_reliable", True):
            base_strategy.cpu_primary_method = "top"

        return base_strategy

    @classmethod
    def clear_cache(cls):
        """清除缓存"""
        cls._device_profile_cache.clear()
        logger.debug("设备配置缓存已清除")


def get_device_profile(device_id: str) -> DeviceProfile:
    """获取设备配置档案（便捷函数）

    Args:
        device_id: 设备 ID

    Returns:
        DeviceProfile: 设备配置档案
    """
    return DeviceProfileFactory.create(device_id)


def clear_device_profile_cache():
    """清除设备配置缓存（便捷函数）"""
    DeviceProfileFactory.clear_cache()
