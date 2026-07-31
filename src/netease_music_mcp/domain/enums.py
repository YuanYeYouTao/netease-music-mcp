from enum import StrEnum


class SearchCategory(StrEnum):
    SONG = "song"
    ARTIST = "artist"
    ALBUM = "album"
    PLAYLIST = "playlist"


class ReleaseArea(StrEnum):
    ALL = "all"
    CHINESE = "zh"
    EUROPEAN_AMERICAN = "ea"
    KOREAN = "kr"
    JAPANESE = "jp"


class DetailLevel(StrEnum):
    SUMMARY = "summary"
    FULL = "full"


class LibrarySection(StrEnum):
    PLAYLISTS = "playlists"
    ARTIST_SUBSCRIPTIONS = "artist_subscriptions"
    ALBUM_SUBSCRIPTIONS = "album_subscriptions"
    DAILY_RECOMMENDATIONS = "daily_recommendations"
    PLAY_HISTORY = "play_history"
    LIKED_SONGS = "liked_songs"


class HistoryScope(StrEnum):
    WEEK = "week"
    ALL = "all"


class AuthenticationState(StrEnum):
    ANONYMOUS = "anonymous"
    AUTHENTICATED = "authenticated"
    EXPIRED = "expired"
    INVALID = "invalid"
