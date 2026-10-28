import pytest

from lint.tests.reporting import reported_codes

COMMENT_CODES = {"BOS101", "BOS102", "BOS103"}
COMMENTED_SNIPPETS = [
    "total = compute()  # running total\n",
    "# explains the next line\ntotal = compute()\n",
    "total = compute()\n#!/usr/bin/env python\n",
]
SUPPRESSED_SNIPPETS = [
    "import os  # noqa: F401\n",
    "total = len(1)  # type: ignore[arg-type]\n",
    "total = compute()  # pragma: no cover\n",
    "total = compute()  # fmt: skip\n",
    "total = compute()  # NOQA\n",
]
DOCSTRING_SNIPPETS = [
    '"""Module docstring."""\n',
    """
    def total() -> int:
        '''Sum things.'''
        return 1
    """,
    """
    class Order(TypedDict):
        '''An order.'''
        total: int
    """,
    """
    def total() -> int:
        'stray note in the middle'
        return 1
    """,
]
CLEAN_SNIPPETS = [
    "#!/usr/bin/env python\ntotal = compute()\n",
    "label = compute('not # a comment')\n",
    """
    @tool(description="Look up a product price.")
    def price_lookup(sku: str) -> str:
        return sku
    """,
]


@pytest.mark.parametrize("snippet", COMMENTED_SNIPPETS)
def test_comments_are_reported(snippet: str) -> None:
    assert "BOS101" in reported_codes(snippet)


@pytest.mark.parametrize("snippet", SUPPRESSED_SNIPPETS)
def test_suppressions_are_reported(snippet: str) -> None:
    codes = reported_codes(snippet)
    assert "BOS103" in codes
    assert "BOS101" not in codes


@pytest.mark.parametrize("snippet", DOCSTRING_SNIPPETS)
def test_docstrings_are_reported(snippet: str) -> None:
    assert "BOS102" in reported_codes(snippet)


@pytest.mark.parametrize("snippet", CLEAN_SNIPPETS)
def test_clean_code_has_no_comment_codes(snippet: str) -> None:
    assert not reported_codes(snippet) & COMMENT_CODES
