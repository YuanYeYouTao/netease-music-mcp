import asyncio
import json
from typing import Literal

import httpx2
import pytest
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from netease_music_mcp.config import Settings
from netease_music_mcp.server import create_server


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["auto", "legacy"])
async def test_streamable_http_compatibility_modes(mode: Literal["auto", "legacy"]) -> None:
    adapter = create_server(Settings(backend="fake", cache_backend="none"))
    app = adapter.streamable_http_app()

    async with asyncio.timeout(30):
        async with app.router.lifespan_context(app):
            async with httpx2.AsyncClient(
                transport=httpx2.ASGITransport(app=app),
                base_url="http://127.0.0.1:8766",
            ) as http_client:
                for _ in range(2):
                    async with Client(
                        streamable_http_client(
                            "http://127.0.0.1:8766/mcp", http_client=http_client
                        ),
                        mode=mode,
                    ) as client:
                        tools = await client.list_tools()
                        resource_templates = await client.list_resource_templates()
                        playlist = await client.read_resource("netease://playlist/30")
                        assert getattr(adapter.application.backend, "closed", False) is False
                        result = await client.call_tool(
                            "get_playlist",
                            {"playlist_id": "30", "include_tracks": False},
                        )
                        assert client.server_info is not None
                        assert client.server_info.name == "netease-music-mcp"
                        assert client.server_info.version == "1.0.0"
                        assert len(tools.tools) == 15
                        assert len(resource_templates.resource_templates) == 4
                        assert json.loads(playlist.contents[0].text)["playlist"]["id"] == "30"
                        assert result.is_error is False
                        assert result.structured_content is not None
                        assert getattr(adapter.application.backend, "closed", False) is False
    assert getattr(adapter.application.backend, "closed", False) is True
