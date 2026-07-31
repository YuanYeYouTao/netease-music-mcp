# 当前上游接口与稳定性

`NeteaseWebBackend` 使用网易云 Web 客户端相关的非公开接口。它们没有公开兼容承诺，字段、
认证和限流行为可能变化；生产部署应监控 `upstream_response_error` 并锁定本项目版本。

| 操作 | 当前路径 | 稳定性 |
| --- | --- | --- |
| 搜索 | `POST /api/cloudsearch/pc` | 非公开；type/结果容器可能变化 |
| 歌曲详情 | `POST /api/song/detail/` | 非公开；`ar/al` 与 `artists/album` 均规范化 |
| 专辑 | `GET /api/album/{id}` | 非公开；曲目在 Backend 本地分页 |
| 歌手 | `GET /api/artist/{id}` | 非公开；热门歌曲数量可能由上游限制 |
| 歌单 | `POST /api/v6/playlist/detail` | 非公开；曲目 ID 再批量读取详情 |
| 歌词 | `GET /api/song/lyric` | 非公开；LRC 时间戳在 Normalizer 对齐 |
| 用户歌单 | `GET /api/user/playlist` | 需要有效认证 |
| 收藏歌手/专辑 | `GET /api/artist/sublist`, `/api/album/sublist` | 需要有效认证 |
| 每日推荐 | `GET /api/v3/discovery/recommend/songs` | 需要有效认证 |
| 播放记录 | `GET /api/v1/play/record` | 需要有效认证；type 0/1 |
| 推荐歌单 | `GET /api/personalized/playlist` | 非公开；响应随登录态变化，不持久化缓存 |
| 相似歌曲 | `GET /api/v1/discovery/simiSong` | 非公开；以额外一条结果探测是否还有下一页 |
| 推荐新歌 | `GET /api/personalized/newsong` | 非公开；areaId 为 0/7/96/16/8；不持久化缓存 |
| 排行榜 | `GET /api/toplist/detail` | 非公开；榜单只返回上游摘要曲目 |
| 喜欢的歌曲 ID | `GET /api/song/like/get` | 需要有效认证；随后批量读取歌曲详情 |
| 登录检查 | `GET /api/nuser/account/get` | 仅 CLI doctor；不是 MCP Tool |

上游 JSON 先经 Provider Pydantic Model 验证，再由 `NeteaseNormalizer` 处理 ID、字段别名、
时间戳、时长、缺图、别名、空描述、权限和缺失歌曲。Tool 与 Service 不含字段兼容分支。
