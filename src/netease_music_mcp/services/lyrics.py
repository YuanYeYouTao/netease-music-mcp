from netease_music_mcp.backends.base import MusicCatalogBackend
from netease_music_mcp.cache.base import CacheBackend
from netease_music_mcp.config import Settings
from netease_music_mcp.domain.errors import InvalidRequestError
from netease_music_mcp.domain.models import LyricsDocument

from .common import ServiceBase


class LyricsService(ServiceBase):
    def __init__(
        self, backend: MusicCatalogBackend, cache: CacheBackend, settings: Settings
    ) -> None:
        super().__init__(backend, cache, settings)

    async def get_lyrics(
        self,
        song_id: str,
        include_translation: bool = True,
        include_romanization: bool = False,
        offset: int = 0,
        limit: int | None = None,
    ) -> LyricsDocument:
        self.require_supported("get_lyrics")
        normalized_id = self.identifier(song_id, "song_id")
        resolved_limit = self.settings.default_lyrics_limit if limit is None else limit
        if offset < 0:
            raise InvalidRequestError("offset must be at least 0")
        if resolved_limit < 1 or resolved_limit > self.settings.max_lyrics_limit:
            raise InvalidRequestError(
                f"limit must be between 1 and {self.settings.max_lyrics_limit}"
            )
        parameters = {
            "include_romanization": include_romanization,
            "include_translation": include_translation,
            "limit": resolved_limit,
            "offset": offset,
            "song_id": normalized_id,
        }
        key = self.cache_key("get_lyrics", parameters)
        cached = await self.cache.get(key)
        if cached is not None:
            return LyricsDocument.model_validate_json(cached)
        result = await self.backend.get_lyrics(
            normalized_id,
            include_translation,
            include_romanization,
            offset,
            resolved_limit,
        )
        await self.cache.set(key, result.model_dump_json(), self.settings.lyrics_cache_ttl_seconds)
        return result
