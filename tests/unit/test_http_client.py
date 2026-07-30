import httpx
import pytest

from netease_music_mcp.backends.netease_web import NeteaseWebBackend
from netease_music_mcp.clients.authentication import AuthenticationProvider
from netease_music_mcp.clients.http import NeteaseHttpClient
from netease_music_mcp.config import Settings
from netease_music_mcp.domain.enums import DetailLevel, SearchCategory
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
