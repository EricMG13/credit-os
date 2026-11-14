import json
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from credit_os.checks.figures import ISO_4217, Figure, read_figures

KEY: dict[str, Any] = json.loads(
    (Path(__file__).resolve().parent / "expected" / "figures.json").read_text("utf-8")
)
ROWS = [(row, side) for row in KEY["reader"] for side in row["sides"]]
SECONDS = 2.0


def test_iso_4217() -> None:
    codes = KEY["iso_4217"]
    assert len(codes) == 176
    assert len(set(codes)) == 176
    assert frozenset(codes) == ISO_4217


@pytest.mark.parametrize(("row", "side"), ROWS, ids=[f"{row['text']}|{side}" for row, side in ROWS])
def test_reader(row: dict[str, Any], side: str) -> None:
    read = read_figures(row["text"], passage=side == "passage")
    for figure in read:
        assert isinstance(figure.value, Decimal)
        assert not figure.value.is_signed()
    assert [
        (f.value, f.negative, f.bracketed, f.unit, f.currency, f.shown, f.column) for f in read
    ] == [
        (Decimal(value), negative, bracketed, unit, currency, shown, column)
        for value, negative, bracketed, unit, currency, shown, column in row["figures"]
    ]


def test_figure_is_a_frozen_node() -> None:
    figure = read_figures("It is 5%.", passage=True)[0]
    assert isinstance(figure, Figure)
    field = "negative"
    with pytest.raises(ValueError, match="frozen"):
        setattr(figure, field, True)


_SIGNS = {
    "none": ("", "", False, False),
    "minus": ("-", "", True, False),
    "unicode": ("−", "", True, False),
    "bracket": ("(", ")", True, True),
}
# What is written before the number -> the code a reader must give it.
_CURRENCIES = {
    None: ("", None),
    "US$": ("US$", "USD"),
    "$": ("$", "USD"),
    "€": ("€", "EUR"),
    "£": ("£", "GBP"),
    "¥": ("¥", "¥"),
    "USD": ("USD ", "USD"),
    "EUR": ("EUR ", "EUR"),
    "GBP": ("GBP ", "GBP"),
    "SEK": ("SEK ", "SEK"),
    "A$": ("A$", "AUD"),
}
# What is written after the number -> the unit a reader must give it.
_UNIT_WORDS = {
    "none": ("", None),
    "%": ("%", "%"),
    "x": ("x", "x"),
    "times": (" times", "x"),
    "pp": (" pp", "pp"),
    "bps": (" bps", "bp"),
    "basis points": (" basis points", "bp"),
    "notches": (" notches", "notch"),
    "days": (" days", "day"),
    "weeks": (" weeks", "week"),
    "months": (" months", "month"),
    "quarters": (" quarters", "quarter"),
    "years": (" years", "year"),
    "per cent": (" per cent", "%"),
}
_SCALE_WORDS = {
    "thousand": ("thousand", "k"),
    "mm": ("mm", "m"),
    "million": ("million", "m"),
    "bn": ("bn", "b"),
    "trillion": ("trillion", "t"),
}
# A currency written between the number and its scale.
_INSIDE = {"US$": "USD", "EUR": "EUR", "€": "EUR", "A$": "AUD", "USD": "USD"}


@settings(max_examples=200)
@given(
    sign=st.sampled_from(sorted(_SIGNS)),
    currency=st.sampled_from(sorted(_CURRENCIES, key=str)),
    whole=st.integers(min_value=0, max_value=10**9),
    commas=st.booleans(),
    decimals=st.one_of(st.none(), st.text(alphabet="0123456789", min_size=1, max_size=6)),
    leading_point=st.booleans(),
    unit=st.sampled_from(sorted(_UNIT_WORDS) + sorted(_SCALE_WORDS)),
    inside=st.one_of(st.none(), st.sampled_from(sorted(_INSIDE))),
    in_brackets=st.booleans(),
)
def test_reader_reads_back_the_parts(
    sign: str,
    currency: str | None,
    whole: int,
    commas: bool,
    decimals: str | None,
    leading_point: bool,
    unit: str,
    inside: str | None,
    in_brackets: bool,
) -> None:
    opening, closing, negative, bracketed = _SIGNS[sign]
    before, code = _CURRENCIES[currency]
    fraction = "" if decimals is None else "." + decimals
    if leading_point and decimals is not None:
        number, value = fraction, Decimal("0" + fraction)
    else:
        number = (f"{whole:,}" if commas else str(whole)) + fraction
        value = Decimal(str(whole) + fraction)
    spelled: str | None
    if unit in _SCALE_WORDS:
        word, spelled = _SCALE_WORDS[unit]
        written = " " + word if inside is None else f" {inside} {word}"
        code = code or (None if inside is None else _INSIDE[inside])
    else:
        written, spelled = _UNIT_WORDS[unit]
    inner = ""
    if in_brackets and closing:
        before, inner, code = "", "GBP ", "GBP"
    text = f"The amount was {before}{opening}{inner}{number}{closing}{written} here."
    read = read_figures(text, passage=True)
    assert len(read) == 1
    assert read[0].value == value
    assert read[0].negative == negative
    assert read[0].bracketed == bracketed
    assert read[0].unit == spelled
    assert read[0].currency == code


def test_a_thousand_figures_give_a_thousand_findings() -> None:
    line = "1,250 " * 1000
    assert len(read_figures(line, passage=True)) == 1000
    assert len(read_figures(line, passage=False)) == 1000


_SLOW_LINES = [
    "9" * 10000,
    "(USD 1" * 1666,
    "A$1 " * 2500,
    ".5" * 5000,
    "9M " * 2500,
    " \u2013 1" * 2500,
    "1," * 5000,
    "1 " * 5000,
    "(" * 10000,
    "USD " * 2500,
    "USD" + " " * 9000 + "1,250",
    "May" + " " * 9000,
    "$1 " * 3333,
    "-$1 " * 2500,
    "( 1 )" * 2000,
    ("1" + " " * 9 + "m") * 900,
    "1,2" * 3333,
    "\u20131" * 5000,
]


@pytest.mark.parametrize(
    "line",
    _SLOW_LINES,
    ids=[f"line{index}-{len(line)}" for index, line in enumerate(_SLOW_LINES)],
)
def test_runs_in_bounded_time(line: str) -> None:
    for passage in (True, False):
        start = time.perf_counter()
        read_figures(line, passage=passage)
        assert time.perf_counter() - start < SECONDS


def test_a_hundred_digit_figure() -> None:
    digits = "1234567890" * 10
    read = read_figures(f"It was {digits} then.", passage=True)
    assert [f.value for f in read] == [Decimal(digits)]


def test_a_run_of_nines_reaches_the_reader() -> None:
    line = "9" * 10000
    for passage in (True, False):
        assert [f.value for f in read_figures(line, passage=passage)] == [Decimal(line)]


def test_a_lowercase_us_dollar_sign_is_dollars() -> None:
    assert [
        (f.currency, f.unit) for f in read_figures("It was us$5 m and us$ 6 bn.", passage=True)
    ] == [
        ("USD", "m"),
        ("USD", "b"),
    ]


def test_a_currency_inside_the_figure_comes_before_one_written_before_it() -> None:
    assert [(f.currency, f.shown) for f in read_figures("It was USD -\u20ac5.", passage=True)] == [
        ("EUR", "-\u20ac5")
    ]


def test_a_minus_sign_before_a_bracket_keeps_the_currency() -> None:
    # Hand mutant N25 (U+2212 dropped from the sign walk); expected from the re-review's
    # closure probe, rows M-C2 (pr4-fx2-adv-closure.py).
    assert [
        (f.value, f.negative, f.bracketed, f.unit, f.currency, f.shown, f.column)
        for f in read_figures("It is USD \u2212(250) million.", passage=True)
    ] == [(Decimal(250), True, True, "m", "USD", "(250) million", 12)]


def test_a_second_sign_or_currency_inside_brackets() -> None:
    # Hand mutants N09, N17 and N18; expected as the re-review's mutant probe wrote them.
    read = read_figures("It was (-USD EUR 5) now.", passage=True)
    assert [(f.negative, f.bracketed) for f in read] == [(True, False)]
    assert [f.currency for f in read_figures("It was (USD EUR 5) now.", passage=True)] == ["USD"]
