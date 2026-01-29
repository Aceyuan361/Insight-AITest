# -*- coding: utf-8 -*-
"""
FastAPI Web 应用主入口
提供 Insight-Eye 的 Web API 服务
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from logzero import logger
import sys
import os

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# TODO: 将在后续路由中使用
# from insight_eyes.core.device_manager import DeviceManager
# from insight_eyes.core.database import DatabaseManager

# 版本管理
__version__ = "1.0.3"

# 从环境变量读取允许的来源
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000"
).split(",")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("FastAPI 应用启动")
    yield
    logger.info("FastAPI 应用关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title="Insight-Eye API",
    description="移动设备性能监控工具 Web API",
    version=__version__,
    lifespan=lifespan,
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """根路径，返回 API 信息"""
    return {
        "name": "Insight-Eye API",
        "version": app.version,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
