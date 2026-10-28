import ast
import os
from pathlib import Path

from lint.schemas import Rule, Violation

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def report(rule: Rule, node: ast.AST, detail: str = "") -> Violation:
    line = int(getattr(node, "lineno", 1))
    column = int(getattr(node, "col_offset", 0)) + 1
    return Violation(line, column, rule.code, rule.message.format(detail))


def absolute_root_parts(path: Path) -> tuple[str, ...]:
    resolved = path.resolve()
    inside = resolved.is_relative_to(PROJECT_ROOT)
    return resolved.relative_to(PROJECT_ROOT).parts if inside else ()


def root_parts(path: Path) -> tuple[str, ...]:
    return (
        absolute_root_parts(path)
        if path.is_absolute()
        else Path(os.path.normpath(path)).parts
    )


def is_inside(path: Path, folder_parts: tuple[str, ...]) -> bool:
    return root_parts(path)[: len(folder_parts)] == folder_parts


def is_file(path: Path, file_parts: tuple[str, ...]) -> bool:
    return root_parts(path) == file_parts
