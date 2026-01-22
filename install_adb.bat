@echo off
setlocal enabledelayedexpansion

REM ========================================
REM Insight-Eye ADB 自动安装脚本
REM ========================================

echo.
echo ========================================
echo   Insight-Eye ADB 自动安装程序
echo ========================================
echo.

set "ADB_DIR=%USERPROFILE%\platform-tools"
set "ADB_URL=https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
set "TEMP_ZIP=%TEMP%\platform-tools.zip"

REM 检查是否已安装
if exist "%ADB_DIR%\adb.exe" (
    echo [√] ADB 已安装: %ADB_DIR%
    echo.
    set /p reinstall="是否重新安装? (Y/N): "
    if /i not "!reinstall!"=="Y" (
        echo 安装已取消
        goto :end
    )
    echo 正在卸载旧版本...
    rmdir /s /q "%ADB_DIR%" 2>nul
)

echo [1/3] 下载 Platform Tools...
echo.

REM 创建下载目录
if not exist "%TEMP%" mkdir "%TEMP%"

REM 使用 PowerShell 下载
powershell -Command "& {Invoke-WebRequest -Uri '%ADB_URL%' -OutFile '%TEMP_ZIP%'}"

if not exist "%TEMP_ZIP%" (
    echo [×] 下载失败，请检查网络连接
    echo.
    echo 手动下载地址: %ADB_URL%
    goto :end
)

echo [√] 下载完成
echo.

echo [2/3] 解压文件...
echo.

REM 解压到用户目录
powershell -Command "& {Expand-Archive -Force '%TEMP_ZIP%' '%USERPROFILE%'}"

if not exist "%ADB_DIR%\adb.exe" (
    echo [×] 解压失败
    goto :end
)

echo [√] 解压完成
echo.

echo [3/3] 添加到系统 PATH...
echo.

REM 检查是否已在 PATH 中
reg query "HKCU\Environment" /v Path | findstr /i "%ADB_DIR%" >nul
if %errorlevel% equ 0 (
    echo [√] PATH 已包含 ADB 目录
) else (
    REM 添加到用户 PATH
    for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "CURRENT_PATH=%%b"
    if not defined CURRENT_PATH (
        reg add "HKCU\Environment" /v Path /t REG_EXPAND_SZ /d "%ADB_DIR%" /f >nul
    ) else (
        reg add "HKCU\Environment" /v Path /t REG_EXPAND_SZ /d "%CURRENT_PATH%;%ADB_DIR%" /f >nul
    )
    echo [√] 已添加到 PATH
)

REM 清理临时文件
del "%TEMP_ZIP%" 2>nul

echo.
echo ========================================
echo   安装完成！
echo ========================================
echo.
echo ADB 路径: %ADB_DIR%
echo.
echo 重要提示:
echo 1. 请重启命令行窗口使 PATH 生效
echo 2. 或运行: %ADB_DIR%\adb.exe version
echo 3. 连接 Android 设备并启用 USB 调试
echo.

:end
pause
