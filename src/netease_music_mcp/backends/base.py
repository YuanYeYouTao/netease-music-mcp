from typing import Protocol

from netease_music_mcp.domain.enums import (
    DetailLevel,
    HistoryScope,
    LibrarySection,
    PlaylistTrackOperation,
    ReleaseArea,
    SearchCategory,
)
from netease_music_mcp.domain.models import (
    AlbumDetail,
    ArtistDetail,
    GetSongsResult,
    LyricsDocument,
    NewSongsPage,
    PlaylistDetail,
    RankingPage,
    RecommendationPage,
    SearchPage,
    SimilarSongsPage,
    UserLibraryPage,
    WriteResult,
)
from netease_music_mcp.domain.pagination import PageRequest

CORE_BACKEND_OPERATIONS = frozenset(
    {
        "search",
        "get_songs",
        "get_album",
        "get_artist",
        "get_playlist",
        "get_user_library:playlists",
    }
)

ALL_BACKEND_OPERATIONS = CORE_BACKEND_OPERATIONS | frozenset(
    {
        "get_recommendations",
        "get_similar_songs",
        "get_new_songs",
        "get_rankings",
        "get_lyrics",
        "get_playlist_statistics",
        "get_user_library:artist_subscriptions",
        "get_user_library:album_subscriptions",
        "get_user_library:daily_recommendations",
        "get_user_library:play_history",
        "get_user_library:liked_songs",
        "create_playlist",
        "update_playlist_tracks",
        "set_song_like",
    }
)


class MusicCatalogBackend(Protocol):
    name: str
    supported_operations: frozenset[str]

    async def search(
        self,
        query: str,
        category: SearchCategory,
        page: PageRequest,
        detail_level: DetailLevel,
    ) -> SearchPage: ...

    async def get_songs(
        self, song_ids: tuple[str, ...], detail_level: DetailLevel
    ) -> GetSongsResult: ...

    async def get_recommendations(self, page: PageRequest) -> RecommendationPage: ...

    async def get_similar_songs(self, song_id: str, page: PageRequest) -> SimilarSongsPage: ...

    async def get_new_songs(self, area: ReleaseArea, page: PageRequest) -> NewSongsPage: ...

    async def get_rankings(self, page: PageRequest) -> RankingPage: ...

    async def get_album(
        self, album_id: str, include_tracks: bool, track_page: PageRequest
    ) -> AlbumDetail: ...

    async def get_artist(
        self, artist_id: str, include_top_songs: bool, top_song_count: int
    ) -> ArtistDetail: ...

    async def get_playlist(
        self, playlist_id: str, include_tracks: bool, track_page: PageRequest
    ) -> PlaylistDetail: ...

    async def get_lyrics(
        self,
        song_id: str,
        include_translation: bool,
        include_romanization: bool,
        offset: int,
        limit: int,
    ) -> LyricsDocument: ...

    async def get_user_library(
        self,
        section: LibrarySection,
        user_id: str,
        page: PageRequest,
        history_scope: HistoryScope,
    ) -> UserLibraryPage: ...

    async def create_playlist(self, name: str, private: bool) -> WriteResult: ...

    async def update_playlist_tracks(
        self,
        playlist_id: str,
        operation: PlaylistTrackOperation,
        song_ids: tuple[str, ...],
    ) -> WriteResult: ...

    async def set_song_like(self, song_id: str, liked: bool) -> WriteResult: ...

    async def close(self) -> None: ...
