from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from netease_music_mcp.application import MusicApplication
from netease_music_mcp.domain.enums import DetailLevel, SearchCategory
from netease_music_mcp.domain.models import SearchPage

from .common import translate_music_errors


def register(server: MCPServer[object], application: MusicApplication) -> None:
    @server.tool(
        name="music_search",
        description="Search songs, artists, albums, or playlists with compact paginated results.",
        structured_output=True,
    )
    @translate_music_errors
    async def music_search(
        query: Annotated[str, Field(description="Non-empty search text.")],
        category: Annotated[SearchCategory, Field(description="Music entity category.")],
        page: Annotated[int, Field(description="One-based result page.")] = 1,
        page_size: Annotated[
            int | None,
            Field(description="Items per page; the configured default is used when omitted."),
        ] = None,
        detail_level: Annotated[
            DetailLevel, Field(description="Requested result detail; summary is token-efficient.")
        ] = DetailLevel.SUMMARY,
    ) -> SearchPage:
        return await application.music_search(query, category, page, page_size, detail_level)
