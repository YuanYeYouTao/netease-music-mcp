import ast
from pathlib import Path

PACKAGE = Path("src/netease_music_mcp")


def imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def test_mcp_sdk_imports_are_isolated() -> None:
    violations = []
    for path in PACKAGE.rglob("*.py"):
        relative = path.relative_to(PACKAGE)
        allowed = relative.name in {"mcp_adapter.py", "server.py"} or relative.parts[0] == "tools"
        if "mcp" in imported_roots(path) and not allowed:
            violations.append(str(relative))
    assert violations == []


def test_tools_do_not_import_httpx() -> None:
    assert all("httpx" not in imported_roots(path) for path in (PACKAGE / "tools").glob("*.py"))


def test_project_has_no_qq_onebot_or_llm_runtime_dependency() -> None:
    dependency_text = Path("pyproject.toml").read_text(encoding="utf-8").casefold()
    for forbidden in ("onebot", "napcat", "openai", "anthropic", "langchain"):
        assert forbidden not in dependency_text
