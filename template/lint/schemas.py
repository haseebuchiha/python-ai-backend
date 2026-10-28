import ast
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple


class Rule(NamedTuple):
    code: str
    message: str


class Violation(NamedTuple):
    line: int
    column: int
    code: str
    message: str


class SourceFile(NamedTuple):
    path: Path
    text: str
    tree: ast.Module
    is_test: bool


class NameCheck(NamedTuple):
    rule: Rule
    finder: Callable[[str], list[str]]


class Binding(NamedTuple):
    name: str
    node: ast.AST
    kind: str
