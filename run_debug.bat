@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   Insight-Eye Debug 模式启动
echo ========================================
echo.
echo 正在启动应用（启用详细调试日志）...
echo.

python -m insight_eyes.desktop.main --debug

if errorlevel 1 (
    echo.
    echo ========================================
    echo 启动失败！错误代码: %errorlevel%
    echo ========================================
    echo.
    pause
)
