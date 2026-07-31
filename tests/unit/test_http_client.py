import httpx
import pytest

from netease_music_mcp.backends.netease_web import NeteaseWebBackend
from netease_music_mcp.clients.authentication import AuthenticationProvider
from netease_music_mcp.clients.http import NeteaseHttpClient
from netease_music_mcp.config import Settings
from netease_music_mcp.domain.enums import (
    DetailLevel,
    HistoryScope,
    LibrarySection,
    ReleaseArea,
    SearchCategory,
)
from netease_music_mcp.domain.errors import (
    RateLimitedError,
    ResourceNotFoundError,
    UpstreamResponseError,
    UpstreamUnavailableError,
)
from netease_music_mcp.domain.pagination import PageRequest


def make_client(handler: httpx.MockTransport) -> NeteaseHttpClient:
    settings = Settings(retry_attempts=0, cookie="MUSIC_U=do-not-log")
    return NeteaseHttpClient(
        settings,
        AuthenticationProvider.from_settings(settings),
        transport=handler,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "error"),
    [(404, ResourceNotFoundError), (429, RateLimitedError), (503, UpstreamUnavailableError)],
)
async def test_http_status_mapping(status: int, error: type[Exception]) -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(status, request=request))
    client = make_client(transport)
    try:
        with pytest.raises(error) as captured:
            await client.request_json("GET", "/test")
        assert "do-not-log" not in str(captured.value)
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_invalid_json_mapping() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, text="not-json", request=request)
    )
    client = make_client(transport)
    try:
        with pytest.raises(UpstreamResponseError, match="invalid JSON"):
            await client.request_json("GET", "/test")
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_timeout_mapping() -> None:
    def timeout(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out")

    client = make_client(httpx.MockTransport(timeout))
    try:
        with pytest.raises(UpstreamUnavailableError):
            await client.request_json("GET", "/test")
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_public_request_has_no_cookie_when_anonymous() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"code": 200}, request=request)

    settings = Settings(cookie=None, music_u=None, csrf=None)
    client = NeteaseHttpClient(
        settings,
        AuthenticationProvider.from_settings(settings),
        transport=httpx.MockTransport(handler),
    )
    try:
        await client.request_json("GET", "/test")
        assert "cookie" not in seen[0].headers
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_request_uses_browser_profile_required_by_netease_search() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"code": 200}, request=request)

    settings = Settings()
    client = NeteaseHttpClient(
        settings,
        AuthenticationProvider.from_settings(settings),
        transport=httpx.MockTransport(handler),
    )
    try:
        await client.request_json(
            "POST",
            "/api/cloudsearch/pc",
            data={"s": "Reminiscences", "type": 1, "limit": 5, "offset": 0},
        )
    finally:
        await client.close()

    assert len(seen) == 1
    request = seen[0]
    assert request.url.path == "/api/cloudsearch/pc"
    assert request.headers["user-agent"].startswith("Mozilla/5.0")
    assert request.headers["referer"] == "https://music.163.com/"
    assert request.headers["accept-language"].startswith("zh-CN")
    assert b"s=Reminiscences" in request.content


@pytest.mark.asyncio
async def test_backend_search_uses_cloud_search_endpoint() -> None:
    seen_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_paths.append(request.url.path)
        return httpx.Response(
            200,
            json={
                "code": 200,
                "result": {
                    "songCount": 1,
                    "songs": [
                        {
                            "id": 1364370190,
                            "name": "Reminiscences",
                            "artists": [{"id": 1, "name": "re:plus"}],
                        }
                    ],
                },
            },
            request=request,
        )

    settings = Settings()
    authentication = AuthenticationProvider.from_settings(settings)
    client = NeteaseHttpClient(
        settings,
        authentication,
        transport=httpx.MockTransport(handler),
    )
    backend = NeteaseWebBackend(client, authentication)
    try:
        result = await backend.search(
            "Reminiscences",
            SearchCategory.SONG,
            PageRequest(page=1, page_size=5),
            DetailLevel.SUMMARY,
        )
    finally:
        await backend.close()

    assert seen_paths == ["/api/cloudsearch/pc"]
    assert result.items[0].id == "1364370190"


@pytest.mark.asyncio
async def test_playlist_library_normalizes_nulls_and_paginates_locally() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json={
                "code": 200,
                "playlist": [
                    {"id": index, "description": None, "tracks": None} for index in range(1, 6)
                ],
            },
            request=request,
        )

    settings = Settings(cookie="MUSIC_U=test")
    authentication = AuthenticationProvider.from_settings(settings)
    client = NeteaseHttpClient(
        settings,
        authentication,
        transport=httpx.MockTransport(handler),
    )
    backend = NeteaseWebBackend(client, authentication)
    try:
        result = await backend.get_user_library(
            LibrarySection.PLAYLISTS,
            "99",
            PageRequest(page=2, page_size=2),
            HistoryScope.WEEK,
        )
    finally:
        await backend.close()

    assert [item.id for item in result.items] == ["3", "4"]
    assert all(item.description == "" for item in result.items)
    assert result.page.total == 5
    assert result.page.has_more is True
    assert seen[0].url.params["offset"] == "0"
    assert seen[0].url.params["limit"] == "4"


@pytest.mark.asyncio
async def test_discovery_and_liked_library_endpoints_are_normalized() -> None:
    seen_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_paths.append(request.url.path)
        if request.url.path == "/api/personalized/playlist":
            return httpx.Response(
                200,
                json={
                    "code": 200,
                    "result": [
                        {"id": 30, "name": "Recommendation", "picUrl": "https://example.test/p.jpg"}
                    ],
                },
                request=request,
            )
        if request.url.path == "/api/v1/discovery/simiSong":
            return httpx.Response(
                200,
                json={
                    "code": 200,
                    "songs": [
                        {"id": 2, "name": "Similar", "artists": [{"id": 10, "name": "Artist"}]}
                    ],
                },
                request=request,
            )
        if request.url.path == "/api/personalized/newsong":
            return httpx.Response(
                200,
                json={
                    "code": 200,
                    "result": [
                        {
                            "song": {
                                "id": 20,
                                "name": "New Song",
                                "artists": [{"id": 10, "name": "Artist"}],
                            }
                        }
                    ],
                },
                request=request,
            )
        if request.url.path == "/api/toplist/detail":
            return httpx.Response(
                200,
                json={
                    "code": 200,
                    "list": [
                        {
                            "id": 30,
                            "name": "Ranking",
                            "updateFrequency": "daily",
                            "trackCount": 1,
                            "tracks": [
                                {
                                    "first": {"id": 2, "name": "Similar"},
                                    "second": {"id": 10, "name": "Artist"},
                                }
                            ],
                        }
                    ],
                },
                request=request,
            )
        if request.url.path == "/api/song/like/get":
            return httpx.Response(200, json={"code": 200, "ids": [1]}, request=request)
        if request.url.path == "/api/song/detail/":
            return httpx.Response(
                200,
                json={
                    "code": 200,
                    "songs": [
                        {"id": 1, "name": "Liked", "artists": [{"id": 10, "name": "Artist"}]}
                    ],
                },
                request=request,
            )
        raise AssertionError(request.url.path)

    settings = Settings(cookie="MUSIC_U=test")
    authentication = AuthenticationProvider.from_settings(settings)
    client = NeteaseHttpClient(
        settings,
        authentication,
        transport=httpx.MockTransport(handler),
    )
    backend = NeteaseWebBackend(client, authentication)
    try:
        recommendation = await backend.get_recommendations(PageRequest(page=1, page_size=1))
        similar = await backend.get_similar_songs("1", PageRequest(page=1, page_size=1))
        releases = await backend.get_new_songs(ReleaseArea.ALL, PageRequest(page=1, page_size=1))
        rankings = await backend.get_rankings(PageRequest(page=1, page_size=1))
        liked = await backend.get_user_library(
            LibrarySection.LIKED_SONGS,
            "99",
            PageRequest(page=1, page_size=1),
            HistoryScope.WEEK,
        )
    finally:
        await backend.close()

    assert recommendation.items[0].id == "30"
    assert similar.items[0].id == "2"
    assert releases.items[0].id == "20"
    assert rankings.items[0].top_tracks[0].artist == "Artist"
    assert liked.items[0].id == "1"
    assert seen_paths == [
        "/api/personalized/playlist",
        "/api/v1/discovery/simiSong",
        "/api/personalized/newsong",
        "/api/toplist/detail",
        "/api/song/like/get",
        "/api/song/detail/",
    ]
