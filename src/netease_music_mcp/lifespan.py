from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from netease_music_mcp.application import MusicApplication
from netease_music_mcp.backends import FakeMusicCatalogBackend, NeteaseWebBackend
from netease_music_mcp.backends.base import MusicCatalogBackend
from netease_music_mcp.cache import MemoryCacheBackend, NullCacheBackend, SQLiteCacheBackend
from netease_music_mcp.cache.base import CacheBackend
from netease_music_mcp.clients import AuthenticationProvider, NeteaseHttpClient
from netease_music_mcp.config import BackendName, CacheBackendName, Settings


def create_cache(settings: Settings) -> CacheBackend:
    if settings.cache_backend is CacheBackendName.NONE:
        return NullCacheBackend()
    if settings.cache_backend is CacheBackendName.SQLITE:
        return SQLiteCacheBackend(settings.cache_path)
    return MemoryCacheBackend()


def create_application(settings: Settings) -> MusicApplication:
    authentication = AuthenticationProvider.from_settings(settings)
    cache = create_cache(settings)
    backend: MusicCatalogBackend
    if settings.backend is BackendName.FAKE:
        backend = FakeMusicCatalogBackend()
    else:
        client = NeteaseHttpClient(settings, authentication)
        backend = NeteaseWebBackend(client, authentication)
    return MusicApplication(backend, cache, settings, authentication)


def application_lifespan(application: MusicApplication) -> Any:
    @asynccontextmanager
    async def lifespan(_server: Any) -> AsyncIterator[dict[str, object]]:
        try:
            yield {"application": application}
        finally:
            await application.close()

    return lifespan
