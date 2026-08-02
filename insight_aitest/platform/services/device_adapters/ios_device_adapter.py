# -*- coding: utf-8 -*-
"""
iOS设备适配器 (pymobiledevice3 v9.x async API)

通过 IOSConnectionManager 统一管理设备连接（usbmux 或 iOS 17+ tunnel）。
对外暴露同步接口，内部通过 AsyncLoopThread 桥接 pymobiledevice3 v9.x 的 async API。

pymobiledevice3 v9.x 关键变更：
- create_using_usbmux() → 协程
- lockdown.get_value() → async def
- DvtSecureSocketProxyService 已删除 → DvtProvider (async context manager)
- make_channel/launchProcess_/killPid_/processList 已删除 → ProcessControl/DeviceInfo
- InstallationProxyService.install_from_local()/uninstall() → async def
- DiagnosticsService.get_battery() → async def
"""

import threading
import time
from typing import Optional, Dict, Any
from logzero import logger

from .models import DeviceInfo, Platform
from .base import BaseDeviceAdapter
from insight_aitest.platform.services.collectors.ios.exceptions import (
    DeviceNotTrustedError,
    DeviceConnectionError,
    PMD3NotInstalledError,
    DeveloperModeNotEnabledError,
)
from insight_aitest.platform.services.collectors.ios.connection_manager import (
    IOSConnectionManager,
)

# 模块级依赖（版本容忍导入，保证模块在 pymobiledevice3 不同版本下均能加载）。
try:
    from pymobiledevice3 import usbmux
except ImportError:  # pragma: no cover
    usbmux = None  # type: ignore[assignment]

try:
    from insight_aitest.platform.services.collectors.ios.devdisk_helper import DevDiskHelper
except ImportError:  # pragma: no cover
    DevDiskHelper = None  # type: ignore[assignment]


# ========== 自动重连配置 ==========
RECONNECT_MAX_RETRIES = 3  # 最大重试次数
RECONNECT_INITIAL_DELAY = 1.0  # 初始重试延迟（秒）
RECONNECT_MAX_DELAY = 16.0  # 最大重试延迟（秒）
RECONNECT_BACKOFF_MULTIPLIER = 2.0  # 退避倍数

# 不应重试的异常类型（用户需手动干预）
NO_RETRY_EXCEPTIONS = (
    DeviceNotTrustedError,
    PMD3NotInstalledError,
    DeveloperModeNotEnabledError,
)


class IOSDeviceAdapter(BaseDeviceAdapter):
    """
    iOS设备适配器
    通过 IOSConnectionManager 与 iOS 设备通信（兼容 iOS 11-16 和 iOS 17+）
    """

    def __init__(self, device_id: str):
        super().__init__(device_id)
        self._lockdown_proxy = None  # SyncLockdownProxy
        self._conn_mgr: Optional[IOSConnectionManager] = None
        self._connected = False
        self._apm = None  # IOSAPM 实例缓存
        self._apm_lock = threading.Lock()  # APM 实例锁
        self.platform = Platform.IOS  # 平台标识

        # 重连机制相关
        self._retry_count = 0
        self._last_error = None
        self._connecting = False
        self._connect_lock = threading.Lock()

    @property
    def _lockdown_client(self):
        """兼容属性：返回 SyncLockdownProxy（供现有代码使用）。"""
        return self._lockdown_proxy

    def connect(self) -> bool:
        """连接iOS设备（带自动重试机制）"""
        with self._connect_lock:
            if self._connecting:
                logger.debug(f"iOS设备正在连接中，等待: {self.device_id}")
                return self._connected

            self._connecting = True

        try:
            return self._connect_with_retry()
        finally:
            with self._connect_lock:
                self._connecting = False

    def _connect_with_retry(self) -> bool:
        """带重试机制的连接实现（指数退避策略）"""
        delay = RECONNECT_INITIAL_DELAY

        for attempt in range(RECONNECT_MAX_RETRIES + 1):
            self._retry_count = attempt

            try:
                success = self._attempt_connect()
                if success:
                    if attempt > 0:
                        logger.info(f"iOS设备重连成功: {self.device_id} (第 {attempt} 次重试)")
                    return True

            except NO_RETRY_EXCEPTIONS as e:
                logger.error(f"iOS设备连接失败（需手动干预）: {type(e).__name__}: {e}")
                self._last_error = e
                raise

            except Exception as e:
                self._last_error = e
                logger.warning(
                    f"iOS设备连接失败 (尝试 {attempt + 1}/{RECONNECT_MAX_RETRIES + 1}): {e}"
                )

                if attempt < RECONNECT_MAX_RETRIES:
                    logger.info(f"等待 {delay:.1f} 秒后重试...")
                    time.sleep(delay)
                    delay = min(delay * RECONNECT_BACKOFF_MULTIPLIER, RECONNECT_MAX_DELAY)
                else:
                    logger.error(f"iOS设备连接失败（已达最大重试次数）: {self.device_id}")
                    error = DeviceConnectionError(
                        self.device_id, f"已重试 {RECONNECT_MAX_RETRIES} 次均失败"
                    )
                    raise error

        return False

    def _attempt_connect(self) -> bool:
        """单次连接尝试：通过 IOSConnectionManager 建立连接"""
        # 检查 pymobiledevice3 是否安装
        if usbmux is None:
            error = PMD3NotInstalledError()
            logger.error(str(error))
            logger.error(error.get_install_command())
            raise error

        # 通过 IOSConnectionManager 连接（自动版本检测 + tunnel/usbmux 路径选择）
        self._conn_mgr = IOSConnectionManager.get_instance(self.device_id)

        if not self._conn_mgr.is_connected:
            self._conn_mgr.connect()

        # 获取同步 lockdown 代理
        self._lockdown_proxy = self._conn_mgr.get_lockdown()
        self._connected = True

        logger.info(
            f"iOS设备连接成功: {self.device_id} "
            f"(version={self._conn_mgr.product_version}, "
            f"ios17+={self._conn_mgr.is_ios17_plus})"
        )

        # 确保 DeveloperDiskImage / Personalized DDI 已挂载。
        # iOS <17：普通 DDI 提供 DVT 服务；
        # iOS 17+：必须挂载 personalized DDI 后 RSD 才会暴露
        #          com.apple.instruments.dtservicehub（DVT/instruments 服务）。
        try:
            if DevDiskHelper is not None and not DevDiskHelper.ensure_developer_disk_mounted(
                self.device_id
            ):
                logger.warning("DeveloperDiskImage 挂载失败，DVT 服务可能不可用")
        except DeveloperModeNotEnabledError:
            # iOS 17+ 未启用 Developer Mode：自动尝试让开关显示在设置中，再提示用户。
            if DevDiskHelper is not None:
                logger.info("检测到 Developer Mode 未启用，尝试让开关显示在设置中...")
                DevDiskHelper.reveal_developer_mode(self.device_id)
            logger.error(
                "iOS 17+ 未启用 Developer Mode，无法挂载 DDI / 使用 DVT 服务。\n"
                "请按以下步骤操作：\n"
                "  1. 在设备「设置 → 隐私与安全性」底部找到「开发者 Mode」\n"
                "     （若仍看不到，重新插拔设备后重试连接，会自动再次发送 reveal）\n"
                "  2. 打开 Developer Mode 开关 → 重启设备\n"
                "  3. 重启后在弹窗中确认「Turn On」\n"
                "  4. 重新运行本程序连接设备"
            )
            raise
        except Exception as e:
            logger.warning(f"DeveloperDiskImage 挂载检查失败: {e}，继续连接")

        return True

    def disconnect(self) -> bool:
        """断开iOS设备连接"""
        try:
            # 停止 APM
            if self._apm:
                try:
                    self._apm.stop()
                except Exception:
                    pass
                self._apm = None

            # ConnectionManager 断开（共享连接，仅清理本地引用）
            self._lockdown_proxy = None
            self._connected = False
            logger.info(f"iOS设备已断开: {self.device_id}")
            return True

        except Exception as e:
            logger.error(f"断开iOS设备连接异常: {e}")
            return False

    def is_connected(self) -> bool:
        """检查iOS设备是否连接"""
        try:
            if not self._connected:
                return False
            if self._lockdown_proxy:
                self._lockdown_proxy.get_value()
            return True
        except Exception as e:
            logger.debug(f"检查iOS设备连接状态失败: {e}")
            self._connected = False
            return False

    def is_healthy(self) -> bool:
        """检查连接是否健康"""
        try:
            if not self.is_connected():
                return False
            device_info = self.get_device_info()
            return device_info is not None
        except Exception as e:
            logger.debug(f"iOS设备健康检查失败: {e}")
            return False

    def get_device_info(self) -> Optional[DeviceInfo]:
        """获取iOS设备详细信息（通过 SyncLockdownProxy 查询）"""
        try:
            if not self._lockdown_proxy:
                logger.warning("iOS 设备未连接")
                return None
            ld = self._lockdown_proxy
            return DeviceInfo(
                device_id=self.device_id,
                name=ld.get_value(key="DeviceName") or "iPhone",
                platform=Platform.IOS,
                model=ld.get_value(key="ProductType") or "iPhone",
                os_version=ld.get_value(key="ProductVersion") or "iOS",
                serial_number=ld.get_value(key="SerialNumber") or self.device_id,
            )
        except Exception as e:
            logger.error(f"获取iOS设备信息失败: {e}")
            return None

    def check_device_ready(self) -> bool:
        """检查设备是否准备好进行监控"""
        try:
            if not self.is_connected():
                return False
            if self._lockdown_proxy:
                self._lockdown_proxy.get_value()
                return True
            return False
        except Exception as e:
            logger.warning(f"检查iOS设备准备状态失败: {e}")
            return False

    def execute_command(self, command: str, timeout: int = 30) -> str:
        """在iOS设备上执行命令（iOS 限制较多）"""
        logger.warning("iOS 设备不支持直接执行命令")
        return ""

    def install_app(self, app_path: str) -> bool:
        """安装 iOS 应用（通过 async InstallationProxyService）"""
        try:
            from pymobiledevice3.services.installation_proxy import (
                InstallationProxyService,
            )

            mgr = self._conn_mgr
            lockdown = mgr.get_async_lockdown()
            service = InstallationProxyService(lockdown)
            mgr.run_async(service.install_from_local(app_path), timeout=120)
            logger.info(f"iOS 应用安装成功: {app_path}")
            return True
        except Exception as e:
            logger.error(f"iOS 应用安装失败: {e}")
            return False

    def uninstall_app(self, package_name: str) -> bool:
        """卸载 iOS 应用"""
        try:
            from pymobiledevice3.services.installation_proxy import (
                InstallationProxyService,
            )

            mgr = self._conn_mgr
            lockdown = mgr.get_async_lockdown()
            service = InstallationProxyService(lockdown)
            mgr.run_async(service.uninstall(package_name), timeout=30)
            logger.info(f"iOS 应用卸载成功: {package_name}")
            return True
        except Exception as e:
            logger.error(f"iOS 应用卸载失败: {e}")
            return False

    def start_app(self, package_name: str, activity: str = None) -> bool:
        """启动 iOS 应用（通过 async ProcessControl.launch()）"""
        try:
            mgr = self._conn_mgr
            if mgr is None:
                logger.error("iOS 设备未连接")
                return False

            pid = mgr.run_async(self._launch_app_async(package_name), timeout=15)
            logger.info(f"iOS 应用启动成功: {package_name} (pid={pid})")
            return True
        except Exception as e:
            logger.error(f"iOS 应用启动失败: {e}")
            return False

    async def _launch_app_async(self, bundle_id: str) -> int:
        """异步启动应用"""
        from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
        from pymobiledevice3.services.dvt.instruments.process_control import (
            ProcessControl,
        )

        lockdown = self._conn_mgr.get_async_lockdown()
        async with DvtProvider(lockdown) as dvt:
            async with ProcessControl(dvt) as pc:
                return await pc.launch(bundle_id=bundle_id)

    def stop_app(self, package_name: str) -> bool:
        """停止 iOS 应用（通过 async ProcessControl.kill()）"""
        try:
            mgr = self._conn_mgr
            if mgr is None:
                logger.error("iOS 设备未连接")
                return False

            mgr.run_async(self._kill_app_async(package_name), timeout=15)
            logger.info(f"iOS 应用停止成功: {package_name}")
            return True
        except Exception as e:
            logger.error(f"iOS 应用停止失败: {e}")
            return False

    async def _kill_app_async(self, bundle_id: str) -> None:
        """异步停止应用：先通过 DeviceInfo.proclist() 找到 PID，再 kill"""
        from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
        from pymobiledevice3.services.dvt.instruments.device_info import DeviceInfo
        from pymobiledevice3.services.dvt.instruments.process_control import (
            ProcessControl,
        )

        lockdown = self._conn_mgr.get_async_lockdown()
        async with (
            DvtProvider(lockdown) as dvt,
            DeviceInfo(dvt) as device_info,
            ProcessControl(dvt) as pc,
        ):
            processes = await device_info.proclist()
            for proc in processes:
                if proc.get("bundleIdentifier") == bundle_id:
                    pid = proc.get("pid")
                    if pid:
                        await pc.kill(pid)
                        return
            logger.warning(f"未找到运行中的 iOS 应用: {bundle_id}")

    def get_battery_level(self) -> int:
        """获取电池电量（通过 async DiagnosticsService.get_battery()）"""
        try:
            from pymobiledevice3.services.diagnostics import DiagnosticsService

            mgr = self._conn_mgr
            lockdown = mgr.get_async_lockdown()
            diag = DiagnosticsService(lockdown)
            battery = mgr.run_async(diag.get_battery(), timeout=10)
            return int(battery.get("BatteryCurrentCapacity", 100))
        except Exception as e:
            logger.debug(f"获取电池电量失败: {e}")
            return 100

    def get_device_temperature(self) -> float:
        """获取设备温度（iOS 限制访问）"""
        return 0.0

    def get_network_type(self) -> str:
        """获取网络类型"""
        return "Unknown"

    # ========== 性能指标采集接口 ==========

    def collect_fps(self, package_name: str) -> Optional[Dict[str, Any]]:
        """采集FPS数据（通过 DVT Graphics 服务的 CoreAnimation 帧率）"""
        try:
            apm = self._get_apm(package_name)
            if apm:
                return apm.collectFps()
        except Exception as e:
            logger.debug(f"iOS FPS 采集失败: {e}")
        return {"fps": 0, "jank": 0, "bigJank": 0}

    def collect_memory(self, package_name: str) -> Optional[Dict[str, Any]]:
        """采集内存数据"""
        apm = self._get_apm(package_name)
        if apm:
            return apm.collectMemory()
        return None

    def collect_cpu(self, package_name: str) -> Optional[Dict[str, Any]]:
        """采集CPU数据"""
        apm = self._get_apm(package_name)
        if apm:
            return apm.collectCpu()
        return None

    def collect_network(self, package_name: str) -> Optional[Dict[str, Any]]:
        """采集网络数据"""
        try:
            apm = self._get_apm(package_name)
            if apm:
                return apm.collectFlow()
        except Exception as e:
            logger.debug(f"iOS 网络采集失败: {e}")
        return {"upFlow": 0.0, "downFlow": 0.0}

    def collect_battery(self) -> Optional[Dict[str, Any]]:
        """采集电池数据"""
        try:
            apm = self._get_apm("__battery__")
            if apm:
                return apm.collectBattery()
        except Exception as e:
            logger.debug(f"iOS 电池采集失败: {e}")
        return {"level": 100, "temperature": 25.0}

    # ========== APM 管理方法 ==========

    def _get_apm(self, bundle_name: str):
        """获取或初始化 IOSAPM 实例 - 线程安全版本"""
        if bundle_name == "__battery__":
            with self._apm_lock:
                if self._apm:
                    return self._apm
                from insight_aitest.platform.services.collectors.ios.ios_apm import IOSAPM

                logger.debug(f"[APM管理] 创建电池专用 APM 实例: device={self.device_id}")
                self._apm = IOSAPM("", self.device_id)
                return self._apm

        if self._apm is not None and self._apm.bundle_name == bundle_name:
            return self._apm

        with self._apm_lock:
            if self._apm is not None and self._apm.bundle_name == bundle_name:
                return self._apm

            from insight_aitest.platform.services.collectors.ios.ios_apm import IOSAPM

            if self._apm is not None:
                try:
                    logger.debug(f"[APM管理] 停止旧 APM 实例: {self._apm.bundle_name}")
                    self._apm.stop()
                except Exception as e:
                    logger.warning(f"[APM管理] 停止旧 APM 失败: {e}")

            logger.debug(
                f"[APM管理] 创建新 APM 实例: bundle={bundle_name}, device={self.device_id}"
            )
            self._apm = IOSAPM(bundle_name, self.device_id)
            try:
                self._apm.start()
                logger.debug(f"[APM管理] APM 启动成功: {bundle_name}")
            except Exception as start_error:
                logger.error(f"[APM管理] APM 启动失败: {type(start_error).__name__}: {start_error}")
                self._apm = None
                raise

        return self._apm

    def cleanup(self):
        """清理设备适配器资源"""
        logger.info(f"开始清理iOS设备适配器: {self.device_id}")

        with self._connect_lock:
            try:
                # 停止 APM
                if self._apm:
                    try:
                        logger.debug(f"停止 IOSAPM: {self._apm.bundle_name}")
                        self._apm.stop()
                        self._apm = None
                    except Exception as e:
                        logger.error(f"停止 IOSAPM 失败（继续清理）: {e}")
                        self._apm = None

                # 断开设备连接
                try:
                    self.disconnect()
                except Exception as e:
                    logger.warning(f"断开设备连接失败（继续清理）: {e}")

                self._connected = False
                self._lockdown_proxy = None
                self._retry_count = 0
                self._last_error = None
                self._connecting = False

                logger.info(f"iOS设备适配器已清理: {self.device_id}")

            except Exception as e:
                logger.error(f"清理iOS设备适配器时出错: {e}", exc_info=True)
                self._connected = False
                self._lockdown_proxy = None
