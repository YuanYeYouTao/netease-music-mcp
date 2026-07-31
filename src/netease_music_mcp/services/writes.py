from netease_music_mcp.backends.base import MusicCatalogBackend
from netease_music_mcp.cache.base import CacheBackend
from netease_music_mcp.clients.authentication import AuthenticationProvider
from netease_music_mcp.config import Settings
from netease_music_mcp.domain.enums import PlaylistTrackOperation
from netease_music_mcp.domain.errors import InvalidRequestError, UnsupportedOperationError
from netease_music_mcp.domain.identifiers import normalize_id
from netease_music_mcp.domain.models import WriteResult

from .common import require_supported


class WriteService:
    def __init__(
        self,
        backend: MusicCatalogBackend,
        cache: CacheBackend,
        settings: Settings,
        authentication: AuthenticationProvider,
    ) -> None:
        self.backend = backend
        self.cache = cache
        self.settings = settings
        self.authentication = authentication

    def _guard(self, confirm: bool, operation: str) -> None:
        if not self.settings.write_operations_enabled:
            raise UnsupportedOperationError("write operations are disabled")
        self.authentication.require_user_id(None)
        if not confirm:
            raise InvalidRequestError("confirm must be true for account-changing operations")
        require_supported(self.backend, operation)

    async def _invalidate_cache(self) -> None:
        # A write can change playlist details, library listings, or liked songs.
        await self.cache.clear()

    async def create_playlist(self, name: str, private: bool, confirm: bool) -> WriteResult:
        self._guard(confirm, "create_playlist")
        normalized_name = name.strip()
        if not normalized_name:
            raise InvalidRequestError("name cannot be empty")
        if len(normalized_name) > 100:
            raise InvalidRequestError("name must be at most 100 characters")
        result = await self.backend.create_playlist(normalized_name, private)
        await self._invalidate_cache()
        return result

    async def update_playlist_tracks(
        self,
        playlist_id: str,
        operation: PlaylistTrackOperation,
        song_ids: tuple[str, ...],
        confirm: bool,
    ) -> WriteResult:
        self._guard(confirm, "update_playlist_tracks")
        normalized_playlist_id = self._identifier(playlist_id, "playlist_id")
        if not song_ids:
            raise InvalidRequestError("song_ids cannot be empty")
        if len(song_ids) > self.settings.max_batch_song_ids:
            raise InvalidRequestError(
                f"song_ids cannot contain more than {self.settings.max_batch_song_ids} IDs"
            )
        normalized_song_ids = tuple(self._identifier(song_id, "song_id") for song_id in song_ids)
        if len(set(normalized_song_ids)) != len(normalized_song_ids):
            raise InvalidRequestError("song_ids must not contain duplicates")
        result = await self.backend.update_playlist_tracks(
            normalized_playlist_id, operation, normalized_song_ids
        )
        await self._invalidate_cache()
        return result

    async def set_song_like(self, song_id: str, liked: bool, confirm: bool) -> WriteResult:
        self._guard(confirm, "set_song_like")
        result = await self.backend.set_song_like(self._identifier(song_id, "song_id"), liked)
        await self._invalidate_cache()
        return result

    @staticmethod
    def _identifier(value: str, kind: str) -> str:
        try:
            return normalize_id(value)
        except ValueError as exc:
            raise InvalidRequestError(f"{kind} must contain decimal digits") from exc
