from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from netease_music_mcp.application import MusicApplication
from netease_music_mcp.domain.models import PlaylistStatistics

from .common import translate_music_errors


def register(server: MCPServer[object], application: MusicApplication) -> None:
    @server.tool(
        name="get_playlist_statistics",
        description=(
            "Compute deterministic duration, artist, album, year, and availability statistics."
        ),
        structured_output=True,
    )
    @translate_music_errors
    async def get_playlist_statistics(
        playlist_id: Annotated[str, Field(description="NetEase playlist ID.")],
        track_limit: Annotated[
            int | None,
            Field(description="Maximum analyzed tracks; uses configured maximum when omitted."),
        ] = None,
    ) -> PlaylistStatistics:
        return await application.get_playlist_statistics(playlist_id, track_limit)
