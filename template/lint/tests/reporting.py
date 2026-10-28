from pathlib import Path
from textwrap import dedent

from lint.checker import text_violations


def all_reported_codes(snippet: str, filename: str = "module.py") -> list[str]:
    violations = text_violations(dedent(snippet), Path(filename))
    return [violation.code for violation in violations]


def reported_codes(snippet: str, filename: str = "module.py") -> set[str]:
    return set(all_reported_codes(snippet, filename))
