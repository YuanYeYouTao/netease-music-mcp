from datetime import date

import pytest

from netease_music_mcp.backends.normalizer import NeteaseNormalizer
from netease_music_mcp.clients.responses import ProviderSong
from netease_music_mcp.domain.models import SongDetail


@pytest.mark.parametrize(
    ("payload", "expected_album"),
    [
        (
            {
                "id": 123,
                "name": "Short keys",
                "ar": [{"id": 7, "name": "Artist"}],
                "al": {"id": 8, "name": "Album", "picUrl": "https://example.test/a.jpg"},
                "dt": 3210,
            },
            "8",
        ),
        (
            {
                "id": "124",
                "name": "Long keys",
                "artists": [{"id": "9", "name": "Artist 2"}],
                "album": {"id": "10", "name": "Album 2"},
                "duration": 4567,
            },
            "10",
        ),
    ],
)
def test_song_layouts_are_normalized(payload: dict[str, object], expected_album: str) -> None:
    song = NeteaseNormalizer().song(ProviderSong.model_validate(payload))
    assert isinstance(song.id, str)
    assert all(isinstance(artist.id, str) for artist in song.artists)
    assert song.album is not None
    assert song.album.id == expected_album
    assert song.duration_ms in {3210, 4567}


def test_timestamp_missing_cover_and_detail_fields() -> None:
    provider = ProviderSong.model_validate(
        {
            "id": 1,
            "name": "Detailed",
            "ar": [{"id": 2, "name": "A"}],
            "al": {"id": 3, "name": "B", "publishTime": 1704153600000},
            "dt": 1000,
            "publishTime": 1704153600000,
            "no": 4,
            "cd": "2",
            "privilege": {"st": -1, "fee": 1},
        }
    )
    song = NeteaseNormalizer().song(provider, detailed=True)
    assert isinstance(song, SongDetail)
    assert song.publish_date == date(2024, 1, 2)
    assert song.album is not None and song.album.cover_url is None
    assert song.track_number == 4
    assert song.disc_number == 2
    assert song.available is False


def test_lyrics_translation_and_romanization_align_by_timestamp() -> None:
    lines = NeteaseNormalizer().lyrics(
        "[00:01.00]One\n[00:02.500]Two",
        "[00:02.50]二\n[00:01.000]一",
        "[00:01.00]Yi",
    )
    assert [line.timestamp_ms for line in lines] == [1000, 2500]
    assert lines[0].translated_text == "一"
    assert lines[0].romanized_text == "Yi"
    assert lines[1].translated_text == "二"
    assert lines[1].romanized_text is None
