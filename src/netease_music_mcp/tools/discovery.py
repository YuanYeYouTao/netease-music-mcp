from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from netease_music_mcp.application import MusicApplication
from netease_music_mcp.domain.enums import ReleaseArea
from netease_music_mcp.domain.models import (
    NewSongsPage,
    RankingPage,
    RecommendationPage,
    SimilarSongsPage,
)

from .common import translate_music_errors


def register(server: MCPServer[object], application: MusicApplication) -> None:
    @server.tool(
        name="get_recommendations",
        description="Read a page of NetEase's read-only recommended playlists.",
        structured_output=True,
    )
    @translate_music_errors
    async def get_recommendations(
        page: Annotated[int, Field(description="One-based result page.")] = 1,
        page_size: Annotated[
            int | None, Field(description="Items per page; uses configured default when omitted.")
        ] = None,
    ) -> RecommendationPage:
        return await application.get_recommendations(page, page_size)

    @server.tool(
        name="get_similar_songs",
        description="Read a page of songs similar to one NetEase song.",
        structured_output=True,
    )
    @translate_music_errors
    async def get_similar_songs(
        song_id: Annotated[str, Field(description="NetEase song ID.")],
        page: Annotated[int, Field(description="One-based result page.")] = 1,
        page_size: Annotated[
            int | None, Field(description="Items per page; uses configured default when omitted.")
        ] = None,
    ) -> SimilarSongsPage:
        return await application.get_similar_songs(song_id, page, page_size)

    @server.tool(
        name="get_new_songs",
        description="Read a page of recommended new songs by region.",
        structured_output=True,
    )
    @translate_music_errors
    async def get_new_songs(
        area: Annotated[ReleaseArea, Field(description="Release region filter.")] = ReleaseArea.ALL,
        page: Annotated[int, Field(description="One-based result page.")] = 1,
        page_size: Annotated[
            int | None, Field(description="Items per page; uses configured default when omitted.")
        ] = None,
    ) -> NewSongsPage:
        return await application.get_new_songs(area, page, page_size)

    @server.tool(
        name="get_rankings",
        description="Read a page of NetEase ranking boards with compact top tracks.",
        structured_output=True,
    )
    @translate_music_errors
    async def get_rankings(
        page: Annotated[int, Field(description="One-based result page.")] = 1,
        page_size: Annotated[
            int | None, Field(description="Items per page; uses configured default when omitted.")
        ] = None,
    ) -> RankingPage:
        return await application.get_rankings(page, page_size)
