# netease-music-mcp

`netease-music-mcp` 是面向通用 MCP Client 的网易云音乐数据服务器。它以紧凑、分页、
结构化的方式提供歌曲、歌手、专辑、歌单、歌词和登录用户音乐库数据，可供 Claude Desktop、
Codex、IDE Agent、Yuki 等 MCP Client 使用。

当前开发版本：`1.0.0`。本项目是独立的社区项目，不是网易云音乐官方项目，也未获得网易公司的
认可或担保。所用 Web 接口不是公开稳定 API，可能随上游变更。

项目不调用任何 LLM，不下载、播放或转发音频，不提供付费音频链接，也不绕过会员、版权、
地区或 DRM 限制。写操作默认启用，可用 `NETEASE_WRITE_OPERATIONS_ENABLED=false` 关闭；每次
写调用仍必须显式传入 `confirm=true`，且不提供删除歌单接口。

## 安装

本地开发需要 Python 3.12 与 [uv](https://docs.astral.sh/uv/)：

```bash
git clone <repository-url> netease-music-mcp
cd netease-music-mcp
uv sync --all-extras
```

公开查询无需 Cookie。访问私人音乐库前，将 `.env.example` 复制为 `.env` 并配置
`NETEASE_COOKIE` 与 `NETEASE_USER_ID`。服务不会自动读取浏览器 Cookie。

Windows 与 macOS 部署建议直接使用 Docker Desktop；仅用 `.env` 启动容器时宿主机不需要 Python，
网易云 Cookie 通过项目目录的 `.env` 注入容器。Docker Compose 使用具名缓存卷，不依赖宿主机路径格式。
如果使用下方 `auth` 宿主机导入命令，则宿主机需要 Python 3.12 与 uv；Keychain/DPAPI 不能在
Linux 容器内部代替宿主机读取。

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

## 宿主机本地认证导入

Windows/macOS 桌面客户端登录态可由宿主机在运行前读取。导入器只读取网易云桌面客户端的
本地 MMKV Cookie 归档，并兼容 CEF Chromium Cookie 数据库；首次运行必须确认。读取加密的
CEF Cookie 时，macOS 使用 Keychain，Windows 使用 DPAPI。它不会扫描浏览器，不会打印 Cookie，
也不会把 Cookie 写入仓库或镜像。

仅查看脱敏结果：

```bash
uv run netease-music-mcp auth import-local
```

确认后直接以一次性环境变量启动 Docker（默认重新构建镜像）：

```bash
uv run netease-music-mcp auth run-docker --detach
```

`run-docker` 只把 Cookie 传给本次 `docker compose` 子进程；接口请求使用固定的 `appver=2.9.7`，
导入器不落盘。
使用 `--detach` 时，Cookie 会随运行中的本地容器存在；停止后执行 `docker compose down` 清理。
非交互环境必须显式使用 `--yes`，否则导入会拒绝执行。客户端未登录、存储不存在或系统密钥
访问失败时会返回明确错误，不会使用空 Cookie 继续启动。

## 十五个工具

| Tool | 用途 | 返回模型 |
| --- | --- | --- |
| `music_search` | 分页搜索歌曲、歌手、专辑或歌单 | `SearchPage` |
| `get_songs` | 按输入顺序批量读取歌曲元数据 | `GetSongsResult` |
| `get_recommendations` | 读取只读推荐歌单 | `RecommendationPage` |
| `get_similar_songs` | 读取相似歌曲 | `SimilarSongsPage` |
| `get_new_songs` | 按地区读取推荐新歌 | `NewSongsPage` |
| `get_rankings` | 读取排行榜摘要和 Top 曲目 | `RankingPage` |
| `get_album` | 读取专辑与可选的单页曲目 | `AlbumDetail` |
| `get_artist` | 读取歌手与可选的限量热门歌曲 | `ArtistDetail` |
| `get_playlist` | 读取歌单与可选的单页曲目 | `PlaylistDetail` |
| `get_lyrics` | 分页读取原文、翻译和罗马音歌词 | `LyricsDocument` |
| `get_user_library` | 读取已登录用户的音乐库分区 | `UserLibraryPage` |
| `get_playlist_statistics` | 计算确定性的歌单统计 | `PlaylistStatistics` |
| `create_playlist` | 创建歌单（需确认） | `WriteResult` |
| `update_playlist_tracks` | 增删歌单曲目（需确认） | `WriteResult` |
| `set_song_like` | 点赞或取消点赞（需确认） | `WriteResult` |

搜索结果只保留概要；歌曲详情使用批量工具读取。专辑和歌单默认不包含曲目，歌词默认只返回
一页。MCP 响应使用 `structuredContent`，兼容文本内容仅为一句短摘要。

完整参数见 [docs/tools.md](docs/tools.md)，模型见 [docs/data-models.md](docs/data-models.md)。

## 四类资源

| URI 模板 | 内容 |
| --- | --- |
| `netease://song/{id}` | 单曲完整元数据 |
| `netease://album/{id}` | 专辑元数据，不展开曲目 |
| `netease://artist/{id}` | 歌手元数据，不展开热门歌曲 |
| `netease://playlist/{id}` | 歌单元数据，不展开曲目 |

资源以 `application/json` 返回，并复用工具的验证、缓存和错误处理路径。需要曲目列表或热门
歌曲时，继续使用相应工具的显式分页/数量参数。

## 认证与数据边界

无需登录：搜索、歌曲、歌手、专辑、公开歌单、歌词、推荐、新歌速递和排行榜（以上游允许为准）。

需要 Cookie：用户歌单、收藏歌手、收藏专辑、每日推荐、播放记录和喜欢的歌曲。`user_id` 未传时使用
`NETEASE_USER_ID`；无登录态会返回 `authentication_required`，不会返回空列表伪装成功。

可直接配置完整 `NETEASE_COOKIE`，或使用 `NETEASE_MUSIC_U` 与 `NETEASE_CSRF` 由认证组件
统一组装。Cookie 不进入日志、异常、MCP 输出或缓存。详见
[docs/authentication.md](docs/authentication.md)。

写工具仅对已认证账号开放。真实测试建议先读取歌单和喜欢状态，选择原本未存在的歌曲执行
“添加后删除”或“点赞后取消点赞”，并在每一步核对恢复结果。

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
docker build -t netease-music-mcp:1.0.0 .
docker compose up --build
```

Windows PowerShell 使用同样的 Docker 命令；Cookie 可用以下命令准备：

```powershell
Copy-Item .env.example .env
docker compose up --build
```

macOS、Windows 和 Linux 的 Compose 行为保持一致：从本地 `.env` 读取配置，将 SQLite 缓存放入
具名卷，并暴露可配置端口。容器以非 root 用户运行，健康检查只检查 TCP 监听，不调用真实搜索接口。

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

服务器读取并规范化元数据和歌词，也可按显式确认执行歌单和点赞写操作。数据、封面与歌词的权利属于各自权利人；使用者应遵守
网易云音乐服务条款、适用法律及地区限制。本项目不缓存认证响应、Header 或原始上游 JSON。

更多信息：

- [架构](docs/architecture.md)
- [配置](docs/configuration.md)
- [传输](docs/transports.md)
- [Token 效率](docs/token-efficiency.md)
- [路线图](docs/roadmap.md)
- [0.1.0 完成报告](docs/release-report.md)
