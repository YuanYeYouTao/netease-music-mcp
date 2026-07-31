import hashlib
import json
from enum import StrEnum
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Transport(StrEnum):
    STDIO = "stdio"
    STREAMABLE_HTTP = "streamable-http"


class BackendName(StrEnum):
    NETEASE_WEB = "netease-web"
    FAKE = "fake"


class CacheBackendName(StrEnum):
    NONE = "none"
    MEMORY = "memory"
    SQLITE = "sqlite"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NETEASE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        validate_default=True,
    )

    mcp_transport: Transport = Transport.STDIO
    mcp_host: str = "127.0.0.1"
    mcp_port: int = Field(default=8766, ge=1, le=65535)
    mcp_path: str = "/mcp"

    backend: BackendName = BackendName.NETEASE_WEB
    cookie: SecretStr | None = Field(default=None, repr=False)
    music_u: SecretStr | None = Field(default=None, repr=False)
    csrf: SecretStr | None = Field(default=None, repr=False)
    user_id: str | None = None

    connect_timeout_seconds: float = Field(default=5.0, gt=0)
    request_timeout_seconds: float = Field(default=15.0, gt=0)
    max_connections: int = Field(default=20, ge=1)
    max_keepalive_connections: int = Field(default=10, ge=0)
    retry_attempts: int = Field(default=2, ge=0)
    retry_initial_seconds: float = Field(default=0.25, ge=0)

    default_page_size: int = Field(default=20, ge=1)
    max_page_size: int = Field(default=100, ge=1)
    max_batch_song_ids: int = Field(default=100, ge=1)
    default_top_song_count: int = Field(default=10, ge=1)
    max_top_song_count: int = Field(default=50, ge=1)
    default_lyrics_limit: int = Field(default=50, ge=1)
    max_lyrics_limit: int = Field(default=200, ge=1)
    max_statistics_tracks: int = Field(default=1000, ge=1)

    cache_backend: CacheBackendName = CacheBackendName.MEMORY
    cache_path: Path = Path(".cache/netease-music-mcp/cache.sqlite3")
    search_cache_ttl_seconds: int = Field(default=300, ge=0)
    detail_cache_ttl_seconds: int = Field(default=1800, ge=0)
    lyrics_cache_ttl_seconds: int = Field(default=3600, ge=0)
    library_cache_ttl_seconds: int = Field(default=60, ge=0)

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    @model_validator(mode="after")
    def validate_cross_field_ranges(self) -> Self:
        if self.default_page_size > self.max_page_size:
            raise ValueError("default_page_size cannot exceed max_page_size")
        if self.default_top_song_count > self.max_top_song_count:
            raise ValueError("default_top_song_count cannot exceed max_top_song_count")
        if self.default_lyrics_limit > self.max_lyrics_limit:
            raise ValueError("default_lyrics_limit cannot exceed max_lyrics_limit")
        if not self.mcp_path.startswith("/"):
            raise ValueError("mcp_path must start with '/'")
        return self

    @property
    def cookie_configured(self) -> bool:
        return any((self.cookie, self.music_u))

    def cache_fingerprint(self) -> str:
        values = {
            "backend": self.backend,
            "default_page_size": self.default_page_size,
            "max_page_size": self.max_page_size,
            "max_batch_song_ids": self.max_batch_song_ids,
            # Bump when response semantics change so persisted entries created
            # by an older request profile cannot poison new search results.
            "schema": "0.3.0-discovery",
        }
        encoded = json.dumps(values, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(encoded.encode()).hexdigest()
