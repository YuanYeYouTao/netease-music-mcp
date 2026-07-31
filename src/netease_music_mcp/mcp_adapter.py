from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Protocol

import anyio
from mcp.server.mcpserver import MCPServer
from starlette.applications import Starlette

from netease_music_mcp import __version__
from netease_music_mcp.application import MusicApplication
from netease_music_mcp.config import Settings
from netease_music_mcp.tools import register_all_resources, register_all_tools


class MCPServerAdapter(Protocol):
    def register_tools(self, application: MusicApplication) -> None: ...

    def register_resources(self, application: MusicApplication) -> None: ...

    def run_stdio(self) -> None: ...

    def run_streamable_http(self) -> None: ...

    def streamable_http_app(self) -> Starlette: ...


class MCPV2ServerAdapter:
    def __init__(self, application: MusicApplication, settings: Settings) -> None:
        self.application = application
        self.settings = settings
        self.mcp: MCPServer[object] = MCPServer(
            name="netease-music-mcp",
            instructions=(
                "Structured NetEase Cloud Music metadata with optional, "
                "explicitly confirmed account writes."
            ),
            version=__version__,
            log_level=settings.log_level,
        )
        self.register_tools(application)
        self.register_resources(application)

    def register_tools(self, application: MusicApplication) -> None:
        register_all_tools(self.mcp, application)

    def register_resources(self, application: MusicApplication) -> None:
        register_all_resources(self.mcp, application)

    def run_stdio(self) -> None:
        anyio.run(self._run_stdio)

    async def _run_stdio(self) -> None:
        try:
            await self.mcp.run_stdio_async()
        finally:
            await self.application.close()

    def streamable_http_app(self) -> Starlette:
        """Build HTTP transport with process-owned application resources."""

        app = self.mcp.streamable_http_app(
            streamable_http_path=self.settings.mcp_path,
            json_response=True,
            stateless_http=True,
            host=self.settings.mcp_host,
        )
        session_manager_lifespan = app.router.lifespan_context

        @asynccontextmanager
        async def lifespan(starlette_app: Starlette) -> AsyncIterator[None]:
            async with session_manager_lifespan(starlette_app):
                try:
                    yield
                finally:
                    await self.application.close()

        app.router.lifespan_context = lifespan
        return app

    def run_streamable_http(self) -> None:
        import uvicorn

        uvicorn.run(
            self.streamable_http_app(),
            host=self.settings.mcp_host,
            port=self.settings.mcp_port,
            log_level=self.settings.log_level.lower(),
        )


# Keep the old import name available to callers that used the 0.x adapter.
MCPV1ServerAdapter = MCPV2ServerAdapter
