# 配置

配置由 `pydantic-settings` 读取，环境变量以 `NETEASE_` 开头，也可来自项目根目录 `.env`。
CLI 参数仅覆盖 transport、host、port 和 path。非法配置会使启动失败，不会静默修正。

| 变量 | 默认值 | 约束/用途 |
| --- | --- | --- |
| `NETEASE_MCP_TRANSPORT` | `stdio` | `stdio` / `streamable-http` |
| `NETEASE_MCP_HOST` | `127.0.0.1` | HTTP 监听地址 |
| `NETEASE_MCP_PORT` | `8766` | 1–65535 |
| `NETEASE_MCP_PATH` | `/mcp` | 必须以 `/` 开头 |
| `NETEASE_BACKEND` | `netease-web` | `netease-web` / `fake` |
| `NETEASE_COOKIE` | 空 | 完整 Cookie，敏感 |
| `NETEASE_MUSIC_U` / `NETEASE_CSRF` | 空 | 可选拆分 Cookie，敏感 |
| `NETEASE_USER_ID` | 空 | 当前登录用户字符串 ID |
| `NETEASE_CONNECT_TIMEOUT_SECONDS` | `5` | 正数 |
| `NETEASE_REQUEST_TIMEOUT_SECONDS` | `15` | 正数 |
| `NETEASE_MAX_CONNECTIONS` | `20` | 至少 1 |
| `NETEASE_MAX_KEEPALIVE_CONNECTIONS` | `10` | 至少 0 |
| `NETEASE_RETRY_ATTEMPTS` | `2` | 非负 |
| `NETEASE_RETRY_INITIAL_SECONDS` | `0.25` | 非负；指数退避基数 |
| `NETEASE_DEFAULT_PAGE_SIZE` | `20` | 1–max page size |
| `NETEASE_MAX_PAGE_SIZE` | `100` | 至少 1 |
| `NETEASE_MAX_BATCH_SONG_IDS` | `100` | 至少 1 |
| `NETEASE_DEFAULT_TOP_SONG_COUNT` | `10` | 1–max top songs |
| `NETEASE_MAX_TOP_SONG_COUNT` | `50` | 至少 1 |
| `NETEASE_DEFAULT_LYRICS_LIMIT` | `50` | 1–max lyrics limit |
| `NETEASE_MAX_LYRICS_LIMIT` | `200` | 至少 1 |
| `NETEASE_MAX_STATISTICS_TRACKS` | `1000` | 至少 1 |
| `NETEASE_CACHE_BACKEND` | `memory` | `none` / `memory` / `sqlite` |
| `NETEASE_CACHE_PATH` | `.cache/.../cache.sqlite3` | SQLite 路径 |
| `NETEASE_SEARCH_CACHE_TTL_SECONDS` | `300` | 0 表示不写该类缓存 |
| `NETEASE_DETAIL_CACHE_TTL_SECONDS` | `1800` | 非负 |
| `NETEASE_LYRICS_CACHE_TTL_SECONDS` | `3600` | 非负 |
| `NETEASE_LIBRARY_CACHE_TTL_SECONDS` | `60` | 非负 |
| `NETEASE_LOG_LEVEL` | `INFO` | Python 标准日志级别集合 |
