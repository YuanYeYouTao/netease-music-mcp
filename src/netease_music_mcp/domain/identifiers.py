from typing import NewType

SongId = NewType("SongId", str)
ArtistId = NewType("ArtistId", str)
AlbumId = NewType("AlbumId", str)
PlaylistId = NewType("PlaylistId", str)
UserId = NewType("UserId", str)


def normalize_id(value: str | int) -> str:
    """Normalize an upstream numeric identifier for the public string schema."""
    normalized = str(value).strip()
    if not normalized or not normalized.isdigit():
        raise ValueError("identifier must contain decimal digits")
    return normalized
