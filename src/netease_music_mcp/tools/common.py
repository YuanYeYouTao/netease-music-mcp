import functools
from collections.abc import Awaitable, Callable
from typing import cast

from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import CallToolResult, TextContent
from pydantic import BaseModel

from netease_music_mcp.domain.errors import MusicMCPError


def translate_music_errors[**P, R](
    function: Callable[P, Awaitable[R]],
) -> Callable[P, Awaitable[R]]:
    """Translate domain failures once at the MCP boundary."""

    @functools.wraps(function)
    async def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            result = await function(*args, **kwargs)
        except MusicMCPError as exc:
            raise ToolError(exc.to_payload().model_dump_json()) from exc
        if isinstance(result, BaseModel):
            return cast(
                R,
                CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"{type(result).__name__} returned as structured content.",
                        )
                    ],
                    structuredContent=result.model_dump(mode="json"),
                ),
            )
        return result

    return wrapped
