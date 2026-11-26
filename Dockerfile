FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    APP_DB_PATH=/app/data/app.db

RUN pip install --no-cache-dir uv==0.13.10

WORKDIR /app

# 先只拷依赖清单，让依赖层能被 Docker 缓存；按锁文件安装，保证可复现。
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app ./app

# 补装项目本身（此时才有 app 目录可打包）。
RUN uv sync --frozen --no-dev

RUN mkdir -p /app/data

EXPOSE 8000

# 服务必须监听 0.0.0.0，否则容器外访问不到。
CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
