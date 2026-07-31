"""Registration of public MCP tools and resources."""

from mcp.server.fastmcp import FastMCP

from netease_music_mcp.application import MusicApplication

from . import catalog, discovery, library, lyrics, resources, search, statistics, writes


def register_all_tools(server: FastMCP[object], application: MusicApplication) -> None:
    search.register(server, application)
    discovery.register(server, application)
    catalog.register(server, application)
    lyrics.register(server, application)
    library.register(server, application)
    statistics.register(server, application)
    writes.register(server, application)


def register_all_resources(server: FastMCP[object], application: MusicApplication) -> None:
    resources.register(server, application)


__all__ = ["register_all_resources", "register_all_tools"]
