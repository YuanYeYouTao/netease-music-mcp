import plistlib
import sqlite3
from pathlib import Path

import pytest

from netease_music_mcp.local_auth import (
    LocalAuthError,
    LocalAuthReader,
    LocalAuthSnapshot,
    read_chromium_cookie_database,
    read_mmkv_cookie_store,
)


def _write_cookie_db(path: Path, rows: list[tuple[str, str, bytes, str, int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "CREATE TABLE cookies ("
            "name TEXT, value TEXT, encrypted_value BLOB, host_key TEXT, "
            "expires_utc INTEGER, last_access_utc INTEGER)"
        )
        connection.executemany(
            "INSERT INTO cookies(name, value, encrypted_value, host_key, expires_utc, "
            "last_access_utc) "
            "VALUES (?, ?, ?, ?, ?, 1)",
            rows,
        )
        connection.commit()
    finally:
        connection.close()


def _write_mmkv_cookie_store(path: Path) -> None:
    objects: list[object] = ["$null"]

    def add(value: object) -> int:
        objects.append(value)
        return len(objects) - 1

    root_index = add(None)
    domain_index = add("music.163.com")
    domain_map_index = add(None)
    cookie_name_index = add("MUSIC_U")
    cookie_index = add(None)
    properties_index = add(None)
    domain_key_index = add("Domain")
    name_key_index = add("Name")
    value_key_index = add("Value")
    cookie_domain_index = add(".music.163.com")
    cookie_value_index = add("user")
    objects[root_index] = {
        "NS.keys": [plistlib.UID(domain_index)],
        "NS.objects": [plistlib.UID(domain_map_index)],
    }
    objects[domain_map_index] = {
        "NS.keys": [plistlib.UID(cookie_name_index)],
        "NS.objects": [plistlib.UID(cookie_index)],
    }
    objects[cookie_index] = {"properties": plistlib.UID(properties_index)}
    objects[properties_index] = {
        "NS.keys": [
            plistlib.UID(domain_key_index),
            plistlib.UID(name_key_index),
            plistlib.UID(value_key_index),
        ],
        "NS.objects": [
            plistlib.UID(cookie_domain_index),
            plistlib.UID(cookie_name_index),
            plistlib.UID(cookie_value_index),
        ],
    }
    archive = {
        "$version": 100000,
        "$archiver": "NSKeyedArchiver",
        "$top": {"root": plistlib.UID(root_index)},
        "$objects": objects,
    }
    value = b"\x87\x3a" + plistlib.dumps(archive, fmt=plistlib.FMT_BINARY)
    path.parent.mkdir(parents=True, exist_ok=True)

    def encode_varint(number: int) -> bytes:
        encoded = bytearray()
        while number >= 0x80:
            encoded.append((number & 0x7F) | 0x80)
            number >>= 7
        encoded.append(number)
        return bytes(encoded)

    path.write_bytes(
        b"\0" * 8 + encode_varint(len(b"cookie")) + b"cookie" + encode_varint(len(value)) + value
    )


def test_cookie_parser_reads_allowlist_and_ignores_other_hosts(tmp_path: Path) -> None:
    path = tmp_path / "Cookies"
    _write_cookie_db(
        path,
        [
            ("MUSIC_R_U", "user", b"", ".music.163.com", 0),
            ("NMTID", "nmtid", b"", ".music.163.com", 0),
            ("unrelated", "secret", b"", ".music.163.com", 0),
            ("MUSIC_U", "other-host", b"", ".example.invalid", 0),
            ("MUSIC_U", "lookalike-host", b"", "evil163.com", 0),
        ],
    )
    values = read_chromium_cookie_database(path)
    assert values == {"MUSIC_R_U": "user", "NMTID": "nmtid"}


def test_cookie_parser_uses_injected_decryptor_without_logging_values(tmp_path: Path) -> None:
    path = tmp_path / "Cookies"
    _write_cookie_db(path, [("MUSIC_U", "", b"encrypted", ".music.163.com", 0)])
    seen: list[bytes] = []

    def decrypt(value: bytes) -> str:
        seen.append(value)
        return "decrypted-user"

    values = read_chromium_cookie_database(path, decrypt_value=decrypt)
    assert values == {"MUSIC_U": "decrypted-user"}
    assert seen == [b"encrypted"]


def test_mmkv_cookie_store_reads_nskeyedarchiver_cookie(tmp_path: Path) -> None:
    path = tmp_path / "mmkv.default"
    _write_mmkv_cookie_store(path)

    assert read_mmkv_cookie_store(path) == {"MUSIC_U": "user"}


def test_local_reader_prefers_macos_mmkv_store(tmp_path: Path) -> None:
    store = (
        tmp_path
        / "Library"
        / "Application Support"
        / "com.netease.163music"
        / "Documents"
        / "storage"
        / "mmkv.default"
    )
    _write_mmkv_cookie_store(store)

    snapshot = LocalAuthReader(system="Darwin", home=tmp_path, env={}).read()

    assert snapshot.cookie == "MUSIC_U=user"
    assert snapshot.source == "macos-desktop"


def test_local_reader_discovers_macos_database(tmp_path: Path) -> None:
    database = (
        tmp_path
        / "Library"
        / "Application Support"
        / "com.netease.163music"
        / "Documents"
        / "storage"
        / "CEFCache"
        / "Cookies"
    )
    _write_cookie_db(database, [("MUSIC_U", "user", b"", ".music.163.com", 0)])

    snapshot = LocalAuthReader(system="Darwin", home=tmp_path, env={}).read()
    assert snapshot.source == "macos-desktop"
    assert snapshot.cookie_names == ("MUSIC_U",)
    assert snapshot.cookie == "MUSIC_U=user"
    assert "user" not in repr(snapshot)


def test_local_reader_discovers_windows_database_without_decryption(tmp_path: Path) -> None:
    appdata = tmp_path / "AppData" / "Roaming"
    database = appdata / "Netease" / "CloudMusic" / "CEFCache" / "Cookies"
    _write_cookie_db(database, [("MUSIC_R_U", "user", b"", ".music.163.com", 0)])

    snapshot = LocalAuthReader(
        system="Windows",
        home=tmp_path,
        env={"APPDATA": str(appdata), "LOCALAPPDATA": str(tmp_path / "Local")},
    ).read()
    assert snapshot.source == "windows-desktop"
    assert snapshot.cookie == "MUSIC_R_U=user"


def test_local_reader_discovers_windows_mmkv_store(tmp_path: Path) -> None:
    appdata = tmp_path / "AppData" / "Roaming"
    store = appdata / "Netease" / "CloudMusic" / "mmkv.default"
    _write_mmkv_cookie_store(store)

    snapshot = LocalAuthReader(
        system="Windows",
        home=tmp_path,
        env={"APPDATA": str(appdata), "LOCALAPPDATA": str(tmp_path / "Local")},
    ).read()

    assert snapshot.source == "windows-desktop"
    assert snapshot.cookie == "MUSIC_U=user"


def test_local_reader_rejects_unsupported_host_platform(tmp_path: Path) -> None:
    with pytest.raises(LocalAuthError, match="Windows and macOS"):
        LocalAuthReader(system="Linux", home=tmp_path, env={}).read()


def test_snapshot_repr_never_contains_cookie() -> None:
    snapshot = LocalAuthSnapshot(
        cookie="MUSIC_U=do-not-print",
        source="macos-desktop",
        cookie_names=("MUSIC_U",),
    )
    assert "do-not-print" not in repr(snapshot)
