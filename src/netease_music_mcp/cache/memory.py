import asyncio
import time
from dataclasses import dataclass

from .base import CacheStats


@dataclass
class _MemoryEntry:
    value: str
    expires_at: float


class MemoryCacheBackend:
    def __init__(self) -> None:
        self._entries: dict[str, _MemoryEntry] = {}
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0

    async def get(self, key: str) -> str | None:
        async with self._lock:
            entry = self._entries.get(key)
            if entry is None or entry.expires_at <= time.monotonic():
                self._entries.pop(key, None)
                self._misses += 1
                return None
            self._hits += 1
            return entry.value

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            return
        async with self._lock:
            self._entries[key] = _MemoryEntry(
                value=value,
                expires_at=time.monotonic() + ttl_seconds,
            )

    async def clear(self) -> int:
        async with self._lock:
            count = len(self._entries)
            self._entries.clear()
            return count

    async def stats(self) -> CacheStats:
        async with self._lock:
            now = time.monotonic()
            expired = [key for key, entry in self._entries.items() if entry.expires_at <= now]
            for key in expired:
                del self._entries[key]
            return CacheStats(entries=len(self._entries), hits=self._hits, misses=self._misses)

    async def close(self) -> None:
        return None


class NullCacheBackend:
    async def get(self, key: str) -> str | None:
        del key
        return None

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        del key, value, ttl_seconds

    async def clear(self) -> int:
        return 0

    async def stats(self) -> CacheStats:
        return CacheStats(entries=0, hits=0, misses=0)

    async def close(self) -> None:
        return None
