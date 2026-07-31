from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from netease_music_mcp.application import MusicApplication
from netease_music_mcp.domain.enums import PlaylistTrackOperation
from netease_music_mcp.domain.models import WriteResult

from .common import translate_music_errors


def register(server: MCPServer[object], application: MusicApplication) -> None:
    @server.tool(
        name="create_playlist",
        description="Create a NetEase playlist after explicit confirmation.",
        structured_output=True,
    )
    @translate_music_errors
    async def create_playlist(
        name: Annotated[str, Field(description="New playlist name.")],
        private: Annotated[bool, Field(description="Create a private playlist.")] = False,
        confirm: Annotated[bool, Field(description="Must be true to change the account.")] = False,
    ) -> WriteResult:
        return await application.create_playlist(name, private, confirm)

    @server.tool(
        name="update_playlist_tracks",
        description="Add or remove songs from a NetEase playlist after confirmation.",
        structured_output=True,
    )
    @translate_music_errors
    async def update_playlist_tracks(
        playlist_id: Annotated[str, Field(description="NetEase playlist ID.")],
        operation: Annotated[PlaylistTrackOperation, Field(description="Add or remove the songs.")],
        song_ids: Annotated[tuple[str, ...], Field(description="NetEase song IDs.")],
        confirm: Annotated[bool, Field(description="Must be true to change the account.")] = False,
    ) -> WriteResult:
        return await application.update_playlist_tracks(playlist_id, operation, song_ids, confirm)

    @server.tool(
        name="set_song_like",
        description="Like or unlike one NetEase song after explicit confirmation.",
        structured_output=True,
    )
    @translate_music_errors
    async def set_song_like(
        song_id: Annotated[str, Field(description="NetEase song ID.")],
        liked: Annotated[bool, Field(description="True to like, false to unlike.")] = True,
        confirm: Annotated[bool, Field(description="Must be true to change the account.")] = False,
    ) -> WriteResult:
        return await application.set_song_like(song_id, liked, confirm)
