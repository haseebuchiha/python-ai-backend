import pytest

from lint.tests.reporting import all_reported_codes, reported_codes

SERVICE_FILE = "app/services/sales.py"
CONFIG_FILE = "app/config/settings.py"
TEST_FILE = "tests/test_sales.py"
BANNED_API_SNIPPETS = [
    "import dataclasses\n",
    "from dataclasses import dataclass\n",
    "from dataclasses import dataclass as shape\n",
    "from dataclasses import field\n",
    "from pydantic.dataclasses import dataclass\n",
    "from pydantic import dataclasses\n",
    "from typing import cast\n",
    "from typing_extensions import cast\n",
    "import typing\n\ntotal = typing.cast(int, compute())\n",
    "import typing as typing_module\n\ntotal = typing_module.cast(int, compute())\n",
    "from typing import no_type_check\n",
    """
    import typing

    @typing.no_type_check
    def build() -> int:
        return 1
    """,
]
ALLOWED_API_SNIPPETS = [
    "import typing\n",
    "from typing import TypedDict\n",
    "from pydantic import BaseModel, Field\n",
    "total = cast(int, compute())\n",
    "total = shapes.dataclass\n",
    "import dataclasses_json\n",
]
ENVIRONMENT_SNIPPETS = [
    "import os\n\nhost = os.environ['DATABASE_URL']\n",
    "import os\n\nhost = os.getenv('DATABASE_URL')\n",
    "import os\n\nos.putenv('DATABASE_URL', 'x')\n",
    "from os import environ\n",
    "from os import getenv as read_setting\n",
    "import os as system\n\nhost = system.environ['DATABASE_URL']\n",
    "import posix\n\nhost = posix.environ['DATABASE_URL']\n",
    "import posix\n\nhost = posix.environb[b'DATABASE_URL']\n",
    "from posix import environ\n",
    "import nt\n\nnt.putenv('DATABASE_URL', 'x')\n",
    "from nt import unsetenv\n",
    "import dotenv\n\ndotenv.load_dotenv()\n",
    "from dotenv import load_dotenv\n",
    "from dotenv import dotenv_values\n",
    "from dotenv import find_dotenv as locate\n",
    "from dotenv.main import load_dotenv\n",
    "import dotenv.main\n\nsettings = dotenv.main.dotenv_values()\n",
]
ENVIRONMENT_FREE_SNIPPETS = [
    "import os\n\nfolder = os.path.join('a', 'b')\n",
    "from os import path\n",
    "host = settings.environ\n",
    "import posix\n\nprocess_id = posix.getpid()\n",
    "def load_dotenv() -> None:\n    return None\n\n\nload_dotenv()\n",
]
TYPE_CHECKING_DEFINITION_SNIPPETS = [
    """
    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        def parse(text: str) -> int: ...
    else:
        def parse(text):
            return int(text)
    """,
    """
    import typing

    if typing.TYPE_CHECKING:
        from app.schemas import Order
    else:
        Order = dict
    """,
    """
    if not TYPE_CHECKING:
        class Order(dict):
            total: int
    """,
    "if TYPE_CHECKING:\n    total: int = 1\n",
    """
    if TYPE_CHECKING:
        from app.schemas import Order
    elif READY:
        async def fetch() -> None: ...
    """,
    """
    def build() -> None:
        if TYPE_CHECKING:
            import app.schemas
            order_type = app.schemas.Order
    """,
]
IMPORT_ONLY_SNIPPETS = [
    """
    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from app.schemas import Order
    """,
    """
    import typing

    if typing.TYPE_CHECKING:
        import app.schemas
    else:
        from app import schemas
    """,
    """
    if TYPE_CHECKING:
        from app.schemas import Order
    elif READY:
        import app.schemas
    """,
    "if READY:\n    def build() -> int:\n        return 1\n",
]


@pytest.mark.parametrize("snippet", BANNED_API_SNIPPETS)
def test_banned_apis_are_reported(snippet: str) -> None:
    assert "BOS901" in reported_codes(snippet)


@pytest.mark.parametrize("snippet", BANNED_API_SNIPPETS)
def test_banned_apis_apply_to_tests(snippet: str) -> None:
    assert "BOS901" in reported_codes(snippet, TEST_FILE)


@pytest.mark.parametrize("snippet", ALLOWED_API_SNIPPETS)
def test_other_apis_are_allowed(snippet: str) -> None:
    assert "BOS901" not in reported_codes(snippet)


@pytest.mark.parametrize("snippet", ENVIRONMENT_SNIPPETS)
def test_environment_elsewhere_is_reported(snippet: str) -> None:
    assert "BOS902" in reported_codes(snippet, SERVICE_FILE)


@pytest.mark.parametrize("snippet", ENVIRONMENT_SNIPPETS)
def test_environment_is_banned_in_tests(snippet: str) -> None:
    assert "BOS902" in reported_codes(snippet, TEST_FILE)


@pytest.mark.parametrize("snippet", ENVIRONMENT_SNIPPETS)
def test_environment_in_config_is_allowed(snippet: str) -> None:
    assert "BOS902" not in reported_codes(snippet, CONFIG_FILE)


@pytest.mark.parametrize("snippet", ENVIRONMENT_FREE_SNIPPETS)
def test_other_os_calls_are_allowed(snippet: str) -> None:
    assert "BOS902" not in reported_codes(snippet, SERVICE_FILE)


def test_environment_get_is_reported_once() -> None:
    snippet = "import os\n\nhost = os.environ.get('DATABASE_URL')\n"
    assert all_reported_codes(snippet, SERVICE_FILE).count("BOS902") == 1


@pytest.mark.parametrize("snippet", TYPE_CHECKING_DEFINITION_SNIPPETS)
def test_type_checking_definitions_fail(snippet: str) -> None:
    assert "BOS903" in reported_codes(snippet)


@pytest.mark.parametrize("snippet", TYPE_CHECKING_DEFINITION_SNIPPETS)
def test_type_checking_rule_applies_to_tests(snippet: str) -> None:
    assert "BOS903" in reported_codes(snippet, TEST_FILE)


@pytest.mark.parametrize("snippet", IMPORT_ONLY_SNIPPETS)
def test_type_checking_imports_pass(snippet: str) -> None:
    assert "BOS903" not in reported_codes(snippet)
