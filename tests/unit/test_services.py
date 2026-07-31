import pytest
from pydantic import ValidationError

from netease_music_mcp.application import MusicApplication
from netease_music_mcp.backends.base import CORE_BACKEND_OPERATIONS
from netease_music_mcp.backends.fake import FakeMusicCatalogBackend
from netease_music_mcp.cache.memory import MemoryCacheBackend
from netease_music_mcp.clients.authentication import AuthenticationProvider
from netease_music_mcp.config import Settings
from netease_music_mcp.domain.enums import (
    DetailLevel,
    LibrarySection,
    PlaylistTrackOperation,
    SearchCategory,
)
from netease_music_mcp.domain.errors import (
    AuthenticationRequiredError,
    InvalidRequestError,
    UnsupportedOperationError,
)
from netease_music_mcp.domain.models import SongDetail


@pytest.mark.asyncio
async def test_empty_search_is_rejected(application: MusicApplication) -> None:
    with pytest.raises(InvalidRequestError, match="empty"):
        await application.music_search("  ", SearchCategory.SONG)


def test_search_enum_rejects_unknown_category() -> None:
    with pytest.raises(ValueError):
        SearchCategory("podcast")


def test_illegal_pagination_configuration_fails_at_startup() -> None:
    with pytest.raises(ValidationError, match="default_page_size"):
        Settings(default_page_size=101, max_page_size=100)


def test_write_operations_are_disabled_by_default() -> None:
    assert Settings().write_operations_enabled is False


@pytest.mark.asyncio
async def test_page_size_is_not_silently_clamped(application: MusicApplication) -> None:
    with pytest.raises(InvalidRequestError, match="between"):
        await application.music_search("Example", SearchCategory.SONG, page_size=5)


@pytest.mark.asyncio
async def test_batch_details_keep_order_and_missing_ids(application: MusicApplication) -> None:
    result = await application.get_songs(("2", "404", "1"), DetailLevel.FULL)
    assert [song.id for song in result.songs] == ["2", "1"]
    assert result.missing_ids == ("404",)
    assert all(isinstance(song, SongDetail) for song in result.songs)


@pytest.mark.asyncio
async def test_batch_limit_comes_from_configuration(application: MusicApplication) -> None:
    with pytest.raises(InvalidRequestError, match="more than 4"):
        await application.get_songs(("1", "2", "3", "4", "5"))


@pytest.mark.asyncio
async def test_playlist_tracks_are_paginated(application: MusicApplication) -> None:
    first = await application.get_playlist("30", True, 1, 2)
    second = await application.get_playlist("30", True, 2, 2)
    without_tracks = await application.get_playlist("30", False, 1, 2)
    assert [song.id for song in first.tracks] == ["1", "2"]
    assert [song.id for song in second.tracks] == ["3"]
    assert first.track_page.has_more is True
    assert without_tracks.tracks == ()


@pytest.mark.asyncio
async def test_lyrics_default_and_explicit_pagination(application: MusicApplication) -> None:
    default_page = await application.get_lyrics("1")
    explicit_page = await application.get_lyrics("1", True, True, 2, 3)
    assert default_page.limit == application.settings.default_lyrics_limit
    assert [line.timestamp_ms for line in explicit_page.lines] == [20_000, 30_000, 40_000]
    assert explicit_page.lines[0].translated_text is not None
    assert explicit_page.lines[0].romanized_text is not None


@pytest.mark.asyncio
async def test_public_tools_do_not_require_cookie() -> None:
    settings = Settings(backend="fake", cache_backend="none", cookie=None, music_u=None)
    authentication = AuthenticationProvider.from_settings(settings)
    app = MusicApplication(
        FakeMusicCatalogBackend(), MemoryCacheBackend(), settings, authentication
    )
    result = await app.music_search("Example", SearchCategory.SONG)
    assert result.items
    with pytest.raises(AuthenticationRequiredError):
        await app.get_user_library(LibrarySection.PLAYLISTS)


@pytest.mark.asyncio
async def test_private_library_uses_authenticated_configured_user(
    application: MusicApplication,
) -> None:
    result = await application.get_user_library(LibrarySection.PLAYLISTS)
    assert result.user_id == "99"
    assert result.items


@pytest.mark.asyncio
async def test_discovery_pages_and_liked_songs_use_domain_models(
    application: MusicApplication,
) -> None:
    recommendations = await application.get_recommendations(page_size=1)
    similar = await application.get_similar_songs("1", page_size=1)
    releases = await application.get_new_songs(page_size=1)
    rankings = await application.get_rankings(page_size=1)
    liked = await application.get_user_library(LibrarySection.LIKED_SONGS, page_size=1)
    assert recommendations.items[0].id == "30"
    assert similar.song_id == "1"
    assert releases.items[0].id == "1"
    assert rankings.items[0].id == "30"
    assert liked.items[0].id == "1"


@pytest.mark.asyncio
async def test_write_operations_require_confirmation_and_restore_fake_state(
    application: MusicApplication,
) -> None:
    with pytest.raises(InvalidRequestError, match="confirm"):
        await application.set_song_like("1")
    created = await application.create_playlist("temporary", confirm=True)
    assert created.playlist_id is not None
    before_add = await application.get_playlist(created.playlist_id, True, 1, 4)
    assert before_add.tracks == ()
    added = await application.update_playlist_tracks(
        created.playlist_id, PlaylistTrackOperation.ADD, ("1",), confirm=True
    )
    assert added.song_ids == ("1",)
    after_add = await application.get_playlist(created.playlist_id, True, 1, 4)
    assert [song.id for song in after_add.tracks] == ["1"]
    await application.update_playlist_tracks(
        created.playlist_id, PlaylistTrackOperation.REMOVE, ("1",), confirm=True
    )
    after_remove = await application.get_playlist(created.playlist_id, True, 1, 4)
    assert after_remove.tracks == ()


@pytest.mark.asyncio
async def test_write_operations_can_be_disabled(fake_settings: Settings) -> None:
    settings = fake_settings.model_copy(update={"write_operations_enabled": False})
    authentication = AuthenticationProvider.from_settings(settings)
    app = MusicApplication(
        FakeMusicCatalogBackend(), MemoryCacheBackend(), settings, authentication
    )
    with pytest.raises(UnsupportedOperationError, match="disabled"):
        await app.create_playlist("blocked", confirm=True)


@pytest.mark.asyncio
async def test_write_operations_do_not_require_configured_user_id() -> None:
    settings = Settings(
        backend="fake",
        cache_backend="none",
        write_operations_enabled=True,
        cookie="MUSIC_U=test-cookie",
        user_id=None,
    )
    authentication = AuthenticationProvider.from_settings(settings)
    app = MusicApplication(
        FakeMusicCatalogBackend(), MemoryCacheBackend(), settings, authentication
    )

    created = await app.create_playlist("authenticated", confirm=True)

    assert created.playlist_id is not None


class CountingFakeBackend(FakeMusicCatalogBackend):
    def __init__(self) -> None:
        super().__init__()
        self.search_calls = 0
        self.song_calls = 0

    async def search(self, *args: object, **kwargs: object):
        self.search_calls += 1
        return await super().search(*args, **kwargs)

    async def get_songs(self, *args: object, **kwargs: object):
        self.song_calls += 1
        return await super().get_songs(*args, **kwargs)


class CoreOnlyFakeBackend(FakeMusicCatalogBackend):
    supported_operations = CORE_BACKEND_OPERATIONS


@pytest.mark.asyncio
async def test_unsupported_backend_capability_is_not_an_empty_result(
    fake_settings: Settings,
) -> None:
    authentication = AuthenticationProvider.from_settings(fake_settings)
    app = MusicApplication(
        CoreOnlyFakeBackend(), MemoryCacheBackend(), fake_settings, authentication
    )
    with pytest.raises(UnsupportedOperationError, match="get_recommendations"):
        await app.get_recommendations()
    with pytest.raises(UnsupportedOperationError, match="liked_songs"):
        await app.get_user_library(LibrarySection.LIKED_SONGS)


@pytest.mark.asyncio
async def test_search_and_detail_cache_hits(fake_settings: Settings) -> None:
    backend = CountingFakeBackend()
    authentication = AuthenticationProvider.from_settings(fake_settings)
    app = MusicApplication(backend, MemoryCacheBackend(), fake_settings, authentication)
    await app.music_search("Example", SearchCategory.SONG)
    await app.music_search("Example", SearchCategory.SONG)
    await app.get_songs(("1",), DetailLevel.FULL)
    await app.get_songs(("1",), DetailLevel.FULL)
    assert backend.search_calls == 1
    assert backend.song_calls == 1


@pytest.mark.asyncio
async def test_playlist_statistics_are_deterministic(application: MusicApplication) -> None:
    first = await application.get_playlist_statistics("30")
    second = await application.get_playlist_statistics("30")
    assert first == second
    assert first.analyzed_track_count == 3
    assert first.total_duration_ms == 546_000
    assert first.unavailable_track_count == 1
    assert first.artist_counts[0].name == "Example Artist"
