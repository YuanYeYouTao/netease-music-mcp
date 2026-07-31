import json

import pytest
from jsonschema.validators import Draft202012Validator
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import CallToolResult

from netease_music_mcp.config import Settings
from netease_music_mcp.domain.models import (
    AlbumDetail,
    ArtistDetail,
    GetSongsResult,
    LyricsDocument,
    PlaylistDetail,
    PlaylistStatistics,
    SearchPage,
    SongDetail,
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
EXPECTED_RESOURCE_TEMPLATES = {
    "netease://song/{id}",
    "netease://album/{id}",
    "netease://artist/{id}",
    "netease://playlist/{id}",
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
async def test_resource_templates_return_valid_bounded_details() -> None:
    mcp = fake_adapter().mcp
    templates = await mcp.list_resource_templates()
    assert {template.uriTemplate for template in templates} == EXPECTED_RESOURCE_TEMPLATES
    assert await mcp.list_resources() == []

    song = next(iter(await mcp.read_resource("netease://song/1")))
    album = next(iter(await mcp.read_resource("netease://album/20")))
    artist = next(iter(await mcp.read_resource("netease://artist/10")))
    playlist = next(iter(await mcp.read_resource("netease://playlist/30")))

    assert SongDetail.model_validate_json(song.content)
    assert AlbumDetail.model_validate_json(album.content).tracks == ()
    assert ArtistDetail.model_validate_json(artist.content).top_songs == ()
    assert PlaylistDetail.model_validate_json(playlist.content).tracks == ()
    assert all(
        resource.mime_type == "application/json" for resource in (song, album, artist, playlist)
    )


@pytest.mark.asyncio
async def test_missing_song_resource_is_an_error() -> None:
    with pytest.raises(ValueError, match="song 404 was not found"):
        await fake_adapter().mcp.read_resource("netease://song/404")


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
