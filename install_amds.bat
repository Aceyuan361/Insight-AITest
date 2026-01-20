@echo off
REM 安装 Apple Mobile Device Support
REM 从 iTunes 安装包中提取

echo ========================================
echo Apple Mobile Device Support 安装工具
echo ========================================
echo.
echo 正在下载 iTunes（仅提取驱动组件）...
echo.

REM 创建临时目录
set TEMP_DIR=%TEMP%\iTunes_Installer
if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

REM 下载 iTunes（包含 AMD Support）
echo [1/3] 下载 iTunes 安装包...
powershell -Command "& {Invoke-WebRequest -Uri 'https://www.apple.com/itunes/download/win64' -OutFile '%TEMP_DIR%\iTunes64Setup.exe'}" 2>nul

if not exist "%TEMP_DIR%\iTunes64Setup.exe" (
    echo [错误] 下载失败，请检查网络连接
    pause
    exit /b 1
)

echo [2/3] 解压安装包...
REM 使用 7-Zip 或 Windows 内置解压
powershell -Command "& {Expand-Archive -Path '%TEMP_DIR%\iTunes64Setup.exe' -DestinationPath '%TEMP_DIR%\iTunes_Extract' -Force}" 2>nul

if not exist "%TEMP_DIR%\iTunes_Extract\AppleMobileDeviceSupport64.msi" (
    echo [备用] 尝试直接运行安装程序...
    start /wait "%TEMP_DIR%\iTunes64Setup.exe" /extract:"%TEMP_DIR%\iTunes_Extract"
)

echo [3/3] 安装 Apple Mobile Device Support...
if exist "%TEMP_DIR%\iTunes_Extract\AppleMobileDeviceSupport64.msi" (
    msiexec /i "%TEMP_DIR%\iTunes_Extract\AppleMobileDeviceSupport64.msi" /qb
    echo.
    echo ========================================
    echo 安装完成！
    echo ========================================
    echo 请重新连接 iOS 设备并运行: tidevice list
    echo.
) else (
    echo.
    echo ========================================
    echo 自动安装失败，请手动操作
    echo ========================================
    echo.
    echo 方法1: 访问以下链接下载 iTunes
    echo https://www.apple.com/itunes/download/win64
    echo.
    echo 方法2: 或仅安装驱动组件
    echo https://support.apple.com/kb/DL8371
    echo.
)

REM 清理临时文件
rd /s /q "%TEMP_DIR%" 2>nul

pause
