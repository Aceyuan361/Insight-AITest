# -*- coding: utf-8 -*-
"""
Insight-Eye Windows 打包脚本

使用 PyInstaller 将应用打包为 Windows 可执行文件

依赖:
    pip install pyinstaller

使用:
    python build.py
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

# ==================== 配置 ====================
PROJECT_DIR = Path(__file__).parent.absolute()
BUILD_DIR = PROJECT_DIR / "build"
DIST_DIR = PROJECT_DIR / "dist"
SPEC_FILE = PROJECT_DIR / "insight_eye.spec"

# 需要保留的核心文件和目录
CORE_DIRS = [
    "insight_eyes/__init__.py",
    "insight_eyes/__main__.py",
    "insight_eyes/public",
    "insight_eyes/desktop",
]

# 需要排除的文件模式
EXCLUDE_PATTERNS = [
    "*.pyc",
    "__pycache__",
    "*.pyo",
    ".pytest_cache",
    "venv",
    ".git",
    ".idea",
    ".vscode",
]

# 排除测试文件
EXCLUDE_FILES = [
    "test_*.py",
    "verify_*.py",
    "fix_*.py",
    "diagnose_*.py",
    "simple_test.py",
    "final_test.py",
    "quick_test*.py",
    "nul",
    "app.log",
    "crash_log.txt",
    "test_results.txt",
    "run_*.py",
    "*完成报告.md",
    "*SUMMARY.md",
    "*REPORT.md",
]

# 需要排除的文档（开发相关）
EXCLUDE_DOCS = [
    "docs/plans",
    "docs/daily",
    "docs/*报告*.md",
    "docs/*迁移*.md",
    "docs/*SUMMARY*.md",
    "docs/*Task*.md",
    "docs/Claude_Code_*.md",
    "docs/Skills*.md",
    "agents/",
    ".claude/",
]

# ==================== 工具函数 ====================
def log(message: str):
    """打印日志"""
    print(f"[Build] {message}")

def run_command(cmd: list, cwd=None):
    """运行命令"""
    log(f"执行: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        log(f"错误: {result.stderr}")
        raise RuntimeError(f"命令执行失败: {' '.join(cmd)}")
    return result.stdout

def clean_build_dirs():
    """清理构建目录"""
    log("清理构建目录...")

    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
        log(f"删除: {BUILD_DIR}")

    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
        log(f"删除: {DIST_DIR}")

def install_dependencies():
    """安装打包依赖"""
    log("安装打包依赖...")
    run_command([sys.executable, "-m", "pip", "install", "pyinstaller==5.13.2"])

def check_pyinstaller():
    """检查 PyInstaller 是否安装"""
    try:
        result = run_command([sys.executable, "-m", "PyInstaller", "--version"])
        log(f"PyInstaller 版本: {result.strip()}")
        return True
    except RuntimeError:
        return False

def prepare_source():
    """准备源代码 - 移除不需要的文件"""
    log("准备源代码...")

    # 检查 requirements.txt
    req_file = PROJECT_DIR / "insight_eyes" / "desktop" / "requirements.txt"
    if not req_file.exists():
        log(f"警告: requirements.txt 不存在于 {req_file}")

    # 创建临时的干净版本（仅用于打包）
    # 这里我们选择在原目录上工作，通过 .spec 文件控制打包内容

def build_executable():
    """构建可执行文件"""
    log("开始构建可执行文件...")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        str(SPEC_FILE)
    ]

    run_command(cmd, cwd=PROJECT_DIR)
    log("构建完成!")

def create_portable_package():
    """创建便携版包"""
    log("创建便携版包...")

    portable_dir = DIST_DIR / "Insight-Eye-Portable"
    if portable_dir.exists():
        shutil.rmtree(portable_dir)
    portable_dir.mkdir()

    # 复制可执行文件（PyInstaller 生成的文件名是 Insight-Eye.exe）
    exe_src = DIST_DIR / "Insight-Eye" / "Insight-Eye.exe"
    if exe_src.exists():
        shutil.copy2(exe_src, portable_dir / "Insight-Eye.exe")
        log(f"复制可执行文件到: {portable_dir}")
    else:
        raise RuntimeError(f"找不到可执行文件: {exe_src}")

    # 创建必要目录结构
    (portable_dir / "data").mkdir(exist_ok=True)
    (portable_dir / "logs").mkdir(exist_ok=True)

    # 创建启动脚本
    start_bat = portable_dir / "启动应用.bat"
    start_bat.write_text("""@echo off
chcp 65001 > nul
echo 正在启动 Insight-Eye...
start "" "Insight-Eye.exe"
""")

    # 创建说明文档
    readme = portable_dir / "README.txt"
    readme.write_text("""Insight-Eye 便携版使用说明
========================

1. 双击 "启动应用.bat" 启动程序

2. 系统要求:
   - Windows 10/11 64位
   - 屏幕分辨率建议 1280x720 或更高

3. 设备支持:
   [Android 设备]
   - 需要安装 ADB (Android Debug Bridge)
   - 如未安装 ADB，请运行 installer 目录中的 install_adb.bat
   - 或手动下载: https://developer.android.com/studio/releases/platform-tools

   [iOS 设备]
   - 需要安装 pymobiledevice3 库
   - 需要信任电脑并启用开发者模式
   - 支持系统: iOS 16.3.1 及以上版本

4. 首次使用:
   [Android]
   - 连接 Android 设备到电脑
   - 启用 USB 调试模式
   - 允许 USB 调试
   - 在应用中点击 "刷新设备" 按钮

   [iOS]
   - 连接 iOS 设备到电脑
   - 在设备上信任此电脑
   - 启用开发者模式（iOS 16+）
   - 在应用中点击 "刷新设备" 按钮

5. 监控能力:
   [Android 平台]
   - CPU 使用率、内存使用、FPS 帧率
   - 网络流量（应用级）、GPU 能耗
   - 电池状态、温度监控

   [iOS 平台]
   - CPU 使用率、内存使用、FPS（系统刷新率参考）
   - 网络流量（系统级）、电池状态
   - 注意：iOS GPU 监控受系统限制暂不支持

6. 数据目录:
   - data/: 存储数据库文件
   - logs/: 存储日志文件

7. 常见问题:
   [Android]
   - 如果无法识别设备，请检查 ADB 是否正确安装
   - 在命令行运行 `adb devices` 确认设备连接
   - 确保 USB 数据线支持数据传输（非仅充电线）

   [iOS]
   - 确保已安装 pymobiledevice3: pip install pymobiledevice3
   - 首次连接需要在设备上信任电脑
   - iOS 16+ 需要在设置中启用开发者模式

版本: 1.0.1
""")

    log(f"便携版包创建完成: {portable_dir}")

def create_installer_script():
    """创建安装程序脚本"""
    log("创建安装程序配置...")

    # 这里可以集成 NSIS 或 Inno Setup，暂时先创建一个简单的安装脚本
    installer_dir = DIST_DIR / "installer"
    if installer_dir.exists():
        shutil.rmtree(installer_dir)
    installer_dir.mkdir()

    # 复制 ADB 安装脚本
    adb_installer = PROJECT_DIR / "install_adb.bat"
    if adb_installer.exists():
        shutil.copy2(adb_installer, installer_dir / "install_adb.bat")
        log(f"复制 ADB 安装脚本")

    # 创建安装脚本
    install_bat = installer_dir / "install.bat"
    install_bat.write_text("""@echo off
setlocal enabledelayedexpansion

echo ========================================
echo   Insight-Eye 安装程序 v1.0.1
echo ========================================
echo.
echo 支持平台: Android、iOS
echo.

set "INSTALL_DIR=%USERPROFILE%\\Insight-Eye"

echo 安装目录: !INSTALL_DIR!
echo.
echo 请选择安装类型:
echo   1. 便携版（推荐）
echo   2. 安装版
echo.
set /p choice="请输入选项 (1 或 2): "

if "!choice!"=="1" (
    echo.
    echo 正在安装便携版...
    xcopy /E /I /Y "Insight-Eye-Portable" "!INSTALL_DIR!"
    echo.
    echo 安装完成！
    echo.
    echo 安装位置: !INSTALL_DIR!
    echo.
    echo 如需卸载，直接删除安装目录即可

) else if "!choice!"=="2" (
    echo.
    echo 正在安装安装版...
    xcopy /E /I /Y "Insight-Eye-Portable" "!INSTALL_DIR!"

    REM 创建开始菜单快捷方式
    set "START_MENU=%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs"
    powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%START_MENU%\\Insight-Eye.lnk'); $s.TargetPath = '!INSTALL_DIR!\\启动应用.bat'; $s.WorkingDirectory = '!INSTALL_DIR!'; $s.Save()"

    REM 创建桌面快捷方式
    set "DESKTOP=%USERPROFILE%\\Desktop"
    powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%DESKTOP%\\Insight-Eye.lnk'); $s.TargetPath = '!INSTALL_DIR!\\启动应用.bat'; $s.WorkingDirectory = '!INSTALL_DIR!'; $s.Save()"

    echo.
    echo 安装完成！
    echo 开始菜单: Insight-Eye
    echo 桌面快捷方式: Insight-Eye
    echo.
    echo 如需卸载，请删除安装目录和快捷方式

) else (
    echo 无效选项，安装取消。
    goto :end
)

echo.
echo ========================================
echo   ADB 安装检查
echo ========================================
echo.

REM 检查 ADB 是否已安装
where adb >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] 未检测到 ADB
    echo.
    echo Insight-Eye 需要 ADB 来连接 Android 设备
    echo.
    set /p install_adb="是否现在安装 ADB? (Y/N): "
    if /i "!install_adb!"=="Y" (
        start /wait "" "%~dp0install_adb.bat"
    )
) else (
    echo [√] ADB 已安装
)

echo.
:end
pause
""")

    # 创建卸载脚本
    uninstall_bat = installer_dir / "uninstall.bat"
    uninstall_bat.write_text("""@echo off
setlocal enabledelayedexpansion

echo ========================================
echo   Insight-Eye 卸载程序
echo ========================================
echo.

set "INSTALL_DIR=%USERPROFILE%\\Insight-Eye"

if not exist "%INSTALL_DIR%" (
    echo Insight-Eye 未安装
    goto :end
)

echo 卸载将删除以下内容:
echo   - 安装目录: %INSTALL_DIR%
echo   - 开始菜单快捷方式
echo   - 桌面快捷方式
echo.
set /p confirm="确认卸载? (Y/N): "

if /i not "%confirm%"=="Y" (
    echo 卸载已取消
    goto :end
)

echo.
echo 正在卸载...

REM 删除快捷方式
del "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Insight-Eye.lnk" 2>nul
del "%USERPROFILE%\\Desktop\\Insight-Eye.lnk" 2>nul

REM 删除安装目录
rmdir /s /q "%INSTALL_DIR%" 2>nul

echo.
echo [√] 卸载完成

:end
pause
""")

    log(f"安装脚本创建完成: {install_bat}")

def build_installer():
    """构建完整安装包"""
    clean_build_dirs()
    prepare_source()
    build_executable()
    create_portable_package()
    create_installer_script()

    log("=" * 60)
    log("Insight-Eye v1.0.1 构建完成！")
    log("=" * 60)
    log(f"可执行文件: {DIST_DIR / 'Insight-Eye' / 'Insight-Eye.exe'}")
    log(f"便携版包: {DIST_DIR / 'Insight-Eye-Portable'}")
    log(f"安装程序: {DIST_DIR / 'installer'}")
    log("=" * 60)
    log("支持平台: Android、iOS")
    log("=" * 60)

# ==================== 主程序 ====================
if __name__ == "__main__":
    try:
        print("=" * 60)
        print("Insight-Eye v1.0.1 Windows 打包工具")
        print("=" * 60)

        # 检查 PyInstaller
        if not check_pyinstaller():
            print("\nPyInstaller 未安装，正在安装...")
            install_dependencies()

        # 执行构建
        build_installer()

        print("\n按任意键退出...")
        input()

    except Exception as e:
        log(f"构建失败: {e}")
        import traceback
        traceback.print_exc()
        input("按任意键退出...")
