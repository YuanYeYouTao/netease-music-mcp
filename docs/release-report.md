# 0.1.0 完成报告

## 提交与文件

- 起始提交：`3ae423b501dd8c909c61710c676ce4ea5390af76`。
- 最终提交：在交付完成后由 Git 记录，见仓库最新提交。
- 新建 72 个受项目管理的文件（含隐藏配置与 lockfile），覆盖项目元数据、源码、测试、文档与容器配置。

```text
netease-music-mcp/
├── pyproject.toml / uv.lock / README.md / CHANGELOG.md / LICENSE
├── .env.example / Dockerfile / compose.yaml
├── src/netease_music_mcp/
│   ├── config.py / application.py / lifespan.py / mcp_adapter.py / server.py / cli.py
│   ├── domain/       # enums, identifiers, pagination, models, errors
│   ├── clients/      # authentication, shared async HTTP, provider responses
│   ├── backends/     # protocol, fake, NetEase web, normalizer
│   ├── services/     # catalog, library, lyrics, deterministic statistics
│   ├── cache/        # protocol, memory/null, SQLite
│   └── tools/        # exactly eight MCP tool registrations
├── tests/
│   ├── unit/
│   ├── contract/
│   └── integration/
└── docs/
    ├── architecture.md / configuration.md / tools.md / data-models.md
    ├── transports.md / authentication.md / token-efficiency.md
    ├── yuki-integration.md / upstream-apis.md / roadmap.md
    └── release-report.md
```

## MCP Tool 输入输出

| Tool | 输入 | 输出 |
| --- | --- | --- |
| `music_search` | query/category/page/page_size/detail_level | `SearchPage` |
| `get_songs` | song_ids/detail_level | `GetSongsResult` |
| `get_album` | album_id/include_tracks/track_page/track_page_size | `AlbumDetail` |
| `get_artist` | artist_id/include_top_songs/top_song_count | `ArtistDetail` |
| `get_playlist` | playlist_id/include_tracks/track_page/track_page_size | `PlaylistDetail` |
| `get_lyrics` | song_id/translation/romanization/offset/limit | `LyricsDocument` |
| `get_user_library` | section/user_id/page/page_size/history_scope | `UserLibraryPage` |
| `get_playlist_statistics` | playlist_id/track_limit | `PlaylistStatistics` |

领域模型包括 Artist/Album/Song/Playlist 的 Summary 与 Detail、LyricsLine/Document、
SearchPage、GetSongsResult、UserLibraryPage、PlaylistStatistics、CountEntry、YearCount、
PageRequest/PageInfo、ErrorPayload 及相关枚举。所有公共 ID 是字符串。

## Backend 与规范化

`MusicCatalogBackend` 定义 search、批量 songs、album、artist、playlist、lyrics、user library 和
close。生产实现是 `NeteaseWebBackend`，离线测试实现是 `FakeMusicCatalogBackend`。

响应规范化集中处理 `ar/artists`、`al/album`、数字 ID、Unix 毫秒到 ISO 日期、`dt/duration`
到 duration_ms、缺失图片、别名、空描述、权限可用性、LRC 翻译/罗马音对齐、统一分页与缺失
歌曲 ID。未知 Provider 字段被忽略，不进入领域 metadata。

## Cookie、缓存与分页

Cookie 仅由 `AuthenticationProvider` 从完整或拆分环境变量组装。公开工具不要求 Cookie；私人
音乐库必须有认证并按用户 ID 隔离。SecretStr、定制 repr、红acted CLI 与缓存键设计共同确保
Cookie 不进入日志、异常、输出或 SQLite。

缓存只保存规范化领域 JSON。Memory 与 SQLite 实现共享 Protocol；稳定 SHA-256 键包含
Backend、操作、规范化参数、认证作用域、模型版本和非敏感配置指纹。搜索、详情、歌词、私人
资料 TTL 分离且均来自 Settings，可用 `none` 关闭。

除歌词按明确规格使用 offset/limit 外，列表统一使用一基 page/page_size 和 PageInfo。默认
page size 与最大值只由 Settings 控制；超界明确报错，不 clamp。Backend 负责转成上游 offset。

## 启动与接入

```bash
uv run netease-music-mcp serve --transport stdio
uv run netease-music-mcp serve --transport streamable-http --host 127.0.0.1 --port 8766
```

Yuki `.mcp.json` 的 stdio 与 HTTP 示例见 README；`yuki` 字段只供 Client 使用。

## Token 指标

指标由 Fake Backend 与正式 Schema 生成，字符序列化使用紧凑 JSON：

- 八个 Tool 合计 Schema：28,077 字符。
- description：55–81 字符/Tool。
- 典型 search page：963 字符；兼容文本 42 字符。
- 典型 full song detail：578 字符；兼容文本 46 字符。
- 典型 playlist page：1,260 字符；兼容文本 46 字符。
- 典型 lyrics page：240 字符；兼容文本 46 字符。

## 验证结果

- `uv sync --all-extras`：通过（50 packages checked）。
- `uv run ruff format --check .`：通过。
- `uv run ruff check .`：通过。
- `uv run mypy src`：通过，40 个源码文件无问题。
- `uv run pytest`：36 passed，1 skipped；跳过项是显式 opt-in 的真实网易云只读测试。
- MCP 合约：8 个正式工具、输入/输出 JSON Schema、structuredContent、错误映射通过。
- stdio：initialize/list_tools/call_tool/错误返回通过。
- Streamable HTTP：initialize/list_tools/call_tool 与 lifespan 关闭通过。
- `docker build -t netease-music-mcp:0.1.0 .`：通过。
- 容器内 `netease-music-mcp config`：以非 root 运行并通过。
- `docker compose config`：通过。
- `uv run mcp dev ...` 的交互式 Inspector 人工点击流程未运行；其底层协议路径已有自动测试。

真实网易云集成测试未运行，因为未配置 `NETEASE_INTEGRATION_ENABLED=true`。因此只能确认
MockTransport 契约和当前响应模型，不能保证交付时刻所有非公开接口仍接受请求。

## 上游与边界

当前路径和稳定性逐项列在 `docs/upstream-apis.md`。这些是非公开 Web 接口，可能无预告变化；
Backend 隔离使变更不影响 Tool、Service 和 Domain。

固定边界及真实来源见 `docs/architecture.md`：Python/MCP 版本来自技术基线；端口和 HTTP 状态
来自协议；搜索/历史 type 来自当前上游接口；其余数量、分页、批量、超时、重试和 TTL 均来自
Settings，不在 Service 或 Tool 静默修正。

## 明确不存在的能力

- 不存在任何 LLM 调用；服务器只提供结构化音乐数据。
- 不存在歌曲音频下载、播放、付费直链或 QQ 分享能力。
- 代码、测试、日志、MCP 输出和 SQLite 中均不暴露 Cookie；实际运行日志安全仍应纳入部署审计。
