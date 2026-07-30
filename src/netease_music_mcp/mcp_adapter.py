from typing import Protocol

from mcp.server.fastmcp import FastMCP

from netease_music_mcp.application import MusicApplication
from netease_music_mcp.config import Settings
from netease_music_mcp.lifespan import application_lifespan
from netease_music_mcp.tools import register_all_tools


class MCPServerAdapter(Protocol):
    def register_tools(self, application: MusicApplication) -> None: ...

    def run_stdio(self) -> None: ...

    def run_streamable_http(self) -> None: ...


class MCPV1ServerAdapter:
    def __init__(self, application: MusicApplication, settings: Settings) -> None:
        self.application = application
        self.settings = settings
        self.mcp: FastMCP[object] = FastMCP(
            "netease-music-mcp",
            instructions="Read-only structured NetEase Cloud Music metadata.",
            host=settings.mcp_host,
            port=settings.mcp_port,
            streamable_http_path=settings.mcp_path,
            stateless_http=True,
            json_response=True,
            log_level=settings.log_level,
            lifespan=application_lifespan(application),
        )
        self.register_tools(application)

    def register_tools(self, application: MusicApplication) -> None:
        register_all_tools(self.mcp, application)

    def run_stdio(self) -> None:
        self.mcp.run(transport="stdio")

    def run_streamable_http(self) -> None:
        self.mcp.run(transport="streamable-http")
