from datetime import date

from netease_music_mcp.domain.enums import (
    DetailLevel,
    HistoryScope,
    LibrarySection,
    PlaylistTrackOperation,
    ReleaseArea,
    SearchCategory,
)
from netease_music_mcp.domain.errors import ResourceNotFoundError
from netease_music_mcp.domain.models import (
    AlbumDetail,
    AlbumSummary,
    ArtistDetail,
    ArtistSummary,
    GetSongsResult,
    LibraryItem,
    LyricsDocument,
    LyricsLine,
    NewSongsPage,
    PlaylistDetail,
    PlaylistSummary,
    RankingPage,
    RankingSummary,
    RankingTrack,
    RecommendationPage,
    SearchPage,
    SimilarSongsPage,
    SongDetail,
    SongSummary,
    UserLibraryPage,
    WriteResult,
)
from netease_music_mcp.domain.pagination import PageInfo, PageRequest

from .base import ALL_BACKEND_OPERATIONS


class FakeMusicCatalogBackend:
    """Deterministic in-process backend used by the default test suite."""

    name = "fake"
    supported_operations = ALL_BACKEND_OPERATIONS

    def __init__(self) -> None:
        artist = ArtistSummary(id="10", name="Example Artist", aliases=("示例歌手",))
        album = AlbumSummary(
            id="20",
            name="Example Album",
            artists=(artist,),
            cover_url="https://example.invalid/album.jpg",
            publish_date=date(2024, 1, 2),
            canonical_url="https://music.163.com/#/album?id=20",
        )
        self.songs = {
            str(index): SongDetail(
                id=str(index),
                title=f"Example Song {index}",
                artists=(artist,),
                album=album,
                duration_ms=180_000 + index * 1000,
                aliases=(),
                canonical_url=f"https://music.163.com/#/song?id={index}",
                track_number=index,
                disc_number=1,
                publish_date=date(2024, 1, index),
                fee_type=0,
                available=index != 3,
                popularity=90 - index,
                metadata={},
            )
            for index in range(1, 4)
        }
        self.artist_detail = ArtistDetail(
            **artist.model_dump(),
            description="A deterministic fixture artist.",
            cover_url="https://example.invalid/artist.jpg",
            music_count=3,
            album_count=1,
            mv_count=0,
            top_songs=tuple(self.songs.values()),
            canonical_url="https://music.163.com/#/artist?id=10",
        )
        self.album_summary = album
        self.playlist_summary = PlaylistSummary(
            id="30",
            name="Example Playlist",
            creator="Fixture User",
            cover_url="https://example.invalid/playlist.jpg",
            description="A deterministic fixture playlist.",
            track_count=3,
            play_count=42,
            subscribed_count=7,
            tags=("test",),
            canonical_url="https://music.163.com/#/playlist?id=30",
        )
        self.playlists = {self.playlist_summary.id: self.playlist_summary}
        self.playlist_tracks = {self.playlist_summary.id: list(self.songs)}
        self.liked_song_ids = set(self.songs)
        self._next_playlist_id = 100
        self.ranking = RankingSummary(
            id="30",
            name="Example Ranking",
            update_frequency="每天更新",
            cover_url="https://example.invalid/ranking.jpg",
            track_count=3,
            top_tracks=(RankingTrack(id="1", title="Example Song 1", artist="Example Artist"),),
            canonical_url="https://music.163.com/#/playlist?id=30",
        )
        self.closed = False

    async def search(
        self,
        query: str,
        category: SearchCategory,
        page: PageRequest,
        detail_level: DetailLevel,
    ) -> SearchPage:
        del detail_level
        query_folded = query.casefold()
        if category is SearchCategory.SONG:
            values: list[SongSummary | ArtistSummary | AlbumSummary | PlaylistSummary] = [
                SongSummary(**song.model_dump(include=set(SongSummary.model_fields)))
                for song in self.songs.values()
                if query_folded in song.title.casefold() or query_folded == "example"
            ]
        elif category is SearchCategory.ARTIST:
            values = [
                ArtistSummary(
                    **self.artist_detail.model_dump(include=set(ArtistSummary.model_fields))
                )
            ]
        elif category is SearchCategory.ALBUM:
            values = [self.album_summary]
        else:
            values = list(self.playlists.values())
        sliced = values[page.offset : page.offset + page.page_size]
        return SearchPage(
            query=query,
            category=category,
            items=tuple(sliced),
            page=PageInfo.from_request(page, len(values)),
        )

    async def get_songs(
        self, song_ids: tuple[str, ...], detail_level: DetailLevel
    ) -> GetSongsResult:
        songs: list[SongSummary | SongDetail] = []
        missing: list[str] = []
        for song_id in song_ids:
            song = self.songs.get(song_id)
            if song is None:
                missing.append(song_id)
            elif detail_level is DetailLevel.FULL:
                songs.append(song)
            else:
                songs.append(SongSummary(**song.model_dump(include=set(SongSummary.model_fields))))
        return GetSongsResult(songs=tuple(songs), missing_ids=tuple(missing))

    async def get_recommendations(self, page: PageRequest) -> RecommendationPage:
        values = (self.playlist_summary,)
        return RecommendationPage(
            items=values[page.offset : page.offset + page.page_size],
            page=PageInfo.from_request(page, len(values)),
        )

    async def get_similar_songs(self, song_id: str, page: PageRequest) -> SimilarSongsPage:
        if song_id not in self.songs:
            raise ResourceNotFoundError(f"song {song_id} was not found")
        values = tuple(
            SongSummary(**song.model_dump(include=set(SongSummary.model_fields)))
            for key, song in self.songs.items()
            if key != song_id
        )
        return SimilarSongsPage(
            song_id=song_id,
            items=values[page.offset : page.offset + page.page_size],
            page=PageInfo.from_request(page, len(values)),
        )

    async def get_new_songs(self, area: ReleaseArea, page: PageRequest) -> NewSongsPage:
        songs = tuple(
            SongSummary(**song.model_dump(include=set(SongSummary.model_fields)))
            for song in self.songs.values()
        )
        return NewSongsPage(
            area=area,
            items=songs[page.offset : page.offset + page.page_size],
            page=PageInfo.from_request(page, len(songs)),
        )

    async def get_rankings(self, page: PageRequest) -> RankingPage:
        values = (self.ranking,)
        return RankingPage(
            items=values[page.offset : page.offset + page.page_size],
            page=PageInfo.from_request(page, len(values)),
        )

    async def get_album(
        self, album_id: str, include_tracks: bool, track_page: PageRequest
    ) -> AlbumDetail:
        if album_id != self.album_summary.id:
            raise ResourceNotFoundError(f"album {album_id} was not found")
        all_tracks = tuple(self.songs.values())
        tracks = (
            all_tracks[track_page.offset : track_page.offset + track_page.page_size]
            if include_tracks
            else ()
        )
        return AlbumDetail(
            **self.album_summary.model_dump(),
            description="A deterministic fixture album.",
            company="Fixture Records",
            type="album",
            size=len(all_tracks),
            tracks=tracks,
            track_page=PageInfo.from_request(track_page, len(all_tracks)),
        )

    async def get_artist(
        self, artist_id: str, include_top_songs: bool, top_song_count: int
    ) -> ArtistDetail:
        if artist_id != self.artist_detail.id:
            raise ResourceNotFoundError(f"artist {artist_id} was not found")
        return self.artist_detail.model_copy(
            update={
                "top_songs": self.artist_detail.top_songs[:top_song_count]
                if include_top_songs
                else ()
            }
        )

    async def get_playlist(
        self, playlist_id: str, include_tracks: bool, track_page: PageRequest
    ) -> PlaylistDetail:
        playlist = self.playlists.get(playlist_id)
        if playlist is None:
            raise ResourceNotFoundError(f"playlist {playlist_id} was not found")
        all_tracks = tuple(self.songs[song_id] for song_id in self.playlist_tracks[playlist_id])
        tracks = (
            all_tracks[track_page.offset : track_page.offset + track_page.page_size]
            if include_tracks
            else ()
        )
        return PlaylistDetail(
            playlist=playlist.model_copy(update={"track_count": len(all_tracks)}),
            tracks=tracks,
            track_page=PageInfo.from_request(track_page, len(all_tracks)),
            privileges_available=sum(song.available for song in all_tracks),
        )

    async def get_lyrics(
        self,
        song_id: str,
        include_translation: bool,
        include_romanization: bool,
        offset: int,
        limit: int,
    ) -> LyricsDocument:
        if song_id not in self.songs:
            raise ResourceNotFoundError(f"song {song_id} was not found")
        all_lines = tuple(
            LyricsLine(
                timestamp_ms=index * 10_000,
                text=f"Line {index}",
                translated_text=f"译文 {index}" if include_translation else None,
                romanized_text=f"Romanized {index}" if include_romanization else None,
            )
            for index in range(8)
        )
        lines = all_lines[offset : offset + limit]
        return LyricsDocument(
            song_id=song_id,
            lines=lines,
            offset=offset,
            limit=limit,
            total=len(all_lines),
            has_more=offset + limit < len(all_lines),
        )

    async def get_user_library(
        self,
        section: LibrarySection,
        user_id: str,
        page: PageRequest,
        history_scope: HistoryScope,
    ) -> UserLibraryPage:
        del history_scope
        values: tuple[LibraryItem, ...]
        if section is LibrarySection.PLAYLISTS:
            values = tuple(self.playlists.values())
        elif section is LibrarySection.ARTIST_SUBSCRIPTIONS:
            values = (
                ArtistSummary(
                    **self.artist_detail.model_dump(include=set(ArtistSummary.model_fields))
                ),
            )
        elif section is LibrarySection.ALBUM_SUBSCRIPTIONS:
            values = (self.album_summary,)
        elif section is LibrarySection.LIKED_SONGS:
            values = tuple(
                SongSummary(**song.model_dump(include=set(SongSummary.model_fields)))
                for song_id, song in self.songs.items()
                if song_id in self.liked_song_ids
            )
        else:
            values = tuple(
                SongSummary(**song.model_dump(include=set(SongSummary.model_fields)))
                for song in self.songs.values()
            )
        items = values[page.offset : page.offset + page.page_size]
        info = PageInfo.from_request(page, len(values))
        return UserLibraryPage(
            section=section,
            user_id=user_id,
            items=items,
            page=info,
            total=info.total,
            has_more=info.has_more,
        )

    async def create_playlist(self, name: str, private: bool) -> WriteResult:
        del private
        playlist_id = str(self._next_playlist_id)
        self._next_playlist_id += 1
        playlist = self.playlist_summary.model_copy(
            update={"id": playlist_id, "name": name, "track_count": 0}
        )
        self.playlists[playlist_id] = playlist
        self.playlist_tracks[playlist_id] = []
        return WriteResult(action="create_playlist", code=200, playlist_id=playlist_id)

    async def update_playlist_tracks(
        self,
        playlist_id: str,
        operation: PlaylistTrackOperation,
        song_ids: tuple[str, ...],
    ) -> WriteResult:
        if playlist_id not in self.playlist_tracks:
            raise ResourceNotFoundError(f"playlist {playlist_id} was not found")
        if any(song_id not in self.songs for song_id in song_ids):
            raise ResourceNotFoundError("one or more songs were not found")
        tracks = self.playlist_tracks[playlist_id]
        if operation is PlaylistTrackOperation.ADD:
            tracks.extend(song_id for song_id in song_ids if song_id not in tracks)
        else:
            self.playlist_tracks[playlist_id] = [
                song_id for song_id in tracks if song_id not in song_ids
            ]
        self.playlists[playlist_id] = self.playlists[playlist_id].model_copy(
            update={"track_count": len(self.playlist_tracks[playlist_id])}
        )
        return WriteResult(
            action="update_playlist_tracks",
            code=200,
            playlist_id=playlist_id,
            song_ids=song_ids,
            operation=operation,
        )

    async def set_song_like(self, song_id: str, liked: bool) -> WriteResult:
        if song_id not in self.songs:
            raise ResourceNotFoundError(f"song {song_id} was not found")
        if liked:
            self.liked_song_ids.add(song_id)
        else:
            self.liked_song_ids.discard(song_id)
        return WriteResult(action="set_song_like", code=200, song_ids=(song_id,), liked=liked)

    async def close(self) -> None:
        self.closed = True
