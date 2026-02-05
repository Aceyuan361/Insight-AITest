"""
Insight-Eye Web 应用入口点

启动 Web 后端服务 (FastAPI) 并自动打开浏览器
"""
from __future__ import absolute_import
import sys
import os
import webbrowser
import threading
import time

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import uvicorn


def open_browser():
    """延迟打开浏览器，等待服务器启动"""
    time.sleep(2)  # 等待服务器启动
    try:
        # 打开 API 文档页面
        webbrowser.open("http://localhost:8001/docs")
        print("OK Browser opened to API docs")
    except Exception as e:
        print(f"WARNING Failed to open browser: {e}")
        print("  Please visit: http://localhost:8001/docs")


def main():
    """启动 Web 服务器并自动打开浏览器"""
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
║  API 服务 / API: http://localhost:8001                     ║
║  API 文档 / Docs: http://localhost:8001/docs               ║
╠════════════════════════════════════════════════════════════╣
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
        print("\n\n👋 Insight-Eye Web 已停止 / Stopped")
        sys.exit(0)


if __name__ == '__main__':
    main()
