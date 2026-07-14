@echo off
REM ============================================================
REM  Insight-AITest 一键启动脚本（Windows）
REM  双击运行即可。首次运行自动安装 Python 依赖，之后快速启动。
REM ============================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

title Insight-AITest 启动器

echo.
echo ============================================================
echo   Insight-AITest 一键启动
echo ============================================================
echo.

REM ---------- 1. 检测 Python ----------
set "PY_CMD="
py --version >nul 2>&1 && set "PY_CMD=py"
if not defined PY_CMD (
    python --version >nul 2>&1 && set "PY_CMD=python"
)
if not defined PY_CMD (
    echo [错误] 未检测到 Python。
    echo.
    echo 请安装 Python 3.10+ 并将其加入系统 PATH：
    echo   https://www.python.org/downloads/
    echo.
    echo 安装完成后重新双击本脚本。
    echo.
    pause
    exit /b 1
)
for /f "delims=" %%v in ('%PY_CMD% --version') do set "PY_VER=%%v"
echo [1/4] Python 检测通过：!PY_VER! （命令：%PY_CMD%）

REM ---------- 2. 检测 Node.js ----------
set "NODE_OK=0"
where npm >nul 2>&1 && set "NODE_OK=1"
where node >nul 2>&1 || set "NODE_OK=0"
if "!NODE_OK!"=="1" (
    for /f "delims=" %%v in ('node --version') do set "NODE_VER=%%v"
    echo [2/4] Node.js 检测通过：!NODE_VER!
) else (
    echo [2/4] [警告] 未检测到 Node.js / npm。
    echo        前端界面需要 Node.js 16+（推荐 20 或 22）。
    echo        下载：https://nodejs.org/
    echo        安装后重新运行本脚本。
    echo.
    choice /c YN /m "Node.js 未安装，仍要继续吗（前端将无法启动）[Y/N]"
    if errorlevel 2 (
        echo 已取消。
        pause
        exit /b 1
    )
)

REM ---------- 3. 首次运行安装 Python 依赖 ----------
if exist ".insight_initialized" (
    echo [3/4] 已完成初始化，跳过依赖安装（快速启动）。
) else (
    echo [3/4] 首次运行，开始安装 Python 依赖（仅需一次）...
    echo.
    call %PY_CMD% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [错误] 依赖安装失败。请检查网络或手动执行：
        echo   pip install -r requirements.txt
        pause
        exit /b 1
    )
    echo.
    echo        Python 依赖安装完成。
    echo        提示：如需使用「UI 自动化」模块，请额外执行：
    echo          %PY_CMD% -m playwright install chromium
    echo.
    REM 标记初始化完成（记录 Python 命令，便于后续一致）
    >".insight_initialized" echo installed=%PY_CMD%
)

REM ---------- 4. 启动平台 ----------
echo [4/4] 启动 Insight-AITest ...
echo.
echo        前端界面：    http://localhost:80
echo        后端 API：    http://localhost:8001
echo        API 文档：    http://localhost:8001/docs
echo        浏览器将自动打开。
echo        按 Ctrl+C 可停止服务。
echo ============================================================
echo.

%PY_CMD% -m insight_aitest

if errorlevel 1 (
    echo.
    echo [启动失败] 请查看上方错误信息。
    pause
)

endlocal
