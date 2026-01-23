# -*- coding: utf-8 -*-
"""
iOS DeveloperDiskImage 自动挂载助手

提供 iOS 设备的 DeveloperDiskImage 自动挂载功能
特别针对 iOS 17+ 设备优化

使用 pymobiledevice3 的 mounter 服务实现自动挂载

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License
"""

from typing import Optional
from logzero import logger


class DevDiskHelper:
    """
    DeveloperDiskImage 挂载助手

    负责在 iOS 设备上自动挂载 DeveloperDiskImage，
    这是使用 DVT 协议进行性能监控的前提条件。
    """

    @staticmethod
    def ensure_developer_disk_mounted(device_udid: Optional[str] = None) -> bool:
        """
        确保 DeveloperDiskImage 已挂载

        如果未挂载，自动执行挂载操作。

        Args:
            device_udid: iOS 设备 UDID，如果为 None 则使用默认设备

        Returns:
            bool: DeveloperDiskImage 是否已挂载（或挂载成功）

        注意：
            - iOS 17+ 需要启用 Developer Mode
            - 首次挂载可能需要网络连接下载镜像
            - 挂载操作可能需要几秒钟
        """
        try:
            from pymobiledevice3.lockdown import create_using_usbmux
            from pymobiledevice3.services.mounter import MounterService

            logger.info("===== DeveloperDiskImage 挂载检查 =====")

            # 创建 lockdown 连接
            if device_udid:
                lockdown = create_using_usbmux(device_udid)
            else:
                lockdown = create_using_usbmux()

            # 创建 MounterService
            mounter = MounterService(lockdown)

            # 检查是否已挂载
            logger.info("检查 DeveloperDiskImage 挂载状态...")
            mounted_images = mounter.list_images()

            is_mounted = False
            for image in mounted_images:
                if image.get('DiskImageType') == 'Developer' and image.get('IsMounted'):
                    logger.info(f"✓ DeveloperDiskImage 已挂载: {image.get('MountPath')}")
                    is_mounted = True
                    break

            if is_mounted:
                return True

            # 未挂载，执行自动挂载
            logger.info("DeveloperDiskImage 未挂载，开始自动挂载...")

            # 使用 auto-mount 功能（pymobiledevice3 7.x+ 支持）
            # 这会自动检测设备型号并下载/挂载对应的 DeveloperDiskImage
            mounter.auto_mount()

            logger.info("✓ DeveloperDiskImage 挂载成功")
            return True

        except ImportError:
            logger.error("无法导入 pymobiledevice3.mounter，请确保安装了最新版本")
            return False

        except Exception as e:
            logger.error(f"DeveloperDiskImage 挂载失败: {type(e).__name__}: {e}")
            logger.info("提示: iOS 17+ 需要先启用 Developer Mode")
            logger.info("      在设备上: 设置 > 隐私与安全 > 开发者模式")
            return False

    @staticmethod
    def query_developer_mode_status(device_udid: Optional[str] = None) -> Optional[bool]:
        """
        查询设备 Developer Mode 状态

        Args:
            device_udid: iOS 设备 UDID

        Returns:
            bool: Developer Mode 是否启用，如果查询失败返回 None
        """
        try:
            from pymobiledevice3.lockdown import create_using_usbmux
            from pymobiledevice3.services.mounter import MounterService

            if device_udid:
                lockdown = create_using_usbmux(device_udid)
            else:
                lockdown = create_using_usbmux()

            mounter = MounterService(lockdown)
            status = mounter.query_developer_mode_status()

            logger.info(f"Developer Mode 状态: {status}")
            return status

        except Exception as e:
            logger.warning(f"查询 Developer Mode 状态失败: {e}")
            return None

    @staticmethod
    def enable_developer_mode(device_udid: Optional[str] = None) -> bool:
        """
        启用 Developer Mode（需要在设备上确认）

        Args:
            device_udid: iOS 设备 UDID

        Returns:
            bool: 是否成功触发启用流程

        注意：
            - 此操作需要在设备上手动确认
            - 设备可能需要重启
        """
        try:
            from pymobiledevice3.services.amfi import AmfiService

            logger.info("尝试启用 Developer Mode...")
            logger.info("请在设备上确认此操作")

            if device_udid:
                lockdown = create_using_usbmux(device_udid)
            else:
                lockdown = create_using_usbmux()

            amfi = AmfiService(lockdown)
            amfi.enable_developer_mode()

            logger.info("Developer Mode 启用流程已触发")
            logger.info("请在设备上完成确认并重启设备")
            return True

        except Exception as e:
            logger.error(f"启用 Developer Mode 失败: {e}")
            return False
