import os

import pytest

from netease_music_mcp.config import Settings
from netease_music_mcp.domain.enums import SearchCategory
from netease_music_mcp.lifespan import create_application


@pytest.mark.netease_integration
@pytest.mark.asyncio
async def test_live_read_only_search() -> None:
    if os.getenv("NETEASE_INTEGRATION_ENABLED", "").casefold() != "true":
        pytest.skip("set NETEASE_INTEGRATION_ENABLED=true to run live read-only tests")
    application = create_application(Settings())
    try:
        result = await application.music_search("test", SearchCategory.SONG, page_size=1)
        assert result.items
    finally:
        await application.close()
