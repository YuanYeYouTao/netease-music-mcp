# MCP Tools

所有 ID 输入输出均为字符串。`page` 一律从 1 开始；`page_size=None` 使用唯一配置默认值，
超过配置上限会返回 `invalid_request`。

| Tool | 输入 | 输出 |
| --- | --- | --- |
| `music_search` | `query`, `category`, `page=1`, `page_size=None`, `detail_level=summary` | `SearchPage` |
| `get_songs` | `song_ids`, `detail_level=summary` | `GetSongsResult {songs, missing_ids}` |
| `get_album` | `album_id`, `include_tracks=false`, `track_page=1`, `track_page_size=None` | `AlbumDetail` |
| `get_artist` | `artist_id`, `include_top_songs=false`, `top_song_count=None` | `ArtistDetail` |
| `get_playlist` | `playlist_id`, `include_tracks=false`, `track_page=1`, `track_page_size=None` | `PlaylistDetail` |
| `get_lyrics` | `song_id`, `include_translation=true`, `include_romanization=false`, `offset=0`, `limit=None` | `LyricsDocument` |
| `get_user_library` | `section`, `user_id=None`, `page=1`, `page_size=None`, `history_scope=week` | `UserLibraryPage` |
| `get_playlist_statistics` | `playlist_id`, `track_limit=None` | `PlaylistStatistics` |

`category`：`song`、`artist`、`album`、`playlist`。

`section`：`playlists`、`artist_subscriptions`、`album_subscriptions`、
`daily_recommendations`、`play_history`。

错误在统一 MCP 边界表示为 `error_code`、`message`、`retryable`。未找到与上游故障不同；
私人数据无登录态明确返回 `authentication_required`。
