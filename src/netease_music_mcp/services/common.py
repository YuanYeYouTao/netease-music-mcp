from typing import Any

from netease_music_mcp.backends.base import MusicCatalogBackend
from netease_music_mcp.cache.base import CacheBackend, build_cache_key
from netease_music_mcp.config import Settings
from netease_music_mcp.domain.errors import InvalidRequestError
from netease_music_mcp.domain.identifiers import normalize_id
from netease_music_mcp.domain.pagination import PageRequest


class ServiceBase:
    def __init__(
        self,
        backend: MusicCatalogBackend,
        cache: CacheBackend,
        settings: Settings,
    ) -> None:
        self.backend = backend
        self.cache = cache
        self.settings = settings

    def page_request(self, page: int, page_size: int | None) -> PageRequest:
        resolved_size = self.settings.default_page_size if page_size is None else page_size
        if page < 1:
            raise InvalidRequestError("page must be at least 1")
        if resolved_size < 1 or resolved_size > self.settings.max_page_size:
            raise InvalidRequestError(
                f"page_size must be between 1 and {self.settings.max_page_size}"
            )
        return PageRequest(page=page, page_size=resolved_size)

    @staticmethod
    def identifier(value: str, kind: str) -> str:
        try:
            return normalize_id(value)
        except ValueError as exc:
            raise InvalidRequestError(f"{kind} must contain decimal digits") from exc

    def cache_key(
        self,
        operation: str,
        parameters: dict[str, Any],
        *,
        authentication_scope: str = "public",
    ) -> str:
        return build_cache_key(
            backend=self.backend.name,
            operation=operation,
            parameters=parameters,
            authentication_scope=authentication_scope,
            config_fingerprint=self.settings.cache_fingerprint(),
        )
