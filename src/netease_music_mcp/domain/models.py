from datetime import date

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

from .enums import LibrarySection, ReleaseArea, SearchCategory
from .pagination import PageInfo


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ArtistSummary(DomainModel):
    id: str
    name: str
    aliases: tuple[str, ...] = ()


class AlbumSummary(DomainModel):
    id: str
    name: str
    artists: tuple[ArtistSummary, ...] = ()
    cover_url: AnyHttpUrl | None = None
    publish_date: date | None = None
    canonical_url: AnyHttpUrl


class SongSummary(DomainModel):
    id: str
    title: str
    artists: tuple[ArtistSummary, ...]
    album: AlbumSummary | None = None
    duration_ms: int = Field(ge=0)
    aliases: tuple[str, ...] = ()
    canonical_url: AnyHttpUrl


type StableMetadataValue = str | int | bool | None


class SongDetail(SongSummary):
    track_number: int | None = Field(default=None, ge=0)
    disc_number: int | None = Field(default=None, ge=0)
    publish_date: date | None = None
    fee_type: int | None = None
    available: bool = True
    popularity: int | None = Field(default=None, ge=0)
    metadata: dict[str, StableMetadataValue] = Field(default_factory=dict)


class ArtistDetail(ArtistSummary):
    description: str = ""
    cover_url: AnyHttpUrl | None = None
    music_count: int = Field(default=0, ge=0)
    album_count: int = Field(default=0, ge=0)
    mv_count: int = Field(default=0, ge=0)
    top_songs: tuple[SongSummary, ...] = ()
    canonical_url: AnyHttpUrl


class AlbumDetail(DomainModel):
    id: str
    name: str
    artists: tuple[ArtistSummary, ...]
    description: str = ""
    cover_url: AnyHttpUrl | None = None
    publish_date: date | None = None
    company: str | None = None
    type: str | None = None
    size: int = Field(default=0, ge=0)
    tracks: tuple[SongSummary, ...] = ()
    track_page: PageInfo
    canonical_url: AnyHttpUrl


class PlaylistSummary(DomainModel):
    id: str
    name: str
    creator: str | None = None
    cover_url: AnyHttpUrl | None = None
    description: str = ""
    track_count: int = Field(default=0, ge=0)
    play_count: int = Field(default=0, ge=0)
    subscribed_count: int = Field(default=0, ge=0)
    tags: tuple[str, ...] = ()
    canonical_url: AnyHttpUrl


class PlaylistDetail(DomainModel):
    playlist: PlaylistSummary
    tracks: tuple[SongSummary, ...] = ()
    track_page: PageInfo
    privileges_available: int = Field(default=0, ge=0)


class LyricsLine(DomainModel):
    timestamp_ms: int = Field(ge=0)
    text: str
    translated_text: str | None = None
    romanized_text: str | None = None


class LyricsDocument(DomainModel):
    song_id: str
    lines: tuple[LyricsLine, ...]
    offset: int = Field(ge=0)
    limit: int = Field(ge=1)
    total: int = Field(ge=0)
    has_more: bool


type SearchItem = SongSummary | ArtistSummary | AlbumSummary | PlaylistSummary


class SearchPage(DomainModel):
    query: str
    category: SearchCategory
    items: tuple[SearchItem, ...]
    page: PageInfo


class RecommendationPage(DomainModel):
    items: tuple[PlaylistSummary, ...]
    page: PageInfo


class SimilarSongsPage(DomainModel):
    song_id: str
    items: tuple[SongSummary, ...]
    page: PageInfo


class NewSongsPage(DomainModel):
    area: ReleaseArea
    items: tuple[SongSummary, ...]
    page: PageInfo


class RankingTrack(DomainModel):
    id: str | None = None
    title: str
    artist: str | None = None


class RankingSummary(DomainModel):
    id: str
    name: str
    update_frequency: str | None = None
    cover_url: AnyHttpUrl | None = None
    track_count: int = Field(default=0, ge=0)
    top_tracks: tuple[RankingTrack, ...] = ()
    canonical_url: AnyHttpUrl


class RankingPage(DomainModel):
    items: tuple[RankingSummary, ...]
    page: PageInfo


class GetSongsResult(DomainModel):
    songs: tuple[SongSummary | SongDetail, ...]
    missing_ids: tuple[str, ...]


type LibraryItem = PlaylistSummary | ArtistSummary | AlbumSummary | SongSummary


class UserLibraryPage(DomainModel):
    section: LibrarySection
    user_id: str
    items: tuple[LibraryItem, ...]
    page: PageInfo
    total: int = Field(ge=0)
    has_more: bool


class CountEntry(DomainModel):
    name: str
    count: int = Field(ge=1)


class YearCount(DomainModel):
    year: int
    count: int = Field(ge=1)


class PlaylistStatistics(DomainModel):
    playlist_id: str
    playlist_track_count: int = Field(ge=0)
    analyzed_track_count: int = Field(ge=0)
    total_duration_ms: int = Field(ge=0)
    average_duration_ms: int = Field(ge=0)
    artist_counts: tuple[CountEntry, ...]
    album_counts: tuple[CountEntry, ...]
    release_year_distribution: tuple[YearCount, ...]
    unavailable_track_count: int = Field(ge=0)
