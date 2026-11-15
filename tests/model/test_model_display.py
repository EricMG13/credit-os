"""Display text and JSON number tokens, against the controller's answer key."""

import decimal
import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from credit_os.model.display import display_text, json_number
from credit_os.model.value import Missing, MissingCode, Value

KEY = json.loads((Path(__file__).parent / "expected" / "display.json").read_text("utf-8"))
TEXT = KEY["display_text"]
NUMBER = KEY["json_number"]
WIDE = decimal.Context(prec=400)
TOKEN = re.compile(r"-?(0|[1-9][0-9]*)(\.[0-9]*[1-9])?")


ERRORS: dict[str, type[Exception]] = {
    "ValueError": ValueError,
    "TypeError": TypeError,
    "Inexact": decimal.Inexact,
    "Overflow": decimal.Overflow,
    "Underflow": decimal.Underflow,
}


@pytest.mark.parametrize(
    ("text", "places", "expected"),
    TEXT["rows"],
    ids=[f"t{i}" for i in range(len(TEXT["rows"]))],
)
def test_display_rows(text: str, places: int, expected: str) -> None:
    assert display_text(Value(amount=Decimal(text)), places) == expected


@pytest.mark.parametrize(
    ("code", "words", "places"),
    TEXT["missing"]["rows"],
    ids=[f"m{i}" for i in range(len(TEXT["missing"]["rows"]))],
)
def test_display_missing(code: str, words: str, places: int) -> None:
    value = Value(missing=Missing(MissingCode[code], words))
    assert display_text(value, places) is None


@pytest.mark.parametrize("row", TEXT["refused"], ids=[f"r{i}" for i in range(len(TEXT["refused"]))])
def test_display_refused(row: dict[str, Any]) -> None:
    raw = row["value"]
    value: Any = Value(amount=Decimal("1.5")) if raw == "1.5" else Decimal("1.5")
    with pytest.raises(ERRORS[str(row["error"])]):
        display_text(value, row["places"])


@pytest.mark.parametrize(
    ("text", "expected"),
    NUMBER["rows"],
    ids=[f"n{i}" for i in range(len(NUMBER["rows"]))],
)
def test_json_number_rows(text: str, expected: str) -> None:
    assert json_number(Decimal(text)) == expected


@pytest.mark.parametrize(
    "row", NUMBER["refused"], ids=[f"x{i}" for i in range(len(NUMBER["refused"]))]
)
def test_json_number_refused(row: dict[str, str]) -> None:
    with pytest.raises(ERRORS[row["error"]]):
        json_number(Decimal(row["value"]))


@pytest.mark.parametrize("bad", [1, 1.5, "1"], ids=["int", "float", "str"])
def test_json_number_types(bad: Any) -> None:
    with pytest.raises(TypeError):
        json_number(bad)


bounded = st.decimals(allow_nan=False, allow_infinity=False, places=None).filter(
    lambda d: d == 0 or -100 <= d.adjusted() <= 100
)


def _fits(d: Decimal) -> bool:
    try:
        Value(amount=d)
    except (decimal.DecimalException, ValueError):
        return False
    return True


valid = bounded.filter(_fits)


@given(valid)
def test_json_number_roundtrip(d: Decimal) -> None:
    token = json_number(d)
    assert Decimal(token) == d
    assert TOKEN.fullmatch(token)
    assert token != "-0"


@given(valid, st.integers(min_value=0, max_value=6))
def test_display_within_half_unit(d: Decimal, places: int) -> None:
    shown = display_text(Value(amount=d), places)
    assert shown is not None
    parsed = Decimal(shown.replace(",", ""))
    gap = WIDE.subtract(parsed, d).copy_abs()
    assert gap <= Decimal(5).scaleb(-(places + 1))
    fraction = shown.partition(".")[2]
    assert len(fraction) == places
