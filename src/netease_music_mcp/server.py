from mcp.server.fastmcp import FastMCP

from netease_music_mcp.config import Settings
from netease_music_mcp.lifespan import create_application
from netease_music_mcp.mcp_adapter import MCPV1ServerAdapter


def create_server(settings: Settings | None = None) -> MCPV1ServerAdapter:
    resolved = settings or Settings()
    return MCPV1ServerAdapter(create_application(resolved), resolved)


def create_fastmcp(settings: Settings | None = None) -> FastMCP[object]:
    return create_server(settings).mcp


mcp = create_fastmcp()


if __name__ == "__main__":
    mcp.run()
