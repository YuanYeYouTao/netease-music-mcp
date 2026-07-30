from typing import Protocol

from netease_music_mcp.domain.enums import (
    DetailLevel,
    HistoryScope,
    LibrarySection,
    SearchCategory,
)
from netease_music_mcp.domain.models import (
    AlbumDetail,
    ArtistDetail,
    GetSongsResult,
    LyricsDocument,
    PlaylistDetail,
    SearchPage,
    UserLibraryPage,
)
from netease_music_mcp.domain.pagination import PageRequest


class MusicCatalogBackend(Protocol):
    name: str

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

    async def close(self) -> None: ...
