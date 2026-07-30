from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from netease_music_mcp.application import MusicApplication
from netease_music_mcp.domain.models import LyricsDocument

from .common import translate_music_errors


def register(server: FastMCP[object], application: MusicApplication) -> None:
    @server.tool(
        name="get_lyrics",
        description=(
            "Fetch a bounded lyric page with optional aligned translation and romanization."
        ),
        structured_output=True,
    )
    @translate_music_errors
    async def get_lyrics(
        song_id: Annotated[str, Field(description="NetEase song ID.")],
        include_translation: Annotated[
            bool, Field(description="Include aligned translated text when available.")
        ] = True,
        include_romanization: Annotated[
            bool, Field(description="Include aligned romanized text when available.")
        ] = False,
        offset: Annotated[int, Field(description="Zero-based lyric-line offset.")] = 0,
        limit: Annotated[
            int | None,
            Field(description="Maximum lyric lines; uses configured default when omitted."),
        ] = None,
    ) -> LyricsDocument:
        return await application.get_lyrics(
            song_id, include_translation, include_romanization, offset, limit
        )
