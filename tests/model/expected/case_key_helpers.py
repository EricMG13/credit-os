"""Helpers shared by the 7a1 and 7a2 case tests, loaded by path (tests/ has no packages).

They read a key row; they compute no expected value. The oracle scripts stay free of `credit_os`.
"""

import decimal
import importlib.util
from decimal import Context
from pathlib import Path
from typing import Any

from credit_os.model.inputs import ForecastInputs, parse_inputs
from credit_os.model.value import Missing, MissingCode, Value, amount_text

EXPECTED = Path(__file__).resolve().parent
HOSTILE = Context(prec=5, rounding=decimal.ROUND_UP)


def load_oracle(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, EXPECTED / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inputs_of(oracle: Any, edits: list[Any]) -> ForecastInputs:
    return parse_inputs(oracle.edited(edits))[0]


def ids(rows: list[dict[str, Any]]) -> list[str]:
    return [r["name"] for r in rows]


def want(reasons: dict[str, Any], item: Any) -> Value | str:
    """An expected value: the amount text, or the Value that is missing."""
    if isinstance(item, str):
        return item
    missing = item["missing"]
    if isinstance(missing, str):
        code, text = reasons[missing]
        return Value(missing=Missing(MissingCode(code), text))
    return Value(missing=Missing(MissingCode(missing["code"]), missing["text"]))


def same_value(reasons: dict[str, Any], got: Value, item: Any, where: str) -> None:
    expected = want(reasons, item)
    if isinstance(expected, str):
        assert got.missing is None, where
        assert got.amount is not None, where
        assert amount_text(got.amount) == expected, where
    else:
        assert got == expected, where
