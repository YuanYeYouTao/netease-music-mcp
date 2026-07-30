# netease-music-mcp

`netease-music-mcp` 是面向通用 MCP Client 的只读网易云音乐数据服务器。它以紧凑、分页、
结构化的方式提供歌曲、歌手、专辑、歌单、歌词和登录用户音乐库数据，可供 Claude Desktop、
Codex、IDE Agent、Yuki 等 MCP Client 使用。

当前版本：`0.1.0`。本项目是独立的社区项目，不是网易云音乐官方项目，也未获得网易公司的
认可或担保。所用 Web 接口不是公开稳定 API，可能随上游变更。

项目不调用任何 LLM，不下载、播放或转发音频，不提供付费音频链接，也不绕过会员、版权、
地区或 DRM 限制。0.1.0 中没有写操作、MCP Resources、Prompts、Sampling 或 Elicitation。

## 安装

需要 Python 3.12 与 [uv](https://docs.astral.sh/uv/)：

```bash
git clone <repository-url> netease-music-mcp
cd netease-music-mcp
uv sync --all-extras
```

公开查询无需 Cookie。访问私人音乐库前，将 `.env.example` 复制为 `.env` 并配置
`NETEASE_COOKIE` 与 `NETEASE_USER_ID`。服务不会自动读取浏览器 Cookie。

## 启动

stdio：

```bash
uv run netease-music-mcp serve --transport stdio
```

Streamable HTTP（默认路径 `/mcp`）：

```bash
uv run netease-music-mcp serve \
  --transport streamable-http \
  --host 127.0.0.1 \
  --port 8766
```

辅助命令：

```bash
uv run netease-music-mcp config
uv run netease-music-mcp doctor
uv run netease-music-mcp cache stats
uv run netease-music-mcp cache clear
```

`config` 仅显示非敏感值、配置来源和 Cookie 是否已配置，不会显示 Cookie 内容。
`doctor` 检查配置、缓存可写性、公开查询和（已配置时）登录状态。

## 八个工具

| Tool | 用途 | 返回模型 |
| --- | --- | --- |
| `music_search` | 分页搜索歌曲、歌手、专辑或歌单 | `SearchPage` |
| `get_songs` | 按输入顺序批量读取歌曲元数据 | `GetSongsResult` |
| `get_album` | 读取专辑与可选的单页曲目 | `AlbumDetail` |
| `get_artist` | 读取歌手与可选的限量热门歌曲 | `ArtistDetail` |
| `get_playlist` | 读取歌单与可选的单页曲目 | `PlaylistDetail` |
| `get_lyrics` | 分页读取原文、翻译和罗马音歌词 | `LyricsDocument` |
| `get_user_library` | 读取已登录用户的音乐库分区 | `UserLibraryPage` |
| `get_playlist_statistics` | 计算确定性的歌单统计 | `PlaylistStatistics` |

搜索结果只保留概要；歌曲详情使用批量工具读取。专辑和歌单默认不包含曲目，歌词默认只返回
一页。MCP 响应使用 `structuredContent`，兼容文本内容仅为一句短摘要。

完整参数见 [docs/tools.md](docs/tools.md)，模型见 [docs/data-models.md](docs/data-models.md)。

## 认证与数据边界

无需登录：搜索、歌曲、歌手、专辑、公开歌单和歌词（以上游允许为准）。

需要 Cookie：用户歌单、收藏歌手、收藏专辑、每日推荐和播放记录。`user_id` 未传时使用
`NETEASE_USER_ID`；无登录态会返回 `authentication_required`，不会返回空列表伪装成功。

可直接配置完整 `NETEASE_COOKIE`，或使用 `NETEASE_MUSIC_U` 与 `NETEASE_CSRF` 由认证组件
统一组装。Cookie 不进入日志、异常、MCP 输出或缓存。详见
[docs/authentication.md](docs/authentication.md)。

## Yuki 接入

stdio `.mcp.json` 示例：

```json
{
  "mcpServers": {
    "netease_music": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/netease-music-mcp",
        "run",
        "netease-music-mcp",
        "serve",
        "--transport",
        "stdio"
      ],
      "env": { "NETEASE_COOKIE": "${NETEASE_COOKIE}" },
      "lifecycle": "lazy",
      "yuki": {
        "scope": "mcp.netease_music",
        "summary": "歌曲、歌手、专辑、歌单、歌词和音乐库查询",
        "tags": ["音乐", "网易云", "歌曲", "歌手", "专辑", "歌单", "歌词"]
      }
    }
  }
}
```

HTTP 示例：

```json
{
  "mcpServers": {
    "netease_music": {
      "url": "http://127.0.0.1:8766/mcp",
      "lifecycle": "lazy",
      "yuki": {
        "scope": "mcp.netease_music",
        "summary": "网易云音乐数据查询"
      }
    }
  }
}
```

`yuki` 仅是 Client 读取的文档字段，本项目不依赖 Yuki。

## Docker

```bash
docker build -t netease-music-mcp:0.1.0 .
docker compose up --build
```

Compose 从本地 `.env` 读取配置，将 SQLite 缓存放入具名卷，并暴露可配置端口。容器以
非 root 用户运行，健康检查只检查 TCP 监听，不调用真实搜索接口。

## 故障排查

- 启动即配置错误：运行 `uv run netease-music-mcp config`，检查分页默认值是否超过最大值、
  路径是否以 `/` 开头、端口是否有效。
- 私人数据返回 `authentication_required`：配置 Cookie 和 `NETEASE_USER_ID`，再运行
  `doctor`。Cookie 过期会返回 `authentication_expired`。
- `rate_limited`：等待后重试；服务器只按配置进行有限指数退避。
- `upstream_unavailable`：检查网络与网易云状态。
- `upstream_response_error`：通常表示非公开 Web 接口的响应结构已变，需要更新 Backend 或
  Normalizer。
- HTTP Client 无法连接：确认 URL 为 `http://host:port/mcp`，且容器/防火墙端口一致。

## 数据与版权

服务器只读取并规范化元数据和歌词。数据、封面与歌词的权利属于各自权利人；使用者应遵守
网易云音乐服务条款、适用法律及地区限制。本项目不缓存认证响应、Header 或原始上游 JSON。

更多信息：

- [架构](docs/architecture.md)
- [配置](docs/configuration.md)
- [传输](docs/transports.md)
- [Token 效率](docs/token-efficiency.md)
- [路线图](docs/roadmap.md)
- [0.1.0 完成报告](docs/release-report.md)
