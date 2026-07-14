# -*- coding: utf-8 -*-
"""
iOS 网络流量监控采集器 (pymobiledevice3 v9.x async API)

基于 pcapd 服务的 async watch() 实现系统级网络流量监控。

pymobiledevice3 v9.x 变更：
- PcapdService.watch() 变为 async generator，需要 async for 消费
- lockdown 通过 IOSConnectionManager 获取（支持 iOS 17+ tunnel）

捕获协程运行在 ConnectionManager 的 AsyncLoopThread 上。
"""

import asyncio
import threading
import time
from typing import Dict, Optional
from logzero import logger

from pymobiledevice3.services.pcapd import PcapdService

from .connection_manager import IOSConnectionManager


class NetworkCollector:
    """iOS 网络流量采集器（基于 pcapd 服务）"""

    def __init__(self, adapter, bundle_id: str, interface_name: Optional[str] = None):
        """
        初始化网络流量采集器

        Args:
            adapter: IOSDeviceAdapter 实例
            bundle_id: 应用 Bundle ID（用于过滤）
            interface_name: 网络接口名称（如 'en' 用于 WiFi，'pdp_ip' 用于移动网络）
                          None 表示监控所有接口
        """
        self.adapter = adapter
        self.bundle_id = bundle_id
        self.interface_name = interface_name

        # 流量统计
        self._traffic_data = {
            "total_upload": 0,  # 总上传字节
            "total_download": 0,  # 总下载字节
            "last_upload": 0,  # 上次采集时的上传量
            "last_download": 0,  # 上次采集时的下载量
            "last_time": time.time(),  # 上次采集时间
        }

        # 进程名映射表（Bundle ID -> 进程名）
        self._process_names = set()
        self._build_process_name_map()

        # 后台捕获 task（运行在 ConnectionManager 事件循环上）
        self._capture_task: Optional[asyncio.Future] = None
        self._running = False
        self._lock = threading.Lock()

    def _build_process_name_map(self):
        """
        构建 Bundle ID 到进程名的映射

        iOS 应用的进程名通常是 Bundle ID 的最后一部分
        例如: com.example.app -> app
        """
        # 获取 Bundle ID 的最后一部分作为进程名
        parts = self.bundle_id.split(".")
        if len(parts) > 1:
            # 添加完整 Bundle ID 的最后一部分
            self._process_names.add(parts[-1])
            # 也可能应用名就是最后一部分的大写开头
            self._process_names.add(parts[-1].capitalize())

            # 对于常见应用，添加特殊映射
            common_apps = {
                "com.apple.mobilesafari": ["Safari"],
                "com.tencent.xin": ["WeChat", "MicroMessenger"],
                "com.alipay.iphoneclient": ["Alipay"],
            }
            if self.bundle_id in common_apps:
                self._process_names.update(common_apps[self.bundle_id])

        logger.debug(f"网络采集器进程名列表: {self._process_names}")

    def start(self):
        """启动网络流量捕获"""
        if self._running:
            logger.warning("网络采集器已在运行")
            return

        device_id = getattr(self.adapter, "device_id", None)
        if not device_id:
            logger.error("无 device_id，无法启动网络采集器")
            return

        logger.info("启动网络流量采集器...")
        self._running = True
        self._reset_traffic_stats()

        # 在 ConnectionManager 事件循环上启动 async 捕获协程
        mgr = IOSConnectionManager.get_instance(device_id)
        if not mgr.is_connected:
            mgr.connect()

        self._capture_task = mgr.loop_thread.create_task(self._capture_coroutine())

        logger.info("网络流量采集器已启动")

    def stop(self):
        """停止网络流量捕获"""
        if not self._running:
            return

        logger.info("停止网络流量采集器...")
        self._running = False

        # 取消捕获协程
        if self._capture_task is not None:
            try:
                self._capture_task.cancel()
            except Exception:
                pass
            self._capture_task = None

        logger.info("网络流量采集器已停止")

    def collect(self) -> Dict[str, float]:
        """
        采集网络流量数据

        返回自上次调用以来的平均流量速率（KB/s）

        Returns:
            {
                'upFlow': float,      # 上传流量速率 (KB/s)
                'downFlow': float     # 下载流量速率 (KB/s)
            }
        """
        with self._lock:
            current_time = time.time()
            elapsed = current_time - self._traffic_data["last_time"]

            # 获取当前累计流量
            current_upload = self._traffic_data["total_upload"]
            current_download = self._traffic_data["total_download"]

            # 计算增量
            upload_delta = current_upload - self._traffic_data["last_upload"]
            download_delta = current_download - self._traffic_data["last_download"]

            # 计算速率 (字节/秒 -> KB/s)
            if elapsed > 0:
                up_flow_kb = (upload_delta / elapsed) / 1024
                down_flow_kb = (download_delta / elapsed) / 1024
            else:
                up_flow_kb = 0.0
                down_flow_kb = 0.0

            # 更新上次记录
            self._traffic_data["last_upload"] = current_upload
            self._traffic_data["last_download"] = current_download
            self._traffic_data["last_time"] = current_time

            logger.debug(f"网络流量: 上传={up_flow_kb:.2f} KB/s, " f"下载={down_flow_kb:.2f} KB/s")

            return {"upFlow": round(up_flow_kb, 2), "downFlow": round(down_flow_kb, 2)}

    def _reset_traffic_stats(self):
        """重置流量统计"""
        with self._lock:
            self._traffic_data = {
                "total_upload": 0,
                "total_download": 0,
                "last_upload": 0,
                "last_download": 0,
                "last_time": time.time(),
            }

    async def _capture_coroutine(self):
        """async 捕获协程：通过 pcapd.watch() 持续接收数据包。

        运行在 IOSConnectionManager 的 AsyncLoopThread 上。
        """
        try:
            device_id = getattr(self.adapter, "device_id", None)
            if not device_id:
                logger.error("网络采集协程: 无 device_id")
                self._running = False
                return

            mgr = IOSConnectionManager.get_instance(device_id)
            lockdown = mgr.get_async_lockdown()

            pcapd = PcapdService(lockdown)

            logger.info("pcapd 服务已启动，开始捕获网络数据包...")

            # pymobiledevice3 v9.x: watch() 是 async generator
            async for packet in pcapd.watch(packets_count=-1):  # 无限捕获
                if not self._running:
                    break

                # 处理数据包
                self._process_packet(packet)

        except asyncio.CancelledError:
            logger.info("网络捕获协程已取消")
            raise
        except Exception as e:
            logger.error(f"网络捕获协程异常: {type(e).__name__}: {e}")
            # 设置失败标志
            with self._lock:
                self._running = False

    def _process_packet(self, packet):
        """
        处理单个数据包

        Args:
            packet: pcapd 返回的数据包对象
        """
        try:
            # 过滤接口
            if self.interface_name and packet.interface_name != self.interface_name:
                return

            # 注意：iOS pcapd 提供 io 字段来判断方向
            # io=1 (0x01) → 出站/上传
            # io=16 (0x10) 或其他值 → 入站/下载

            # 获取数据长度
            data_len = len(packet.data) if packet.data else 0
            if data_len == 0:
                return

            # 使用 io 字段判断方向
            # io=1 表示出站(上传)，其他值表示入站(下载)
            is_upload = packet.io == 1

            with self._lock:
                if is_upload:
                    self._traffic_data["total_upload"] += data_len
                else:
                    self._traffic_data["total_download"] += data_len

        except Exception as e:
            logger.debug(f"处理数据包时出错: {e}")
