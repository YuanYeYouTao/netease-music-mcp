import json

import pytest
from jsonschema.validators import Draft202012Validator
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import CallToolResult

from netease_music_mcp.config import Settings
from netease_music_mcp.domain.models import (
    GetSongsResult,
    LyricsDocument,
    PlaylistDetail,
    PlaylistStatistics,
    SearchPage,
)
from netease_music_mcp.server import create_server

EXPECTED_TOOLS = {
    "music_search",
    "get_songs",
    "get_album",
    "get_artist",
    "get_playlist",
    "get_lyrics",
    "get_user_library",
    "get_playlist_statistics",
}


def fake_adapter():
    return create_server(
        Settings(
            backend="fake",
            cache_backend="none",
            cookie="MUSIC_U=test",
            user_id="99",
        )
    )


@pytest.mark.asyncio
async def test_tools_list_has_exactly_eight_valid_schemas() -> None:
    tools = await fake_adapter().mcp.list_tools()
    assert {tool.name for tool in tools} == EXPECTED_TOOLS
    assert len(tools) == 8
    for tool in tools:
        Draft202012Validator.check_schema(tool.inputSchema)
        assert tool.outputSchema is not None
        Draft202012Validator.check_schema(tool.outputSchema)
        assert tool.description is not None and len(tool.description) <= 120


@pytest.mark.asyncio
async def test_tool_outputs_are_structured_and_model_valid() -> None:
    mcp = fake_adapter().mcp
    search = await mcp.call_tool("music_search", {"query": "Example", "category": "song"})
    songs = await mcp.call_tool("get_songs", {"song_ids": ["2", "404", "1"]})
    playlist = await mcp.call_tool("get_playlist", {"playlist_id": "30"})
    lyrics = await mcp.call_tool("get_lyrics", {"song_id": "1", "limit": 2})
    statistics = await mcp.call_tool("get_playlist_statistics", {"playlist_id": "30"})
    assert isinstance(search, CallToolResult)
    assert isinstance(songs, CallToolResult)
    assert isinstance(playlist, CallToolResult)
    assert isinstance(lyrics, CallToolResult)
    assert isinstance(statistics, CallToolResult)
    assert SearchPage.model_validate(search.structuredContent)
    assert GetSongsResult.model_validate(songs.structuredContent)
    assert PlaylistDetail.model_validate(playlist.structuredContent)
    assert LyricsDocument.model_validate(lyrics.structuredContent)
    assert PlaylistStatistics.model_validate(statistics.structuredContent)
    for result in (search, songs, playlist, lyrics, statistics):
        assert len(result.content) == 1
        assert len(result.content[0].text) < 80  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_tool_errors_preserve_structured_error_fields() -> None:
    with pytest.raises(ToolError) as captured:
        await fake_adapter().mcp.call_tool("music_search", {"query": " ", "category": "song"})
    payload = json.loads(str(captured.value)[str(captured.value).index("{") :])
    assert payload == {
        "error_code": "invalid_request",
        "message": "query cannot be empty",
        "retryable": False,
    }


@pytest.mark.asyncio
async def test_server_instructions_are_compact() -> None:
    instructions = fake_adapter().mcp.instructions
    assert instructions is not None
    assert len(instructions) <= 100
