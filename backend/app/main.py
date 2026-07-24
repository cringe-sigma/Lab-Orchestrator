"""Lab Orchestrator — FastAPI 入口"""
from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.database import init_db
from app.api import auth, boards, experiments, bookings, ws_boards


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭生命周期"""
    await init_db()
    print(f"[{settings.APP_NAME}] 数据库初始化完成")
    print(f"[{settings.APP_NAME}] AI Agent: {'已配置' if settings.ANTHROPIC_API_KEY else '未配置(请在.env中设置ANTHROPIC_API_KEY)'}")
    yield
    # 关闭时的清理
    from app.services.board_manager import board_manager
    await board_manager.disconnect_all()
    print(f"[{settings.APP_NAME}] 已关闭")


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — 允许前端 dev server 跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router)
app.include_router(boards.router)
app.include_router(experiments.router)
app.include_router(bookings.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}
