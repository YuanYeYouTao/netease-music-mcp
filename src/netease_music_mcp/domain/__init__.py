"""Transport-independent music domain."""

from .enums import (
    AuthenticationState,
    DetailLevel,
    HistoryScope,
    LibrarySection,
    SearchCategory,
)
from .models import (
    AlbumDetail,
    AlbumSummary,
    ArtistDetail,
    ArtistSummary,
    GetSongsResult,
    LyricsDocument,
    LyricsLine,
    PlaylistDetail,
    PlaylistStatistics,
    PlaylistSummary,
    SearchPage,
    SongDetail,
    SongSummary,
    UserLibraryPage,
)
from .pagination import PageInfo, PageRequest

__all__ = [
    "AlbumDetail",
    "AlbumSummary",
    "ArtistDetail",
    "ArtistSummary",
    "AuthenticationState",
    "DetailLevel",
    "GetSongsResult",
    "HistoryScope",
    "LibrarySection",
    "LyricsDocument",
    "LyricsLine",
    "PageInfo",
    "PageRequest",
    "PlaylistDetail",
    "PlaylistStatistics",
    "PlaylistSummary",
    "SearchCategory",
    "SearchPage",
    "SongDetail",
    "SongSummary",
    "UserLibraryPage",
]
