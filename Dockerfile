FROM python:3.12-slim AS runtime

RUN pip install --no-cache-dir uv==0.11.32

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    NETEASE_MCP_TRANSPORT=streamable-http \
    NETEASE_MCP_HOST=0.0.0.0 \
    NETEASE_MCP_PORT=8766 \
    NETEASE_CACHE_BACKEND=sqlite \
    NETEASE_CACHE_PATH=/data/cache.sqlite3

WORKDIR /app

COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

RUN useradd --uid 10001 --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin app \
    && mkdir -p /data \
    && chown app:app /data

USER app
VOLUME ["/data"]
EXPOSE 8766

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD ["/app/.venv/bin/python", "-c", "import socket; s=socket.create_connection(('127.0.0.1',8766),2); s.close()"]

CMD ["/app/.venv/bin/netease-music-mcp", "serve", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8766"]
