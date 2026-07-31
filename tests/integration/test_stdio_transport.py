import asyncio
import json
import os
from typing import Literal

import pytest
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["auto", "legacy"])
async def test_stdio_compatibility_modes(mode: Literal["auto", "legacy"]) -> None:
    environment = {
        **os.environ,
        "NETEASE_BACKEND": "fake",
        "NETEASE_CACHE_BACKEND": "none",
    }
    parameters = StdioServerParameters(
        command="uv",
        args=["run", "netease-music-mcp", "serve", "--transport", "stdio"],
        env=environment,
        cwd=os.getcwd(),
    )
    async with asyncio.timeout(30):
        async with Client(stdio_client(parameters), mode=mode) as client:
            tools = await client.list_tools()
            resource_templates = await client.list_resource_templates()
            song = await client.read_resource("netease://song/1")
            result = await client.call_tool(
                "music_search", {"query": "Example", "category": "song"}
            )
            error = await client.call_tool("music_search", {"query": " ", "category": "song"})
            assert client.server_info is not None
            assert client.server_info.name == "netease-music-mcp"
            assert client.server_info.version == "1.0.0"
            assert len(tools.tools) == 15
            assert len(resource_templates.resource_templates) == 4
            assert json.loads(song.contents[0].text)["id"] == "1"
            assert result.is_error is False
            assert result.structured_content is not None
            assert error.is_error is True
            assert "invalid_request" in error.content[0].text  # type: ignore[union-attr]
