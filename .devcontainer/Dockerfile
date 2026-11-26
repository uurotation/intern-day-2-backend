FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

# 该基础镜像已自带 git 2.50 / curl 7.88 / Python 3.12 / pip，无需再用 apt 安装。
# 但镜像预置的 yarn apt 源签名已失效（apt 会报 NO_PUBKEY 并整体失败），一并移除，
# 避免以后在容器里执行 apt-get update 时被它拖垮。
RUN rm -f /etc/apt/sources.list.d/yarn.list /etc/apt/sources.list.d/yarn.sources

# 开发容器统一用 uv 管依赖，版本与宿主机保持一致。
RUN pip install --no-cache-dir uv==0.13.10
