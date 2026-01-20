@echo off
REM Insight-Eye Desktop Application Launcher
REM 移动设备性能监控桌面应用启动脚本

echo ========================================
echo    Insight-Eye Desktop Application
echo    移动设备性能监控工具
echo ========================================
echo.

REM 切换到项目目录
cd /d "%~dp0"

echo [1/3] 检查 Python 环境...
python --version
if errorlevel 1 (
    echo 错误: 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

echo.
echo [2/3] 检查 PyQt6 依赖...
python -c "import PyQt6; print('PyQt6 已安装')" 2>nul
if errorlevel 1 (
    echo 警告: PyQt6 未安装，正在尝试安装...
    pip install PyQt6 pyqtgraph numpy logzero
)

echo.
echo [3/3] 启动 Insight-Eye 应用...
echo.
python insight_eyes\desktop\main.py

if errorlevel 1 (
    echo.
    echo 启动失败！请检查错误信息。
    pause
)
