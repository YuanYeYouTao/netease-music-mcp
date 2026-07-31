# 数据模型

领域模型使用 `extra="forbid"` 与 `frozen=True`。日期是 ISO 8601，时长是非负
`duration_ms`，URL 经过 Pydantic 验证，网易云 ID 一律为字符串。

- `ArtistSummary`：id、name、aliases。
- `AlbumSummary`：id、name、artists、cover_url、publish_date、canonical_url。
- `SongSummary`：id、title、artists、album、duration_ms、aliases、canonical_url。
- `SongDetail`：Summary 加 track/disc number、publish_date、fee_type、available、popularity 和
  仅含稳定字段的 metadata。
- `ArtistDetail`：简介、封面、歌曲/专辑/MV 数量、可选 top songs、canonical URL。
- `AlbumDetail`：简介、封面、发布日期、公司、类型、size、分页 tracks。
- `PlaylistSummary` / `PlaylistDetail`：创建者、计数、标签、分页 tracks、可用权限数。
- `LyricsLine` / `LyricsDocument`：时间戳对齐的原文/翻译/罗马音和 offset/limit 分页。
- `SearchPage`、`UserLibraryPage`：统一 `PageInfo`。
- `RecommendationPage`、`SimilarSongsPage`、`NewSongsPage`、`RankingPage`：发现内容统一分页；
  排行榜只保留榜单元数据和上游提供的紧凑 Top 曲目。
- `PlaylistStatistics`：曲目数、分析数、总/平均时长、歌手/专辑计数、年份分布和不可用数。
- `WriteResult`：写操作、上游状态码及受影响的歌单/歌曲、点赞状态。

Normalizer 只选择稳定、有明确用途的字段，不把原始上游 JSON 复制到 metadata。
