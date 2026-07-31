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
    # NetEase's anonymous web endpoints silently return unrelated search
    # results to non-browser user agents while still reporting HTTP 200. Keep
    # this profile close to the web player so successful responses are useful.
    BROWSER_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/138.0.0.0 Safari/537.36"
    )

    def __init__(
        self,
        settings: Settings,
        authentication: AuthenticationProvider,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        headers = {
            "User-Agent": self.BROWSER_USER_AGENT,
            "Referer": "https://music.163.com/",
            "Accept": "application/json",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
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
