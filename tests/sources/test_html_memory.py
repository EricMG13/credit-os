"""Peak memory of html_pages: bounded by the input, and nothing but the pages grows."""

import sys
import tracemalloc
from collections.abc import Callable

import pytest

from credit_os.sources import SourceUnreadable
from credit_os.sources.html import html_pages

_MIB = 1_048_576
_BIG = _MIB
_SMALL = 262_144  # token floods run smaller: tracemalloc makes them slow
ASTRAL = b"\xf0\x9f\x98\x80"
MARKUP = (
    b'<div class="row"><p style="margin:0">Revenue rose&nbsp;to &euro;100m in the year.</p>'
    b'<table><tr><td class="n">FY2025</td><td>100</td></tr></table></div>\n'
)


def _row(
    ident: str, size: int, raw: Callable[[int], bytes], outcome: int | str, ceiling: float
) -> object:
    """A row: its size n, the raw bytes built from n, the page count or the refusal reason, and
    the most MiB the reading may hold beyond the pages it returns."""
    return pytest.param(size, raw, outcome, ceiling, id=ident)


_ROWS = [
    _row("text-run", _BIG, lambda n: b"x" * n, 350, 0.5),
    _row("words", _BIG, lambda n: b"word " * (n // 5), 350, 0.5),
    _row(
        "astral-on-every-page",
        _BIG,
        lambda n: (ASTRAL + b"x" * 2995 + b" ") * (n // 3000),
        349,
        0.5,
    ),
    _row(
        "astral-and-most-pages",
        _BIG,
        lambda n: (b"<p>" + ASTRAL + b"</p><p>" + ASTRAL + b"x" * 2998 + b"</p>") * (n // 3020),
        694,
        0.75,
    ),
    _row(
        "typographic-on-every-page",
        _BIG,
        lambda n: (b"\xe2\x80\x99" + b"x" * 2996 + b" ") * (n // 3000),
        349,
        0.5,
    ),
    _row("entities", _BIG, lambda n: b"&amp;" * (n // 5), 70, 0.5),
    _row("astral-references", _BIG, lambda n: b"&#128512;" * (n // 9), 39, 0.5),
    _row(
        "one-tag-of-attributes", _BIG, lambda n: b"<a " + b"b=1 " * (n // 4 - 3) + b">x</a>", 1, 4.0
    ),
    _row("tag-never-closed", _BIG, lambda n: b"<a" * (n // 2), "has no visible text", 0.25),
    _row(
        "comment-never-closed",
        _BIG,
        lambda n: b"<!--" + b"x" * (n - 4),
        "has no visible text",
        0.25,
    ),
    _row(
        "script-never-closed",
        _BIG,
        lambda n: b"<script>" + b"x<y " * (n // 4 - 3),
        "has no visible text",
        0.25,
    ),
    _row(
        "data-uri-image",
        _BIG,
        lambda n: b'<img src="data:image/png;base64,' + b"QUJD" * (n // 4 - 12) + b'">after',
        1,
        0.25,
    ),
    _row(
        "astral-in-a-long-attribute",
        _BIG,
        lambda n: b'<div title="' + ASTRAL + b"x" * (n - 40) + b'">after</div>',
        1,
        0.5,
    ),
    _row(
        "long-plain-style",
        _BIG,
        lambda n: (
            b'<div style="background:url(data:image/png;base64,'
            + b"QUJD" * (n // 4 - 25)
            + b');display:none">hidden</div>shown'
        ),
        1,
        0.25,
    ),
    _row("zero-width", _BIG, lambda n: b"\xe2\x80\x8b" * (n // 3), "has no visible text", 0.25),
    _row(
        "windows-1252-found-at-the-end",
        _BIG,
        lambda n: b'<meta charset="windows-1252">' + b"word " * ((n - 40) // 5) + b"\xe9",
        350,
        0.5,
    ),
    _row("paragraphs", _SMALL, lambda n: b"<p>a</p>" * (n // 8), 22, 0.25),
    _row("line-breaks", _SMALL, lambda n: b"<br>" * (n // 4), "has no visible text", 0.25),
    _row("less-than-signs", _SMALL, lambda n: b"<" * n, 88, 0.25),
    _row("nested-div", _SMALL, lambda n: b"<div>" * (n // 5), "has no visible text", 0.25),
    _row("nested-a-b", _SMALL, lambda n: b"<a><b>" * (n // 6), "has no visible text", 0.3),
    _row("unclosed-paragraphs", _SMALL, lambda n: b"<p>a" * (n // 4), 44, 0.3),
    _row("end-tags", _SMALL, lambda n: b"</div>" * (n // 6), "has no visible text", 0.25),
    _row(
        "hidden-subtree",
        _SMALL,
        lambda n: b"<p style='display:none'>" + b"<b>x</b>" * (n // 8 - 3),
        "has no visible text",
        0.25,
    ),
    _row(
        "4096-names",
        _SMALL,
        lambda n: b"".join(b"<n%d>" % (i % 4096) for i in range(n // 8)),
        "has no visible text",
        1.0,
    ),
    _row("open-references", _SMALL, lambda n: b"&a" * (n // 2), 88, 0.5),
    _row(
        "open-references-in-textarea",
        _SMALL,
        lambda n: b"<textarea>" + b"&a" * (n // 2 - 5),
        88,
        0.5,
    ),
    _row(
        "name-only-attributes", _SMALL, lambda n: b"<a " + b"b " * (n // 2 - 5) + b">x</a>", 1, 4.0
    ),
    _row(
        "tags-at-the-parser-limit",
        _SMALL,
        lambda n: (b"<a " + b"b " * 8000 + b">x</a> ") * (n // 16009),
        1,
        4.0,
    ),
    _row("ordinary-markup", _SMALL, lambda n: MARKUP * (n // len(MARKUP)), 27, 0.25),
    _row("textarea-open-reference", _SMALL, lambda n: b"<textarea>&" + b"x" * 262000, 88, 0.25),
]


@pytest.mark.parametrize(("size", "build", "outcome", "ceiling"), _ROWS)
def test_peak_memory(
    size: int, build: Callable[[int], bytes], outcome: int | str, ceiling: float
) -> None:
    raw = build(size)  # built before tracing starts
    assert len(raw) <= size
    tracemalloc.start()
    try:
        try:
            result = html_pages("t.html", raw)
            pages, refusal = len(result.pages), ""
            text = sum(sys.getsizeof(page.text) for page in result.pages)
        except SourceUnreadable as error:
            pages, text, refusal = -1, 0, str(error)
        peak = tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()
    if isinstance(outcome, int):
        assert pages == outcome
    else:
        assert refusal == "t.html: " + outcome
    assert peak <= 4.5 * len(raw) + 6 * _MIB  # the stated bound
    assert peak - text <= ceiling * _MIB  # nothing but the pages grows
