import json
from typing import Literal

import pytest
from jsonschema.validators import Draft202012Validator
from mcp import Client
from mcp.server.mcpserver.exceptions import ResourceError, ToolError
from mcp.types import CallToolResult

from netease_music_mcp.config import Settings
from netease_music_mcp.domain.models import (
    AlbumDetail,
    ArtistDetail,
    GetSongsResult,
    LyricsDocument,
    NewSongsPage,
    PlaylistDetail,
    PlaylistStatistics,
    RankingPage,
    RecommendationPage,
    SearchPage,
    SimilarSongsPage,
    SongDetail,
    WriteResult,
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
    "get_recommendations",
    "get_similar_songs",
    "get_new_songs",
    "get_rankings",
    "create_playlist",
    "update_playlist_tracks",
    "set_song_like",
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
            write_operations_enabled=True,
            cookie="MUSIC_U=test",
            user_id="99",
        )
    )


@pytest.mark.asyncio
async def test_tools_list_has_exactly_fifteen_valid_schemas() -> None:
    tools = await fake_adapter().mcp.list_tools()
    assert {tool.name for tool in tools} == EXPECTED_TOOLS
    assert len(tools) == 15
    for tool in tools:
        Draft202012Validator.check_schema(tool.input_schema)
        assert tool.output_schema is not None
        Draft202012Validator.check_schema(tool.output_schema)
        assert tool.description is not None and len(tool.description) <= 120


@pytest.mark.asyncio
async def test_tool_outputs_are_structured_and_model_valid() -> None:
    mcp = fake_adapter().mcp
    search = await mcp.call_tool("music_search", {"query": "Example", "category": "song"})
    songs = await mcp.call_tool("get_songs", {"song_ids": ["2", "404", "1"]})
    playlist = await mcp.call_tool("get_playlist", {"playlist_id": "30"})
    lyrics = await mcp.call_tool("get_lyrics", {"song_id": "1", "limit": 2})
    statistics = await mcp.call_tool("get_playlist_statistics", {"playlist_id": "30"})
    recommendations = await mcp.call_tool("get_recommendations", {"page_size": 1})
    similar = await mcp.call_tool("get_similar_songs", {"song_id": "1", "page_size": 1})
    releases = await mcp.call_tool("get_new_songs", {"page_size": 1})
    rankings = await mcp.call_tool("get_rankings", {"page_size": 1})
    created = await mcp.call_tool("create_playlist", {"name": "fixture", "confirm": True})
    added = await mcp.call_tool(
        "update_playlist_tracks",
        {"playlist_id": "30", "operation": "add", "song_ids": ["1"], "confirm": True},
    )
    liked = await mcp.call_tool("set_song_like", {"song_id": "1", "liked": True, "confirm": True})
    assert isinstance(search, CallToolResult)
    assert isinstance(songs, CallToolResult)
    assert isinstance(playlist, CallToolResult)
    assert isinstance(lyrics, CallToolResult)
    assert isinstance(statistics, CallToolResult)
    assert isinstance(recommendations, CallToolResult)
    assert isinstance(similar, CallToolResult)
    assert isinstance(releases, CallToolResult)
    assert isinstance(rankings, CallToolResult)
    assert isinstance(created, CallToolResult)
    assert isinstance(added, CallToolResult)
    assert isinstance(liked, CallToolResult)
    assert SearchPage.model_validate(search.structured_content)
    assert GetSongsResult.model_validate(songs.structured_content)
    assert PlaylistDetail.model_validate(playlist.structured_content)
    assert LyricsDocument.model_validate(lyrics.structured_content)
    assert PlaylistStatistics.model_validate(statistics.structured_content)
    assert RecommendationPage.model_validate(recommendations.structured_content)
    assert SimilarSongsPage.model_validate(similar.structured_content)
    assert NewSongsPage.model_validate(releases.structured_content)
    assert RankingPage.model_validate(rankings.structured_content)
    assert WriteResult.model_validate(created.structured_content)
    assert WriteResult.model_validate(added.structured_content)
    assert WriteResult.model_validate(liked.structured_content)
    for result in (
        search,
        songs,
        playlist,
        lyrics,
        statistics,
        recommendations,
        similar,
        releases,
        rankings,
        created,
        added,
        liked,
    ):
        assert len(result.content) == 1
        assert len(result.content[0].text) < 80  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_resource_templates_return_valid_bounded_details() -> None:
    mcp = fake_adapter().mcp
    templates = await mcp.list_resource_templates()
    assert {template.uri_template for template in templates} == EXPECTED_RESOURCE_TEMPLATES
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
    with pytest.raises(ResourceError) as captured:
        await fake_adapter().mcp.read_resource("netease://song/404")
    assert json.loads(str(captured.value)) == {
        "error_code": "not_found",
        "message": "song 404 was not found",
        "retryable": False,
    }


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


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["auto", "legacy"])
async def test_in_memory_client_compatibility(mode: Literal["auto", "legacy"]) -> None:
    adapter = fake_adapter()
    try:
        async with Client(adapter.mcp, mode=mode) as client:
            assert client.server_info is not None
            assert client.server_info.version == "1.0.0"
            result = await client.call_tool(
                "music_search", {"query": "Example", "category": "song"}
            )
            resource = await client.read_resource("netease://song/1")
            assert result.is_error is False
            assert SearchPage.model_validate(result.structured_content)
            assert resource.contents[0].mime_type == "application/json"
    finally:
        await adapter.application.close()
