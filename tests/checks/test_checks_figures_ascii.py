"""Answer key (controller's) for the figure reader's ASCII-digits rule: no foreign decimal digit is a figure.

Every non-ASCII character is built with chr(0x....); this file is pure ASCII. The expected values were
worked by hand from the rule before any reader was run, not by running production code.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from checks_context_support import build_context
from hypothesis import given, settings
from hypothesis import strategies as st

from credit_os.checks import figures
from credit_os.checks.figures import read_figures
from credit_os.checks.findings import CheckContext
from credit_os.delivery import passages
from credit_os.handoff.document import HandoffDocument, parse

KEY: dict[str, Any] = json.loads(
    (Path(__file__).resolve().parent / "expected" / "figures.json").read_text("utf-8")
)
_DIGITS = "digits 0 to 9"
_BARE = "reword it in words or move it to a table"
_REASONS = {"digits": _DIGITS, "bare": _BARE}

_LEAKS = [
    pytest.param("See T" + chr(0x661) + ".2 here.", (), id="leak-t-ai"),
    pytest.param("See T1." + chr(0x662) + " here.", (), id="leak-t-1-ai"),
    pytest.param("See T1.2 here.", ("T1.2",), id="leak-ctl-t"),
    pytest.param("See CP-7 here.", ("CP-7",), id="leak-ctl-cp"),
]


@pytest.mark.parametrize(("text", "want"), _LEAKS)
def test_narrative_leaks(text: str, want: tuple[str, ...]) -> None:
    assert passages.narrative_leaks(text, ()) == want


# (pattern name, text, the text the pattern's first match covers, or None for no match)
_PATTERNS = [
    pytest.param("CODE", "T" + chr(0x661) + ".2", None, id="pat-code-t-ai"),
    pytest.param("CODE", "T1." + chr(0x662), None, id="pat-code-t-1-ai"),
    pytest.param("CODE", "T1.2", "T1.2", id="pat-code-ctl"),
    pytest.param(
        "DATE",
        chr(0x662) + chr(0x660) + chr(0x662) + chr(0x665) + "-01-01",
        None,
        id="pat-date-ai-year",
    ),
    pytest.param("DATE", "2025-" + chr(0x660) + chr(0x661) + "-01", None, id="pat-date-ai-month"),
    pytest.param("DATE", "March " + chr(0x663) + chr(0x661) + ", 2025", None, id="pat-date-ai-day"),
    pytest.param(
        "DATE", chr(0x663) + chr(0x661) + " March 2025", "March 2025", id="pat-date-ai-day-first"
    ),
    pytest.param("DATE", "2025-01-01", "2025-01-01", id="pat-date-ctl"),
    pytest.param("DATE", "March 31, 2025", "March 31, 2025", id="pat-date-ctl-month"),
    pytest.param(
        "PERIOD",
        "FY" + chr(0x662) + chr(0x660) + chr(0x662) + chr(0x665),
        None,
        id="pat-period-fy-ai",
    ),
    pytest.param("PERIOD", "3Q" + chr(0x662) + chr(0x664), None, id="pat-period-3q-ai"),
    pytest.param("PERIOD", "1H" + chr(0x662) + chr(0x664), None, id="pat-period-1h-ai"),
    pytest.param("PERIOD", "20" + chr(0x662) + chr(0x665) + "E", None, id="pat-period-year-ai"),
    pytest.param("PERIOD", "FY2025", "FY2025", id="pat-period-ctl"),
    pytest.param("MONTH_COUNT", chr(0x661) + "9M", None, id="pat-month-ai-before"),
    pytest.param("MONTH_COUNT", "9M", "9M", id="pat-month-ctl"),
]


@pytest.mark.parametrize(("pattern", "text", "matched"), _PATTERNS)
def test_public_patterns_on_raw_text(pattern: str, text: str, matched: str | None) -> None:
    found = getattr(figures, pattern).search(text)
    assert (None if found is None else found[0]) == matched


def _context() -> CheckContext:
    return build_context({"kind": "data", **KEY["context"]}, {}, ())


def _bottom_line(line: str) -> HandoffDocument:
    return parse((KEY["head"] + "### Bottom line\n" + line + "\n" + KEY["tail"]).encode("utf-8"))


# (Bottom line, [(quoted, column, which reason)]); the line is line 8 of the document.
_FORMS = [
    pytest.param(
        "It was USD " + chr(0x661) + chr(0x667) + chr(0x665) + " million then.",
        [(chr(0x661) + chr(0x667) + chr(0x665), 12, "digits")],
        id="form-ai-usd-m",
    ),
    pytest.param(
        "The ratio stands at "
        + chr(0xFF12)
        + chr(0xFF10)
        + chr(0xFF12)
        + chr(0xFF14)
        + ", which matters.",
        [(chr(0xFF12) + chr(0xFF10) + chr(0xFF12) + chr(0xFF14), 21, "digits")],
        id="form-fw-2024",
    ),
    pytest.param(
        "The ratio stands at 1" + chr(0xFF11) + chr(0xFF10) + chr(0xFF10) + ", which matters.",
        [("1" + chr(0xFF11) + chr(0xFF10) + chr(0xFF10), 21, "digits")],
        id="form-mix-1-fw100",
    ),
    pytest.param(
        "It was 1," + chr(0x662) + chr(0x663) + chr(0x664) + " then.",
        [("1," + chr(0x662) + chr(0x663) + chr(0x664), 8, "digits")],
        id="form-mix-comma",
    ),
    pytest.param(
        "It was " + chr(0x665) + " and 5% then.", [(chr(0x665), 8, "digits")], id="form-near"
    ),
    pytest.param(
        "On " + chr(0x662) + chr(0x660) + chr(0x662) + chr(0x665) + "-01-01 it paid.",
        [(chr(0x662) + chr(0x660) + chr(0x662) + chr(0x665), 4, "digits")],
        id="form-date-ai",
    ),
    pytest.param(
        "It was " + chr(0x661) + " and " + chr(0xFF12) + " then.",
        [(chr(0x661), 8, "digits"), (chr(0xFF12), 14, "digits")],
        id="form-two-runs",
    ),
    pytest.param(
        "It was " + chr(0x665) + " and 250 then.",
        [(chr(0x665), 8, "digits"), ("250", 14, "bare")],
        id="form-near-bare",
    ),
    pytest.param(
        "See CP-7." + chr(0x661) + " now.", [(chr(0x661), 10, "digits")], id="form-code-then-ai"
    ),
    pytest.param("It grew 5 m" + chr(0xB2) + " then.", [], id="form-sup2"),
    pytest.param("It was USD 175 million then.", [], id="form-ctl"),
    pytest.param("It was 250 then.", [("250", 8, "bare")], id="form-ctl-bare"),
]


@pytest.mark.parametrize(("line", "want"), _FORMS)
def test_check_form(line: str, want: list[tuple[str, int, str]]) -> None:
    found = figures.check_form(_bottom_line(line), _context())
    assert [(f.check, f.severity, f.line, f.quoted, f.column) for f in found] == [
        ("figure.form", "refusal", 8, quoted, column) for quoted, column, _ in want
    ]
    for finding, (_, _, which) in zip(found, want, strict=True):
        assert _REASONS[which] in finding.reason


_ALPHABET = [
    *"0123456789,.- ()%xMQT",
    "USD",
    chr(0x661),
    chr(0x6F5),
    chr(0x967),
    chr(0xFF12),
]


def _runs(text: str) -> list[tuple[int, int]]:
    """Spans of decimal digits joined by a single comma or point between two decimal digits."""
    spans: list[tuple[int, int]] = []
    at = 0
    while at < len(text):
        if not text[at].isdecimal():
            at += 1
            continue
        end = at + 1
        while end < len(text):
            if text[end].isdecimal():
                end += 1
            elif text[end] in ",." and end + 1 < len(text) and text[end + 1].isdecimal():
                end += 2
            else:
                break
        spans.append((at, end))
        at = end
    return spans


@settings(max_examples=200)
@given(parts=st.lists(st.sampled_from(_ALPHABET), max_size=14), passage=st.booleans())
def test_no_foreign_digit_is_read_as_a_figure(parts: list[str], passage: bool) -> None:
    text = "".join(parts)
    foreign = [(a, b) for a, b in _runs(text) if not text[a:b].isascii()]
    for figure in read_figures(text, passage=passage):
        assert not any(c.isdecimal() and not c.isascii() for c in figure.shown)
        first, last = _runs(figure.shown)[0]
        start = figure.column - 1 + first
        end = figure.column - 1 + last
        assert not any(start < b and a < end for a, b in foreign)
