import asyncio
from collections.abc import Mapping
from typing import Any

import httpx

from netease_music_mcp.config import Settings
from netease_music_mcp.domain.errors import (
    RateLimitedError,
    ResourceNotFoundError,
    UpstreamResponseError,
    UpstreamUnavailableError,
)

from .authentication import AuthenticationProvider

JsonObject = dict[str, Any]


class NeteaseHttpClient:
    """One shared async client with retry and provider-error normalization."""

    BASE_URL = "https://music.163.com"

    def __init__(
        self,
        settings: Settings,
        authentication: AuthenticationProvider,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        headers = {
            "User-Agent": "netease-music-mcp/0.1.0 (+read-only MCP data client)",
            "Referer": "https://music.163.com/",
            "Accept": "application/json",
        }
        cookie = authentication.cookie_header()
        if cookie:
            headers["Cookie"] = cookie
        timeout = httpx.Timeout(
            settings.request_timeout_seconds,
            connect=settings.connect_timeout_seconds,
        )
        limits = httpx.Limits(
            max_connections=settings.max_connections,
            max_keepalive_connections=settings.max_keepalive_connections,
        )
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers=headers,
            timeout=timeout,
            limits=limits,
            follow_redirects=True,
            transport=transport,
        )
        self._retry_attempts = settings.retry_attempts
        self._retry_initial_seconds: float = settings.retry_initial_seconds

    async def request_json(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, str | int] | None = None,
        data: Mapping[str, str | int] | None = None,
    ) -> JsonObject:
        response: httpx.Response | None = None
        for attempt in range(self._retry_attempts + 1):
            try:
                response = await self._client.request(method, path, params=params, data=data)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt >= self._retry_attempts:
                    raise UpstreamUnavailableError("NetEase request failed") from exc
                await asyncio.sleep(self._backoff(attempt))
                continue
            if response.status_code == 429 or response.status_code >= 500:
                if attempt < self._retry_attempts:
                    await asyncio.sleep(self._backoff(attempt))
                    continue
            break

        if response is None:
            raise UpstreamUnavailableError("NetEase request failed")
        if response.status_code == 404:
            raise ResourceNotFoundError("NetEase resource was not found")
        if response.status_code == 429:
            raise RateLimitedError("NetEase rate limit reached")
        if response.status_code >= 500:
            raise UpstreamUnavailableError("NetEase service is unavailable")
        if response.is_error:
            raise UpstreamResponseError(
                f"NetEase returned unexpected HTTP status {response.status_code}"
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise UpstreamResponseError("NetEase returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise UpstreamResponseError("NetEase returned a non-object JSON response")
        return payload

    def _backoff(self, attempt: int) -> float:
        return float(self._retry_initial_seconds * (2**attempt))

    async def close(self) -> None:
        await self._client.aclose()
