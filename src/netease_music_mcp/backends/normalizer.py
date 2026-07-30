import re
from datetime import UTC, date, datetime

from netease_music_mcp.clients.responses import (
    ProviderAlbum,
    ProviderArtist,
    ProviderPlaylist,
    ProviderSong,
)
from netease_music_mcp.domain.identifiers import normalize_id
from netease_music_mcp.domain.models import (
    AlbumSummary,
    ArtistSummary,
    LyricsLine,
    PlaylistSummary,
    SongDetail,
    SongSummary,
)

_LRC_TIMESTAMP = re.compile(r"\[(\d{1,3}):(\d{2})(?:[.:](\d{1,3}))?]\s*(.*)")


class NeteaseNormalizer:
    """Convert provider response models to stable transport-independent models."""

    @staticmethod
    def date_from_timestamp(value: int | None) -> date | None:
        if value is None or value <= 0:
            return None
        return datetime.fromtimestamp(value / 1000, tz=UTC).date()

    @staticmethod
    def artist(value: ProviderArtist) -> ArtistSummary:
        aliases = [*value.alias]
        if value.trans and value.trans not in aliases:
            aliases.append(value.trans)
        return ArtistSummary(id=normalize_id(value.id), name=value.name, aliases=tuple(aliases))

    def album(self, value: ProviderAlbum) -> AlbumSummary:
        artists = value.artists or ([value.artist] if value.artist else [])
        album_id = normalize_id(value.id)
        return AlbumSummary(
            id=album_id,
            name=value.name,
            artists=tuple(self.artist(artist) for artist in artists),
            cover_url=value.pic_url or value.cover_img_url or None,
            publish_date=self.date_from_timestamp(value.publish_time),
            canonical_url=f"https://music.163.com/#/album?id={album_id}",
        )

    def song(self, value: ProviderSong, *, detailed: bool = False) -> SongSummary | SongDetail:
        artists = value.artists or value.ar
        album = value.album or value.al
        song_id = normalize_id(value.id)
        common = {
            "id": song_id,
            "title": value.name,
            "artists": tuple(self.artist(artist) for artist in artists),
            "album": self.album(album) if album else None,
            "duration_ms": max(value.duration if value.duration is not None else value.dt or 0, 0),
            "aliases": tuple(value.alias or value.alia),
            "canonical_url": f"https://music.163.com/#/song?id={song_id}",
        }
        if not detailed:
            return SongSummary(**common)
        disc_number: int | None = None
        if value.cd and value.cd.isdigit():
            disc_number = int(value.cd)
        available = value.privilege is None or value.privilege.st >= 0
        return SongDetail(
            **common,
            track_number=value.no,
            disc_number=disc_number,
            publish_date=self.date_from_timestamp(value.publish_time),
            fee_type=value.fee
            if value.fee is not None
            else (value.privilege.fee if value.privilege else None),
            available=available,
            popularity=value.popularity if value.popularity is not None else value.pop,
            metadata={"mv_id": value.mv} if value.mv else {},
        )

    @staticmethod
    def playlist(value: ProviderPlaylist) -> PlaylistSummary:
        playlist_id = normalize_id(value.id)
        return PlaylistSummary(
            id=playlist_id,
            name=value.name,
            creator=value.creator.nickname if value.creator else None,
            cover_url=value.cover_img_url or None,
            description=value.description or "",
            track_count=max(value.track_count, 0),
            play_count=max(value.play_count, 0),
            subscribed_count=max(value.subscribed_count, 0),
            tags=tuple(value.tags),
            canonical_url=f"https://music.163.com/#/playlist?id={playlist_id}",
        )

    def lyrics(
        self,
        original: str,
        translated: str = "",
        romanized: str = "",
    ) -> tuple[LyricsLine, ...]:
        translation_map = self._parse_lrc(translated)
        romanization_map = self._parse_lrc(romanized)
        original_map = self._parse_lrc(original)
        return tuple(
            LyricsLine(
                timestamp_ms=timestamp,
                text=text,
                translated_text=translation_map.get(timestamp),
                romanized_text=romanization_map.get(timestamp),
            )
            for timestamp, text in sorted(original_map.items())
        )

    @staticmethod
    def _parse_lrc(value: str) -> dict[int, str]:
        parsed: dict[int, str] = {}
        for raw_line in value.splitlines():
            match = _LRC_TIMESTAMP.match(raw_line.strip())
            if not match:
                continue
            minutes, seconds, fraction, text = match.groups()
            fraction_ms = 0
            if fraction:
                fraction_ms = int(fraction.ljust(3, "0")[:3])
            timestamp = int(minutes) * 60_000 + int(seconds) * 1000 + fraction_ms
            parsed[timestamp] = text.strip()
        return parsed
