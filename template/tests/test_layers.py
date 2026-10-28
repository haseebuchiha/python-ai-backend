import importlib

import pytest

LAYERS = ["routes", "services", "models", "config", "schemas"]


@pytest.mark.parametrize("layer", LAYERS)
def test_each_layer_is_a_package(layer: str) -> None:
    package = importlib.import_module(f"app.{layer}")
    assert package.__path__
