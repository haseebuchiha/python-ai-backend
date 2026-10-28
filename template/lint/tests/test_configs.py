import sys
from pathlib import Path

import pytest

from lint.configs import main, nested_config_problems

PROJECT_FOLDER = Path(__file__).parents[2]
ROOT_CONFIG = '[tool.ruff.lint]\nselect = ["ALL"]\n'
RAISED_LIMIT = 'extend = "../../pyproject.toml"\n\n[lint.pylint]\nmax-statements = 10\n'
BAD_NESTED_CONFIGS = [
    'extend = "../../pyproject.toml"\n\n[lint]\nignore = ["ALL"]\n',
    "[lint.pylint]\nmax-statements = 10\n",
    'extend = "../pyproject.toml"\n\n[lint.pylint]\nmax-statements = 10\n',
    'extend = "../../pyproject.toml"\n\n[lint.per-file-ignores]\n"*" = ["ALL"]\n',
    'extend = "../../pyproject.toml"\nline-length = 200\n',
    'extend = "../../pyproject.toml"\n\n[lint.pylint]\nmax-statements = 11\n',
    'extend = "../../pyproject.toml"\n\n[lint.pylint]\nmax-statements = 50\n',
    'extend = "../../pyproject.toml"\n\n[lint.pylint]\nmax-statements = "8"\n',
    'extend = "../../pyproject.toml"\n\n[lint.pylint]\nmax-statements = 9.5\n',
    'extend = "../../pyproject.toml"\n\n[lint.pylint]\nmax-statements = true\n',
]
LIMITED_CONFIGS = [
    RAISED_LIMIT,
    'extend = "../../pyproject.toml"\n\n[lint.pylint]\nmax-statements = 8\n',
]


def project_with(scratch_folder: Path, nested: str, name: str = "ruff.toml") -> Path:
    (scratch_folder / "pyproject.toml").write_text(ROOT_CONFIG, encoding="utf-8")
    folder = scratch_folder / "app" / "routes"
    folder.mkdir(parents=True)
    (folder / name).write_text(nested, encoding="utf-8")
    return scratch_folder


def test_real_project_configs_pass() -> None:
    assert nested_config_problems(PROJECT_FOLDER) == []


@pytest.mark.parametrize("nested", LIMITED_CONFIGS)
def test_statement_limit_up_to_ten_passes(scratch_folder: Path, nested: str) -> None:
    assert nested_config_problems(project_with(scratch_folder, nested)) == []


@pytest.mark.parametrize("nested", BAD_NESTED_CONFIGS)
def test_other_nested_settings_fail(scratch_folder: Path, nested: str) -> None:
    assert nested_config_problems(project_with(scratch_folder, nested))


def test_hidden_ruff_toml_is_checked(scratch_folder: Path) -> None:
    project = project_with(scratch_folder, BAD_NESTED_CONFIGS[0], ".ruff.toml")
    assert nested_config_problems(project)


def test_nested_pyproject_with_ruff_fails(scratch_folder: Path) -> None:
    nested = '[tool.ruff.lint]\nignore = ["ALL"]\n'
    project = project_with(scratch_folder, nested, "pyproject.toml")
    assert nested_config_problems(project)


def test_pyproject_without_ruff_passes(scratch_folder: Path) -> None:
    nested = '[project]\nname = "inner"\n'
    project = project_with(scratch_folder, nested, "pyproject.toml")
    assert nested_config_problems(project) == []


def test_hidden_folders_are_skipped(scratch_folder: Path) -> None:
    project = project_with(scratch_folder, RAISED_LIMIT)
    hidden_folder = project / ".venv" / "package"
    hidden_folder.mkdir(parents=True)
    (hidden_folder / "ruff.toml").write_text(BAD_NESTED_CONFIGS[0], encoding="utf-8")
    assert nested_config_problems(project) == []


def test_main_reports_bad_configs(
    scratch_folder: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project = project_with(scratch_folder, BAD_NESTED_CONFIGS[0])
    monkeypatch.setattr(sys, "argv", ["configs", str(project)])
    assert main() == 1
    assert "lint.ignore" in capsys.readouterr().out
