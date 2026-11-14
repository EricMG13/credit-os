import json
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from checks_context_support import build_context
from hypothesis import given, settings
from hypothesis import strategies as st

from credit_os.checks import figures
from credit_os.checks.figures import ISO_4217, Figure, read_figures
from credit_os.checks.findings import CheckContext, Finding
from credit_os.checks.run import check_handoff
from credit_os.handoff.document import HandoffDocument, parse
from credit_os.handoff.errors import HandoffError
from credit_os.handoff.reader import read_reader

KEY: dict[str, Any] = json.loads(
    (Path(__file__).resolve().parent / "expected" / "figures.json").read_text("utf-8")
)
FIGURE_CASES: dict[str, dict[str, Any]] = {case["name"]: case for case in KEY["cases"]}
ROWS = [(row, side) for row in KEY["reader"] for side in row["sides"]]
SECONDS = 2.0
_KEY_ONLY = ("name", "findings", "front", "tail", "expect", "columns", "reason_has")


def _document(case: dict[str, Any]) -> HandoffDocument:
    text = case.get("front", "") + KEY["head"] + case["findings"] + case.get("tail", KEY["tail"])
    return parse(text.encode("utf-8"))


def _context(case: dict[str, Any]) -> CheckContext:
    return build_context({"kind": "data", **KEY["context"]}, case, _KEY_ONLY)


def _bottom_line(line: str) -> HandoffDocument:
    return parse((KEY["head"] + "### Bottom line\n" + line + "\n" + KEY["tail"]).encode("utf-8"))


def _row(finding: Finding) -> list[Any]:
    return [finding.check, finding.severity, finding.line, finding.quoted]


def _form(document: HandoffDocument) -> tuple[Finding, ...]:
    return figures.check_form(document, _context({}))


def test_iso_4217() -> None:
    codes = KEY["iso_4217"]
    assert len(codes) == 176
    assert len(set(codes)) == 176
    assert frozenset(codes) == ISO_4217


@pytest.mark.parametrize(
    ("row", "side"), ROWS, ids=[f"row{index}-{side}" for index, (_, side) in enumerate(ROWS)]
)
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


@pytest.mark.parametrize(
    "name", list(FIGURE_CASES), ids=[f"case{i}" for i in range(len(FIGURE_CASES))]
)
def test_case(name: str) -> None:
    case = FIGURE_CASES[name]
    found = check_handoff(_document(case), _context(case))
    assert [_row(finding) for finding in found] == case["expect"]
    if "columns" in case:
        assert [finding.column for finding in found] == case["columns"]
    for index, texts in case.get("reason_has", {}).items():
        for text in texts if isinstance(texts, list) else [texts]:
            assert text in found[int(index)].reason


@pytest.mark.parametrize(
    "name", list(FIGURE_CASES), ids=[f"case{i}" for i in range(len(FIGURE_CASES))]
)
def test_every_finding_has_a_reason(name: str) -> None:
    case = FIGURE_CASES[name]
    for finding in check_handoff(_document(case), _context(case)):
        assert finding.reason.strip() != ""


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
    assert len(_form(_bottom_line(line))) == 1000


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
    ids=[f"line{index}" for index in range(len(_SLOW_LINES))],
)
def test_runs_in_bounded_time(line: str) -> None:
    for passage in (True, False):
        start = time.perf_counter()
        read_figures(line, passage=passage)
        assert time.perf_counter() - start < SECONDS
    document = _bottom_line(line)
    start = time.perf_counter()
    check_handoff(document, _context({}))
    assert time.perf_counter() - start < SECONDS


def test_a_hundred_digit_figure() -> None:
    # `figures.check_form` called directly: `check_handoff` adds a `prose.hash` finding on a
    # run of 12 or more digits, which is not what this test is about.
    digits = "1234567890" * 10
    read = read_figures(f"It was {digits} then.", passage=True)
    assert [f.value for f in read] == [Decimal(digits)]
    found = _form(_bottom_line(f"It was {digits} then."))
    assert [f.quoted for f in found] == [digits[:80] + "\u2026"]


@pytest.mark.parametrize(
    ("digits", "refused"),
    [
        ("0" * 4998 + "42", False),
        ("0" * 4998 + "99", False),
        ("0" * 4997 + "100", True),
        ("1" + "0" * 4999, True),
        ("0" * 4996 + "2024", True),
        ("2024", False),
        ("2100", True),
        ("1899", True),
        ("1900", False),
    ],
    ids=[f"row{i}" for i in range(9)],
)
def test_whole_number_judgement_is_by_value(digits: str, refused: bool) -> None:
    # `figures.check_form` called directly (no `prose.hash` finding); Decimal, never int().
    found = _form(_bottom_line(f"It was {digits} then."))
    assert len(found) == (1 if refused else 0)


def test_a_run_of_nines_reaches_the_reader_and_the_check() -> None:
    line = "9" * 10000
    for passage in (True, False):
        assert [f.value for f in read_figures(line, passage=passage)] == [Decimal(line)]
    checks = {f.check for f in check_handoff(_bottom_line(line), _context({}))}
    assert {"prose.hash", "figure.form"} <= checks


def test_a_lowercase_us_dollar_sign_is_dollars() -> None:
    assert [
        (f.currency, f.unit) for f in read_figures("It was us$5 m and us$ 6 bn.", passage=True)
    ] == [
        ("USD", "m"),
        ("USD", "b"),
    ]
    assert _form(_bottom_line("It was us$5 million and usd 6 and Gbp 7 million.")) == ()


def test_a_dash_before_an_ordinal_is_not_a_figure() -> None:
    assert _form(_bottom_line("It was the \u201315th and the 3rd of it.")) == ()


@pytest.mark.parametrize(
    ("line", "quoted"),
    [
        ("Margin was 5\u201310% of it.", []),
        ("Margin was 5%\u201310% of it.", []),
        ("Margin was 5 percent\u201310 of it.", []),
        ("Margin was Q3\u20135% of it.", []),
        ("Margin was 2023-01-15\u20135% of it.", []),
        ("Tranche B2\u20135% of it.", []),
        ("Margin was 5 \u201310% of it.", ["\u201310%"]),
        ("Margin was 5% \u201310% of it.", ["\u201310%"]),
        ("Margin was 5 percent \u201310 of it.", ["\u201310"]),
        ("Margin was Q3 \u20135% of it.", ["\u20135%"]),
        ("Margin was 2023-01-15 \u20135% of it.", ["\u20135%"]),
        ("Tranche B2 \u20135% of it.", ["\u20135%"]),
        ("In Q3, \u20135% it fell.", ["\u20135%"]),
        ("In LTM \u20135% it fell.", ["\u20135%"]),
        ("On 2024-09-30: \u20135% then.", ["\u20135%"]),
        ("Margin was a  \u20135% of it.", ["\u20135%"]),
        ("\u20135% of it.", ["\u20135%"]),
        ("Margin was the 5th \u20135% of it.", ["\u20135%"]),
        ("Margin was in \u20135 of it.", ["\u20135"]),
        ("\u20135 and 2", ["\u20135"]),
        ("5\u201310% of it.", []),
    ],
    ids=[f"row{i}" for i in range(21)],
)
def test_a_dash_is_a_range_only_after_a_figure(line: str, quoted: list[str]) -> None:
    assert [f.quoted for f in _form(_bottom_line(line))] == quoted


def test_a_comma_step_comes_before_the_decimals_step() -> None:
    found = _form(_bottom_line("It was 12,5678% and 1.2345,6 then."))
    assert [f.quoted for f in found] == ["12,5678", "1.2345,6"]
    assert {f.reason for f in found} == {figures._COMMA}


def test_a_comma_run_stops_before_punctuation() -> None:
    found = _form(_bottom_line("It was 12,5. Then 3,4, and 1,2."))
    assert [f.quoted for f in found] == ["12,5", "3,4", "1,2"]


def test_a_currency_inside_the_figure_comes_before_one_written_before_it() -> None:
    assert [(f.currency, f.shown) for f in read_figures("It was USD -\u20ac5.", passage=True)] == [
        ("EUR", "-\u20ac5")
    ]
    assert _form(_bottom_line("It was USD -\u20ac5 and USD (EUR 6).")) == ()
    found = _form(_bottom_line("It was EUR -a$5m and $-5m."))
    assert [f.quoted for f in found] == ["5m"]


def test_a_dash_before_a_currency_is_refused_unless_it_is_a_range() -> None:
    found = _form(_bottom_line("It was \u2013$5m, 5%\u2014USD 6 million and 5 \u2013$5m."))
    assert [f.quoted for f in found] == ["\u2013$5m", "\u2013$5m"]
    assert [f.column for f in found] == [8, 37]


def test_alone_on_an_earlier_format_document() -> None:
    case = FIGURE_CASES["earlier format: one refusal, no figure check"]
    assert _form(_document(case)) == ()


def test_alone_when_the_reader_raises() -> None:
    case = FIGURE_CASES["repeated passage heading: the figure check does not run"]
    document = _document(case)
    with pytest.raises(HandoffError):
        read_reader(document)
    assert _form(document) == ()


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


def test_a_comma_run_stops_at_a_letter() -> None:
    # mutmut survivor `_comma_run` ",." widened to "XX,.XX" (round 3).
    assert [f.quoted for f in _form(_bottom_line("It was 12,5X6 then."))] == ["12,5"]


def test_a_dash_at_the_line_start_before_a_currency_is_refused() -> None:
    # mutmut survivor `_dash_before` `span[0] > 0` changed to `> 1` (round 3).
    found = _form(_bottom_line("\u2013$5m fell."))
    assert [(f.quoted, f.column) for f in found] == [("\u2013$5m", 1)]


def test_a_dash_after_one_letter_at_the_line_start_is_refused() -> None:
    # mutmut survivor `previous_end = -1` changed to `+1` in `_line_findings` (round 3).
    found = _form(_bottom_line("a\u20135% fell."))
    assert [(f.quoted, f.column) for f in found] == [("\u20135%", 2)]


@pytest.mark.parametrize(
    ("line", "quoted"),
    [
        ("Debt was R$ 9M.", "9M"),
        ("Debt was -R$ 9M.", "9M"),
        ("Debt was (R$ -9M).", "9M"),
        ("Debt was R$ -(9M).", "9M"),
    ],
    ids=[f"row{i}" for i in range(4)],
)
def test_a_month_count_with_an_unrecognised_currency_is_an_amount(line: str, quoted: str) -> None:
    # Hand mutants of `_reads_currency` (unrecognised counted as none; the prefix currency, the
    # bracket currency and the sign walk dropped): the reader reads a currency, so the amount
    # is refused as an unrecognised currency, not masked as a month count.
    found = _form(_bottom_line(line))
    assert [(f.quoted, f.reason.startswith("Write the currency")) for f in found] == [
        (quoted, True)
    ]
