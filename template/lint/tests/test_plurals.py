import pytest

from lint.plurals import is_plural
from lint.tests.reporting import reported_codes

SINGULAR_SEQUENCE_SNIPPETS = [
    "def order() -> list[int]:\n    return []\n",
    "def order() -> Sequence[int]:\n    return []\n",
    "def order() -> collections.abc.Iterator[int]:\n    return iter([])\n",
    "def order() -> tuple[int, ...]:\n    return (1, 2)\n",
    "def order() -> list[str] | None:\n    return None\n",
    "def order() -> None | list[str]:\n    return None\n",
    "def order() -> Optional[list[str]]:\n    return None\n",
    "def order() -> typing.Union[list[str], None]:\n    return None\n",
    "def order() -> 'list[str]':\n    return []\n",
    "def order() -> 'list[str] | None':\n    return None\n",
    "order: Annotated[list[str], Field(min_length=1)] = compute()\n",
    "ORDER: Final[list[str]] = compute()\n",
    "ORDER: Final = [1, 2]\n",
    """
    from collections.abc import Sequence as Seq

    def order() -> Seq[int]:
        return []
    """,
    "def build(order: Optional[list[int]]) -> None:\n    pass\n",
    "order = [1, 2]\n",
    "order = {1, 2}\n",
    "order = (1, 2)\n",
    "order = [price for price in prices]\n",
    "order = (price for price in prices)\n",
    "order: list[int] = compute()\n",
    "def build(order: list[int]) -> None:\n    pass\n",
    "class Cart(BaseModel):\n    line: list[int]\n",
]
PLURAL_SEQUENCE_SNIPPETS = [
    "def orders() -> list[int]:\n    return []\n",
    "orders = [1, 2]\n",
    "statuses = ['open']\n",
    "latest_news = ['a']\n",
    "customer_data = [1]\n",
    "def build(orders: list[int]) -> None:\n    pass\n",
    "order = compute()\n",
    """
    def opened_client() -> Iterator[Client]:
        yield Client()
    """,
]
SINGULAR_MAPPING_SNIPPETS = [
    "price = {}\n",
    "price_by_sku = {}\n",
    "PRICE_BY_SKU = {}\n",
    "price = {sku: 1 for sku in skus}\n",
    "def price_list() -> dict[str, int]:\n    return {}\n",
    "lookup: Mapping[str, int] = compute()\n",
    "def price() -> dict[str, int] | None:\n    return None\n",
    "def price() -> 'Optional[dict[str, int]]':\n    return None\n",
]
FIXED_TUPLE_SNIPPETS = [
    "def pair() -> tuple[str, str]:\n    return ('a', 'b')\n",
    "pair: tuple[int, int] = (1, 2)\n",
    "def build(pair: tuple[int, int]) -> None:\n    pass\n",
    "point: Tuple[int, int] = compute()\n",
    "single: tuple[int] = compute()\n",
    "empty: tuple[()] = ()\n",
    "def pair() -> tuple[str, str] | None:\n    return None\n",
    "def pair() -> 'tuple[str, str]':\n    return ('a', 'b')\n",
]
UNCOUNTABLE_SNIPPETS = [
    "chat_history: list[str] = compute()\n",
    "stock_by_sku: dict[str, int] = compute()\n",
    "inventory = [1, 2]\n",
    "feedback = ['good']\n",
    "staff = ['ana']\n",
    "def equipment() -> list[str]:\n    return []\n",
]
PLURAL_MAPPING_SNIPPETS = [
    "prices = {}\n",
    "prices_by_sku = {}\n",
    "PRICES_BY_SKU = {}\n",
    "def prices() -> dict[str, int]:\n    return {}\n",
    "headers: dict[str, str] = compute()\n",
]
PLURAL_WORDS = [
    "statuses",
    "addresses",
    "news",
    "data",
    "series",
    "people",
    "children",
    "criteria",
    "indices",
    "analyses",
    "buses",
    "quizzes",
    "feet",
    "history",
    "stock",
    "inventory",
    "feedback",
    "staff",
    "information",
    "equipment",
    "skus",
    "ids",
    "prices",
]
SINGULAR_WORDS = [
    "status",
    "address",
    "analysis",
    "process",
    "bus",
    "axis",
    "class",
    "boss",
    "matrix",
    "price",
    "config",
    "payload",
]


@pytest.mark.parametrize("snippet", SINGULAR_SEQUENCE_SNIPPETS)
def test_singular_sequences_are_reported(snippet: str) -> None:
    assert "BOS801" in reported_codes(snippet)


@pytest.mark.parametrize("snippet", PLURAL_SEQUENCE_SNIPPETS)
def test_plural_sequences_are_allowed(snippet: str) -> None:
    assert "BOS801" not in reported_codes(snippet)


@pytest.mark.parametrize("snippet", SINGULAR_MAPPING_SNIPPETS)
def test_singular_mappings_are_reported(snippet: str) -> None:
    assert "BOS802" in reported_codes(snippet)


@pytest.mark.parametrize("snippet", PLURAL_MAPPING_SNIPPETS)
def test_plural_mappings_are_allowed(snippet: str) -> None:
    assert "BOS802" not in reported_codes(snippet)


@pytest.mark.parametrize("word", PLURAL_WORDS)
def test_plural_words_are_recognised(word: str) -> None:
    assert is_plural(word)


@pytest.mark.parametrize("word", SINGULAR_WORDS)
def test_singular_words_are_recognised(word: str) -> None:
    assert not is_plural(word)


@pytest.mark.parametrize("snippet", FIXED_TUPLE_SNIPPETS)
def test_fixed_size_tuples_need_no_plural(snippet: str) -> None:
    assert "BOS801" not in reported_codes(snippet)


@pytest.mark.parametrize("snippet", UNCOUNTABLE_SNIPPETS)
def test_uncountable_nouns_are_allowed(snippet: str) -> None:
    assert not reported_codes(snippet) & {"BOS801", "BOS802"}


def test_unparseable_annotation_is_ignored() -> None:
    snippet = "def order() -> 'list[':\n    return []\n"
    assert "BOS801" not in reported_codes(snippet)
