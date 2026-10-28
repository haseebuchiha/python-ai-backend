from pathlib import Path

import pytest

from lint.checker import text_violations
from lint.tests.reporting import all_reported_codes, reported_codes

ELSE_AFTER_EXIT_SNIPPETS = [
    """
    def pick(ready: bool) -> int:
        if ready:
            return 1
        else:
            return 2
    """,
    """
    def pick(ready: bool) -> int:
        if ready:
            raise ValueError
        else:
            return 2
    """,
    """
    def pick(level: int) -> int:
        if level > 2:
            return 1
        elif level > 1:
            return 2
        else:
            return 3
    """,
    """
    def pick(ready: bool, late: bool) -> int:
        if ready:
            return 1
        else:
            if late:
                return 2
            return 3
    """,
]
LENIENT_ELSE_SNIPPETS = [
    """
    def pick(level: int) -> int:
        if level > 2:
            return 1
        elif level > 1:
            return 2
        return 3
    """,
    """
    def pick(ready: bool) -> None:
        if ready:
            ship()
        else:
            hold()
    """,
]
NESTED_TERNARY_SNIPPETS = [
    "label = 'a' if ready else 'b' if late else 'c'\n",
    "label = ('a' if ready else 'b') if late else 'c'\n",
    "label = 'a' if ('x' if ready else '') else 'c'\n",
]
NEGATED_SNIPPETS = [
    "if not ready:\n    hold()\nelse:\n    ship()\n",
    "if status != 'open':\n    hold()\nelse:\n    ship()\n",
    "if order is not None:\n    ship()\nelse:\n    hold()\n",
    "if sku not in prices:\n    hold()\nelse:\n    ship()\n",
    "label = 'late' if not ready else 'on time'\n",
]
POSITIVE_SNIPPETS = [
    "if not ready:\n    hold()\n",
    "if not ready:\n    hold()\nelif late:\n    ship()\n",
    "label = 'on time' if ready else 'late'\n",
    "if ready:\n    ship()\nelse:\n    hold()\n",
]
BUSY_EXPRESSION_SNIPPETS = [
    "ready = first and second and third and fourth\n",
    "ready = (first or second) and (third or fourth)\n",
    "ready = not (first and second and third and fourth)\n",
    "if first and second or third and fourth:\n    ship()\n",
]
SIMPLE_EXPRESSION_SNIPPETS = [
    "ready = first and second and third\n",
    "ready = first and not (second or third)\n",
    "ready = first and second and third\nlate = fourth or fifth or sixth\n",
]


@pytest.mark.parametrize("snippet", ELSE_AFTER_EXIT_SNIPPETS)
def test_else_after_exit_is_reported(snippet: str) -> None:
    assert "BOS501" in reported_codes(snippet)


@pytest.mark.parametrize("snippet", LENIENT_ELSE_SNIPPETS)
def test_elif_and_plain_else_are_allowed(snippet: str) -> None:
    assert "BOS501" not in reported_codes(snippet)


@pytest.mark.parametrize("snippet", NESTED_TERNARY_SNIPPETS)
def test_nested_ternaries_are_reported(snippet: str) -> None:
    assert "BOS502" in reported_codes(snippet)


def test_single_ternary_is_allowed() -> None:
    assert "BOS502" not in reported_codes("label = 'a' if ready else 'b'\n")


@pytest.mark.parametrize("snippet", NEGATED_SNIPPETS)
def test_negated_conditions_are_reported(snippet: str) -> None:
    assert "BOS503" in reported_codes(snippet)


@pytest.mark.parametrize("snippet", POSITIVE_SNIPPETS)
def test_positive_conditions_are_allowed(snippet: str) -> None:
    assert "BOS503" not in reported_codes(snippet)


@pytest.mark.parametrize("snippet", BUSY_EXPRESSION_SNIPPETS)
def test_busy_expressions_are_reported(snippet: str) -> None:
    assert "BOS504" in reported_codes(snippet)


@pytest.mark.parametrize("snippet", SIMPLE_EXPRESSION_SNIPPETS)
def test_simple_expressions_are_allowed(snippet: str) -> None:
    assert "BOS504" not in reported_codes(snippet)


def test_busy_expression_reported_once() -> None:
    snippet = "ready = (first and second and third and fourth) or fifth\n"
    assert all_reported_codes(snippet).count("BOS504") == 1


def negated_message(snippet: str) -> str:
    return next(
        violation.message
        for violation in text_violations(snippet, Path("module.py"))
        if violation.code == "BOS503"
    )


@pytest.mark.parametrize(
    ("snippet", "suggestion"),
    [
        (
            "label = 'late' if not ready else 'on time'\n",
            "'on time' if ready else 'late'",
        ),
        (
            "label = 'a' if status != 'open' else 'b'\n",
            "'b' if status == 'open' else 'a'",
        ),
        (
            "label = 'a' if order is not None else 'b'\n",
            "'b' if order is None else 'a'",
        ),
        (
            "label = 'a' if sku not in prices else 'b'\n",
            "'b' if sku in prices else 'a'",
        ),
    ],
)
def test_negated_ternary_gives_the_rewrite(snippet: str, suggestion: str) -> None:
    assert f"Write `{suggestion}` instead" in negated_message(snippet)


def test_negated_if_names_the_flipped_test() -> None:
    snippet = "if status != 'open':\n    hold()\nelse:\n    ship()\n"
    assert "Test `status == 'open'` instead" in negated_message(snippet)
