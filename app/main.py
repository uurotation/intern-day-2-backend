"""FastAPI 入口。

启动命令：uvicorn app.main:app --host 0.0.0.0 --port 8000
接口文档：http://localhost:8000/docs
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .db import init_db
from .routers import auth, todos
from .schemas import HealthOut


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=config.APP_NAME,
    version=config.APP_VERSION,
    description="第二天练习项目的后端：登录鉴权 + 四象限备忘录。",
    lifespan=lifespan,
)

# 联调方式是浏览器直连宿主机映射的后端端口，
# 所以这里必须放行前端开发服务器的来源，并处理预检请求。
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health", response_model=HealthOut, tags=["system"], summary="健康检查")
def health() -> HealthOut:
    return HealthOut(status="ok", version=config.APP_VERSION)


app.include_router(auth.router)
app.include_router(todos.router)
