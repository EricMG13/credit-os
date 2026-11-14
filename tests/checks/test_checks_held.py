import json
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from checks_context_support import build_context, without_held
from hypothesis import given, settings
from hypothesis import strategies as st

from credit_os.checks import held
from credit_os.checks.figures import read_figures
from credit_os.checks.findings import CheckContext, Finding
from credit_os.checks.run import check_handoff
from credit_os.handoff.document import HandoffDocument, parse
from credit_os.handoff.errors import HandoffError
from credit_os.handoff.reader import read_reader

KEY: dict[str, Any] = json.loads(
    (Path(__file__).resolve().parent / "expected" / "held.json").read_text("utf-8")
)
CASES: list[dict[str, Any]] = KEY["cases"]
ROWS = [(row, side) for row in KEY["reader"] for side in row["sides"]]
SECONDS = 2.0
_KEY_ONLY = (
    "name",
    "findings",
    "front",
    "tail",
    "expect",
    "columns",
    "reason_has",
    "reason_lacks",
    "known_false_refusal",
)


def _text(case: dict[str, Any]) -> str:
    text = case.get("front", "") + KEY["head"] + case["findings"] + case.get("tail", KEY["tail"])
    return str(text)


def _context(case: dict[str, Any]) -> CheckContext:
    return build_context({"kind": "data", **KEY["context"]}, case, _KEY_ONLY)


def _pair(findings: str, tail: str) -> HandoffDocument:
    return parse((KEY["head"] + findings + tail).encode("utf-8"))


def _calculations(body: str) -> str:
    return "## Calculations\n" + body + "## Gaps\nNone.\n## Next module\nNone.\n"


def _row(finding: Finding) -> list[Any]:
    return [finding.check, finding.severity, finding.line, finding.quoted]


def _both(document: HandoffDocument) -> tuple[Finding, ...]:
    context = _context({})
    return (*held.check_not_held(document, context), *held.check_mismatch(document, context))


@pytest.mark.parametrize(("row", "side"), ROWS, ids=[f"{i}|{s}" for i, (_, s) in enumerate(ROWS)])
def test_reader(row: dict[str, Any], side: str) -> None:
    read = read_figures(row["text"], passage=side == "passage")
    assert [
        (f.value, f.negative, f.bracketed, f.unit, f.currency, f.shown, f.column) for f in read
    ] == [
        (Decimal(value), negative, bracketed, unit, currency, shown, column)
        for value, negative, bracketed, unit, currency, shown, column in row["figures"]
    ]


@pytest.mark.parametrize("index", range(len(CASES)))
def test_case(index: int) -> None:
    case = CASES[index]
    found = check_handoff(parse(_text(case).encode("utf-8")), _context(case))
    assert [_row(finding) for finding in found] == case["expect"]
    if "columns" in case:
        assert [finding.column for finding in found] == case["columns"]
    for at, texts in case.get("reason_has", {}).items():
        for text in texts if isinstance(texts, list) else [texts]:
            assert text in found[int(at)].reason
    for at, texts in case.get("reason_lacks", {}).items():
        for text in texts if isinstance(texts, list) else [texts]:
            assert text not in found[int(at)].reason


@pytest.mark.parametrize("index", range(len(CASES)))
def test_every_finding_has_a_reason(index: int) -> None:
    case = CASES[index]
    for finding in check_handoff(parse(_text(case).encode("utf-8")), _context(case)):
        assert finding.reason.strip() != ""


def test_known_false_refusals_stay_in_the_key() -> None:
    known = [case["name"] for case in CASES if "known_false_refusal" in case]
    assert known == [
        "refused: a word that is also a currency code before a hyphen and a digit",
        (
            "known false refusal: a date mask takes `March 1` and leaves 5% of a written 1.5% "
            "(#250 review I-1)"
        ),
    ]


_EARLIER = _pair("### Other\nDebt was USD 1,250 million.\n", _calculations("None.\n"))
_UNREADABLE = _pair(
    "### Bottom line\nDebt was 5%.\n### Bottom line\nDebt was 6%.\n", _calculations("None.\n")
)


def test_the_fixtures_for_the_silent_cases_are_what_they_say() -> None:
    assert read_reader(_EARLIER).format == "earlier"
    with pytest.raises(HandoffError, match="repeated"):
        read_reader(_UNREADABLE)


@pytest.mark.parametrize("document", [_EARLIER, _UNREADABLE], ids=["earlier", "unreadable"])
def test_each_check_alone_is_silent_without_a_new_format_reader(document: HandoffDocument) -> None:
    assert held.check_not_held(document, _context({})) == ()
    assert held.check_mismatch(document, _context({})) == ()


def test_check_handoff_runs_neither_on_an_earlier_format_document() -> None:
    found = check_handoff(_EARLIER, _context({}))
    assert [f.check for f in found if f.check.startswith("figure.")] == []


def test_a_new_format_document_with_nothing_to_judge_gives_nothing() -> None:
    assert _both(_pair("### Bottom line\nA plain sentence.\n", _calculations("None.\n"))) == ()


_UNITS = ("%", "x", "m")
_NUMBERS = st.integers(min_value=1, max_value=10**6)


def _figure_text(negative: bool, currency: str, number: int, unit: str) -> str:
    return f"{'-' if negative else ''}{currency}{number}{unit}"


def _judged(passage: str, held_text: str) -> tuple[list[Finding], list[Finding]]:
    document = _pair(
        f"### Bottom line\nDebt was {passage}.\n",
        _calculations(f"| Item | Value |\n| --- | --- |\n| Debt | {held_text} |\n"),
    )
    context = _context({})
    return list(held.check_not_held(document, context)), list(
        held.check_mismatch(document, context)
    )


@settings(max_examples=200)
@given(
    negative=st.booleans(),
    currency=st.sampled_from(["", "USD ", "EUR "]),
    number=_NUMBERS,
    unit=st.sampled_from(_UNITS),
)
def test_a_figure_copied_into_a_table_cell_is_held(
    negative: bool, currency: str, number: int, unit: str
) -> None:
    text = _figure_text(negative, currency, number, unit)
    assert _judged(text, text) == ([], [])


@settings(max_examples=200)
@given(
    currency=st.sampled_from(["", "USD "]),
    number=_NUMBERS,
    other=_NUMBERS,
    unit=st.sampled_from(_UNITS),
)
def test_a_changed_digit_is_not_held(currency: str, number: int, other: int, unit: str) -> None:
    if other == number:
        return
    not_held, mismatch = _judged(
        _figure_text(False, currency, number, unit), _figure_text(False, currency, other, unit)
    )
    assert [f.quoted for f in not_held] == [f"{number}{unit}"]
    assert mismatch == []


@settings(max_examples=200)
@given(
    number=_NUMBERS,
    held_unit=st.sampled_from(_UNITS),
    passage_unit=st.sampled_from(_UNITS),
)
def test_a_changed_unit_is_a_mismatch(number: int, held_unit: str, passage_unit: str) -> None:
    if held_unit == passage_unit:
        return
    not_held, mismatch = _judged(f"{number}{passage_unit}", f"{number}{held_unit}")
    assert not_held == []
    assert [f.quoted for f in mismatch] == [f"{number}{passage_unit}"]
    assert f"writes it: {number}{held_unit}." in mismatch[0].reason


@settings(max_examples=200)
@given(number=_NUMBERS, unit=st.sampled_from(_UNITS))
def test_a_minus_the_handoff_does_not_write_is_a_mismatch(number: int, unit: str) -> None:
    not_held, mismatch = _judged(f"-{number}{unit}", f"{number}{unit}")
    assert not_held == []
    assert [f.quoted for f in mismatch] == [f"-{number}{unit}"]


@settings(max_examples=200)
@given(number=_NUMBERS, unit=st.sampled_from(_UNITS))
def test_a_changed_currency_is_a_mismatch(number: int, unit: str) -> None:
    not_held, mismatch = _judged(f"USD {number}{unit}", f"EUR {number}{unit}")
    assert not_held == []
    assert [f.quoted for f in mismatch] == [f"{number}{unit}"]


@settings(max_examples=200)
@given(
    start=st.text(alphabet="0123456789 abc%x.", max_size=12),
    end=st.text(alphabet="0123456789 abc%x.", max_size=12),
    prefix=st.sampled_from(["Not supplied: ", "Not calculable: "]),
)
def test_no_gap_text_holds_a_zero(start: str, end: str, prefix: str) -> None:
    gap = f"{prefix}{start}0{end}"
    for body in (f"{gap}\n", f"| Item | Value |\n| --- | --- |\n| Debt | {gap} |\n"):
        document = _pair("### Bottom line\nDebt was 0.\n", _calculations(body))
        assert [f.quoted for f in held.check_not_held(document, _context({}))] == ["0"]


def _within(seconds: float, start: float) -> None:
    assert time.perf_counter() - start < seconds


def test_five_thousand_notes_in_one_line_read_in_time_on_both_sides() -> None:
    line = "1.5(2) " * 5000
    assert len(line) == 35_000
    for passage in (True, False):
        start = time.perf_counter()
        read = read_figures(line, passage=passage)
        _within(SECONDS, start)
        assert len(read) == 10_000
        assert not any(f.negative for f in read)


def test_a_thousand_held_figures_and_a_thousand_judged_figures_run_in_time() -> None:
    rows = "".join(f"| Item {n} | {n}% |\n" for n in range(1, 1001))
    lines = "".join(
        "- " + " ".join(f"{n}%" for n in range(start, start + 10)) + "\n"
        for start in range(1, 1001, 10)
    )
    document = _pair(
        "### Bottom line\n" + lines, _calculations("| Item | Value |\n| --- | --- |\n" + rows)
    )
    start = time.perf_counter()
    found = _both(document)
    _within(SECONDS, start)
    assert found == ()
    document = _pair("### Bottom line\n" + lines, _calculations("None.\n"))
    start = time.perf_counter()
    found = held.check_not_held(document, _context({}))
    _within(SECONDS, start)
    assert len(found) == 1000


def _read_pair(text: str, passage: bool) -> list[tuple[bool, bool]]:
    return [(f.negative, f.bracketed) for f in read_figures(text, passage=passage)]


@pytest.mark.parametrize("passage", [True, False])
def test_a_hundred_digit_figure_is_rounded_without_raising(passage: bool) -> None:
    # 99...9.55 rounded half up to one place is 99...9.6, written in the bracket: a note.
    text = f"It was {'9' * 100}.55 ({'9' * 100}.6)."
    assert _read_pair(text, passage) == [(False, False), (False, False)]


@pytest.mark.parametrize("passage", [True, False])
def test_a_figure_with_many_leading_zeros_is_rounded_without_raising(passage: bool) -> None:
    # 0.(31 zeros)49 to 32 places is 0.(31 zeros)5; to 2 places it is 0.00.
    before = "0." + "0" * 31 + "49"
    text = f"It was {before} (0.{'0' * 31}5) and {before} (0.00)."
    assert _read_pair(text, passage) == [(False, False)] * 4


@pytest.mark.parametrize("passage", [True, False])
def test_the_same_figure_with_separators_on_both_sides_is_a_negative(passage: bool) -> None:
    assert _read_pair("It was 1,250.50 (1,250.50).", passage) == [(False, False), (True, True)]


def test_a_currency_symbol_before_a_minus_is_not_refused_by_r59() -> None:
    document = _pair("### Bottom line\nIt lost US$-5m.\n", _calculations("It lost -US$5m.\n"))
    assert check_handoff(document, _context({})) == ()


def test_r59_refuses_the_currency_after_a_hyphen_that_is_no_currency() -> None:
    document = _pair(
        "### Bottom line\nThe B-1 loan lost USD-5 million.\n",
        _calculations("The B-1 loan lost USD 5 million.\n"),
    )
    found = check_handoff(document, _context({}))
    assert [(f.check, f.quoted, f.column) for f in found] == [("figure.form", "USD-5", 19)]


def test_a_held_spelling_over_eighty_characters_is_cut_by_echo_in_the_mismatch_reason() -> None:
    long_shown = "5" + " " * 100 + "million"
    document = _pair(
        "### Bottom line\nDebt was USD 5 million.\n",
        _calculations(f"| Item | Value |\n| --- | --- |\n| Debt | EUR {long_shown} |\n"),
    )
    found = held.check_mismatch(document, _context({}))
    assert len(found) == 1
    # echo's rule: the first 80 characters of the spelling, then one ellipsis.
    cut = "5" + " " * 79 + "\u2026"
    assert found[0].reason == f"Keep the sign, unit and currency as the handoff writes it: {cut}."


def test_a_figure_held_only_in_an_accepted_or_an_upstream_document_is_not_held() -> None:
    other = _pair("### Bottom line\nText.\n", _calculations("Margin was 12%.\n"))
    this = _pair("### Bottom line\nMargin was 12%.\n", _calculations("None.\n"))
    for context in (
        CheckContext(kind="data", accepted={"CP-1": other}),
        CheckContext(kind="data", upstream={"CP-0": other}),
    ):
        assert [(f.check, f.quoted) for f in held.check_not_held(this, context)] == [
            ("figure.not-held", "12%")
        ]
        assert held.check_mismatch(this, context) == ()


def test_without_held_drops_exactly_the_two_held_checks_and_keeps_the_rest_in_order() -> None:
    names = [
        "figure.form",
        "figure.not-held",
        "prose.provider-marker",
        "figure.mismatch",
        "figure.form",
    ]
    findings = [
        Finding(check=name, severity="refusal", line=index + 1, column=1, quoted="q", reason="r")
        for index, name in enumerate(names)
    ]
    kept = without_held(findings)
    assert [(f.check, f.line) for f in kept] == [
        ("figure.form", 1),
        ("prose.provider-marker", 3),
        ("figure.form", 5),
    ]
