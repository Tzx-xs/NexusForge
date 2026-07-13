FROM python:3.12-slim AS builder
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS runtime
# L-05 修复：Dockerfile 安全基线强化。
# 1) 创建非 root 用户并以该用户运行（最小权限原则）
# 2) 添加 HEALTHCHECK 健康检查
# 3) uvicorn 添加 --workers 参数提升并发能力
# 4) 仍绑定 0.0.0.0（容器内默认行为，外部由反向代理管控）
WORKDIR /app
RUN useradd -r -u 1000 -m -d /home/appuser appuser && mkdir -p /data && chown appuser:appuser /data
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --chown=appuser:appuser backend/ ./backend/
COPY --chown=appuser:appuser frontend/dist/ ./frontend/dist/
USER appuser
EXPOSE 8000
ENV PYTHONPATH=/app/backend
ENV DATA_DIR=/data
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"
CMD ["python", "-m", "uvicorn", "interfaces.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
