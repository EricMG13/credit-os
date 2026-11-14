"""The HTML reader's decoding and its line writer."""

import re
import tracemalloc
from html.parser import HTMLParser

import pytest

from credit_os.sources import Page, SourcePages, SourceUnreadable
from credit_os.sources import html as reader
from credit_os.sources.html import _encoding, _LineText, html_pages

_NO_CHARSET = "not valid UTF-8 and declares no charset in its first 4,096 bytes"
_E_ACUTE = b"\xc3\xa9"

_ACCEPTED_ROWS = [
    pytest.param(b"<p>caf\xc3\xa9</p>", ("utf-8", "utf-8", 0), id="utf-8"),
    pytest.param(b"\xef\xbb\xbf<p>caf\xc3\xa9</p>", ("utf-8", "utf-8", 3), id="bom"),
    pytest.param(b"", ("utf-8", "utf-8", 0), id="empty"),
    pytest.param(
        b'<meta charset="windows-1252"><p>caf\xe9 \x80</p>',
        ("cp1252", "windows-1252", 0),
        id="windows-1252",
    ),
    pytest.param(
        b"<?xml version='1.0' encoding='ISO-8859-1'?><p>caf\xe9</p>",
        ("iso8859-1", "iso-8859-1", 0),
        id="xml-iso",
    ),
    pytest.param(
        b'<meta charset="latin1"><p>caf\xe9</p>', ("iso8859-1", "iso-8859-1", 0), id="latin1"
    ),
    pytest.param(
        b'<meta charset="windows-1252"><p>caf\xc3\xa9</p>',
        ("utf-8", "utf-8", 0),
        id="utf-8-wins",
    ),
    pytest.param(b"x" * 8191 + _E_ACUTE, ("utf-8", "utf-8", 0), id="split-letter"),
    pytest.param(b"charset=latin1 caf\xe9", ("iso8859-1", "iso-8859-1", 0), id="charset-first"),
]


@pytest.mark.parametrize(("raw", "result"), _ACCEPTED_ROWS)
def test_encoding_accepts(raw: bytes, result: tuple[str, str, int]) -> None:
    assert _encoding("f.html", raw) == result


_REFUSAL_ROWS = [
    pytest.param(b"x" * 8191 + b"\xc3", _NO_CHARSET, UnicodeDecodeError, id="cut-letter"),
    pytest.param(b"<p>caf\xe9</p>", _NO_CHARSET, UnicodeDecodeError, id="no-charset"),
    pytest.param(b"\xe9 x", _NO_CHARSET, UnicodeDecodeError, id="first-byte"),
    pytest.param(
        b"\x81charset=cp1252", "not valid windows-1252", UnicodeDecodeError, id="first-byte-codec"
    ),
    pytest.param(
        b" " * 5000 + b'<meta charset="windows-1252"><p>caf\xe9</p>',
        _NO_CHARSET,
        UnicodeDecodeError,
        id="late-charset",
    ),
    pytest.param(
        b'<meta charset="klingon"><p>caf\xe9</p>',
        "declares a charset that is not accepted: 'klingon'",
        LookupError,
        id="klingon",
    ),
    pytest.param(
        b'<meta charset="utf-16"><p>caf\xe9</p>',
        "declares a charset that is not accepted: 'utf-16'",
        None,
        id="utf-16",
    ),
    pytest.param(
        b'<meta charset="' + b"k" * 60 + b'"><p>caf\xe9</p>',
        "declares a charset that is not accepted: " + repr("k" * 40),
        LookupError,
        id="long-name",
    ),
    pytest.param(
        b'<meta charset="ascii"><p>caf\xe9</p>',
        "not valid ascii",
        UnicodeDecodeError,
        id="ascii",
    ),
    pytest.param(
        b'<meta charset="windows-1252"><p>\x81</p>',
        "not valid windows-1252",
        UnicodeDecodeError,
        id="cp1252-hole",
    ),
    pytest.param(
        b"\xef\xbb\xbf<p>\xff</p>",
        "not valid UTF-8 after its byte-order mark",
        UnicodeDecodeError,
        id="bom-invalid",
    ),
    pytest.param(
        b'<meta charset="utf-8"><p>caf\xe9</p>',
        "not valid utf-8",
        UnicodeDecodeError,
        id="declared-utf-8",
    ),
]


@pytest.mark.parametrize(("raw", "message", "cause"), _REFUSAL_ROWS)
def test_encoding_refuses(raw: bytes, message: str, cause: type[BaseException] | None) -> None:
    with pytest.raises(SourceUnreadable) as caught:
        _encoding("f.html", raw)
    assert str(caught.value) == "f.html: " + message
    if cause is None:
        assert caught.value.__cause__ is None
    else:
        assert isinstance(caught.value.__cause__, cause)


@pytest.mark.parametrize(
    ("raw", "encoding"),
    [
        pytest.param(b'<meta charset="ascii"><p>caf\xe9</p>', "ascii", id="ascii"),
        pytest.param(b'<meta charset="windows-1252"><p>\x81</p>', "charmap", id="cp1252-hole"),
    ],
)
def test_encoding_refusal_chains_the_declared_codecs_error(raw: bytes, encoding: str) -> None:
    with pytest.raises(SourceUnreadable) as caught:
        _encoding("f.html", raw)
    cause = caught.value.__cause__
    assert isinstance(cause, UnicodeDecodeError)
    assert cause.encoding == encoding


def test_encoding_refusal_shows_a_long_name_cut() -> None:
    with pytest.raises(SourceUnreadable) as caught:
        _encoding("a" * 130 + ".html", b"<p>caf\xe9</p>")
    assert str(caught.value) == "a" * 120 + "\N{HORIZONTAL ELLIPSIS}: " + _NO_CHARSET


@pytest.mark.parametrize(
    ("raw", "size", "result"),
    [
        pytest.param(b"caf\xc3\xa9 " * 174_762, 1_048_572, ("utf-8", "utf-8", 0), id="utf-8"),
        pytest.param(
            b"\xef\xbb\xbf" + b"caf\xc3\xa9 " * 174_762,
            1_048_575,
            ("utf-8", "utf-8", 3),
            id="bom",
        ),
        pytest.param(
            b'<meta charset="windows-1252">' + b"caf\xe9 " * 209_709,
            1_048_574,
            ("cp1252", "windows-1252", 0),
            id="declared",
        ),
    ],
)
def test_encoding_holds_no_decoded_copy(
    raw: bytes, size: int, result: tuple[str, str, int]
) -> None:
    assert len(raw) == size
    tracemalloc.start()
    try:
        found = _encoding("f.html", raw)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert found == result
    print(f"measured _encoding peak: {peak} bytes")
    assert peak <= 262_144


def test_constants() -> None:
    assert reader._SNIFF_BYTES == 4_096
    assert reader._ACCEPTED == {
        "utf-8": "utf-8",
        "cp1252": "windows-1252",
        "iso8859-1": "iso-8859-1",
        "ascii": "ascii",
    }
    assert reader._CHARSET.pattern == rb"""(?:charset|encoding)\s*=\s*["']?\s*([A-Za-z0-9_.:\-]+)"""
    assert reader._CHARSET.flags & re.IGNORECASE
    assert reader.PIECE_BYTES == reader.HELD_CHARACTERS == 8_192
    assert reader.PARSED_CHARACTERS == 16_384
    assert reader.MAX_TAG_NAMES == 4_096
    assert reader.PAGE_CHARACTERS == 3_000
    assert reader.REFERENCE_WINDOW == 34
    assert reader.REFERENCE_DIGITS == 32
    assert reader.LINE_TAGS == frozenset(
        {"p", "tr", "li", "br", "h1", "h2", "h3", "h4", "h5", "h6"}
    )
    assert reader.SKIP == {"script", "style", "head", "ix:header"}
    assert reader.VOID == {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "source",
        "wbr",
    }
    assert reader.BLOCK == {
        "address",
        "blockquote",
        "body",
        "br",
        "caption",
        "center",
        "dd",
        "div",
        "dl",
        "dt",
        "fieldset",
        "form",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "hr",
        "li",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "tbody",
        "td",
        "tfoot",
        "th",
        "thead",
        "tr",
        "ul",
    }


_ZW = "\N{ZERO WIDTH SPACE}"
_BOM_CHAR = "\N{ZERO WIDTH NO-BREAK SPACE}"
_NBSP = "\N{NO-BREAK SPACE}"

_LINE_ROWS = [
    pytest.param([("text", "a"), ("text", "b")], "ab", id="joined"),
    pytest.param([("text", "a "), ("text", "b")], "a b", id="trailing-space"),
    pytest.param(
        [("text", "a"), ("text", " "), ("text", "b"), ("line",)], "a b\n", id="space-text"
    ),
    pytest.param([("text", "a"), ("space",), ("text", "b"), ("line",)], "a b\n", id="space"),
    pytest.param([("text", "  a\n\tb  "), ("line",)], "a b\n", id="collapse"),
    pytest.param(
        [("space",), ("text", " "), ("line",), ("line",), ("text", "x"), ("line",)],
        "x\n",
        id="empty-lines",
    ),
    pytest.param([("text", "zero" + _ZW + "width"), ("line",)], "zerowidth\n", id="zero-width"),
    pytest.param(
        [("text", "a" + _ZW), ("text", _BOM_CHAR + "b"), ("line",)], "ab\n", id="zero-width-apart"
    ),
    pytest.param([("text", "a" + _NBSP + "b"), ("line",)], "a b\n", id="no-break-space"),
]


def _drive(events: list[tuple[str, ...]]) -> _LineText:
    lines = _LineText()
    for event in events:
        if event[0] == "text":
            lines.text(event[1])
        elif event[0] == "space":
            lines.space()
        else:
            lines.line_end()
    return lines


@pytest.mark.parametrize(("events", "text"), _LINE_ROWS)
def test_line_text_rows(events: list[tuple[str, ...]], text: str) -> None:
    assert "".join(_drive(events).take()) == text


def test_line_text_take_clears() -> None:
    lines = _drive([("text", "a"), ("line",)])
    assert lines.take() == ["a", "\n"]
    assert lines.take() == []


# --- html_pages: the draft key and design rows, through the public function ---

_EURO = "\N{EURO SIGN}"
_E_ACUTE_CHAR = "\N{LATIN SMALL LETTER E WITH ACUTE}"
_BASIC = (
    b"<!DOCTYPE html><html><head><title>T</title><style>p{color:red}</style></head><body>\n"
    b"<h1>Synthetic  Holdings</h1><p>Revenue rose&nbsp;to &euro;100m.</p>\n"
    b"<div>Block one</div><div>Block two</div>\n"
    b"<table><tr><td>FY2025</td><td>100</td></tr><tr><td>FY2024</td><td>90</td></tr></table>\n"
    b'<p style="display: none">hidden <b>deep</b></p><script>var x = "<p>no</p>";</script>\n'
    b"<ul><li>One</li><li>Two<br>Three</li></ul><p>zero\xe2\x80\x8bwidth</p></body></html>\n"
)
_Q = b"QUJD" * 5000
_ONE_PAGE_ROWS = [
    pytest.param(
        _BASIC,
        "Synthetic Holdings\nRevenue rose to " + _EURO + "100m.\nBlock one Block two\n"
        "FY2025 100\nFY2024 90\nOne\nTwo\nThree\nzerowidth\n",
        "utf-8",
        id="draft-1-basic",
    ),
    pytest.param(
        b"<html><head><title>T</title><body><p>Shown</p></body></html>",
        "Shown\n",
        "utf-8",
        id="draft-2-unclosed-head",
    ),
    pytest.param(
        b"<body><ix:header><p>facts</p></ix:header><p>After</p><P>UPPER</P>"
        b"<p>a<span>b</span> c</p></body>",
        "After\nUPPER\nab c\n",
        "utf-8",
        id="draft-3-ix-header",
    ),
    pytest.param(
        b"<p>one</p></div></table><p>two</p><img src=x><p>three",
        "one\ntwo\nthree\n",
        "utf-8",
        id="draft-4-stray-ends",
    ),
    pytest.param(
        b'<html><head><meta charset="windows-1252"></head><body><p>caf\xe9 \x80 5</p></body></html>',
        "caf" + _E_ACUTE_CHAR + " " + _EURO + " 5\n",
        "windows-1252",
        id="draft-5-cp1252",
    ),
    pytest.param(
        b"<?xml version='1.0' encoding='ISO-8859-1'?><html><body><p>caf\xe9</p></body></html>",
        "caf" + _E_ACUTE_CHAR + "\n",
        "iso-8859-1",
        id="draft-6-xml-iso",
    ),
    pytest.param(
        b"\xef\xbb\xbf<p>caf\xc3\xa9</p>", "caf" + _E_ACUTE_CHAR + "\n", "utf-8", id="draft-7-bom"
    ),
    pytest.param(
        b'<meta charset="windows-1252"><p>caf\xc3\xa9</p>',
        "caf" + _E_ACUTE_CHAR + "\n",
        "utf-8",
        id="draft-9-utf8-wins",
    ),
    pytest.param(
        b'<meta charset="windows-1252"><p>caf\xe9 <img src="' + _Q + b'"> \x80</p>',
        "caf" + _E_ACUTE_CHAR + " " + _EURO + "\n",
        "windows-1252",
        id="b14",
    ),
]


@pytest.mark.parametrize(("raw", "text", "encoding"), _ONE_PAGE_ROWS)
def test_html_pages_one_page(raw: bytes, text: str, encoding: str) -> None:
    assert html_pages("f.html", raw) == SourcePages(
        pages=(Page(number=1, text=text, state="text"),), encoding=encoding
    )


def test_html_pages_paging() -> None:
    raw = b"".join(b"<p>" + (b"%03d " % i) + b"x" * 55 + b"</p>" for i in range(100))
    first = "".join(f"{i:03d} " + "x" * 55 + "\n" for i in range(50))
    second = "".join(f"{i:03d} " + "x" * 55 + "\n" for i in range(50, 100))
    assert html_pages("f.html", raw) == SourcePages(
        pages=(Page(number=1, text=first, state="text"), Page(number=2, text=second, state="text")),
        encoding="utf-8",
    )


def test_html_pages_b13_cuts_after_three_thousand_letters() -> None:
    raw = b"\xe2\x82\xac" * 3000 + b'<img src="' + _Q + b'">\xe2\x82\xac after'
    assert html_pages("f.html", raw) == SourcePages(
        pages=(
            Page(number=1, text=_EURO * 3000, state="text"),
            Page(number=2, text=_EURO + " after\n", state="text"),
        ),
        encoding="utf-8",
    )


_LONG_REFERENCE_REASON = "a character reference of 32 or more digits"
_HTML_REFUSALS = [
    pytest.param(b"<p>a\x00b</p>", "control character U+0000", id="nul"),
    pytest.param(
        b"<html><head><title>T</title></head><body><script>x</script> </body></html>",
        "has no visible text",
        id="no-text",
    ),
    pytest.param(b"", "has no visible text", id="empty"),
    pytest.param(b"<p>&#" + b"0" * 30 + b"65;</p>", _LONG_REFERENCE_REASON, id="d3"),
    pytest.param(b"<p>&#X" + b"0" * 30 + b"41;</p>", _LONG_REFERENCE_REASON, id="d4"),
    pytest.param(b"<p>&#" + b"1" * 5000 + b";</p>", _LONG_REFERENCE_REASON, id="d5"),
    pytest.param(
        b"<script>var s = '&#" + b"1" * 32 + b"';</script><p>x</p>", _LONG_REFERENCE_REASON, id="d6"
    ),
    pytest.param(b"<p>caf\xe9\x00</p>", _NO_CHARSET, id="order-decoding-first"),
    pytest.param(
        b"<p>a\x00&#" + b"1" * 32 + b";</p>", "control character U+0000", id="order-nul-before-long"
    ),
]


@pytest.mark.parametrize(("raw", "reason"), _HTML_REFUSALS)
def test_html_pages_refuses(raw: bytes, reason: str) -> None:
    with pytest.raises(SourceUnreadable) as caught:
        html_pages("f.html", raw)
    assert str(caught.value) == "f.html: " + reason
    # only the decoding refusal has a cause (the UTF-8 error)
    assert (caught.value.__cause__ is None) == (reason != _NO_CHARSET)


def test_html_pages_parser_assertion_error_is_refused_and_chained(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failure = AssertionError("parser gave up")

    def raising(self: HTMLParser, end: bool) -> None:
        raise failure

    monkeypatch.setattr(HTMLParser, "goahead", raising)
    with pytest.raises(SourceUnreadable) as caught:
        html_pages("f.html", b"<p>x</p>")
    assert str(caught.value) == "f.html: markup the parser cannot read"
    assert caught.value.__cause__ is failure
