from pathlib import Path
from types import SimpleNamespace

import pytest

from netease_music_mcp import cli
from netease_music_mcp.cache.base import build_cache_key
from netease_music_mcp.cache.sqlite import SQLiteCacheBackend
from netease_music_mcp.cli import _auth_snapshot_output, _config_output
from netease_music_mcp.clients.authentication import AuthenticationProvider
from netease_music_mcp.config import Settings
from netease_music_mcp.local_auth import LocalAuthSnapshot


def test_cookie_is_redacted_from_repr_and_config() -> None:
    secret = "MUSIC_U=super-secret-value"
    settings = Settings(cookie=secret)
    provider = AuthenticationProvider.from_settings(settings)
    rendered = repr(provider) + str(_config_output(settings)) + repr(settings)
    assert secret not in rendered
    assert "super-secret-value" not in rendered
    assert _config_output(settings)["values"]["cookie_configured"] is True


def test_local_auth_output_is_redacted() -> None:
    output = _auth_snapshot_output(
        LocalAuthSnapshot(
            cookie="MUSIC_U=super-secret-value",
            source="macos-desktop",
            cookie_names=("MUSIC_U",),
        )
    )
    rendered = str(output)
    assert "super-secret-value" not in rendered
    assert output["persisted"] is False


def test_docker_auth_injection_uses_child_environment_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "compose.yaml").write_text("services: {}", encoding="utf-8")
    captured: dict[str, object] = {}

    def run(command: list[str], *, env: dict[str, str], check: bool) -> SimpleNamespace:
        captured["command"] = command
        captured["env"] = env
        captured["check"] = check
        return SimpleNamespace(returncode=0)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli.subprocess, "run", run)
    snapshot = LocalAuthSnapshot(
        cookie="MUSIC_U=child-only-secret",
        source="macos-desktop",
        cookie_names=("MUSIC_U",),
    )

    assert cli._run_docker_with_snapshot(snapshot, SimpleNamespace(no_build=True, detach=True)) == 0
    assert captured["command"] == ["docker", "compose", "up", "--detach"]
    assert captured["check"] is False
    environment = captured["env"]
    assert isinstance(environment, dict)
    assert environment["NETEASE_COOKIE"] == "MUSIC_U=child-only-secret"


def test_private_cache_keys_are_isolated_by_user_and_config() -> None:
    base = dict(
        backend="fake",
        operation="library",
        parameters={"page": 1},
        config_fingerprint="one",
    )
    first = build_cache_key(**base, authentication_scope="user:1")
    second = build_cache_key(**base, authentication_scope="user:2")
    changed = build_cache_key(
        **{**base, "config_fingerprint": "two"}, authentication_scope="user:1"
    )
    assert len({first, second, changed}) == 3


@pytest.mark.asyncio
async def test_sqlite_cache_lifecycle_and_no_cookie_storage(tmp_path: Path) -> None:
    path = tmp_path / "cache.sqlite3"
    cache = SQLiteCacheBackend(path)
    await cache.set("safe-key", '{"id":"1"}', 60)
    assert await cache.get("safe-key") == '{"id":"1"}'
    assert (await cache.stats()).entries == 1
    await cache.close()
    assert b"MUSIC_U" not in path.read_bytes()


@pytest.mark.asyncio
async def test_sqlite_clear_and_close_are_idempotent(tmp_path: Path) -> None:
    cache = SQLiteCacheBackend(tmp_path / "cache.sqlite3")
    await cache.set("one", "1", 60)
    assert await cache.clear() == 1
    await cache.close()
    await cache.close()
