"""Display text and JSON number tokens, against the controller's answer key."""

import decimal
import json
import re
from collections.abc import Callable
from datetime import datetime
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any, cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

from credit_os.model.display import (
    axis_max,
    axis_ticks,
    bridge_positions,
    display_text,
    elapsed_minutes,
    json_number,
    megabytes_text,
    row_positions,
    shares,
    token_sum,
)
from credit_os.model.value import Missing, MissingCode, Value

KEY = json.loads((Path(__file__).parent / "expected" / "display.json").read_text("utf-8"))
TEXT = KEY["display_text"]
NUMBER = KEY["json_number"]
SCALES = json.loads((Path(__file__).parent / "expected" / "scales.json").read_text("utf-8"))
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


AMBIENT = {
    "up5": decimal.Context(prec=5, rounding=decimal.ROUND_UP),
    "tight5": decimal.Context(
        prec=1, rounding=decimal.ROUND_DOWN, traps=[], flags=[], Emax=5, Emin=-5
    ),
    "tight3": decimal.Context(prec=1, Emin=-3, Emax=3, traps=[], flags=[]),
}


@pytest.mark.parametrize("ctx", AMBIENT.values(), ids=list(AMBIENT))
def test_display_and_json_rows_ignore_the_ambient_context(ctx: decimal.Context) -> None:
    with decimal.localcontext(ctx):
        for text, places, expected in TEXT["rows"]:
            assert display_text(Value(amount=Decimal(text)), places) == expected
        for row in TEXT["refused"]:
            value: Any = Value(amount=Decimal("1.5")) if row["value"] == "1.5" else Decimal("1.5")
            with pytest.raises(ERRORS[str(row["error"])]):
                display_text(value, row["places"])
        for text, expected in NUMBER["rows"]:
            assert json_number(Decimal(text)) == expected
        for row in NUMBER["refused"]:
            with pytest.raises(ERRORS[row["error"]]):
                json_number(Decimal(row["value"]))


NOT_SOURCED = Missing(MissingCode.NOT_SOURCED, "Not sourced")


def fig(raw: str | None) -> Value:
    return Value(missing=NOT_SOURCED) if raw is None else Value(amount=Decimal(raw))


def figs(raws: list[str | None]) -> list[Value]:
    return [fig(raw) for raw in raws]


def same(got: Decimal | None, key: str | None) -> None:
    if key is None:
        assert got is None
        return
    assert got is not None
    assert type(got) is Decimal
    assert json_number(got) == key
    assert not (got.is_zero() and got.is_signed())


def same_all(got: tuple[Decimal | None, ...], keys: list[str | None]) -> None:
    assert len(got) == len(keys)
    for one, key in zip(got, keys, strict=True):
        same(one, key)


def ids(rows: list[Any], prefix: str) -> list[str]:
    return [f"{prefix}{i}" for i in range(len(rows))]


def when(raw: str | None) -> datetime | None:
    return None if raw is None else datetime.fromisoformat(raw)


MB = SCALES["megabytes_text"]
ELAPSED = SCALES["elapsed_minutes"]
TOKENS = SCALES["token_sum"]
POSITIONS = SCALES["row_positions"]
SHARES = SCALES["shares"]
TICKS = SCALES["axis_ticks"]
MAXIMA = SCALES["axis_max"]
BRIDGES = SCALES["bridge_positions"]


def _check_ticks(raws: list[str | None], ticks: list[str] | None, places: int | None) -> None:
    got = axis_ticks(figs(raws))
    if ticks is None:
        assert got is None
        return
    assert got is not None
    assert places == got[1]
    same_all(got[0], cast(list[str | None], ticks))


def _check_bridge(steps: list[list[Any]], expected: list[Any] | None) -> None:
    got = bridge_positions([(bool(flag), fig(raw)) for flag, raw in steps])
    if expected is None:
        assert got is None
        return
    assert got is not None
    assert len(got) == len(expected)
    for pair, key in zip(got, expected, strict=True):
        if key is None:
            assert pair is None
            continue
        assert pair is not None
        same_all(pair, key)


def _check_shares(raws: list[str | None], places: int, expected: list[str] | None) -> None:
    got = shares(figs(raws), places)
    if expected is None:
        assert got is None
        return
    assert got is not None
    same_all(got, cast(list[str | None], expected))


def _check_elapsed(start: str | None, end: str | None, key: str | None, text: str | None) -> None:
    got = elapsed_minutes(when(start), when(end))
    same(got, key)
    if got is not None:
        assert display_text(Value(amount=got), 1) == text


def _run_scales() -> None:
    for size, text in MB["rows"]:
        assert megabytes_text(size) == text
    for start, end, key, text in ELAPSED["rows"]:
        _check_elapsed(start, end, key, text)
    for counts, total in TOKENS["rows"]:
        assert token_sum(counts) == total
    for raws, expected in POSITIONS["rows"]:
        same_all(row_positions(figs(raws)), expected)
    for raws, places, expected in SHARES["rows"]:
        _check_shares(raws, places, expected)
    for raws, ticks, places in TICKS["rows"]:
        _check_ticks(raws, ticks, places)
    for raws, key in MAXIMA["rows"]:
        same(axis_max(figs(raws)), key)
    for steps, expected in BRIDGES["rows"]:
        _check_bridge(steps, expected)
    _run_refused()


def _run_refused() -> None:
    for row in MB["refused"]:
        with pytest.raises(ERRORS[row["error"]]):
            megabytes_text(row["value"])
    for row in ELAPSED["refused"]:
        with pytest.raises(ERRORS[row["error"]]):
            elapsed_minutes(when(row["start"]), when(row["end"]))
    for row in TOKENS["refused"]:
        with pytest.raises(ERRORS[row["error"]]):
            token_sum(row["value"])
    for row in SHARES["refused"]:
        with pytest.raises(ERRORS[row["error"]]):
            shares(figs(row["parts"]), row["places"])
    for row in TICKS["refused"]:
        with pytest.raises(ERRORS[row["error"]]):
            axis_ticks(figs(row["values"]))
    for row in MAXIMA["refused"]:
        with pytest.raises(ERRORS[row["error"]]):
            axis_max(figs(row["values"]))
    for row in BRIDGES["refused"]:
        with pytest.raises(ERRORS[row["error"]]):
            bridge_positions([(bool(flag), fig(raw)) for flag, raw in row["steps"]])


@pytest.mark.parametrize(("size", "text"), MB["rows"], ids=ids(MB["rows"], "mb"))
def test_megabytes_rows(size: int, text: str) -> None:
    assert megabytes_text(size) == text


@pytest.mark.parametrize("row", MB["refused"], ids=ids(MB["refused"], "mbx"))
def test_megabytes_refused(row: dict[str, Any]) -> None:
    with pytest.raises(ERRORS[row["error"]]):
        megabytes_text(row["value"])


@pytest.mark.parametrize(
    ("start", "end", "key", "text"), ELAPSED["rows"], ids=ids(ELAPSED["rows"], "el")
)
def test_elapsed_rows(
    start: str | None, end: str | None, key: str | None, text: str | None
) -> None:
    _check_elapsed(start, end, key, text)


@pytest.mark.parametrize("row", ELAPSED["refused"], ids=ids(ELAPSED["refused"], "elx"))
def test_elapsed_refused(row: dict[str, Any]) -> None:
    with pytest.raises(ERRORS[row["error"]]):
        elapsed_minutes(when(row["start"]), when(row["end"]))


@pytest.mark.parametrize("bad", ["2025-03-31T10:00:00+00:00", 5], ids=["text", "int"])
def test_elapsed_type(bad: Any) -> None:
    with pytest.raises(TypeError):
        elapsed_minutes(bad, when("2025-03-31T10:00:00+00:00"))


@pytest.mark.parametrize(("counts", "total"), TOKENS["rows"], ids=ids(TOKENS["rows"], "tk"))
def test_token_sum_rows(counts: list[int | None], total: int | None) -> None:
    assert token_sum(counts) == total


@pytest.mark.parametrize("row", TOKENS["refused"], ids=ids(TOKENS["refused"], "tkx"))
def test_token_sum_refused(row: dict[str, Any]) -> None:
    with pytest.raises(ERRORS[row["error"]]):
        token_sum(row["value"])


@pytest.mark.parametrize(("raws", "expected"), POSITIONS["rows"], ids=ids(POSITIONS["rows"], "rp"))
def test_row_positions_rows(raws: list[str | None], expected: list[str | None]) -> None:
    same_all(row_positions(figs(raws)), expected)


@pytest.mark.parametrize(
    ("raws", "places", "expected"), SHARES["rows"], ids=ids(SHARES["rows"], "sh")
)
def test_shares_rows(raws: list[str | None], places: int, expected: list[str] | None) -> None:
    _check_shares(raws, places, expected)


@pytest.mark.parametrize("row", SHARES["refused"], ids=ids(SHARES["refused"], "shx"))
def test_shares_refused(row: dict[str, Any]) -> None:
    with pytest.raises(ERRORS[row["error"]]):
        shares(figs(row["parts"]), row["places"])


@pytest.mark.parametrize(("raws", "ticks", "places"), TICKS["rows"], ids=ids(TICKS["rows"], "ax"))
def test_axis_ticks_rows(
    raws: list[str | None], ticks: list[str] | None, places: int | None
) -> None:
    _check_ticks(raws, ticks, places)


@pytest.mark.parametrize("row", TICKS["refused"], ids=ids(TICKS["refused"], "axx"))
def test_axis_ticks_refused(row: dict[str, Any]) -> None:
    with pytest.raises(ERRORS[row["error"]]):
        axis_ticks(figs(row["values"]))


@pytest.mark.parametrize(("raws", "key"), MAXIMA["rows"], ids=ids(MAXIMA["rows"], "am"))
def test_axis_max_rows(raws: list[str | None], key: str | None) -> None:
    same(axis_max(figs(raws)), key)


@pytest.mark.parametrize("row", MAXIMA["refused"], ids=ids(MAXIMA["refused"], "amx"))
def test_axis_max_refused(row: dict[str, Any]) -> None:
    with pytest.raises(ERRORS[row["error"]]):
        axis_max(figs(row["values"]))


@pytest.mark.parametrize(("steps", "expected"), BRIDGES["rows"], ids=ids(BRIDGES["rows"], "br"))
def test_bridge_rows(steps: list[list[Any]], expected: list[Any] | None) -> None:
    _check_bridge(steps, expected)


@pytest.mark.parametrize("row", BRIDGES["refused"], ids=ids(BRIDGES["refused"], "brx"))
def test_bridge_refused(row: dict[str, Any]) -> None:
    with pytest.raises(ERRORS[row["error"]]):
        bridge_positions([(bool(flag), fig(raw)) for flag, raw in row["steps"]])


@pytest.mark.parametrize(
    "call",
    [
        lambda: row_positions(cast(Any, [Decimal(1)])),
        lambda: shares(cast(Any, [Decimal(1)]), 1),
        lambda: axis_ticks(cast(Any, [Decimal(1)])),
        lambda: axis_max(cast(Any, [Decimal(1)])),
        lambda: bridge_positions(cast(Any, [(True, Decimal(1))])),
        lambda: bridge_positions(cast(Any, [(1, fig("1"))])),
        lambda: shares(figs(["1"]), cast(int, True)),
    ],
    ids=["rp", "sh", "ax", "am", "br", "flag", "places"],
)
def test_wrong_types_are_refused(call: Callable[[], object]) -> None:
    with pytest.raises(TypeError):
        call()


@pytest.mark.parametrize("ctx", AMBIENT.values(), ids=[f"s_{name}" for name in AMBIENT])
def test_scales_rows_ignore_the_ambient_context(ctx: decimal.Context) -> None:
    with decimal.localcontext(ctx):
        _run_scales()


_small = st.integers(min_value=-(10**6), max_value=10**6)


@given(st.lists(_small, min_size=1, max_size=8))
def test_row_positions_error_and_bounds(raws: list[int]) -> None:
    got = row_positions([Value(amount=Decimal(n)) for n in raws])
    top = max(abs(n) for n in raws)
    for n, position in zip(raws, got, strict=True):
        assert position is not None
        assert -1 <= position <= 1
        exact = Fraction(n, top) if top else Fraction(0)
        assert abs(Fraction(position) - exact) <= Fraction(1, 20000)


@given(
    st.lists(st.integers(min_value=1, max_value=10**6), min_size=1, max_size=8),
    st.integers(min_value=0, max_value=6),
)
def test_shares_error(raws: list[int], places: int) -> None:
    got = shares([Value(amount=Decimal(n)) for n in raws], places)
    assert got is not None
    for n, share in zip(raws, got, strict=True):
        exact = Fraction(100 * n, sum(raws))
        assert abs(Fraction(share) - exact) <= Fraction(1, 2 * 10**places)


STEPS = sorted(
    Fraction(s) * Fraction(10) ** j
    for s in ("1", "1.25", "1.5", "2", "2.5", "3", "4", "5", "6", "7.5")
    for j in range(-12, 13)
)


@given(st.integers(min_value=1, max_value=10**6), st.integers(min_value=-4, max_value=8))
def test_axis_ticks_cover_and_are_least(n: int, exponent: int) -> None:
    top = Decimal((0, tuple(map(int, str(n))), exponent))
    got = axis_ticks([Value(amount=top)])
    assert got is not None
    ticks, _places = got
    assert Fraction(ticks[-1]) >= Fraction(top)
    smaller = [s for s in STEPS if s < Fraction(ticks[1])]
    assert 4 * smaller[-1] < Fraction(top)
