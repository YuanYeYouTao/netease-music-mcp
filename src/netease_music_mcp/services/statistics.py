from collections import Counter

from netease_music_mcp.domain.enums import DetailLevel
from netease_music_mcp.domain.errors import InvalidRequestError
from netease_music_mcp.domain.models import CountEntry, PlaylistStatistics, SongDetail, YearCount

from .catalog import CatalogService


class StatisticsService:
    def __init__(self, catalog: CatalogService) -> None:
        self.catalog = catalog

    async def get_playlist_statistics(
        self, playlist_id: str, track_limit: int | None = None
    ) -> PlaylistStatistics:
        settings = self.catalog.settings
        limit = settings.max_statistics_tracks if track_limit is None else track_limit
        if limit < 1 or limit > settings.max_statistics_tracks:
            raise InvalidRequestError(
                f"track_limit must be between 1 and {settings.max_statistics_tracks}"
            )
        first = await self.catalog.get_playlist(
            playlist_id,
            include_tracks=True,
            track_page=1,
            track_page_size=min(settings.max_page_size, limit),
        )
        summaries = list(first.tracks)
        total_to_analyze = min(first.playlist.track_count, limit)
        page_number = 2
        while len(summaries) < total_to_analyze:
            remaining = total_to_analyze - len(summaries)
            detail = await self.catalog.get_playlist(
                playlist_id,
                include_tracks=True,
                track_page=page_number,
                track_page_size=min(settings.max_page_size, remaining),
            )
            if not detail.tracks:
                break
            summaries.extend(detail.tracks)
            page_number += 1
        ids = tuple(song.id for song in summaries[:total_to_analyze])
        detailed: list[SongDetail] = []
        for index in range(0, len(ids), settings.max_batch_song_ids):
            result = await self.catalog.get_songs(
                ids[index : index + settings.max_batch_song_ids], DetailLevel.FULL
            )
            detailed.extend(song for song in result.songs if isinstance(song, SongDetail))
        artist_counts: Counter[str] = Counter()
        album_counts: Counter[str] = Counter()
        release_years: Counter[int] = Counter()
        for song in detailed:
            artist_counts.update(artist.name for artist in song.artists)
            if song.album:
                album_counts[song.album.name] += 1
            publish_date = song.publish_date or (song.album.publish_date if song.album else None)
            if publish_date:
                release_years[publish_date.year] += 1
        total_duration = sum(song.duration_ms for song in detailed)
        analyzed = len(detailed)
        return PlaylistStatistics(
            playlist_id=first.playlist.id,
            playlist_track_count=first.playlist.track_count,
            analyzed_track_count=analyzed,
            total_duration_ms=total_duration,
            average_duration_ms=round(total_duration / analyzed) if analyzed else 0,
            artist_counts=tuple(
                CountEntry(name=name, count=count)
                for name, count in sorted(
                    artist_counts.items(), key=lambda item: (-item[1], item[0].casefold())
                )
            ),
            album_counts=tuple(
                CountEntry(name=name, count=count)
                for name, count in sorted(
                    album_counts.items(), key=lambda item: (-item[1], item[0].casefold())
                )
            ),
            release_year_distribution=tuple(
                YearCount(year=year, count=count) for year, count in sorted(release_years.items())
            ),
            unavailable_track_count=sum(not song.available for song in detailed),
        )
