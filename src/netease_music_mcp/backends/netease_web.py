import json
from collections.abc import Sequence
from typing import ClassVar, TypeVar

from pydantic import BaseModel, ValidationError

from netease_music_mcp.clients.authentication import AuthenticationProvider
from netease_music_mcp.clients.http import JsonObject, NeteaseHttpClient
from netease_music_mcp.clients.responses import (
    ProviderAlbum,
    ProviderAlbumResponse,
    ProviderArtist,
    ProviderArtistResponse,
    ProviderLibraryResponse,
    ProviderLyricsResponse,
    ProviderPlaylistResponse,
    ProviderSearchResponse,
    ProviderSong,
    ProviderSongsResponse,
)
from netease_music_mcp.domain.enums import (
    DetailLevel,
    HistoryScope,
    LibrarySection,
    SearchCategory,
)
from netease_music_mcp.domain.errors import (
    AuthenticationExpiredError,
    RateLimitedError,
    ResourceNotFoundError,
    UpstreamResponseError,
)
from netease_music_mcp.domain.models import (
    AlbumDetail,
    ArtistDetail,
    GetSongsResult,
    LibraryItem,
    LyricsDocument,
    PlaylistDetail,
    SearchItem,
    SearchPage,
    SongDetail,
    SongSummary,
    UserLibraryPage,
)
from netease_music_mcp.domain.pagination import PageInfo, PageRequest

from .normalizer import NeteaseNormalizer

ProviderT = TypeVar("ProviderT", bound=BaseModel)


class NeteaseWebBackend:
    """Read-only adapter for NetEase's web endpoints.

    These endpoints are not a public compatibility contract and can change without notice.
    """

    name = "netease-web"
    _SEARCH_TYPES: ClassVar[dict[SearchCategory, int]] = {
        SearchCategory.SONG: 1,
        SearchCategory.ALBUM: 10,
        SearchCategory.ARTIST: 100,
        SearchCategory.PLAYLIST: 1000,
    }

    def __init__(
        self,
        client: NeteaseHttpClient,
        authentication: AuthenticationProvider,
        normalizer: NeteaseNormalizer | None = None,
    ) -> None:
        self._client = client
        self._authentication = authentication
        self._normalizer = normalizer or NeteaseNormalizer()

    async def search(
        self,
        query: str,
        category: SearchCategory,
        page: PageRequest,
        detail_level: DetailLevel,
    ) -> SearchPage:
        del detail_level
        payload = await self._client.request_json(
            "POST",
            "/api/search/get",
            data={
                "s": query,
                "type": self._SEARCH_TYPES[category],
                "limit": page.page_size,
                "offset": page.offset,
            },
        )
        response = self._parse(ProviderSearchResponse, payload)
        self._check_code(response.code)
        result = response.result
        items: tuple[SearchItem, ...]
        total: int
        if category is SearchCategory.SONG:
            items = tuple(self._normalizer.song(item) for item in result.songs)
            total = result.song_count
        elif category is SearchCategory.ARTIST:
            items = tuple(self._normalizer.artist(item) for item in result.artists)
            total = result.artist_count
        elif category is SearchCategory.ALBUM:
            items = tuple(self._normalizer.album(item) for item in result.albums)
            total = result.album_count
        else:
            items = tuple(self._normalizer.playlist(item) for item in result.playlists)
            total = result.playlist_count
        return SearchPage(
            query=query,
            category=category,
            items=items,
            page=PageInfo.from_request(page, total),
        )

    async def get_songs(
        self, song_ids: tuple[str, ...], detail_level: DetailLevel
    ) -> GetSongsResult:
        request_items = [{"id": song_id} for song_id in song_ids]
        payload = await self._client.request_json(
            "POST",
            "/api/song/detail/",
            data={
                "ids": json.dumps(list(song_ids), separators=(",", ":")),
                "c": json.dumps(request_items, separators=(",", ":")),
            },
        )
        response = self._parse(ProviderSongsResponse, payload)
        self._check_code(response.code)
        by_id = {str(song.id): song for song in response.songs}
        songs = tuple(
            self._normalizer.song(by_id[song_id], detailed=detail_level is DetailLevel.FULL)
            for song_id in song_ids
            if song_id in by_id
        )
        missing = tuple(song_id for song_id in song_ids if song_id not in by_id)
        return GetSongsResult(songs=songs, missing_ids=missing)

    async def get_album(
        self, album_id: str, include_tracks: bool, track_page: PageRequest
    ) -> AlbumDetail:
        payload = await self._client.request_json("GET", f"/api/album/{album_id}")
        self._check_embedded_code(payload)
        response = self._parse(ProviderAlbumResponse, payload)
        album = self._normalizer.album(response.album)
        total = response.album.size or len(response.songs)
        selected = response.songs[track_page.offset : track_page.offset + track_page.page_size]
        tracks = tuple(self._normalizer.song(song) for song in selected) if include_tracks else ()
        return AlbumDetail(
            **album.model_dump(),
            description=response.album.description or "",
            company=response.album.company,
            type=response.album.type,
            size=max(total, 0),
            tracks=tracks,
            track_page=PageInfo.from_request(track_page, max(total, 0)),
        )

    async def get_artist(
        self, artist_id: str, include_top_songs: bool, top_song_count: int
    ) -> ArtistDetail:
        payload = await self._client.request_json("GET", f"/api/artist/{artist_id}")
        self._check_embedded_code(payload)
        response = self._parse(ProviderArtistResponse, payload)
        artist = self._normalizer.artist(response.artist)
        return ArtistDetail(
            **artist.model_dump(),
            description=response.artist.brief_desc or "",
            cover_url=response.artist.pic_url or None,
            music_count=max(response.artist.music_size, 0),
            album_count=max(response.artist.album_size, 0),
            mv_count=max(response.artist.mv_size, 0),
            top_songs=tuple(
                self._normalizer.song(song) for song in response.hot_songs[:top_song_count]
            )
            if include_top_songs
            else (),
            canonical_url=f"https://music.163.com/#/artist?id={artist.id}",
        )

    async def get_playlist(
        self, playlist_id: str, include_tracks: bool, track_page: PageRequest
    ) -> PlaylistDetail:
        payload = await self._client.request_json(
            "POST", "/api/v6/playlist/detail", data={"id": playlist_id, "n": 100000, "s": 0}
        )
        self._check_embedded_code(payload)
        response = self._parse(ProviderPlaylistResponse, payload)
        provider_playlist = response.playlist
        total = provider_playlist.track_count or len(provider_playlist.track_ids)
        tracks: tuple[SongSummary | SongDetail, ...] = ()
        if include_tracks:
            track_ids = tuple(
                str(item.id)
                for item in provider_playlist.track_ids[
                    track_page.offset : track_page.offset + track_page.page_size
                ]
            )
            if track_ids:
                tracks = (await self.get_songs(track_ids, DetailLevel.SUMMARY)).songs
            elif provider_playlist.tracks:
                selected = provider_playlist.tracks[
                    track_page.offset : track_page.offset + track_page.page_size
                ]
                tracks = tuple(self._normalizer.song(song) for song in selected)
        privileges = response.privileges or provider_playlist.privileges
        available = sum(privilege.st >= 0 for privilege in privileges)
        return PlaylistDetail(
            playlist=self._normalizer.playlist(provider_playlist),
            tracks=tracks,
            track_page=PageInfo.from_request(track_page, max(total, 0)),
            privileges_available=available,
        )

    async def get_lyrics(
        self,
        song_id: str,
        include_translation: bool,
        include_romanization: bool,
        offset: int,
        limit: int,
    ) -> LyricsDocument:
        payload = await self._client.request_json(
            "GET",
            "/api/song/lyric",
            params={"id": song_id, "lv": -1, "kv": -1, "tv": -1, "rv": -1},
        )
        self._check_embedded_code(payload)
        response = self._parse(ProviderLyricsResponse, payload)
        lines = self._normalizer.lyrics(
            response.lrc.lyric,
            response.tlyric.lyric if include_translation else "",
            response.romalrc.lyric if include_romanization else "",
        )
        selected = lines[offset : offset + limit]
        return LyricsDocument(
            song_id=song_id,
            lines=selected,
            offset=offset,
            limit=limit,
            total=len(lines),
            has_more=offset + limit < len(lines),
        )

    async def get_user_library(
        self,
        section: LibrarySection,
        user_id: str,
        page: PageRequest,
        history_scope: HistoryScope,
    ) -> UserLibraryPage:
        self._authentication.require_user_id(user_id)
        items: tuple[LibraryItem, ...]
        if section is LibrarySection.PLAYLISTS:
            payload = await self._client.request_json(
                "GET",
                "/api/user/playlist",
                params={"uid": user_id, "offset": page.offset, "limit": page.page_size},
            )
            response = self._library_response(payload)
            items = tuple(self._normalizer.playlist(item) for item in response.playlist)
            total = response.count or (page.offset + len(items) + (1 if response.has_more else 0))
        elif section is LibrarySection.ARTIST_SUBSCRIPTIONS:
            payload = await self._client.request_json(
                "GET",
                "/api/artist/sublist",
                params={"offset": page.offset, "limit": page.page_size, "total": "true"},
            )
            response = self._library_response(payload)
            artist_items = self._parse_list(ProviderArtist, payload.get("data", response.artists))
            items = tuple(self._normalizer.artist(item) for item in artist_items)
            total = response.count or (page.offset + len(items) + (1 if response.has_more else 0))
        elif section is LibrarySection.ALBUM_SUBSCRIPTIONS:
            payload = await self._client.request_json(
                "GET",
                "/api/album/sublist",
                params={"offset": page.offset, "limit": page.page_size, "total": "true"},
            )
            response = self._library_response(payload)
            album_items = self._parse_list(ProviderAlbum, payload.get("data", response.data))
            items = tuple(self._normalizer.album(item) for item in album_items)
            total = response.count or (page.offset + len(items) + (1 if response.has_more else 0))
        elif section is LibrarySection.DAILY_RECOMMENDATIONS:
            payload = await self._client.request_json("GET", "/api/v3/discovery/recommend/songs")
            self._check_embedded_code(payload)
            data = payload.get("data")
            raw_items = data.get("dailySongs", []) if isinstance(data, dict) else []
            song_items = self._parse_list(ProviderSong, raw_items)
            selected = song_items[page.offset : page.offset + page.page_size]
            items = tuple(self._normalizer.song(item) for item in selected)
            total = len(song_items)
        else:
            scope_key = "weekData" if history_scope is HistoryScope.WEEK else "allData"
            payload = await self._client.request_json(
                "GET",
                "/api/v1/play/record",
                params={"uid": user_id, "type": 1 if history_scope is HistoryScope.WEEK else 0},
            )
            self._check_embedded_code(payload)
            records = payload.get(scope_key, [])
            songs = [record.get("song") for record in records if isinstance(record, dict)]
            history_items = self._parse_list(ProviderSong, songs)
            selected = history_items[page.offset : page.offset + page.page_size]
            items = tuple(self._normalizer.song(item) for item in selected)
            total = len(history_items)
        info = PageInfo.from_request(page, max(total, 0))
        return UserLibraryPage(
            section=section,
            user_id=user_id,
            items=items,
            page=info,
            total=info.total,
            has_more=info.has_more,
        )

    def _library_response(self, payload: JsonObject) -> ProviderLibraryResponse:
        self._check_embedded_code(payload)
        return self._parse(ProviderLibraryResponse, payload)

    @staticmethod
    def _parse(model: type[ProviderT], payload: object) -> ProviderT:
        try:
            return model.model_validate(payload)
        except ValidationError as exc:
            raise UpstreamResponseError(
                "NetEase response did not match the expected schema"
            ) from exc

    @classmethod
    def _parse_list(cls, model: type[ProviderT], payload: object) -> list[ProviderT]:
        if not isinstance(payload, Sequence) or isinstance(payload, (str, bytes)):
            raise UpstreamResponseError("NetEase returned an invalid list response")
        return [cls._parse(model, item) for item in payload]

    @classmethod
    def _check_embedded_code(cls, payload: JsonObject) -> None:
        value = payload.get("code", 200)
        if not isinstance(value, int):
            raise UpstreamResponseError("NetEase returned an invalid response code")
        cls._check_code(value)

    @staticmethod
    def _check_code(code: int) -> None:
        if code in {200, 201}:
            return
        if code in {301, 302, 401}:
            raise AuthenticationExpiredError("NetEase authentication is missing or expired")
        if code == 404:
            raise ResourceNotFoundError("NetEase resource was not found")
        if code == 429:
            raise RateLimitedError("NetEase rate limit reached")
        raise UpstreamResponseError(f"NetEase returned provider code {code}")

    async def close(self) -> None:
        await self._client.close()
