import pytest

from netease_music_mcp.application import MusicApplication
from netease_music_mcp.backends.fake import FakeMusicCatalogBackend
from netease_music_mcp.cache.memory import MemoryCacheBackend
from netease_music_mcp.clients.authentication import AuthenticationProvider
from netease_music_mcp.config import Settings


@pytest.fixture
def fake_settings() -> Settings:
    return Settings(
        backend="fake",
        cache_backend="memory",
        default_page_size=2,
        max_page_size=4,
        max_batch_song_ids=4,
        max_statistics_tracks=10,
        cookie="MUSIC_U=test-cookie",
        user_id="99",
    )


@pytest.fixture
def fake_backend() -> FakeMusicCatalogBackend:
    return FakeMusicCatalogBackend()


@pytest.fixture
def application(fake_settings: Settings, fake_backend: FakeMusicCatalogBackend) -> MusicApplication:
    authentication = AuthenticationProvider.from_settings(fake_settings)
    return MusicApplication(
        fake_backend,
        MemoryCacheBackend(),
        fake_settings,
        authentication,
    )
