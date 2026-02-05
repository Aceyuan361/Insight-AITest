"""
Insight-Eye Web 应用入口点

启动 Web 后端服务 (FastAPI) 和前端开发服务器，并自动打开浏览器
"""
from __future__ import absolute_import
import sys
import os
import webbrowser
import threading
import time
import subprocess
from pathlib import Path

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import uvicorn


def start_frontend():
    """启动前端开发服务器"""
    frontend_dir = Path(__file__).parent / 'web-frontend'

    try:
        # 检查 node_modules 是否存在
        node_modules = frontend_dir / 'node_modules'
        if not node_modules.exists():
            print("Frontend dependencies not found. Installing...")
            subprocess.run(
                ['npm', 'install'],
                cwd=frontend_dir,
                shell=True,
                check=True
            )

        # 启动前端开发服务器
        print("Starting frontend server...")
        subprocess.run(
            ['npm', 'run', 'dev'],
            cwd=frontend_dir,
            shell=True
        )
    except Exception as e:
        print(f"Failed to start frontend: {e}")
        print("Please start frontend manually:")
        print(f"  cd {frontend_dir}")
        print("  npm install  # if not installed")
        print("  npm run dev")


def open_browser():
    """延迟打开浏览器到前端页面"""
    time.sleep(5)  # 等待前端和后端都启动
    try:
        # 尝试打开端口 80，如果失败则尝试 81、82
        for port in [80, 81, 82]:
            try:
                webbrowser.open(f"http://localhost:{port}")
                print(f"OK Browser opened to http://localhost:{port}")
                break
            except:
                continue
    except Exception as e:
        print(f"WARNING Failed to open browser: {e}")


def main():
    """启动完整的 Web 应用（后端 + 前端）"""

    # 在后台线程中启动前端
    frontend_thread = threading.Thread(target=start_frontend, daemon=True)
    frontend_thread.start()

    # 在后台线程中打开浏览器
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()

    # 动态导入以避免启动时的依赖问题
    from insight_eyes.web.api.main import app

    print("""
╔════════════════════════════════════════════════════════════╗
║          Insight-Eye Web - 移动设备性能监控               ║
║                    版本: 1.0.0-web                         ║
║               作者 / Author: Aceyuan361                    ║
╠════════════════════════════════════════════════════════════╣
║  后端 API / Backend: http://localhost:8001                 ║
║  API 文档 / API Docs: http://localhost:8001/docs           ║
║  前端界面 / Frontend: http://localhost:80                   ║
╠════════════════════════════════════════════════════════════╣
║  浏览器将自动打开 / Browser will open automatically        ║
║  按 Ctrl+C 停止服务 / Press Ctrl+C to stop                 ║
╚════════════════════════════════════════════════════════════╝
    """)

    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8001,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n\nStopping Insight-Eye Web...")
        sys.exit(0)


if __name__ == '__main__':
    main()
