# -*- coding: utf-8 -*-
"""
ADB 工具模块
提供 Android Debug Bridge (ADB) 命令的封装
"""

import os
import platform
import subprocess
import shutil
import re
from logzero import logger


class ADBHelper:
    """ADB 工具类，封装 ADB 命令操作"""

    # 安全命令白名单（允许的字符模式）
    _SAFE_CMD_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\s/\.@:=\',\[\]\{\}\(\)\+\*^!~\|&<>]+$")
    # 设备 ID 安全模式
    _SAFE_DEVICE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9:\.\-]+$")

    def __init__(self, adb_path=None):
        """
        初始化 ADB 工具

        Args:
            adb_path: ADB 可执行文件路径，如果为 None 则自动查找
        """
        self._adb_path = adb_path or self._find_adb()
        logger.info(f"ADB 路径: {self.adb_path}")

    @property
    def adb_path(self):
        """获取 ADB 可执行文件路径"""
        if self._adb_path and os.path.exists(self._adb_path):
            return self._adb_path
        # 重新查找
        self._adb_path = self._find_adb()
        return self._adb_path

    @staticmethod
    def _find_adb():
        """
        自动查找系统中的 ADB 可执行文件

        查找顺序:
        1. 系统环境变量 PATH 中的 adb
        2. Android SDK 常见安装路径
        3. 当前目录下的 adb
        """
        # 1. 检查环境变量 PATH
        adb_in_path = shutil.which("adb")
        if adb_in_path:
            return adb_in_path

        # 2. 检查常见的 Android SDK 路径
        system = platform.system()
        possible_paths = []

        if system == "Windows":
            possible_paths = [
                os.path.expanduser("~/AppData/Local/Android/Sdk/platform-tools/adb.exe"),
                os.path.expanduser("~/Android/Sdk/platform-tools/adb.exe"),
                "C:/Android/Sdk/platform-tools/adb.exe",
                "C:/adb/adb.exe",
            ]
        elif system == "Darwin":  # macOS
            possible_paths = [
                os.path.expanduser("~/Library/Android/sdk/platform-tools/adb"),
                "/Users/*/Library/Android/sdk/platform-tools/adb",
                "/opt/homebrew/bin/adb",
                "/usr/local/bin/adb",
            ]
        else:  # Linux
            possible_paths = [
                os.path.expanduser("~/Android/Sdk/platform-tools/adb"),
                "/usr/bin/adb",
                "/opt/android-sdk/platform-tools/adb",
            ]

        # 检查当前目录
        current_dir_adb = os.path.join(os.path.dirname(__file__), "adb")
        if platform.system() == "Windows":
            current_dir_adb += ".exe"
        possible_paths.insert(0, current_dir_adb)

        for path in possible_paths:
            # 展开通配符
            expanded_paths = [path]
            if "*" in path:
                import glob

                expanded_paths = glob.glob(path)

            for expanded_path in expanded_paths:
                if os.path.exists(expanded_path):
                    logger.info(f"找到 ADB: {expanded_path}")
                    return expanded_path

        logger.warning("未找到 ADB，请确保已安装 Android SDK 或将 ADB 添加到 PATH")
        return "adb"  # 返回默认值，希望它在 PATH 中

    @staticmethod
    def _validate_command(cmd: str) -> bool:
        """
        验证命令是否安全

        Args:
            cmd: 要验证的命令

        Returns:
            bool: 命令是否安全
        """
        if not cmd or not isinstance(cmd, str):
            return False

        # 检查是否包含危险的 shell 元字符
        dangerous_patterns = [";", "&&", "||", "|", "`", "$(", "$("]
        for pattern in dangerous_patterns:
            if pattern in cmd:
                logger.warning(f"[ADB] 命令包含危险字符: {pattern}")
                return False

        # 检查是否匹配安全模式
        if not ADBHelper._SAFE_CMD_PATTERN.match(cmd):
            logger.warning(f"[ADB] 命令包含不安全字符: {cmd[:50]}...")
            return False

        return True

    @staticmethod
    def _validate_device_id(device_id: str) -> bool:
        """
        验证设备 ID 是否安全

        Args:
            device_id: 要验证的设备 ID

        Returns:
            bool: 设备 ID 是否安全
        """
        if not device_id or not isinstance(device_id, str):
            return False
        return bool(ADBHelper._SAFE_DEVICE_ID_PATTERN.match(device_id))

    def shell(self, cmd, deviceId=None, timeout=30):
        """
        执行 ADB shell 命令（带输入验证）

        Args:
            cmd: 要执行的 shell 命令
            deviceId: 设备 ID，如果为 None 则使用默认设备
            timeout: 命令超时时间（秒）

        Returns:
            str: 命令执行结果，如果失败返回空字符串
        """
        # 输入验证
        if not self._validate_command(cmd):
            logger.error(f"[ADB] 命令验证失败，拒绝执行: {cmd[:100]}")
            return ""

        if deviceId is not None and not self._validate_device_id(deviceId):
            logger.error(f"[ADB] 设备 ID 验证失败: {deviceId}")
            return ""

        try:
            # 使用参数列表而非字符串拼接，防止命令注入
            cmd_list = [self.adb_path]
            if deviceId:
                cmd_list.extend(["-s", deviceId])
            cmd_list.extend(["shell", cmd])

            result = subprocess.run(
                cmd_list,
                shell=False,  # 不使用 shell，防止命令注入
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logger.warning(f"[ADB] 命令执行失败: {cmd}, 错误: {result.stderr}")
                return ""

        except subprocess.TimeoutExpired:
            logger.error(f"[ADB] 命令超时: {cmd}")
            return ""
        except FileNotFoundError:
            logger.error(f"[ADB] 未找到: {self.adb_path}")
            return ""
        except Exception as e:
            logger.error(f"[ADB] 命令执行异常: {e}")
            return ""

    def shell_noDevice(self, cmd, timeout=30):
        """
        执行不需要设备 ID 的 ADB 命令

        Args:
            cmd: 要执行的命令
            timeout: 命令超时时间（秒）

        Returns:
            int: 命令返回码
        """
        try:
            # 使用参数列表而不是字符串拼接，防止命令注入
            cmd_list = [self.adb_path] + cmd.split()
            result = subprocess.run(
                cmd_list, shell=False, capture_output=True, text=True, timeout=timeout
            )
            return result.returncode
        except Exception as e:
            logger.error(f"ADB 命令执行异常: {e}")
            return -1

    def devices(self, timeout=10):
        """
        获取连接的设备列表

        Returns:
            list: 设备 ID 列表
        """
        try:
            # 使用参数列表防止命令注入
            result = subprocess.run(
                [self.adb_path, "devices"],
                shell=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            if result.returncode != 0:
                logger.error("获取设备列表失败")
                return []

            lines = result.stdout.strip().split("\n")
            devices = []
            for line in lines[1:]:  # 跳过第一行 "List of devices attached"
                line = line.strip()
                if not line:
                    continue
                parts = line.split("\t")
                if len(parts) >= 2 and parts[1] == "device":
                    devices.append(parts[0])

            return devices

        except Exception as e:
            logger.error(f"获取设备列表失败: {e}")
            return []

    def get_device_property(self, prop, deviceId):
        """
        获取设备系统属性

        Args:
            prop: 属性名称，如 "ro.product.model"
            deviceId: 设备 ID

        Returns:
            str: 属性值
        """
        return self.shell(f"getprop {prop}", deviceId)

    def install(self, apk_path, deviceId=None, reinstall=True):
        """
        安装 APK 文件

        Args:
            apk_path: APK 文件路径
            deviceId: 设备 ID
            reinstall: 是否覆盖安装

        Returns:
            bool: 是否成功
        """
        if not os.path.exists(apk_path):
            logger.error(f"APK 文件不存在: {apk_path}")
            return False

        try:
            # 使用参数列表防止命令注入
            cmd_list = [self.adb_path]
            if deviceId:
                cmd_list.extend(["-s", deviceId])
            cmd_list.extend(["install"])
            if reinstall:
                cmd_list.append("-r")
            cmd_list.append(apk_path)

            result = subprocess.run(
                cmd_list, shell=False, capture_output=True, text=True, timeout=120
            )

            if result.returncode == 0:
                logger.info(f"APK 安装成功: {apk_path}")
                return True
            else:
                logger.error(f"APK 安装失败: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"APK 安装异常: {e}")
            return False

    def pull(self, remote_path, local_path, deviceId=None):
        """
        从设备拉取文件

        Args:
            remote_path: 设备上的文件路径
            local_path: 本地保存路径
            deviceId: 设备 ID

        Returns:
            bool: 是否成功
        """
        try:
            # 使用参数列表防止命令注入
            cmd_list = [self.adb_path]
            if deviceId:
                cmd_list.extend(["-s", deviceId])
            cmd_list.extend(["pull", remote_path, local_path])

            result = subprocess.run(cmd_list, shell=False, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"拉取文件失败: {e}")
            return False

    def push(self, local_path, remote_path, deviceId=None):
        """
        推送文件到设备

        Args:
            local_path: 本地文件路径
            remote_path: 设备上的目标路径
            deviceId: 设备 ID

        Returns:
            bool: 是否成功
        """
        try:
            # 使用参数列表防止命令注入
            cmd_list = [self.adb_path]
            if deviceId:
                cmd_list.extend(["-s", deviceId])
            cmd_list.extend(["push", local_path, remote_path])

            result = subprocess.run(cmd_list, shell=False, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"推送文件失败: {e}")
            return False

    def forward(self, local, remote, deviceId=None):
        """
        设置端口转发

        Args:
            local: 本地端口 (如 "tcp:8080")
            remote: 远程端口 (如 "tcp:8080")
            deviceId: 设备 ID

        Returns:
            bool: 是否成功
        """
        try:
            # 使用参数列表防止命令注入
            cmd_list = [self.adb_path]
            if deviceId:
                cmd_list.extend(["-s", deviceId])
            cmd_list.extend(["forward", local, remote])

            result = subprocess.run(cmd_list, shell=False, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"设置端口转发失败: {e}")
            return False


# 创建全局单例实例
adb = ADBHelper()


# 导出 adb_path 属性以保持向后兼容
def shell(cmd, deviceId=None, timeout=30):
    """快捷函数：执行 shell 命令"""
    return adb.shell(cmd, deviceId, timeout)


def shell_noDevice(cmd, timeout=30):
    """快捷函数：执行无设备命令"""
    return adb.shell_noDevice(cmd, timeout)


# 设置 adb_path 属性
def _get_adb_path():
    return adb.adb_path


# 创建模块级的 adb_path 属性
import types  # noqa: E402

adb_module = types.ModuleType("adb")
adb_module.shell = shell
adb_module.shell_noDevice = shell_noDevice
adb_module.adb_path = property(_get_adb_path)
