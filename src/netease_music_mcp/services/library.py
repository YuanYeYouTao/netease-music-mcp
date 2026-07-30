from netease_music_mcp.backends.base import MusicCatalogBackend
from netease_music_mcp.cache.base import CacheBackend
from netease_music_mcp.clients.authentication import AuthenticationProvider
from netease_music_mcp.config import Settings
from netease_music_mcp.domain.enums import HistoryScope, LibrarySection
from netease_music_mcp.domain.models import UserLibraryPage

from .common import ServiceBase


class LibraryService(ServiceBase):
    def __init__(
        self,
        backend: MusicCatalogBackend,
        cache: CacheBackend,
        settings: Settings,
        authentication: AuthenticationProvider,
    ) -> None:
        super().__init__(backend, cache, settings)
        self.authentication = authentication

    async def get_user_library(
        self,
        section: LibrarySection,
        user_id: str | None = None,
        page: int = 1,
        page_size: int | None = None,
        history_scope: HistoryScope = HistoryScope.WEEK,
    ) -> UserLibraryPage:
        resolved_user_id = self.authentication.require_user_id(user_id)
        normalized_user_id = self.identifier(resolved_user_id, "user_id")
        request = self.page_request(page, page_size)
        parameters = {
            "history_scope": history_scope.value,
            "page": request.page,
            "page_size": request.page_size,
            "section": section.value,
            "user_id": normalized_user_id,
        }
        key = self.cache_key(
            "get_user_library",
            parameters,
            authentication_scope=self.authentication.authentication_scope(normalized_user_id),
        )
        cached = await self.cache.get(key)
        if cached is not None:
            return UserLibraryPage.model_validate_json(cached)
        result = await self.backend.get_user_library(
            section, normalized_user_id, request, history_scope
        )
        await self.cache.set(key, result.model_dump_json(), self.settings.library_cache_ttl_seconds)
        return result
