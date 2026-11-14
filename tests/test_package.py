import importlib

import credit_os


def test_version() -> None:
    assert credit_os.__version__ == "0.1.0"


def test_every_layer_imports() -> None:
    assert credit_os.LAYERS == (
        "sources",
        "handoff",
        "model",
        "provider",
        "store",
        "checks",
        "orchestrator",
        "delivery",
        "signal",
    )
    assert frozenset({"signal"}) == credit_os.ISOLATED
    for name in credit_os.LAYERS:
        importlib.import_module(f"credit_os.{name}")
