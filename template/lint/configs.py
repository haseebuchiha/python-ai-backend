import sys
import tomllib
from pathlib import Path

ROOT_CONFIG_NAME = "pyproject.toml"
CONFIG_NAMES = frozenset({"ruff.toml", ".ruff.toml", ROOT_CONFIG_NAME})
ALLOWED_SETTINGS = frozenset({"extend", "lint.pylint.max-statements"})
MAX_STATEMENTS = 10
NOT_EXTENDED = (
    "{}: a nested ruff config must set extend to the root pyproject.toml, "
    "so every rule still applies here.\n"
)
EXTRA_SETTINGS = (
    "{}: a nested ruff config may only change lint.pylint.max-statements, "
    "not {}. Change the root pyproject.toml instead.\n"
)
TOO_MANY_STATEMENTS = (
    "{}: a nested ruff config may raise lint.pylint.max-statements to an "
    "integer of at most 10, not {}. Split the function instead.\n"
)


def child_settings(document: object, key: str) -> dict[str, object]:
    found = document.get(key) if isinstance(document, dict) else None
    return found if isinstance(found, dict) else {}


def ruff_settings(path: Path) -> dict[str, object]:
    document = tomllib.loads(path.read_text(encoding="utf-8"))
    is_pyproject = path.name == ROOT_CONFIG_NAME
    tool_settings = child_settings(document, "tool")
    return child_settings(tool_settings, "ruff") if is_pyproject else document


def setting_keys(settings: dict[str, object], prefix: str = "") -> set[str]:
    return {
        key
        for name, value in settings.items()
        for key in (
            setting_keys(value, f"{prefix}{name}.")
            if isinstance(value, dict)
            else {f"{prefix}{name}"}
        )
    }


def extends_root(path: Path, settings: dict[str, object], root: Path) -> bool:
    extended = (path.parent / str(settings.get("extend", ""))).resolve()
    return extended == (root / ROOT_CONFIG_NAME).resolve()


def statement_limit_problems(path: Path, settings: dict[str, object]) -> list[str]:
    pylint_settings = child_settings(child_settings(settings, "lint"), "pylint")
    limit = pylint_settings.get("max-statements", MAX_STATEMENTS)
    fits = type(limit) is int and limit <= MAX_STATEMENTS
    return [] if fits else [TOO_MANY_STATEMENTS.format(path, limit)]


def config_problems(path: Path, root: Path) -> list[str]:
    settings = ruff_settings(path)
    extra_settings = sorted(setting_keys(settings) - ALLOWED_SETTINGS)
    missing_extend = bool(settings) and not extends_root(path, settings, root)
    extend_problems = [NOT_EXTENDED.format(path)] if missing_extend else []
    setting_problems = [EXTRA_SETTINGS.format(path, ", ".join(extra_settings))]
    return [
        *extend_problems,
        *(setting_problems if extra_settings else []),
        *statement_limit_problems(path, settings),
    ]


def visible_subfolders(folder: Path) -> list[Path]:
    return [
        entry
        for entry in sorted(folder.iterdir())
        if entry.is_dir() and not entry.name.startswith(".")
    ]


def config_paths(folder: Path) -> list[Path]:
    configs = [
        entry for entry in sorted(folder.iterdir()) if entry.name in CONFIG_NAMES
    ]
    nested_configs = [
        found for inner in visible_subfolders(folder) for found in config_paths(inner)
    ]
    return [*configs, *nested_configs]


def nested_config_problems(root: Path) -> list[str]:
    root_config = root / ROOT_CONFIG_NAME
    return [
        problem
        for path in config_paths(root)
        if path != root_config
        for problem in config_problems(path, root)
    ]


def main() -> int:
    problems = nested_config_problems(Path(*sys.argv[1:2]))
    sys.stdout.writelines(problems)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
