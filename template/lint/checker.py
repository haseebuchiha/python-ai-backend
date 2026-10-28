import ast
import sys
from collections.abc import Callable
from itertools import chain
from pathlib import Path

from lint.banned import (
    banned_api_violations,
    environment_violations,
    type_checking_violations,
)
from lint.bindings import (
    outer_rebinding_violations,
    parameter_change_violations,
    reassignment_violations,
)
from lint.branching import (
    boolean_operator_violations,
    else_after_exit_violations,
    negated_condition_violations,
    nested_ternary_violations,
)
from lint.comments import comment_violations, docstring_violations
from lint.core import is_file, is_inside
from lint.naming import constant_case_violations, naming_violations
from lint.plurals import plural_violations
from lint.schemas import Rule, SourceFile, Violation
from lint.structure import (
    class_violations,
    discarded_loop_violations,
    loop_violations,
    nested_function_violations,
    parameter_count_violations,
    placement_violations,
)

type Check = Callable[[SourceFile], list[Violation]]

CHECKS: tuple[Check, ...] = (
    comment_violations,
    docstring_violations,
    loop_violations,
    discarded_loop_violations,
    reassignment_violations,
    outer_rebinding_violations,
    parameter_change_violations,
    class_violations,
    placement_violations,
    else_after_exit_violations,
    nested_ternary_violations,
    negated_condition_violations,
    boolean_operator_violations,
    nested_function_violations,
    parameter_count_violations,
    naming_violations,
    constant_case_violations,
    plural_violations,
    banned_api_violations,
    environment_violations,
    type_checking_violations,
)
SYNTAX_ERROR = Rule("BOS001", "The file does not parse ({}). Fix the syntax first.")
TEST_FOLDERS = (("tests",), ("lint", "tests"))
ROOT_CONFTEST_PARTS = ("conftest.py",)


def is_test_path(path: Path) -> bool:
    in_test_folder = any(is_inside(path, folder) for folder in TEST_FOLDERS)
    return in_test_folder or is_file(path, ROOT_CONFTEST_PARTS)


def source_violations(source: SourceFile) -> list[Violation]:
    return sorted(chain.from_iterable(check(source) for check in CHECKS))


def text_violations(text: str, path: Path) -> list[Violation]:
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as error:
        detail = SYNTAX_ERROR.message.format(error.msg)
        return [
            Violation(error.lineno or 1, error.offset or 1, SYNTAX_ERROR.code, detail)
        ]
    return source_violations(SourceFile(path, text, tree, is_test_path(path)))


def is_hidden(path: Path) -> bool:
    return any(part.startswith(".") and part not in {".", ".."} for part in path.parts)


def python_files(path: Path) -> list[Path]:
    found_paths = sorted(path.rglob("*.py")) if path.is_dir() else [path]
    return [candidate for candidate in found_paths if not is_hidden(candidate)]


def format_violation(path: Path, violation: Violation) -> str:
    position = f"{path}:{violation.line}:{violation.column}"
    return f"{position}: {violation.code} {violation.message}\n"


def report_lines(arguments: list[str]) -> list[str]:
    paths = [found for argument in arguments for found in python_files(Path(argument))]
    return [
        format_violation(path, violation)
        for path in paths
        for violation in text_violations(path.read_text(encoding="utf-8"), path)
    ]


def main() -> int:
    lines = report_lines(sys.argv[1:] or ["."])
    sys.stdout.writelines(lines)
    return 1 if lines else 0
