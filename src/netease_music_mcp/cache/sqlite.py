import asyncio
import time
from pathlib import Path

import aiosqlite

from .base import CacheStats


class SQLiteCacheBackend:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._connection: aiosqlite.Connection | None = None
        self._initialization_lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0

    async def _connect(self) -> aiosqlite.Connection:
        if self._connection is not None:
            return self._connection
        async with self._initialization_lock:
            if self._connection is None:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                connection = await aiosqlite.connect(self._path)
                await connection.execute(
                    "CREATE TABLE IF NOT EXISTS cache_entries ("
                    "cache_key TEXT PRIMARY KEY, value TEXT NOT NULL, expires_at REAL NOT NULL)"
                )
                await connection.commit()
                self._connection = connection
        return self._connection

    async def get(self, key: str) -> str | None:
        connection = await self._connect()
        cursor = await connection.execute(
            "SELECT value, expires_at FROM cache_entries WHERE cache_key = ?", (key,)
        )
        row = await cursor.fetchone()
        await cursor.close()
        if row is None:
            self._misses += 1
            return None
        value, expires_at = row
        if float(expires_at) <= time.time():
            await connection.execute("DELETE FROM cache_entries WHERE cache_key = ?", (key,))
            await connection.commit()
            self._misses += 1
            return None
        self._hits += 1
        return str(value)

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            return
        connection = await self._connect()
        await connection.execute(
            "INSERT INTO cache_entries(cache_key, value, expires_at) VALUES (?, ?, ?) "
            "ON CONFLICT(cache_key) DO UPDATE SET value=excluded.value, "
            "expires_at=excluded.expires_at",
            (key, value, time.time() + ttl_seconds),
        )
        await connection.commit()

    async def clear(self) -> int:
        connection = await self._connect()
        cursor = await connection.execute("SELECT COUNT(*) FROM cache_entries")
        row = await cursor.fetchone()
        await cursor.close()
        await connection.execute("DELETE FROM cache_entries")
        await connection.commit()
        return int(row[0]) if row else 0

    async def stats(self) -> CacheStats:
        connection = await self._connect()
        now = time.time()
        await connection.execute("DELETE FROM cache_entries WHERE expires_at <= ?", (now,))
        cursor = await connection.execute("SELECT COUNT(*) FROM cache_entries")
        row = await cursor.fetchone()
        await cursor.close()
        await connection.commit()
        return CacheStats(
            entries=int(row[0]) if row else 0,
            hits=self._hits,
            misses=self._misses,
        )

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()
            self._connection = None
