from netease_music_mcp.backends.base import MusicCatalogBackend
from netease_music_mcp.cache.base import CacheBackend
from netease_music_mcp.config import Settings
from netease_music_mcp.domain.enums import DetailLevel, SearchCategory
from netease_music_mcp.domain.errors import InvalidRequestError
from netease_music_mcp.domain.models import (
    AlbumDetail,
    ArtistDetail,
    GetSongsResult,
    PlaylistDetail,
    SearchPage,
)

from .common import ServiceBase


class CatalogService(ServiceBase):
    def __init__(
        self, backend: MusicCatalogBackend, cache: CacheBackend, settings: Settings
    ) -> None:
        super().__init__(backend, cache, settings)

    async def search(
        self,
        query: str,
        category: SearchCategory,
        page: int = 1,
        page_size: int | None = None,
        detail_level: DetailLevel = DetailLevel.SUMMARY,
    ) -> SearchPage:
        normalized_query = query.strip()
        if not normalized_query:
            raise InvalidRequestError("query cannot be empty")
        request = self.page_request(page, page_size)
        key = self.cache_key(
            "search",
            {
                "category": category.value,
                "detail_level": detail_level.value,
                "page": request.page,
                "page_size": request.page_size,
                "query": normalized_query,
            },
        )
        cached = await self.cache.get(key)
        if cached is not None:
            return SearchPage.model_validate_json(cached)
        result = await self.backend.search(normalized_query, category, request, detail_level)
        await self.cache.set(key, result.model_dump_json(), self.settings.search_cache_ttl_seconds)
        return result

    async def get_songs(
        self,
        song_ids: tuple[str, ...],
        detail_level: DetailLevel = DetailLevel.SUMMARY,
    ) -> GetSongsResult:
        if not song_ids:
            raise InvalidRequestError("song_ids cannot be empty")
        if len(song_ids) > self.settings.max_batch_song_ids:
            raise InvalidRequestError(
                f"song_ids cannot contain more than {self.settings.max_batch_song_ids} values"
            )
        normalized = tuple(self.identifier(song_id, "song_id") for song_id in song_ids)
        key = self.cache_key(
            "get_songs", {"detail_level": detail_level.value, "song_ids": normalized}
        )
        cached = await self.cache.get(key)
        if cached is not None:
            return GetSongsResult.model_validate_json(cached)
        result = await self.backend.get_songs(normalized, detail_level)
        await self.cache.set(key, result.model_dump_json(), self.settings.detail_cache_ttl_seconds)
        return result

    async def get_album(
        self,
        album_id: str,
        include_tracks: bool = False,
        track_page: int = 1,
        track_page_size: int | None = None,
    ) -> AlbumDetail:
        normalized_id = self.identifier(album_id, "album_id")
        request = self.page_request(track_page, track_page_size)
        parameters = {
            "album_id": normalized_id,
            "include_tracks": include_tracks,
            "page": request.page,
            "page_size": request.page_size,
        }
        key = self.cache_key("get_album", parameters)
        cached = await self.cache.get(key)
        if cached is not None:
            return AlbumDetail.model_validate_json(cached)
        result = await self.backend.get_album(normalized_id, include_tracks, request)
        await self.cache.set(key, result.model_dump_json(), self.settings.detail_cache_ttl_seconds)
        return result

    async def get_artist(
        self,
        artist_id: str,
        include_top_songs: bool = False,
        top_song_count: int | None = None,
    ) -> ArtistDetail:
        normalized_id = self.identifier(artist_id, "artist_id")
        count = self.settings.default_top_song_count if top_song_count is None else top_song_count
        if count < 1 or count > self.settings.max_top_song_count:
            raise InvalidRequestError(
                f"top_song_count must be between 1 and {self.settings.max_top_song_count}"
            )
        parameters = {
            "artist_id": normalized_id,
            "include_top_songs": include_top_songs,
            "top_song_count": count,
        }
        key = self.cache_key("get_artist", parameters)
        cached = await self.cache.get(key)
        if cached is not None:
            return ArtistDetail.model_validate_json(cached)
        result = await self.backend.get_artist(normalized_id, include_top_songs, count)
        await self.cache.set(key, result.model_dump_json(), self.settings.detail_cache_ttl_seconds)
        return result

    async def get_playlist(
        self,
        playlist_id: str,
        include_tracks: bool = False,
        track_page: int = 1,
        track_page_size: int | None = None,
    ) -> PlaylistDetail:
        normalized_id = self.identifier(playlist_id, "playlist_id")
        request = self.page_request(track_page, track_page_size)
        parameters = {
            "playlist_id": normalized_id,
            "include_tracks": include_tracks,
            "page": request.page,
            "page_size": request.page_size,
        }
        key = self.cache_key("get_playlist", parameters)
        cached = await self.cache.get(key)
        if cached is not None:
            return PlaylistDetail.model_validate_json(cached)
        result = await self.backend.get_playlist(normalized_id, include_tracks, request)
        await self.cache.set(key, result.model_dump_json(), self.settings.detail_cache_ttl_seconds)
        return result
