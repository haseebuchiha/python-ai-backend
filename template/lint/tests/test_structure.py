from pathlib import Path
from textwrap import dedent

import pytest

from lint.checker import text_violations
from lint.core import PROJECT_ROOT
from lint.structure import HANDLER_HINT
from lint.tests.reporting import all_reported_codes, reported_codes

LOOP_SNIPPETS = [
    """
    for order in orders:
        ship(order)
    """,
    """
    while waiting():
        poll()
    """,
    """
    async def drain(queue: Queue) -> None:
        async for message in queue:
            await ship(message)
    """,
]
LOOP_FREE_SNIPPETS = [
    "shipped = [ship(order) for order in orders]\n",
    "total = sum(order.price for order in orders)\n",
    "found = any(order.late for order in orders)\n",
]
PLAIN_CLASS_SNIPPETS = [
    "class OrderService:\n    pass\n",
    "class Settings:\n    timeout: int\n",
]
DATA_SHAPE_SNIPPETS = [
    "class Quote(Base):\n    total: int\n",
    "class Quote(dataclasses.Base):\n    total: int\n",
    "class SalesChat(AgentState):\n    stage: str\n",
    "class SalesChat(MessagesState):\n    stage: str\n",
    "class QuoteNotFoundError(Exception):\n    pass\n",
    "class Quote(BaseModel):\n    total: int\n",
    "class Quote(pydantic.BaseModel):\n    total: int\n",
    "class Quote(TypedDict, total=False):\n    total: int\n",
    "class Status(StrEnum):\n    OPEN = 'open'\n",
    "class Level(IntEnum):\n    HIGH = 1\n",
    "class Color(enum.Enum):\n    RED = 1\n",
    "class Point(NamedTuple):\n    horizontal: int\n",
    "class Priced(Protocol[Money]):\n    price: Money\n",
    """
    class Quote(BaseModel):
        total: int

    class SignedQuote(Quote):
        signature: str
    """,
    "class Quote(BaseModel):\n    total: int = 0\n",
    "class Quote(BaseModel):\n    status: Status = Status.OPEN\n",
    "class Quote(BaseModel):\n    limit: int = DEFAULT_LIMIT\n",
    "class Quote(BaseModel):\n    _limit: int = _DEFAULT_LIMIT\n",
    "class Quote(BaseModel):\n    level: int = logging.INFO\n",
    "class Quote(BaseModel):\n    kind: type[Status] = Status\n",
    "class Quote(BaseModel):\n    model_config = ConfigDict(frozen=True)\n",
    "class Message(BaseModel):\n    alias_name: str = Field(alias='to')\n",
    "class Quote(BaseModel):\n    tags: list[str] = Field(default_factory=list)\n",
]
ASSIGNED_METHOD_SNIPPETS = [
    "class Quote(BaseModel):\n    doubled = double_total\n",
    "class Quote(BaseModel):\n    _doubled = _double_total\n",
    "class Quote(BaseModel):\n    run = helpers.run_job\n",
    "class Quote(logging.Handler):\n    emit = logging.Handler.emit\n",
    "class Quote(BaseModel):\n    run: Callable[[], int] = run_job\n",
    "class Quote(BaseModel):\n    first = second = run_job\n",
    "class Quote(BaseModel):\n    run = lambda self: self.total\n",
    "class Quote(BaseModel):\n    build = staticmethod(build_quote)\n",
    "class Quote(BaseModel):\n    build = classmethod(build_quote)\n",
    "class Quote(BaseModel):\n    doubled = property(double_total)\n",
    "class Quote(BaseModel):\n    doubled = functools.cached_property(double_total)\n",
    "class Quote(BaseModel):\n    send = partialmethod(send_quote, urgent=True)\n",
    "class Quote(BaseModel):\n    send = functools.partial(send_quote)\n",
    "class Quote(BaseModel):\n    send = types.MethodType(send_quote, BLANK)\n",
    "class Fetcher(Protocol):\n    fetch = fetch_page\n",
]
METHOD_SNIPPETS = [
    """
    class Quote(BaseModel):
        total: int

        def doubled(self) -> int:
            return self.total * 2
    """,
    """
    class Fetcher(Protocol):
        def fetch(self) -> str:
            return 'x'
    """,
    """
    class Quote(BaseModel):
        def total(self) -> int: ...
    """,
    """
    class Fetcher(Protocol):
        def fetch(self) -> str:
            ...
            return 'x'
    """,
]
PROTOCOL_STUB_SNIPPETS = [
    """
    class Fetcher(Protocol):
        async def fetch(self) -> str: ...
    """,
    """
    class Fetcher(typing.Protocol[Money]):
        def fetch(self) -> Money: ...

        def close(self) -> None: ...
    """,
]
SCHEMA_PATHS = [
    "app/schemas/quote.py",
    "app/schemas/__init__.py",
    "./app/schemas/quote.py",
    str(PROJECT_ROOT / "app" / "schemas" / "messages" / "message.py"),
    "lint/schemas.py",
    str(PROJECT_ROOT / "lint" / "schemas.py"),
    "tests/test_quotes.py",
    "lint/tests/test_orders.py",
]
NON_SCHEMA_PATHS = [
    "app/services/sales.py",
    "app/routes/orders.py",
    "app/models/products.py",
    "app/config/settings.py",
    "app/services/schemas/quote.py",
    "app/main.py",
    "lint/naming.py",
    "/srv/other-project/app/schemas/messages/message.py",
    "app/services/lint/schemas.py",
    "x/app/schemas/y.py",
    "x/lint/schemas.py",
    "app/schemas/../services/quote.py",
    "app/services/test_quotes.py",
]
MISPLACED_CLASS_COUNT = 2
SETTINGS_CLASS = "class Settings(BaseSettings):\n    database_url: str\n"
SETTINGS_PATHS = [
    "app/config/settings.py",
    str(PROJECT_ROOT / "app" / "config" / "settings.py"),
]
MISPLACED_SETTINGS_PATHS = [
    "app/services/sales.py",
    "app/schemas/../services/x.py",
    "app/schemas/settings.py",
    "lint/schemas.py",
    "x/app/config/settings.py",
    "/srv/other-project/app/config/settings.py",
]
LOGGER_FILE = "app/config/logger.py"
INTERCEPT_HANDLER = """
import inspect
import logging
from types import FrameType

from loguru import logger


def loguru_level(record: logging.LogRecord) -> str | int:
    try:
        return logger.level(record.levelname).name
    except ValueError:
        return record.levelno


def caller_depth(frame: FrameType | None, depth: int) -> int:
    if frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
        return caller_depth(frame.f_back, depth + 1)
    return depth


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        depth = caller_depth(inspect.currentframe(), 0)
        logger.opt(depth=depth, exception=record.exc_info).log(
            loguru_level(record),
            record.getMessage(),
        )
"""
HANDLER_CLASS = "class InterceptHandler(logging.Handler):\n"
EMIT_LINE = "    def emit(self, record: logging.LogRecord) -> None:\n"
ALLOWED_HANDLERS = [
    (INTERCEPT_HANDLER, LOGGER_FILE),
    (INTERCEPT_HANDLER, str(PROJECT_ROOT / "app" / "config" / "logger.py")),
    (INTERCEPT_HANDLER, "app/schemas/../config/logger.py"),
    (
        INTERCEPT_HANDLER.replace(
            "import logging\n", "import logging\nfrom logging import Handler\n"
        ).replace("(logging.Handler)", "(Handler)"),
        LOGGER_FILE,
    ),
    (
        INTERCEPT_HANDLER.replace(
            "import logging\n",
            "import logging\nfrom logging import Handler as Base, LogRecord\n",
        )
        .replace("(logging.Handler)", "(Base)")
        .replace(EMIT_LINE, "    def emit(self, record: LogRecord) -> None:\n"),
        LOGGER_FILE,
    ),
    (
        INTERCEPT_HANDLER.replace(
            "from loguru import logger\n", "import loguru\n\nlogger = loguru.logger\n"
        ),
        LOGGER_FILE,
    ),
]
SECOND_HANDLER = (
    f"\n\n{HANDLER_CLASS}{EMIT_LINE}        logger.info(record.getMessage())\n"
)
NESTED_HANDLER = """
import logging

from loguru import logger


def install() -> None:
    class InterceptHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            logger.info(record.getMessage())
"""
ASSIGNED_EMIT_HANDLER = """
import logging

from loguru import logger


def emit_record(handler: logging.Handler, record: logging.LogRecord) -> None:
    logger.info(record.getMessage())


class InterceptHandler(logging.Handler):
    emit = emit_record
"""
BROKEN_HANDLERS = [
    (INTERCEPT_HANDLER, "app/config/settings.py"),
    (INTERCEPT_HANDLER, "/srv/other-project/app/config/logger.py"),
    (INTERCEPT_HANDLER, "x/app/config/logger.py"),
    (ASSIGNED_EMIT_HANDLER, LOGGER_FILE),
    (INTERCEPT_HANDLER, "app/services/logger.py"),
    (INTERCEPT_HANDLER, "app/config/logging/logger.py"),
    (INTERCEPT_HANDLER, "config/logger.py"),
    (INTERCEPT_HANDLER.replace("InterceptHandler", "LoguruHandler"), LOGGER_FILE),
    (INTERCEPT_HANDLER.replace("logging.Handler", "logging.Filter"), LOGGER_FILE),
    (
        INTERCEPT_HANDLER.replace("logging.Handler", "logging.StreamHandler"),
        LOGGER_FILE,
    ),
    (
        INTERCEPT_HANDLER.replace("(logging.Handler)", "(logging.Handler, Mixin)"),
        LOGGER_FILE,
    ),
    (
        INTERCEPT_HANDLER.replace(
            "(logging.Handler)", "(logging.Handler, metaclass=Meta)"
        ),
        LOGGER_FILE,
    ),
    (INTERCEPT_HANDLER.replace(HANDLER_CLASS, f"@final\n{HANDLER_CLASS}"), LOGGER_FILE),
    (
        INTERCEPT_HANDLER.replace(EMIT_LINE, f"    terminator = ''\n\n{EMIT_LINE}"),
        LOGGER_FILE,
    ),
    (
        INTERCEPT_HANDLER.replace(
            EMIT_LINE,
            f"    def close(self) -> None:\n        logger.complete()\n\n{EMIT_LINE}",
        ),
        LOGGER_FILE,
    ),
    (INTERCEPT_HANDLER.replace(EMIT_LINE, f"    @override\n{EMIT_LINE}"), LOGGER_FILE),
    (INTERCEPT_HANDLER.replace("    def emit", "    async def emit"), LOGGER_FILE),
    (INTERCEPT_HANDLER.replace("    def emit", "    def handle"), LOGGER_FILE),
    (
        INTERCEPT_HANDLER.replace(
            EMIT_LINE, "    def emit(self, record: object) -> None:\n"
        ),
        LOGGER_FILE,
    ),
    (
        INTERCEPT_HANDLER.replace(
            EMIT_LINE,
            "    def emit(self, record: logging.LogRecord, *extras: str) -> None:\n",
        ),
        LOGGER_FILE,
    ),
    (
        INTERCEPT_HANDLER.replace(
            EMIT_LINE, "    def emit(self, record: logging.LogRecord):\n"
        ),
        LOGGER_FILE,
    ),
    (
        INTERCEPT_HANDLER.replace(
            EMIT_LINE,
            "    def emit(self, record: logging.LogRecord = BLANK) -> None:\n",
        ),
        LOGGER_FILE,
    ),
    (
        INTERCEPT_HANDLER.replace(
            "from loguru import logger", "from structlog import logger"
        ),
        LOGGER_FILE,
    ),
    (
        INTERCEPT_HANDLER.replace(
            "from loguru import logger", "from loguru import Logger"
        ),
        LOGGER_FILE,
    ),
    (INTERCEPT_HANDLER + SECOND_HANDLER, LOGGER_FILE),
    (NESTED_HANDLER, LOGGER_FILE),
]
TOO_MANY_PARAMETER_SNIPPETS = [
    "def build(first, second, third, fourth) -> None:\n    pass\n",
    "def build(first, second, third, _fourth) -> None:\n    pass\n",
    "def build(first, second, third, **options) -> None:\n    pass\n",
    "def build(first, second, *args, **kwargs) -> None:\n    pass\n",
    "def build(first, *, second, third, fourth) -> None:\n    pass\n",
    "def build(first, /, second, third, fourth) -> None:\n    pass\n",
    "async def build(first, second, third, fourth) -> None:\n    pass\n",
    "build = lambda first, second, third, fourth: first\n",
    "def build(cls, first, second, third, fourth) -> None:\n    pass\n",
]
FEW_PARAMETER_SNIPPETS = [
    "def build(first: int, second: int, third: int) -> None:\n    pass\n",
    "def build(first: int, *args: int, **kwargs: int) -> None:\n    pass\n",
    """
    class Fetcher(Protocol):
        def fetch(self, first: int, second: int, third: int) -> str: ...
    """,
]
DISCARDED_LOOP_SNIPPETS = [
    "[sys.stdout.write(line) for line in lines]\n",
    "list(map(sys.stdout.write, lines))\n",
    "map(ship, orders)\n",
    "{ship(order) for order in orders}\n",
    "{order: ship(order) for order in orders}\n",
    "(ship(order) for order in orders)\n",
    "any(ship(order) for order in orders)\n",
    "collections.deque(map(ship, orders), maxlen=0)\n",
    "tuple(filter(ship, orders))\n",
    "def run(orders: list) -> None:\n    [ship(order) for order in orders]\n",
    "_ = [ship(order) for order in orders]\n",
    "_ = list(map(ship, orders))\n",
    "_shipped = map(ship, orders)\n",
    "_: list[None] = [ship(order) for order in orders]\n",
    "_ = _shipped = [ship(order) for order in orders]\n",
    "def run(orders: list) -> None:\n    _ = list(map(ship, orders))\n",
    "[*map(ship, orders)]\n",
    "(*map(ship, orders),)\n",
    "{*filter(ship, orders)}\n",
    "[*(ship(order) for order in orders)]\n",
    "_ = [*map(ship, orders)]\n",
    "functools.reduce(ship_into, orders, BLANK)\n",
    "reduce(ship_into, orders)\n",
    "_ = reduce(ship_into, orders)\n",
]
USED_LOOP_SNIPPETS = [
    "shipped = [ship(order) for order in orders]\n",
    "sys.stdout.writelines(lines)\n",
    "shipped = list(map(ship, orders))\n",
    "def run(orders: list) -> list:\n    return [ship(order) for order in orders]\n",
    "async def run(orders: list) -> None:\n    await gather(*map(ship, orders))\n",
    "ship(orders)\n",
    "_ = compute()\n",
    "_: int\n",
    "[*orders]\n",
    "shipped = [*map(ship, orders)]\n",
    "_, shipped = [ship(order) for order in orders]\n",
    "_ = shipped = [ship(order) for order in orders]\n",
    "total = reduce(add, prices)\n",
]
MOVABLE_SNIPPETS = [
    """
    def outer(orders: list[int]) -> int:
        def double(amount: int) -> int:
            return amount * 2

        return sum(double(order) for order in orders)
    """,
    """
    def outer(depth: int) -> int:
        def countdown(steps: int) -> int:
            return 0 if steps == 0 else countdown(steps - 1)

        return countdown(depth)
    """,
    """
    def outer(amount: int) -> int:
        def double(amount: int) -> int:
            return amount * 2

        return double(amount)
    """,
]
CLOSURE_SNIPPETS = [
    """
    def outer() -> Callable[[], int]:
        count = 0

        def bump() -> int:
            nonlocal count
            count = 5
            return 1

        return bump
    """,
    """
    def outer(rate: int) -> Callable[[int], int]:
        def scale(amount: int) -> int:
            return amount * rate

        return scale
    """,
    """
    def outer(orders: list[int]) -> int:
        factor = compute()

        def scale(amount: int) -> int:
            return amount * factor

        return sum(scale(order) for order in orders)
    """,
    """
    def outer(router: Router) -> None:
        @router.get("/orders")
        def list_orders() -> list[int]:
            return []
    """,
]


@pytest.mark.parametrize("snippet", LOOP_SNIPPETS)
def test_loops_are_reported(snippet: str) -> None:
    assert "BOS201" in reported_codes(snippet)


@pytest.mark.parametrize("snippet", LOOP_FREE_SNIPPETS)
def test_comprehensions_are_allowed(snippet: str) -> None:
    assert "BOS201" not in reported_codes(snippet)


@pytest.mark.parametrize("snippet", PLAIN_CLASS_SNIPPETS)
def test_plain_classes_are_reported(snippet: str) -> None:
    assert "BOS401" in reported_codes(snippet)


@pytest.mark.parametrize("snippet", DATA_SHAPE_SNIPPETS)
def test_data_shapes_are_allowed(snippet: str) -> None:
    assert not reported_codes(snippet) & {"BOS401", "BOS402"}


@pytest.mark.parametrize("snippet", METHOD_SNIPPETS)
def test_methods_are_reported(snippet: str) -> None:
    codes = reported_codes(snippet)
    assert "BOS402" in codes
    assert "BOS401" not in codes


@pytest.mark.parametrize("snippet", ASSIGNED_METHOD_SNIPPETS)
def test_assigned_methods_are_reported(snippet: str) -> None:
    codes = reported_codes(snippet)
    assert "BOS402" in codes
    assert "BOS401" not in codes


@pytest.mark.parametrize("snippet", MOVABLE_SNIPPETS)
def test_movable_functions_are_reported(snippet: str) -> None:
    assert "BOS601" in reported_codes(snippet)


@pytest.mark.parametrize("snippet", CLOSURE_SNIPPETS)
def test_closures_are_allowed(snippet: str) -> None:
    assert "BOS601" not in reported_codes(snippet)


@pytest.mark.parametrize("snippet", PROTOCOL_STUB_SNIPPETS)
def test_protocol_stubs_are_allowed(snippet: str) -> None:
    assert not reported_codes(snippet) & {"BOS401", "BOS402"}


@pytest.mark.parametrize("path", SCHEMA_PATHS)
def test_classes_allowed_in_schemas(path: str) -> None:
    assert "BOS403" not in reported_codes(
        "class Quote(BaseModel):\n    total: int\n", path
    )


@pytest.mark.parametrize("path", NON_SCHEMA_PATHS)
def test_classes_elsewhere_are_reported(path: str) -> None:
    assert "BOS403" in reported_codes("class Quote(BaseModel):\n    total: int\n", path)


@pytest.mark.parametrize("path", SETTINGS_PATHS)
def test_settings_class_is_allowed_in_config(path: str) -> None:
    assert "BOS403" not in reported_codes(SETTINGS_CLASS, path)


@pytest.mark.parametrize("path", MISPLACED_SETTINGS_PATHS)
def test_settings_elsewhere_is_reported(path: str) -> None:
    assert "BOS403" in reported_codes(SETTINGS_CLASS, path)


def class_messages(snippet: str, path: str) -> list[str]:
    return [
        violation.message
        for violation in text_violations(dedent(snippet), Path(path))
        if violation.code in {"BOS402", "BOS403"}
    ]


@pytest.mark.parametrize(("snippet", "path"), ALLOWED_HANDLERS)
def test_intercept_handler_is_allowed(snippet: str, path: str) -> None:
    assert not reported_codes(snippet, path)


@pytest.mark.parametrize(("snippet", "path"), BROKEN_HANDLERS)
def test_other_handlers_are_reported(snippet: str, path: str) -> None:
    assert {"BOS402", "BOS403"} <= reported_codes(snippet, path)


def test_each_extra_handler_is_reported() -> None:
    codes = all_reported_codes(INTERCEPT_HANDLER + SECOND_HANDLER, LOGGER_FILE)
    assert codes.count("BOS402") == codes.count("BOS403") == MISPLACED_CLASS_COUNT


def test_handlers_in_logger_get_a_hint() -> None:
    snippet = INTERCEPT_HANDLER.replace("logging.Handler", "logging.StreamHandler")
    messages = class_messages(snippet, LOGGER_FILE)
    assert len(messages) == MISPLACED_CLASS_COUNT
    assert all(message.endswith(HANDLER_HINT) for message in messages)


@pytest.mark.parametrize(
    ("snippet", "path"),
    [
        (INTERCEPT_HANDLER, "app/config/settings.py"),
        (METHOD_SNIPPETS[0], LOGGER_FILE),
    ],
)
def test_other_classes_get_no_hint(snippet: str, path: str) -> None:
    messages = class_messages(snippet, path)
    assert messages
    assert not any(HANDLER_HINT in message for message in messages)


def test_errors_and_nested_classes_placed() -> None:
    snippet = """
    class QuoteNotFoundError(Exception):
        pass

    def build() -> None:
        class Inner(TypedDict):
            total: int
    """
    codes = all_reported_codes(snippet, "app/services/sales.py")
    assert codes.count("BOS403") == MISPLACED_CLASS_COUNT


@pytest.mark.parametrize("snippet", TOO_MANY_PARAMETER_SNIPPETS)
def test_too_many_parameters_are_reported(snippet: str) -> None:
    assert "BOS602" in reported_codes(snippet)


@pytest.mark.parametrize("snippet", FEW_PARAMETER_SNIPPETS)
def test_three_parameters_are_allowed(snippet: str) -> None:
    assert "BOS602" not in reported_codes(snippet)


def test_parameter_limit_applies_to_tests() -> None:
    assert "BOS602" in reported_codes(TOO_MANY_PARAMETER_SNIPPETS[0], "tests/test_x.py")


@pytest.mark.parametrize("snippet", DISCARDED_LOOP_SNIPPETS)
def test_discarded_loops_are_reported(snippet: str) -> None:
    assert "BOS202" in reported_codes(snippet)


@pytest.mark.parametrize("snippet", USED_LOOP_SNIPPETS)
def test_used_comprehensions_are_allowed(snippet: str) -> None:
    assert "BOS202" not in reported_codes(snippet)
