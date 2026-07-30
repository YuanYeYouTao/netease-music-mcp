from netease_music_mcp.backends.base import MusicCatalogBackend
from netease_music_mcp.cache.base import CacheBackend
from netease_music_mcp.clients.authentication import AuthenticationProvider
from netease_music_mcp.config import Settings
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
    PlaylistStatistics,
    SearchPage,
    UserLibraryPage,
)
from netease_music_mcp.services import (
    CatalogService,
    LibraryService,
    LyricsService,
    StatisticsService,
)


class MusicApplication:
    def __init__(
        self,
        backend: MusicCatalogBackend,
        cache: CacheBackend,
        settings: Settings,
        authentication: AuthenticationProvider,
    ) -> None:
        self.settings = settings
        self.backend = backend
        self.cache = cache
        self.catalog = CatalogService(backend, cache, settings)
        self.library = LibraryService(backend, cache, settings, authentication)
        self.lyrics = LyricsService(backend, cache, settings)
        self.statistics = StatisticsService(self.catalog)

    async def music_search(
        self,
        query: str,
        category: SearchCategory,
        page: int = 1,
        page_size: int | None = None,
        detail_level: DetailLevel = DetailLevel.SUMMARY,
    ) -> SearchPage:
        return await self.catalog.search(query, category, page, page_size, detail_level)

    async def get_songs(
        self, song_ids: tuple[str, ...], detail_level: DetailLevel = DetailLevel.SUMMARY
    ) -> GetSongsResult:
        return await self.catalog.get_songs(song_ids, detail_level)

    async def get_album(
        self,
        album_id: str,
        include_tracks: bool = False,
        track_page: int = 1,
        track_page_size: int | None = None,
    ) -> AlbumDetail:
        return await self.catalog.get_album(album_id, include_tracks, track_page, track_page_size)

    async def get_artist(
        self,
        artist_id: str,
        include_top_songs: bool = False,
        top_song_count: int | None = None,
    ) -> ArtistDetail:
        return await self.catalog.get_artist(artist_id, include_top_songs, top_song_count)

    async def get_playlist(
        self,
        playlist_id: str,
        include_tracks: bool = False,
        track_page: int = 1,
        track_page_size: int | None = None,
    ) -> PlaylistDetail:
        return await self.catalog.get_playlist(
            playlist_id, include_tracks, track_page, track_page_size
        )

    async def get_lyrics(
        self,
        song_id: str,
        include_translation: bool = True,
        include_romanization: bool = False,
        offset: int = 0,
        limit: int | None = None,
    ) -> LyricsDocument:
        return await self.lyrics.get_lyrics(
            song_id, include_translation, include_romanization, offset, limit
        )

    async def get_user_library(
        self,
        section: LibrarySection,
        user_id: str | None = None,
        page: int = 1,
        page_size: int | None = None,
        history_scope: HistoryScope = HistoryScope.WEEK,
    ) -> UserLibraryPage:
        return await self.library.get_user_library(section, user_id, page, page_size, history_scope)

    async def get_playlist_statistics(
        self, playlist_id: str, track_limit: int | None = None
    ) -> PlaylistStatistics:
        return await self.statistics.get_playlist_statistics(playlist_id, track_limit)

    async def close(self) -> None:
        await self.backend.close()
        await self.cache.close()
