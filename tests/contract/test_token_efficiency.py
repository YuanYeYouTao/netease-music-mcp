import json

import pytest
from mcp.types import CallToolResult

from netease_music_mcp.config import Settings
from netease_music_mcp.server import create_server


@pytest.mark.asyncio
async def test_schema_and_typical_results_remain_bounded() -> None:
    adapter = create_server(Settings(backend="fake", cache_backend="none"))
    tools = await adapter.mcp.list_tools()
    schema_characters = len(
        json.dumps(
            [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input": tool.input_schema,
                    "output": tool.output_schema,
                }
                for tool in tools
            ],
            separators=(",", ":"),
        )
    )
    search = await adapter.mcp.call_tool(
        "music_search", {"query": "Example", "category": "song", "page_size": 2}
    )
    detail = await adapter.mcp.call_tool("get_songs", {"song_ids": ["1"], "detail_level": "full"})
    playlist = await adapter.mcp.call_tool(
        "get_playlist",
        {"playlist_id": "30", "include_tracks": True, "track_page_size": 2},
    )
    lyrics = await adapter.mcp.call_tool("get_lyrics", {"song_id": "1", "limit": 2})
    assert isinstance(search, CallToolResult)
    assert isinstance(detail, CallToolResult)
    assert isinstance(playlist, CallToolResult)
    assert isinstance(lyrics, CallToolResult)
    assert schema_characters < 45_000
    assert len(json.dumps(search.structured_content, default=str)) < 3_000
    assert len(json.dumps(detail.structured_content, default=str)) < 2_000
    assert len(json.dumps(playlist.structured_content, default=str)) < 4_000
    assert len(json.dumps(lyrics.structured_content, default=str)) < 2_000
    assert all(len(result.content[0].text) < 80 for result in (search, detail, playlist, lyrics))  # type: ignore[union-attr]
