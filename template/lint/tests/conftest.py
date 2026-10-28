import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture
def scratch_folder() -> Iterator[Path]:
    with tempfile.TemporaryDirectory() as folder_name:
        yield Path(folder_name)
