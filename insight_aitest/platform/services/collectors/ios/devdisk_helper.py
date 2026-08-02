# -*- coding: utf-8 -*-
"""
iOS DeveloperDiskImage 自动挂载助手 (pymobiledevice3 v10.x async API)

提供 iOS 设备的 DeveloperDiskImage 自动挂载功能。
通过 IOSConnectionManager 在事件循环中执行 async auto_mount()。

注意：
- iOS <17: 挂载 DeveloperDiskImage 即可使用 DVT 服务
- iOS 17+: 需要先启用 Developer Mode，建立 tunnel，再挂载 personalized DDI，
  之后 ``com.apple.instruments.dtservicehub`` 等 DVT 服务才会在 RSD 上可用。
  ``auto_mount()`` 会自动按版本分发到 ``auto_mount_personalized``。
"""

from typing import Optional
from logzero import logger

from .connection_manager import IOSConnectionManager


class DevDiskHelper:
    """
    DeveloperDiskImage 挂载助手

    负责在 iOS 设备上自动挂载 DeveloperDiskImage / Personalized DDI，
    这是使用 DVT 协议进行性能监控的前提条件（iOS <17 和 iOS 17+ 均需要）。
    """

    # 类级别的缓存：记录已挂载的设备
    _mounted_devices: set = set()

    @staticmethod
    def ensure_developer_disk_mounted(device_udid: Optional[str] = None) -> bool:
        """
        确保 DeveloperDiskImage 已挂载

        如果未挂载，自动执行挂载操作。
        通过 IOSConnectionManager 在事件循环中执行 async auto_mount()。
        auto_mount 会自动按 iOS 版本选择：
        - iOS <17 → 普通 DeveloperDiskImage
        - iOS 17+ → personalized DDI（暴露 dtservicehub 等 DVT 服务）

        Args:
            device_udid: iOS 设备 UDID，如果为 None 则使用默认设备

        Returns:
            bool: DeveloperDiskImage 是否已挂载（或挂载成功）

        Raises:
            DeveloperModeNotEnabledError: iOS 17+ 设备未启用 Developer Mode
                （无法挂载 personalized DDI；需用户手动开启后重启设备）

        注意：
            - 首次挂载可能需要网络连接下载镜像
            - 挂载操作可能需要几秒钟
            - 使用缓存避免重复挂载检查（防止 UI 阻塞）
        """
        from .exceptions import DeveloperModeNotEnabledError

        # 使用设备 UDID 作为缓存键
        device_key = device_udid or "default"

        # 检查缓存：如果已挂载，直接返回
        if device_key in DevDiskHelper._mounted_devices:
            logger.debug(f"DeveloperDiskImage 已挂载（缓存）: {device_key}")
            return True

        if not device_udid:
            logger.warning("无 device_udid，跳过 DeveloperDiskImage 挂载")
            return False

        try:
            from pymobiledevice3.services.mobile_image_mounter import auto_mount
            from pymobiledevice3.exceptions import (
                AlreadyMountedError,
                DeveloperModeIsNotEnabledError,
            )

            logger.debug("===== DeveloperDiskImage 挂载检查 =====")

            # 通过 ConnectionManager 在事件循环中执行 async auto_mount
            mgr = IOSConnectionManager.get_instance(device_udid)
            if not mgr.is_connected:
                mgr.connect()

            lockdown = mgr.get_async_lockdown()

            # 在事件循环中执行 async auto_mount()
            try:
                mgr.run_async(auto_mount(lockdown), timeout=120)
                logger.info("✓ DeveloperDiskImage 挂载成功")
                DevDiskHelper._mounted_devices.add(device_key)
                return True
            except AlreadyMountedError:
                logger.info("✓ DeveloperDiskImage 已挂载")
                DevDiskHelper._mounted_devices.add(device_key)
                return True
            except DeveloperModeIsNotEnabledError:
                # iOS 17+ 未启用 Developer Mode → 无法挂载 personalized DDI。
                # 抛出项目自定义异常（在 NO_RETRY_EXCEPTIONS 中），上层不再无谓重试。
                logger.error(
                    "iOS 17+ 设备未启用 Developer Mode，无法挂载 Personalized DDI，"
                    "DVT 服务（dtservicehub）不可用"
                )
                raise DeveloperModeNotEnabledError()

        except ImportError as e:
            logger.error(f"无法导入 pymobiledevice3 模块: {e}")
            logger.error("请确保安装了最新版本的 pymobiledevice3:")
            logger.error("  pip install -U pymobiledevice3")
            return False

        except DeveloperModeNotEnabledError:
            # 已在上面记录日志，向上抛出供适配器处理（不重试）
            raise

        except Exception as e:
            logger.error(f"DeveloperDiskImage 挂载失败: {type(e).__name__}: {e}")
            logger.info("提示: iOS 17+ 需要先启用 Developer Mode")
            logger.info("      在设备上: 设置 > 隐私与安全 > 开发者模式")
            return False

    @staticmethod
    def query_developer_mode_status(device_udid: Optional[str] = None) -> Optional[bool]:
        """
        查询设备 Developer Mode 状态

        通过 IOSConnectionManager 执行 async query_developer_mode_status()。

        Args:
            device_udid: iOS 设备 UDID

        Returns:
            bool: Developer Mode 是否启用，如果查询失败返回 None
        """
        try:
            from pymobiledevice3.services.mobile_image_mounter import (
                MobileImageMounterService,
            )

            if not device_udid:
                return None

            mgr = IOSConnectionManager.get_instance(device_udid)
            if not mgr.is_connected:
                mgr.connect()

            lockdown = mgr.get_async_lockdown()
            mounter = MobileImageMounterService(lockdown=lockdown)
            status = mgr.run_async(mounter.query_developer_mode_status(), timeout=10)

            logger.info(f"Developer Mode 状态: {status}")
            return status

        except Exception as e:
            logger.warning(f"查询 Developer Mode 状态失败: {e}")
            return None

    @staticmethod
    def _run_amfi_action_via_usbmux(device_udid: str, action_coro_factory) -> bool:
        """通过独立的 usbmux lockdown 连接执行一个 AMFI 动作。

        iOS 17+/26 上，``com.apple.amfi.lockdown`` 等基础 lockdown 服务只能通过
        usbmux 访问，RSD tunnel 上没有（RSD 只暴露 CoreDevice/DVT 服务）。
        因此这里不走 IOSConnectionManager 的 RSD 路径，而是用
        ``create_using_usbmux`` 建立临时连接执行完即关闭。

        Args:
            device_udid: 设备 UDID
            action_coro_factory: 接收 amfi 实例、返回待执行协程的回调

        Returns:
            bool: 是否执行成功
        """
        try:
            from pymobiledevice3.lockdown import create_using_usbmux
            from pymobiledevice3.services.amfi import AmfiService
        except ImportError as e:
            logger.error(f"无法导入 pymobiledevice3 模块: {e}")
            return False

        async def _do():
            ld = await create_using_usbmux(device_udid)
            try:
                amfi = AmfiService(lockdown=ld)
                await action_coro_factory(amfi)
            finally:
                try:
                    await ld.close()
                except Exception:
                    pass

        try:
            mgr = IOSConnectionManager.get_instance(device_udid)
            if not mgr.is_connected:
                mgr.connect()
            mgr.run_async(_do(), timeout=30)
            return True
        except Exception as e:
            logger.error(f"AMFI 动作执行失败: {type(e).__name__}: {e}")
            return False

    @staticmethod
    def reveal_developer_mode(device_udid: Optional[str] = None) -> bool:
        """让 Developer Mode 开关在「设置 → 隐私与安全性」中显示出来。

        iOS 16+ 默认隐藏 Developer Mode 开关；只有设备被「配对/用于开发」后才会显示。
        无需 Mac/Xcode：本方法通过 AMFI 服务直接发送 reveal 动作。

        iOS 17+/26：必须经 usbmux 访问 amfi 服务（RSD 上没有 amfi）。

        Args:
            device_udid: 设备 UDID

        Returns:
            bool: 是否成功发送 reveal 动作
        """
        if not device_udid:
            logger.warning("无 device_udid，跳过 reveal Developer Mode")
            return False

        logger.info("尝试让 Developer Mode 开关显示在设置中...")

        ok = DevDiskHelper._run_amfi_action_via_usbmux(
            device_udid, lambda amfi: amfi.reveal_developer_mode_option_in_ui()
        )
        if ok:
            logger.info(
                "✓ 已发送 reveal 动作。请在设备上检查："
                "设置 → 隐私与安全性 → 滑到底部应出现「开发者模式」"
            )
        return ok

    @staticmethod
    def enable_developer_mode(device_udid: Optional[str] = None) -> bool:
        """
        启用 Developer Mode（需要在设备上确认）

        通过 usbmux 路径执行 AMFI 的 enable_developer_mode（设备会重启）。
        iOS 17+/26 必须经 usbmux（RSD 上没有 amfi 服务）。

        注意：调用前通常应先调用 ``reveal_developer_mode`` 让开关显示出来，
        然后用户在设备上手动开启（推荐）。此方法会触发重启，仅在确有必要时使用。

        Args:
            device_udid: iOS 设备 UDID

        Returns:
            bool: 是否成功触发启用流程

        注意：
            - 此操作需要在设备上手动确认
            - 设备可能需要重启
        """
        if not device_udid:
            return False

        logger.info("尝试启用 Developer Mode（设备将重启）...")
        logger.info("请在设备上确认此操作")

        ok = DevDiskHelper._run_amfi_action_via_usbmux(
            device_udid,
            # enable_post_restart=False：避免在 usbmux 临时连接里长时间等待重启
            lambda amfi: amfi.enable_developer_mode(enable_post_restart=False),
        )
        if ok:
            logger.info("Developer Mode 启用流程已触发，请在设备上完成确认并重启设备")
        return ok

    @staticmethod
    def clear_cache() -> None:
        """清除挂载缓存（测试用）。"""
        DevDiskHelper._mounted_devices.clear()
