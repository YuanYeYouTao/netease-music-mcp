import asyncio
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
                result = await session.call_tool(
                    "music_search", {"query": "Example", "category": "song"}
                )
                error = await session.call_tool("music_search", {"query": " ", "category": "song"})
                assert initialized.serverInfo.name == "netease-music-mcp"
                assert len(tools.tools) == 8
                assert result.isError is False
                assert result.structuredContent is not None
                assert error.isError is True
                assert "invalid_request" in error.content[0].text  # type: ignore[union-attr]
