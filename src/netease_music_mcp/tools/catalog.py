from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from netease_music_mcp.application import MusicApplication
from netease_music_mcp.domain.enums import DetailLevel
from netease_music_mcp.domain.models import (
    AlbumDetail,
    ArtistDetail,
    GetSongsResult,
    PlaylistDetail,
)

from .common import translate_music_errors


def register(server: MCPServer[object], application: MusicApplication) -> None:
    @server.tool(
        name="get_songs",
        description="Fetch metadata for multiple songs in one call while preserving input order.",
        structured_output=True,
    )
    @translate_music_errors
    async def get_songs(
        song_ids: Annotated[tuple[str, ...], Field(description="NetEase song IDs.")],
        detail_level: Annotated[
            DetailLevel, Field(description="Summary or scalar-rich song metadata.")
        ] = DetailLevel.SUMMARY,
    ) -> GetSongsResult:
        return await application.get_songs(song_ids, detail_level)

    @server.tool(
        name="get_album",
        description="Fetch album metadata and optionally one page of tracks.",
        structured_output=True,
    )
    @translate_music_errors
    async def get_album(
        album_id: Annotated[str, Field(description="NetEase album ID.")],
        include_tracks: Annotated[
            bool, Field(description="Whether to include a page of album tracks.")
        ] = False,
        track_page: Annotated[int, Field(description="One-based track page.")] = 1,
        track_page_size: Annotated[
            int | None, Field(description="Tracks per page; uses configured default when omitted.")
        ] = None,
    ) -> AlbumDetail:
        return await application.get_album(album_id, include_tracks, track_page, track_page_size)

    @server.tool(
        name="get_artist",
        description="Fetch artist metadata and optionally a bounded list of top songs.",
        structured_output=True,
    )
    @translate_music_errors
    async def get_artist(
        artist_id: Annotated[str, Field(description="NetEase artist ID.")],
        include_top_songs: Annotated[
            bool, Field(description="Whether to include top songs.")
        ] = False,
        top_song_count: Annotated[
            int | None, Field(description="Top-song count; uses configured default when omitted.")
        ] = None,
    ) -> ArtistDetail:
        return await application.get_artist(artist_id, include_top_songs, top_song_count)

    @server.tool(
        name="get_playlist",
        description="Fetch playlist metadata and optionally one bounded page of tracks.",
        structured_output=True,
    )
    @translate_music_errors
    async def get_playlist(
        playlist_id: Annotated[str, Field(description="NetEase playlist ID.")],
        include_tracks: Annotated[
            bool, Field(description="Whether to include a page of tracks.")
        ] = False,
        track_page: Annotated[int, Field(description="One-based track page.")] = 1,
        track_page_size: Annotated[
            int | None, Field(description="Tracks per page; uses configured default when omitted.")
        ] = None,
    ) -> PlaylistDetail:
        return await application.get_playlist(
            playlist_id, include_tracks, track_page, track_page_size
        )
