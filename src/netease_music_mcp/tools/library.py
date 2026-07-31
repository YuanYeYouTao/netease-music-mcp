from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from netease_music_mcp.application import MusicApplication
from netease_music_mcp.domain.enums import HistoryScope, LibrarySection
from netease_music_mcp.domain.models import UserLibraryPage

from .common import translate_music_errors


def register(server: MCPServer[object], application: MusicApplication) -> None:
    @server.tool(
        name="get_user_library",
        description="Read one authenticated, paginated section of a user's music library.",
        structured_output=True,
    )
    @translate_music_errors
    async def get_user_library(
        section: Annotated[LibrarySection, Field(description="Private library section.")],
        user_id: Annotated[
            str | None, Field(description="User ID; configured current user is used when omitted.")
        ] = None,
        page: Annotated[int, Field(description="One-based result page.")] = 1,
        page_size: Annotated[
            int | None, Field(description="Items per page; uses configured default when omitted.")
        ] = None,
        history_scope: Annotated[
            HistoryScope, Field(description="Playback-history time scope.")
        ] = HistoryScope.WEEK,
    ) -> UserLibraryPage:
        return await application.get_user_library(section, user_id, page, page_size, history_scope)
