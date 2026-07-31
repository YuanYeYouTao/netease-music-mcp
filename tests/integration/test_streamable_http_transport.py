import asyncio
import json

import httpx
import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from netease_music_mcp.config import Settings
from netease_music_mcp.server import create_server


@pytest.mark.asyncio
async def test_streamable_http_initialize_list_and_call() -> None:
    adapter = create_server(Settings(backend="fake", cache_backend="none"))
    app = adapter.streamable_http_app()

    async with asyncio.timeout(30):
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://127.0.0.1:8766",
            ) as http_client:
                for _ in range(2):
                    async with streamable_http_client(
                        "http://127.0.0.1:8766/mcp", http_client=http_client
                    ) as (read, write, _get_session_id):
                        async with ClientSession(read, write) as session:
                            initialized = await session.initialize()
                            tools = await session.list_tools()
                            resource_templates = await session.list_resource_templates()
                            playlist = await session.read_resource("netease://playlist/30")
                            assert getattr(adapter.application.backend, "closed", False) is False
                            result = await session.call_tool(
                                "get_playlist",
                                {"playlist_id": "30", "include_tracks": False},
                            )
                            assert initialized.serverInfo.name == "netease-music-mcp"
                            assert len(tools.tools) == 15
                            assert len(resource_templates.resourceTemplates) == 4
                            assert (
                                json.loads(playlist.contents[0].text)["playlist"]["id"] == "30"  # type: ignore[union-attr]
                            )
                            assert result.isError is False
                            assert result.structuredContent is not None
                            assert getattr(adapter.application.backend, "closed", False) is False
    assert getattr(adapter.application.backend, "closed", False) is True
