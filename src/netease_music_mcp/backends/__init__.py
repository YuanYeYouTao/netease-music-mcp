"""Music catalog backend implementations."""

from .base import MusicCatalogBackend
from .fake import FakeMusicCatalogBackend
from .netease_web import NeteaseWebBackend

__all__ = ["FakeMusicCatalogBackend", "MusicCatalogBackend", "NeteaseWebBackend"]
