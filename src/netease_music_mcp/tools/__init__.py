"""Registration of the eight public MCP tools."""

from mcp.server.fastmcp import FastMCP

from netease_music_mcp.application import MusicApplication

from . import catalog, library, lyrics, search, statistics


def register_all_tools(server: FastMCP[object], application: MusicApplication) -> None:
    search.register(server, application)
    catalog.register(server, application)
    lyrics.register(server, application)
    library.register(server, application)
    statistics.register(server, application)


__all__ = ["register_all_tools"]
