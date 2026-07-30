import httpx
import pytest

from netease_music_mcp.clients.authentication import AuthenticationProvider
from netease_music_mcp.clients.http import NeteaseHttpClient
from netease_music_mcp.config import Settings
from netease_music_mcp.domain.errors import (
    RateLimitedError,
    ResourceNotFoundError,
    UpstreamResponseError,
    UpstreamUnavailableError,
)


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
