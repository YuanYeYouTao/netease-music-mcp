from mcp.server.fastmcp import FastMCP

from netease_music_mcp.application import MusicApplication
from netease_music_mcp.domain.enums import DetailLevel
from netease_music_mcp.domain.errors import ResourceNotFoundError


def register(server: FastMCP[object], application: MusicApplication) -> None:
    @server.resource(
        "netease://song/{id}",
        name="song",
        description="Full metadata for one NetEase song.",
        mime_type="application/json",
    )
    async def song(id: str) -> str:
        result = await application.get_songs((id,), DetailLevel.FULL)
        if not result.songs:
            raise ResourceNotFoundError(f"song {id} was not found")
        return result.songs[0].model_dump_json(indent=2)

    @server.resource(
        "netease://album/{id}",
        name="album",
        description="Metadata for one NetEase album without its track list.",
        mime_type="application/json",
    )
    async def album(id: str) -> str:
        return (await application.get_album(id)).model_dump_json(indent=2)

    @server.resource(
        "netease://artist/{id}",
        name="artist",
        description="Metadata for one NetEase artist without top songs.",
        mime_type="application/json",
    )
    async def artist(id: str) -> str:
        return (await application.get_artist(id)).model_dump_json(indent=2)

    @server.resource(
        "netease://playlist/{id}",
        name="playlist",
        description="Metadata for one NetEase playlist without its track list.",
        mime_type="application/json",
    )
    async def playlist(id: str) -> str:
        return (await application.get_playlist(id)).model_dump_json(indent=2)
