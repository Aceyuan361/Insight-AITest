"""
Insight-AITest 应用入口点

启动 Web 后端服务 (FastAPI) 和前端开发服务器，并自动打开浏览器
"""

from __future__ import absolute_import
import sys
import os
import webbrowser
import threading
import time
import subprocess
import socket
import platform
from pathlib import Path

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import uvicorn  # noqa: E402

# 前端端口配置（与 vite.config.ts 中的端口配置保持一致）
FRONTEND_PORTS = [80, 81, 82]

# Windows 平台需要 shell=True 来运行 npm 命令
USE_SHELL = platform.system() == "Windows"


def get_local_ip():
    """获取本机局域网 IP 地址"""
    try:
        # 创建一个 UDP socket 连接到外部地址
        # 这不会实际发送数据，只是用来获取本机 IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 连接到一个外部地址（Google 的 DNS）
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        # 如果获取失败，返回 localhost
        return "localhost"


def start_frontend():
    """启动前端开发服务器"""
    frontend_dir = Path(__file__).parent / "shell-frontend"

    try:
        # 检查 node_modules 是否存在
        node_modules = frontend_dir / "node_modules"
        if not node_modules.exists():
            print("Frontend dependencies not found. Installing...")
            subprocess.run(["npm", "install"], cwd=frontend_dir, shell=USE_SHELL, check=True)

        # 启动前端开发服务器
        print("Starting frontend server...")
        subprocess.run(["npm", "run", "dev"], cwd=frontend_dir, shell=USE_SHELL)
    except Exception as e:
        print(f"Failed to start frontend: {e}")
        print("Please start frontend manually:")
        print(f"  cd {frontend_dir}")
        print("  npm install  # if not installed")
        print("  npm run dev")


def open_browser(local_ip):
    """延迟打开浏览器到前端页面"""
    time.sleep(5)  # 等待前端和后端都启动
    try:
        # 尝试打开端口 80，如果失败则尝试 81、82
        for port in FRONTEND_PORTS:
            try:
                url = f"http://{local_ip}:{port}"
                webbrowser.open(url)
                print(f"OK Browser opened to {url}")
                break
            except Exception:
                continue
    except Exception as e:
        print(f"WARNING Failed to open browser: {e}")


def main():
    """启动完整的 Web 应用（后端 + 前端）"""

    # 获取本机 IP 地址
    local_ip = get_local_ip()

    # 在后台线程中启动前端
    frontend_thread = threading.Thread(target=start_frontend, daemon=True)
    frontend_thread.start()

    # 在后台线程中打开浏览器
    browser_thread = threading.Thread(target=open_browser, args=(local_ip,), daemon=True)
    browser_thread.start()

    # 动态导入平台内核装配的应用
    from insight_aitest.platform.kernel import build_app

    app = build_app()

    banner = f"""
╔════════════════════════════════════════════════════════════╗
║          Insight-AITest - AI 测试与监控平台                ║
║                    版本: 2.0.0                             ║
║               作者 / Author: Aceyuan361                    ║
╠════════════════════════════════════════════════════════════╣
║  后端 API / Backend:                                       ║
║    - 本机 / Local:  http://localhost:8001                  ║
║    - 网络 / Network: http://{local_ip}:8001                ║
║                                                            ║
║  API 文档 / API Docs:                                      ║
║    - 本机 / Local:  http://localhost:8001/docs             ║
║    - 网络 / Network: http://{local_ip}:8001/docs           ║
║                                                            ║
║  前端界面 / Frontend:                                      ║
║    - 本机 / Local:  http://localhost:80                    ║
║    - 网络 / Network: http://{local_ip}:80                  ║
╠════════════════════════════════════════════════════════════╣
║  浏览器将自动打开 / Browser will open automatically        ║
║  其他设备可使用网络地址访问 /                              ║
║  Other devices can use network URL to access              ║
║  按 Ctrl+C 停止服务 / Press Ctrl+C to stop                 ║
╚════════════════════════════════════════════════════════════╝
    """
    print(banner)

    try:
        uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
    except KeyboardInterrupt:
        print("\n\nStopping Insight-AITest...")
        sys.exit(0)


if __name__ == "__main__":
    main()
