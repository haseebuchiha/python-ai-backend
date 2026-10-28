from pathlib import Path

import pytest

from lint.checker import text_violations
from lint.tests.reporting import reported_codes

TEST_FILE = "tests/test_orders.py"
SHORT_OR_LONG_SNIPPETS = [
    "ab = compute()\n",
    "def go(amount: int) -> int:\n    return amount\n",
    "def build(x: int) -> int:\n    return x\n",
    "doubled = [x * 2 for x in orders]\n",
    "import numpy as np\n",
    f"{'a' * 41} = compute()\n",
]
FITTING_NAME_SNIPPETS = [
    "id = compute()\n",
    "ok = compute()\n",
    "_ = compute()\n",
    "sku = compute()\n",
    f"{'a' * 40} = compute()\n",
]
ABBREVIATED_SNIPPETS = [
    "user_msg = compute()\n",
    "def build(ctx: Context) -> None:\n    pass\n",
    "class HttpReq(BaseModel):\n    path: str\n",
    "MAX_LEN = 5\n",
    """
    def build() -> None:
        try:
            ship()
        except ValueError as exc:
            hold(exc)
    """,
]
ALLOWED_SHORT_WORD_SNIPPETS = [
    "def build(*args: int, **kwargs: int) -> None:\n    pass\n",
    "params = compute()\n",
    "env = compute()\n",
    "message = compute()\n",
]
PREFIXED_SNIPPETS = [
    "str_name = compute()\n",
    "dict_prices = compute()\n",
    "STR_LABEL = 'x'\n",
    "_lst_orders = compute()\n",
    "fn_callback = compute()\n",
]
UNPREFIXED_SNIPPETS = [
    "strategy = compute()\n",
    "internal_count = compute()\n",
    "dictionary_words = compute()\n",
]
VAGUE_SNIPPETS = [
    "data = compute()\n",
    "result = compute()\n",
    "def handler() -> None:\n    pass\n",
    "DATA = compute()\n",
    "def build(item: int) -> int:\n    return item\n",
]
SPECIFIC_SNIPPETS = [
    "customer_data = compute()\n",
    "handler_name = compute()\n",
    "order_result = compute()\n",
]
LOWERCASE_CONSTANT_SNIPPETS = [
    "timeout = 30\n",
    "label = 'x'\n",
    "retries = -1\n",
    "debug: bool = True\n",
    "ratio = 0.5\n",
    "nothing = None\n",
    "timeout = 5 * 60\n",
    "base_url = 'https://' + 'x'\n",
    "retry_limit = None\n",
    "retry_limit: int | None = None\n",
    "offset = -(2**8)\n",
    "_timeout = 5\n",
    "allowed_decisions = ('approve', 'reject')\n",
    "limits = (1, (2, -3))\n",
    "statuses: tuple[str, ...] = ('open', 'closed')\n",
]
NEW_VAGUE_SNIPPETS = [
    "results = compute()\n",
    "output = compute()\n",
    "payload = compute()\n",
    "qty = compute()\n",
    "amt = compute()\n",
    "cnt = compute()\n",
]
NEW_ABBREVIATED_SNIPPETS = [
    "order_qty = compute()\n",
    "total_amt = compute()\n",
    "line_cnt = compute()\n",
]
CONSTANT_SNIPPETS = [
    "TIMEOUT = 30\n",
    "__version__ = '1.0'\n",
    "def build() -> int:\n    timeout = 30\n    return timeout\n",
    "client = make_client()\n",
    "NOTHING = None\n",
    "TIMEOUT = 5 * 60\n",
    "_TIMEOUT = 5\n",
    "app = FastAPI()\n",
    "router = APIRouter()\n",
    "logger = logging.getLogger(__name__)\n",
    "base_url = settings.host + '/api'\n",
    "ALLOWED_DECISIONS = ('approve', 'reject')\n",
    "pair = (compute(), 1)\n",
    "pair = (settings.host, 1)\n",
    "pairs = ((1, compute()), (2, 3))\n",
    "decisions = ['approve', 'reject']\n",
]


@pytest.mark.parametrize("snippet", SHORT_OR_LONG_SNIPPETS)
def test_name_length_is_reported(snippet: str) -> None:
    assert "BOS701" in reported_codes(snippet)


@pytest.mark.parametrize("snippet", FITTING_NAME_SNIPPETS)
def test_fitting_names_are_allowed(snippet: str) -> None:
    assert "BOS701" not in reported_codes(snippet)


@pytest.mark.parametrize("snippet", ABBREVIATED_SNIPPETS)
def test_abbreviations_are_reported(snippet: str) -> None:
    assert "BOS702" in reported_codes(snippet)


@pytest.mark.parametrize("snippet", ALLOWED_SHORT_WORD_SNIPPETS)
def test_allowed_short_words_pass(snippet: str) -> None:
    assert "BOS702" not in reported_codes(snippet)


def test_abbreviations_apply_to_tests() -> None:
    assert "BOS702" in reported_codes("user_msg = compute()\n", TEST_FILE)


@pytest.mark.parametrize("snippet", PREFIXED_SNIPPETS)
def test_type_prefixes_are_reported(snippet: str) -> None:
    assert "BOS703" in reported_codes(snippet)


@pytest.mark.parametrize("snippet", UNPREFIXED_SNIPPETS)
def test_lookalike_prefixes_are_allowed(snippet: str) -> None:
    assert "BOS703" not in reported_codes(snippet)


def test_type_prefixes_apply_to_tests() -> None:
    assert "BOS703" in reported_codes("str_name = compute()\n", TEST_FILE)


@pytest.mark.parametrize("snippet", VAGUE_SNIPPETS)
def test_vague_names_are_reported(snippet: str) -> None:
    assert "BOS704" in reported_codes(snippet)


@pytest.mark.parametrize("snippet", SPECIFIC_SNIPPETS)
def test_specific_names_are_allowed(snippet: str) -> None:
    assert "BOS704" not in reported_codes(snippet)


@pytest.mark.parametrize("snippet", VAGUE_SNIPPETS)
def test_vague_names_pass_in_tests(snippet: str) -> None:
    assert "BOS704" not in reported_codes(snippet, TEST_FILE)


@pytest.mark.parametrize("snippet", LOWERCASE_CONSTANT_SNIPPETS)
def test_lowercase_constants_are_reported(snippet: str) -> None:
    assert "BOS705" in reported_codes(snippet)


@pytest.mark.parametrize("snippet", CONSTANT_SNIPPETS)
def test_constants_and_others_are_allowed(snippet: str) -> None:
    assert "BOS705" not in reported_codes(snippet)


@pytest.mark.parametrize("snippet", NEW_VAGUE_SNIPPETS)
def test_new_vague_names_are_reported(snippet: str) -> None:
    assert "BOS704" in reported_codes(snippet)


@pytest.mark.parametrize("snippet", NEW_ABBREVIATED_SNIPPETS)
def test_new_abbreviations_are_reported(snippet: str) -> None:
    assert "BOS702" in reported_codes(snippet)


def test_response_parameter_is_not_vague() -> None:
    snippet = "def route(response: Response) -> int:\n    return 1\n"
    assert "BOS704" not in reported_codes(snippet)


def test_short_field_suggests_an_alias() -> None:
    snippet = "class Message(BaseModel):\n    to: str\n"
    messages = [
        violation.message
        for violation in text_violations(snippet, Path("app/schemas/messages.py"))
        if violation.code == "BOS701"
    ]
    assert len(messages) == 1
    assert "Field(alias='to')" in messages[0]
