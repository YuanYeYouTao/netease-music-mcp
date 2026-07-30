import argparse
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from netease_music_mcp.clients import AuthenticationProvider, NeteaseHttpClient
from netease_music_mcp.config import Settings, Transport
from netease_music_mcp.domain.errors import MusicMCPError
from netease_music_mcp.lifespan import create_cache


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="netease-music-mcp")
    subcommands = parser.add_subparsers(dest="command", required=True)
    serve = subcommands.add_parser("serve", help="Run the MCP server")
    serve.add_argument("--transport", choices=[item.value for item in Transport])
    serve.add_argument("--host")
    serve.add_argument("--port", type=int)
    serve.add_argument("--path")
    subcommands.add_parser("doctor", help="Check configuration and upstream access")
    subcommands.add_parser("config", help="Print redacted effective configuration")
    cache = subcommands.add_parser("cache", help="Manage normalized data cache")
    cache_subcommands = cache.add_subparsers(dest="cache_command", required=True)
    cache_subcommands.add_parser("clear", help="Clear cached data")
    cache_subcommands.add_parser("stats", help="Show cache statistics")
    return parser


def _settings_with_cli(args: argparse.Namespace) -> Settings:
    settings = Settings()
    updates: dict[str, Any] = {}
    for argument, field in (
        ("transport", "mcp_transport"),
        ("host", "mcp_host"),
        ("port", "mcp_port"),
        ("path", "mcp_path"),
    ):
        value = getattr(args, argument, None)
        if value is not None:
            updates[field] = value
    return Settings.model_validate({**settings.model_dump(), **updates})


def _config_output(settings: Settings) -> dict[str, Any]:
    sensitive = {"cookie", "music_u", "csrf"}
    values = settings.model_dump(mode="json", exclude=sensitive)
    values["cookie_configured"] = settings.cookie_configured
    env_file_keys: set[str] = set()
    env_path = Path(".env")
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            key, separator, _value = line.partition("=")
            if separator and key.strip() and not key.lstrip().startswith("#"):
                env_file_keys.add(key.strip())
    sources = {
        field: (
            "environment"
            if f"NETEASE_{field.upper()}" in os.environ
            else ".env"
            if f"NETEASE_{field.upper()}" in env_file_keys
            else "default"
        )
        for field in values
        if field != "cookie_configured"
    }
    sources["cookie_configured"] = "redacted"
    return {"values": values, "sources": sources}


async def _cache_command(settings: Settings, command: str) -> int:
    cache = create_cache(settings)
    try:
        if command == "clear":
            print(json.dumps({"cleared_entries": await cache.clear()}))
        else:
            print(json.dumps((await cache.stats()).as_dict()))
        return 0
    finally:
        await cache.close()


async def _doctor(settings: Settings) -> int:
    checks: list[dict[str, Any]] = []
    authentication = AuthenticationProvider.from_settings(settings)
    checks.append({"name": "configuration", "ok": True, "critical": True})
    checks.append(
        {
            "name": "cookie_configured",
            "ok": settings.cookie_configured,
            "critical": False,
        }
    )
    cache_parent = settings.cache_path.parent
    try:
        cache_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=cache_parent, delete=True):
            pass
        checks.append({"name": "cache_writable", "ok": True, "critical": True})
    except OSError:
        checks.append({"name": "cache_writable", "ok": False, "critical": True})
    client = NeteaseHttpClient(settings, authentication)
    try:
        try:
            search = await client.request_json(
                "POST", "/api/search/get", data={"s": "test", "type": 1, "limit": 1, "offset": 0}
            )
            checks.append(
                {
                    "name": "public_search",
                    "ok": search.get("code") == 200,
                    "critical": True,
                }
            )
        except MusicMCPError as exc:
            checks.append(
                {
                    "name": "public_search",
                    "ok": False,
                    "critical": True,
                    "error_code": exc.error_code,
                }
            )
        if settings.cookie_configured:
            try:
                account = await client.request_json("GET", "/api/nuser/account/get")
                profile = account.get("profile")
                checks.append(
                    {
                        "name": "authentication",
                        "ok": account.get("code") == 200 and isinstance(profile, dict),
                        "critical": True,
                    }
                )
            except MusicMCPError as exc:
                checks.append(
                    {
                        "name": "authentication",
                        "ok": False,
                        "critical": True,
                        "error_code": exc.error_code,
                    }
                )
    finally:
        await client.close()
    print(json.dumps({"checks": checks}, ensure_ascii=False, indent=2))
    return 1 if any(not item["ok"] and item["critical"] for item in checks) else 0


def main() -> None:
    args = _parser().parse_args()
    try:
        settings = _settings_with_cli(args)
    except ValidationError as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    if args.command == "serve":
        from netease_music_mcp.lifespan import create_application
        from netease_music_mcp.mcp_adapter import MCPV1ServerAdapter

        adapter = MCPV1ServerAdapter(create_application(settings), settings)
        if settings.mcp_transport is Transport.STDIO:
            adapter.run_stdio()
        else:
            adapter.run_streamable_http()
        return
    if args.command == "config":
        print(json.dumps(_config_output(settings), ensure_ascii=False, indent=2))
        return
    if args.command == "doctor":
        raise SystemExit(asyncio.run(_doctor(settings)))
    raise SystemExit(asyncio.run(_cache_command(settings, args.cache_command)))
