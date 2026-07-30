import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class CacheStats:
    entries: int
    hits: int
    misses: int

    def as_dict(self) -> dict[str, int]:
        return asdict(self)


class CacheBackend(Protocol):
    async def get(self, key: str) -> str | None: ...

    async def set(self, key: str, value: str, ttl_seconds: int) -> None: ...

    async def clear(self) -> int: ...

    async def stats(self) -> CacheStats: ...

    async def close(self) -> None: ...


def build_cache_key(
    *,
    backend: str,
    operation: str,
    parameters: dict[str, Any],
    authentication_scope: str,
    config_fingerprint: str,
    model_version: str = "0.1.0",
) -> str:
    material = {
        "authentication_scope": authentication_scope,
        "backend": backend,
        "config_fingerprint": config_fingerprint,
        "model_version": model_version,
        "operation": operation,
        "parameters": parameters,
    }
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode()).hexdigest()
