import sys
from pathlib import Path

import pytest

from lint.checker import is_test_path, main, report_lines
from lint.tests.reporting import reported_codes

LINT_FOLDER = Path(__file__).parents[1]
SOURCE_FOLDER = LINT_FOLDER.parent / "app"
TEST_PATHS = [
    "tests/test_orders.py",
    "tests/unit/test_x.py",
    "lint/tests/reporting.py",
    "lint/tests/conftest.py",
    "conftest.py",
    "./tests/../conftest.py",
    str(Path(__file__).resolve()),
    str(LINT_FOLDER.resolve() / "tests" / "conftest.py"),
]
SOURCE_PATHS = [
    "app/orders.py",
    "lint/naming.py",
    "app/services/test_quotes.py",
    "app/tests/x.py",
    "app/services/conftest.py",
    "x/tests/test_orders.py",
    "x/lint/tests/test_orders.py",
    "tests/../app/orders.py",
    "/srv/other-project/tests/test_orders.py",
    "/srv/other-project/conftest.py",
    str(SOURCE_FOLDER.resolve() / "services" / "test_quotes.py"),
]
TEST_ONLY_SNIPPET = "class Quote(BaseModel):\n    data: int\n"


def test_syntax_errors_are_reported() -> None:
    assert reported_codes("def broken(:\n") == {"BOS001"}


def test_checker_passes_its_own_rules() -> None:
    assert report_lines([str(LINT_FOLDER)]) == []


def test_source_code_passes_the_rules() -> None:
    assert report_lines([str(SOURCE_FOLDER)]) == []


@pytest.mark.parametrize("path", TEST_PATHS)
def test_test_paths_are_detected(path: str) -> None:
    assert is_test_path(Path(path))


@pytest.mark.parametrize("path", SOURCE_PATHS)
def test_source_paths_are_not_tests(path: str) -> None:
    assert not is_test_path(Path(path))


@pytest.mark.parametrize("path", TEST_PATHS)
def test_tests_get_their_allowances(path: str) -> None:
    assert not reported_codes(TEST_ONLY_SNIPPET, path) & {"BOS403", "BOS704"}


@pytest.mark.parametrize("path", SOURCE_PATHS)
def test_other_files_follow_every_rule(path: str) -> None:
    assert {"BOS403", "BOS704"} <= reported_codes(TEST_ONLY_SNIPPET, path)


def test_main_fails_on_violations(
    scratch_folder: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    commented_file = scratch_folder / "orders.py"
    commented_file.write_text("total = compute()  # note\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["lint", str(commented_file)])
    assert main() == 1
    assert "BOS101" in capsys.readouterr().out


def test_main_passes_clean_folders(
    scratch_folder: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    hidden_folder = scratch_folder / ".venv"
    hidden_folder.mkdir()
    (hidden_folder / "vendored.py").write_text("total = 1  # note\n", encoding="utf-8")
    (scratch_folder / "orders.py").write_text("TOTAL = 1\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["lint", str(scratch_folder)])
    assert main() == 0
    assert not capsys.readouterr().out
