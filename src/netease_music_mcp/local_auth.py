"""Host-side import of the signed-in NetEase desktop client's local session."""

from __future__ import annotations

import base64
import ctypes
import hashlib
import json
import os
import platform
import plistlib
import sqlite3
import subprocess
import sys
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_COOKIE_NAMES = (
    "MUSIC_U",
    "MUSIC_A_T",
    "MUSIC_R_T",
    "MUSIC_R_U",
    "NMTID",
    "__csrf",
)
_AUTH_COOKIE_NAMES = frozenset({"MUSIC_U", "MUSIC_A_T", "MUSIC_R_T", "MUSIC_R_U"})
_COOKIE_HOST_SUFFIXES = ("music.163.com", "163.com", "netease.com")


class LocalAuthError(RuntimeError):
    """A local desktop authentication snapshot could not be obtained safely."""


@dataclass(frozen=True, repr=False)
class LocalAuthSnapshot:
    """Ephemeral credentials and metadata imported from the host application."""

    cookie: str = field(repr=False)
    source: str
    cookie_names: tuple[str, ...]

    def __repr__(self) -> str:
        return f"LocalAuthSnapshot(source={self.source!r}, cookie_names={self.cookie_names!r})"


def _now_chrome_micros() -> int:
    return int((time.time() + 11_644_473_600) * 1_000_000)


def _cookie_value(value: object) -> str | None:
    if isinstance(value, str):
        return value or None
    if isinstance(value, bytes):
        try:
            decoded = value.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise LocalAuthError("desktop cookie value is not valid UTF-8") from exc
        return decoded or None
    return None


def _build_cookie_header(values: Mapping[str, str]) -> str:
    parts: list[str] = []
    for name in _COOKIE_NAMES:
        value = values.get(name)
        if not value:
            continue
        if "\r" in value or "\n" in value:
            raise LocalAuthError("desktop cookie contains an invalid line break")
        parts.append(f"{name}={value}")
    if not _AUTH_COOKIE_NAMES.intersection(values):
        raise LocalAuthError("desktop client is not signed in or no NetEase auth cookie was found")
    if not parts:
        raise LocalAuthError("desktop client cookie database did not contain usable values")
    return "; ".join(parts)


def _is_netease_host(value: object) -> bool:
    if not isinstance(value, str):
        return False
    host = value.strip().lower().lstrip(".")
    return any(host == suffix or host.endswith(f".{suffix}") for suffix in _COOKIE_HOST_SUFFIXES)


def _plist_object(value: object, objects: list[object]) -> object:
    if not isinstance(value, plistlib.UID):
        return value
    index = value.data
    if not isinstance(index, int) or index < 0 or index >= len(objects):
        raise LocalAuthError("desktop authentication archive contains an invalid reference")
    return objects[index]


def _plist_dictionary(value: object, objects: list[object]) -> dict[str, object]:
    resolved = _plist_object(value, objects)
    if not isinstance(resolved, dict):
        return {}
    keys = resolved.get("NS.keys")
    values = resolved.get("NS.objects")
    if not isinstance(keys, list) or not isinstance(values, list) or len(keys) != len(values):
        return {}
    result: dict[str, object] = {}
    for key_ref, value_ref in zip(keys, values, strict=True):
        key = _plist_object(key_ref, objects)
        if isinstance(key, str):
            result[key] = _plist_object(value_ref, objects)
    return result


def _read_mmkv_entries(path: Path) -> dict[str, bytes]:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise LocalAuthError("desktop authentication store could not be read") from exc
    if len(payload) < 8:
        raise LocalAuthError("desktop authentication store is invalid")

    def read_varint(position: int) -> tuple[int, int]:
        value = 0
        for shift in range(0, 35, 7):
            if position >= len(payload):
                raise LocalAuthError("desktop authentication store is truncated")
            byte = payload[position]
            position += 1
            value |= (byte & 0x7F) << shift
            if not byte & 0x80:
                return value, position
        raise LocalAuthError("desktop authentication store has an invalid length")

    entries: dict[str, bytes] = {}
    position = 8
    while position < len(payload) and payload[position] != 0:
        key_length, position = read_varint(position)
        if key_length == 0 or position + key_length > len(payload):
            break
        key_bytes = payload[position : position + key_length]
        position += key_length
        try:
            key = key_bytes.decode("utf-8")
        except UnicodeDecodeError:
            break
        value_length, position = read_varint(position)
        if position + value_length > len(payload):
            break
        entries[key] = payload[position : position + value_length]
        position += value_length
    return entries


def read_mmkv_cookie_store(path: Path) -> dict[str, str]:
    """Read the allowlisted cookies from the desktop client's MMKV archive."""

    entries = _read_mmkv_entries(path)
    raw_cookie = entries.get("cookie")
    if raw_cookie is None:
        raise LocalAuthError("desktop authentication store has no cookie archive")
    plist_offset = 0 if raw_cookie.startswith(b"bplist00") else 2
    if raw_cookie[plist_offset : plist_offset + 8] != b"bplist00":
        raise LocalAuthError("desktop cookie archive is not a binary property list")
    try:
        archive = plistlib.loads(raw_cookie[plist_offset:])
    except (plistlib.InvalidFileException, ValueError, OSError, TypeError, OverflowError) as exc:
        raise LocalAuthError("desktop cookie archive could not be decoded") from exc
    if not isinstance(archive, dict):
        raise LocalAuthError("desktop cookie archive has an invalid root")
    objects = archive.get("$objects")
    top = archive.get("$top")
    if not isinstance(objects, list) or not isinstance(top, dict):
        raise LocalAuthError("desktop cookie archive has an invalid object table")
    root = _plist_dictionary(top.get("root"), objects)

    selected: dict[str, tuple[int, str]] = {}
    for domain, cookie_map_ref in root.items():
        if not _is_netease_host(domain):
            continue
        cookie_map = _plist_dictionary(cookie_map_ref, objects)
        for cookie_ref in cookie_map.values():
            cookie_object = _plist_object(cookie_ref, objects)
            if not isinstance(cookie_object, dict):
                continue
            properties = _plist_dictionary(cookie_object.get("properties"), objects)
            name = properties.get("Name")
            value = _cookie_value(properties.get("Value"))
            cookie_domain = properties.get("Domain", domain)
            if not isinstance(name, str) or name not in _COOKIE_NAMES:
                continue
            if not _is_netease_host(cookie_domain) or value is None:
                continue
            normalized_domain = str(cookie_domain).strip().lower().lstrip(".")
            rank = 0 if normalized_domain == "music.163.com" else 1
            previous = selected.get(name)
            if previous is None or rank < previous[0]:
                selected[name] = (rank, value)
    return {name: value for name, (_rank, value) in selected.items()}


def read_chromium_cookie_database(
    path: Path,
    *,
    decrypt_value: Callable[[bytes], str] | None = None,
) -> dict[str, str]:
    """Read only the NetEase cookie allowlist from a Chromium cookie database.

    The database is opened read-only. Callers provide decryption so this parser can be
    tested without touching a real Keychain or DPAPI secret.
    """

    if not path.is_file():
        raise LocalAuthError("desktop cookie database was not found")
    host_clauses = " OR ".join(
        "(LOWER(host_key) = ? OR LOWER(host_key) LIKE ?)" for _ in _COOKIE_HOST_SUFFIXES
    )
    name_placeholders = ", ".join("?" for _ in _COOKIE_NAMES)
    query = (
        "SELECT name, value, encrypted_value, host_key, expires_utc, last_access_utc "
        "FROM cookies "
        f"WHERE name IN ({name_placeholders}) AND ({host_clauses}) "
        "ORDER BY CASE WHEN host_key IN ('music.163.com', '.music.163.com') "
        "THEN 0 ELSE 1 END, length(host_key) DESC, last_access_utc DESC"
    )
    host_parameters = [
        value for suffix in _COOKIE_HOST_SUFFIXES for value in (suffix, f"%.{suffix}")
    ]
    parameters = [*_COOKIE_NAMES, *host_parameters]
    values: dict[str, str] = {}
    try:
        connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
        try:
            rows = connection.execute(query, parameters).fetchall()
        finally:
            connection.close()
    except (OSError, sqlite3.Error) as exc:
        raise LocalAuthError("desktop cookie database could not be opened read-only") from exc

    now = _now_chrome_micros()
    for name, value, encrypted_value, _host_key, expires_utc, _last_access_utc in rows:
        if not isinstance(name, str) or name in values:
            continue
        if isinstance(expires_utc, int) and expires_utc > 0 and expires_utc < now:
            continue
        decoded = _cookie_value(value)
        if decoded is None and encrypted_value:
            if decrypt_value is None:
                raise LocalAuthError("desktop cookie is encrypted and needs host decryption")
            if not isinstance(encrypted_value, bytes):
                encrypted_value = bytes(encrypted_value)
            decoded = decrypt_value(encrypted_value)
        if decoded:
            values[name] = decoded
    return values


def _decrypt_aes_gcm(value: bytes, key: bytes) -> str:
    if not value.startswith((b"v10", b"v11")) or len(value) <= 15:
        raise LocalAuthError("unsupported Chromium cookie encryption format")
    try:
        plaintext = AESGCM(key).decrypt(value[3:15], value[15:], None)
    except Exception as exc:  # cryptography exposes provider-specific exceptions
        raise LocalAuthError("desktop cookie decryption failed") from exc
    try:
        return plaintext.rstrip(b"\x00").decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LocalAuthError("decrypted desktop cookie is not valid UTF-8") from exc


def _mac_keychain_key() -> bytes:
    candidates = (
        ("Chromium", "Chromium Safe Storage"),
        ("Chrome", "Chrome Safe Storage"),
        ("Chromium", "Chrome Safe Storage"),
    )
    for account, service in candidates:
        result = subprocess.run(
            ["/usr/bin/security", "find-generic-password", "-a", account, "-s", service, "-w"],
            capture_output=True,
            text=True,
            check=False,
        )
        secret = result.stdout.strip().encode("utf-8")
        if result.returncode == 0 and secret:
            return hashlib.pbkdf2_hmac("sha1", secret, b"saltysalt", 1003, 16)
    raise LocalAuthError("macOS Keychain did not provide Chromium Safe Storage access")


def _windows_unprotect(value: bytes) -> bytes:
    if sys.platform != "win32":
        raise LocalAuthError("Windows DPAPI is only available on Windows")
    from ctypes import wintypes

    class DataBlob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

    crypt_unprotect = ctypes.windll.crypt32.CryptUnprotectData
    crypt_unprotect.argtypes = [
        ctypes.POINTER(DataBlob),
        ctypes.c_wchar_p,
        ctypes.POINTER(DataBlob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(DataBlob),
    ]
    crypt_unprotect.restype = wintypes.BOOL
    input_buffer = ctypes.create_string_buffer(value)
    input_blob = DataBlob(len(value), ctypes.cast(input_buffer, ctypes.POINTER(ctypes.c_byte)))
    output_blob = DataBlob()
    if not crypt_unprotect(
        ctypes.byref(input_blob), None, None, None, None, 0, ctypes.byref(output_blob)
    ):
        raise LocalAuthError("Windows DPAPI could not decrypt the desktop cookie")
    try:
        return ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(output_blob.pbData)


def _windows_local_state(cookie_db: Path) -> Path | None:
    candidates = [parent / "Local State" for parent in cookie_db.parents]
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def _windows_cookie_key(cookie_db: Path) -> bytes:
    local_state = _windows_local_state(cookie_db)
    if local_state is None:
        raise LocalAuthError("Windows Chromium Local State file was not found")
    try:
        payload = json.loads(local_state.read_text(encoding="utf-8"))
        encrypted_key = base64.b64decode(payload["os_crypt"]["encrypted_key"])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise LocalAuthError("Windows Chromium encryption metadata is invalid") from exc
    if encrypted_key.startswith(b"DPAPI"):
        encrypted_key = encrypted_key[5:]
    return _windows_unprotect(encrypted_key)


def _mac_cookie_decryptor() -> Callable[[bytes], str]:
    key: bytes | None = None

    def decrypt(value: bytes) -> str:
        nonlocal key
        if key is None:
            key = _mac_keychain_key()
        return _decrypt_aes_gcm(value, key)

    return decrypt


def _windows_cookie_decryptor(cookie_db: Path) -> Callable[[bytes], str]:
    key: bytes | None = None

    def decrypt(value: bytes) -> str:
        nonlocal key
        if value.startswith((b"v10", b"v11")):
            if key is None:
                key = _windows_cookie_key(cookie_db)
            return _decrypt_aes_gcm(value, key)
        try:
            return _windows_unprotect(value).decode("utf-8").rstrip("\x00")
        except UnicodeDecodeError as exc:
            raise LocalAuthError("decrypted Windows desktop cookie is not valid UTF-8") from exc

    return decrypt


def _mac_cookie_databases(home: Path) -> tuple[Path, ...]:
    root = home / "Library" / "Application Support" / "com.netease.163music"
    explicit = root / "Documents" / "storage" / "CEFCache" / "Cookies"
    discovered: list[Path] = []
    if root.is_dir():
        try:
            discovered.extend(path for path in root.rglob("Cookies") if path.is_file())
        except OSError:
            pass
    return tuple(dict.fromkeys((explicit, *discovered)))


def _mac_mmkv_stores(home: Path) -> tuple[Path, ...]:
    root = home / "Library" / "Application Support" / "com.netease.163music"
    explicit = root / "Documents" / "storage" / "mmkv.default"
    discovered: list[Path] = []
    if root.is_dir():
        try:
            discovered.extend(path for path in root.rglob("mmkv.default") if path.is_file())
        except OSError:
            pass
    return tuple(dict.fromkeys((explicit, *discovered)))


def _windows_app_roots(env: Mapping[str, str], home: Path) -> tuple[Path, ...]:
    roots: list[Path] = []
    for key in ("APPDATA", "LOCALAPPDATA"):
        value = env.get(key)
        if value:
            roots.append(Path(value))
    roots.extend(
        [
            home / "AppData" / "Roaming",
            home / "AppData" / "Local",
        ]
    )
    app_roots: list[Path] = []
    for root in roots:
        for name in ("Netease", "NetEase", "NeteaseCloudMusic", "NeteaseMusic"):
            app_roots.extend((root / name / "CloudMusic", root / name))
    return tuple(dict.fromkeys(app_roots))


def _windows_cookie_databases(env: Mapping[str, str], home: Path) -> tuple[Path, ...]:
    candidates: list[Path] = []
    for root in _windows_app_roots(env, home):
        if not root.is_dir():
            continue
        try:
            candidates.extend(path for path in root.rglob("Cookies") if path.is_file())
        except OSError:
            continue
    return tuple(dict.fromkeys(candidates))


def _windows_mmkv_stores(env: Mapping[str, str], home: Path) -> tuple[Path, ...]:
    candidates: list[Path] = []
    for root in _windows_app_roots(env, home):
        if not root.is_dir():
            continue
        try:
            candidates.extend(path for path in root.rglob("mmkv.default") if path.is_file())
        except OSError:
            continue
    return tuple(dict.fromkeys(candidates))


class LocalAuthReader:
    """Discover and decrypt only the signed-in NetEase desktop app session."""

    def __init__(
        self,
        *,
        system: str | None = None,
        home: Path | None = None,
        env: Mapping[str, str] | None = None,
    ) -> None:
        self.system = system or platform.system()
        self.home = home or Path.home()
        self.env = os.environ if env is None else env

    def read(self) -> LocalAuthSnapshot:
        if self.system == "Darwin":
            stores = _mac_mmkv_stores(self.home)
            databases = _mac_cookie_databases(self.home)
            source = "macos-desktop"
        elif self.system == "Windows":
            stores = _windows_mmkv_stores(self.env, self.home)
            databases = _windows_cookie_databases(self.env, self.home)
            source = "windows-desktop"
        else:
            raise LocalAuthError("local desktop auth import supports Windows and macOS only")

        if not stores and not databases:
            raise LocalAuthError("NetEase desktop authentication store was not found")
        last_error: LocalAuthError | None = None

        def snapshot(values: dict[str, str]) -> LocalAuthSnapshot:
            cookie = _build_cookie_header(values)
            return LocalAuthSnapshot(
                cookie=cookie,
                source=source,
                cookie_names=tuple(sorted(values)),
            )

        for store in stores:
            try:
                return snapshot(read_mmkv_cookie_store(store))
            except LocalAuthError as exc:
                last_error = exc

        for database in databases:
            try:
                decryptor = (
                    _mac_cookie_decryptor()
                    if self.system == "Darwin"
                    else _windows_cookie_decryptor(database)
                )
                values = read_chromium_cookie_database(database, decrypt_value=decryptor)
                return snapshot(values)
            except LocalAuthError as exc:
                last_error = exc
                continue
        if last_error is not None:
            raise last_error
        raise LocalAuthError("NetEase desktop store did not contain a signed-in session")


def read_local_auth() -> LocalAuthSnapshot:
    return LocalAuthReader().read()
