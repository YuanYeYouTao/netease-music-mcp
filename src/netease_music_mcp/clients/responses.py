from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProviderModel(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class ProviderArtist(ProviderModel):
    id: str | int
    name: str = ""
    alias: list[str] = Field(default_factory=list)
    trans: str | None = None
    brief_desc: str = Field(default="", alias="briefDesc")
    pic_url: str | None = Field(default=None, alias="picUrl")
    music_size: int = Field(default=0, alias="musicSize")
    album_size: int = Field(default=0, alias="albumSize")
    mv_size: int = Field(default=0, alias="mvSize")


class ProviderAlbum(ProviderModel):
    id: str | int
    name: str = ""
    artists: list[ProviderArtist] = Field(default_factory=list)
    artist: ProviderArtist | None = None
    pic_url: str | None = Field(default=None, alias="picUrl")
    cover_img_url: str | None = Field(default=None, alias="coverImgUrl")
    publish_time: int | None = Field(default=None, alias="publishTime")
    description: str = ""
    company: str | None = None
    type: str | None = None
    size: int = 0


class ProviderPrivilege(ProviderModel):
    st: int = 0
    fee: int | None = None


class ProviderSong(ProviderModel):
    id: str | int
    name: str = ""
    artists: list[ProviderArtist] = Field(default_factory=list)
    ar: list[ProviderArtist] = Field(default_factory=list)
    album: ProviderAlbum | None = None
    al: ProviderAlbum | None = None
    duration: int | None = None
    dt: int | None = None
    alias: list[str] = Field(default_factory=list)
    alia: list[str] = Field(default_factory=list)
    no: int | None = None
    cd: str | None = None
    publish_time: int | None = Field(default=None, alias="publishTime")
    fee: int | None = None
    privilege: ProviderPrivilege | None = None
    popularity: int | None = None
    pop: int | None = None
    mv: int = 0


class ProviderCreator(ProviderModel):
    user_id: str | int | None = Field(default=None, alias="userId")
    nickname: str = ""


class ProviderTrackId(ProviderModel):
    id: str | int


class ProviderPlaylist(ProviderModel):
    id: str | int
    name: str = ""
    creator: ProviderCreator | None = None
    cover_img_url: str | None = Field(default=None, alias="coverImgUrl")
    description: str = ""
    track_count: int = Field(default=0, alias="trackCount")
    play_count: int = Field(default=0, alias="playCount")
    subscribed_count: int = Field(default=0, alias="subscribedCount")
    tags: list[str] = Field(default_factory=list)
    tracks: list[ProviderSong] = Field(default_factory=list)
    track_ids: list[ProviderTrackId] = Field(default_factory=list, alias="trackIds")
    privileges: list[ProviderPrivilege] = Field(default_factory=list)


class ProviderSearchResult(ProviderModel):
    songs: list[ProviderSong] = Field(default_factory=list)
    song_count: int = Field(default=0, alias="songCount")
    artists: list[ProviderArtist] = Field(default_factory=list)
    artist_count: int = Field(default=0, alias="artistCount")
    albums: list[ProviderAlbum] = Field(default_factory=list)
    album_count: int = Field(default=0, alias="albumCount")
    playlists: list[ProviderPlaylist] = Field(default_factory=list)
    playlist_count: int = Field(default=0, alias="playlistCount")


class ProviderSearchResponse(ProviderModel):
    code: int = 200
    result: ProviderSearchResult = Field(default_factory=ProviderSearchResult)


class ProviderSongsResponse(ProviderModel):
    code: int = 200
    songs: list[ProviderSong] = Field(default_factory=list)


class ProviderAlbumResponse(ProviderModel):
    code: int = 200
    album: ProviderAlbum
    songs: list[ProviderSong] = Field(default_factory=list)


class ProviderArtistResponse(ProviderModel):
    code: int = 200
    artist: ProviderArtist
    hot_songs: list[ProviderSong] = Field(default_factory=list, alias="hotSongs")


class ProviderPlaylistResponse(ProviderModel):
    code: int = 200
    playlist: ProviderPlaylist
    privileges: list[ProviderPrivilege] = Field(default_factory=list)


class ProviderLyricsPart(ProviderModel):
    lyric: str = ""


class ProviderLyricsResponse(ProviderModel):
    code: int = 200
    lrc: ProviderLyricsPart = Field(default_factory=ProviderLyricsPart)
    tlyric: ProviderLyricsPart = Field(default_factory=ProviderLyricsPart)
    romalrc: ProviderLyricsPart = Field(default_factory=ProviderLyricsPart)


class ProviderLibraryResponse(ProviderModel):
    code: int = 200
    playlist: list[ProviderPlaylist] = Field(default_factory=list)
    artists: list[ProviderArtist] = Field(default_factory=list)
    data: list[ProviderAlbum] = Field(default_factory=list)
    recommend: list[ProviderSong] = Field(default_factory=list)
    all_data: list[dict[str, Any]] = Field(default_factory=list, alias="allData")
    week_data: list[dict[str, Any]] = Field(default_factory=list, alias="weekData")
    count: int | None = None
    has_more: bool = Field(default=False, alias="hasMore")
