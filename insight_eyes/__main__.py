"""
Insight-Eye Web 应用入口点

启动 Web 后端服务 (FastAPI)
"""
from __future__ import absolute_import
import sys
import os

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import uvicorn


def main():
    """启动 Web 服务器"""
    # 动态导入以避免启动时的依赖问题
    from insight_eyes.web.api.main import app

    print("""
╔════════════════════════════════════════════════════════════╗
║          Insight-Eye Web - 移动设备性能监控               ║
║                    版本: 1.0.0-web                         ║
╠════════════════════════════════════════════════════════════╣
║  API 服务: http://localhost:8001                           ║
║  API 文档: http://localhost:8001/docs                      ║
╚════════════════════════════════════════════════════════════╝
    """)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info"
    )


if __name__ == '__main__':
    main()
