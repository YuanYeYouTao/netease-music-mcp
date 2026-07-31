import asyncio
import json
import os

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@pytest.mark.asyncio
async def test_stdio_initialize_list_and_call() -> None:
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
        async with stdio_client(parameters) as (read, write):
            async with ClientSession(read, write) as session:
                initialized = await session.initialize()
                tools = await session.list_tools()
                resource_templates = await session.list_resource_templates()
                song = await session.read_resource("netease://song/1")
                result = await session.call_tool(
                    "music_search", {"query": "Example", "category": "song"}
                )
                error = await session.call_tool("music_search", {"query": " ", "category": "song"})
                assert initialized.serverInfo.name == "netease-music-mcp"
                assert len(tools.tools) == 15
                assert len(resource_templates.resourceTemplates) == 4
                assert json.loads(song.contents[0].text)["id"] == "1"  # type: ignore[union-attr]
                assert result.isError is False
                assert result.structuredContent is not None
                assert error.isError is True
                assert "invalid_request" in error.content[0].text  # type: ignore[union-attr]
