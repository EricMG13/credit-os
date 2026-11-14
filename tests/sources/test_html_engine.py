"""The HTML reading engine: text rows, refusals, reading in pieces, and the parser pin."""

import html.parser
import re
import sys

import pytest

from credit_os.sources import SourceUnreadable
from credit_os.sources import html as reader
from credit_os.sources.html import (
    _ATTRIBUTE,
    _COMMENT_CLOSE,
    _TAG_END,
    _TAG_NAME,
    _encoding,
    _visible_text,
)

Q = b"QUJD" * 5000
X = b"x" * 20000
EURO = b"\xe2\x82\xac"
E_ACUTE = "\N{LATIN SMALL LETTER E WITH ACUTE}"
EURO_SIGN = "\N{EURO SIGN}"


def _read(raw: bytes) -> str:
    codec, _, start = _encoding("f.html", raw)
    return "".join(_visible_text("f.html", raw, codec, start))


_BASIC = (
    b"<!DOCTYPE html><html><head><title>T</title><style>p{color:red}</style></head><body>\n"
    b"<h1>Synthetic  Holdings</h1><p>Revenue rose&nbsp;to &euro;100m.</p>\n"
    b"<div>Block one</div><div>Block two</div>\n"
    b"<table><tr><td>FY2025</td><td>100</td></tr><tr><td>FY2024</td><td>90</td></tr></table>\n"
    b'<p style="display: none">hidden <b>deep</b></p><script>var x = "<p>no</p>";</script>\n'
    b"<ul><li>One</li><li>Two<br>Three</li></ul><p>zero\xe2\x80\x8bwidth</p></body></html>\n"
)
_PAGING_RAW = b"".join(b"<p>" + (b"%03d " % i) + b"x" * 55 + b"</p>" for i in range(100))
_PAGING_TEXT = "".join(f"{i:03d} " + "x" * 55 + "\n" for i in range(100))


def _row(rid: str, raw: bytes, text: str) -> object:
    return pytest.param(raw, text, id=rid)


_DRAFT_ROWS = [
    _row(
        "draft-1-basic",
        _BASIC,
        "Synthetic Holdings\nRevenue rose to " + EURO_SIGN + "100m.\nBlock one Block two\n"
        "FY2025 100\nFY2024 90\nOne\nTwo\nThree\nzerowidth\n",
    ),
    _row(
        "draft-2-unclosed-head",
        b"<html><head><title>T</title><body><p>Shown</p></body></html>",
        "Shown\n",
    ),
    _row(
        "draft-3-ix-header",
        b"<body><ix:header><p>facts</p></ix:header><p>After</p><P>UPPER</P>"
        b"<p>a<span>b</span> c</p></body>",
        "After\nUPPER\nab c\n",
    ),
    _row(
        "draft-4-stray-ends",
        b"<p>one</p></div></table><p>two</p><img src=x><p>three",
        "one\ntwo\nthree\n",
    ),
    _row(
        "draft-5-cp1252",
        b'<html><head><meta charset="windows-1252"></head><body><p>caf\xe9 \x80 5</p></body></html>',
        "caf" + E_ACUTE + " " + EURO_SIGN + " 5\n",
    ),
    _row(
        "draft-6-xml-iso",
        b"<?xml version='1.0' encoding='ISO-8859-1'?><html><body><p>caf\xe9</p></body></html>",
        "caf" + E_ACUTE + "\n",
    ),
    _row("draft-7-bom", b"\xef\xbb\xbf<p>caf\xc3\xa9</p>", "caf" + E_ACUTE + "\n"),
    _row("draft-8-paging", _PAGING_RAW, _PAGING_TEXT),
    _row(
        "draft-9-utf8-wins",
        b'<meta charset="windows-1252"><p>caf\xc3\xa9</p>',
        "caf" + E_ACUTE + "\n",
    ),
    _row("hostile-deep", b"<div>" * 20_000 + b"<p>deep</p>", "deep\n"),
    _row("hostile-stray", b"</div>" * 20_000 + b"<p>x</p>", "x\n"),
]

_ROW_A1 = _row("a1", b"<p>" + b"x" * 8187 + b"&amp;y</p>", "x" * 8187 + "&y\n")
_ROW_A3 = _row(
    "a3",
    b'<p title = "'
    + b"a>" * 5000
    + b'">shown</p><p style = "display:none'
    + b" " * 9000
    + b'">hidden</p><p>after</p>',
    "shown\nafter\n",
)
_ROW_A4 = _row(
    "a4",
    b"<!--><p>inside</p>" + b" " * 9000 + b"<!-- c --><p>after</p>",
    "after\n",
)
_ROW_A5 = _row(
    "a5",
    b"<!--><p>shown</p>" + b" " * 9000 + b"<p>after</p>",
    "shown\nafter\n",
)
_ROW_A6 = _row(
    "a6",
    b"<p>a</p><script>" + b"var x = '</scrip'; " * 1000 + b"</script><p>b</p>",
    "a\nb\n",
)
_ROW_A14 = _row(
    "a14",
    b"<p>a</p><!--" + b"x" * 8177 + b"--><p>b</p>",
    "a\nb\n",
)

_SECTION_11_ROWS = [
    _ROW_A1,
    _row("a2", b"<p>" + b"x" * 8188 + b"\xc3\xa9y</p>", "x" * 8188 + E_ACUTE + "y\n"),
    _ROW_A3,
    _ROW_A4,
    _ROW_A5,
    _ROW_A6,
    _row("a7", b"<textarea>" + b"w &amp; " * 2000 + b"</textarea>", "w & " * 1999 + "w &\n"),
    _row(
        "a8",
        b"<xmp>" + b"<b>&amp;</b> " * 1000 + b"</xmp><p>after</p>",
        "<b>&amp;</b> " * 999 + "<b>&amp;</b>\nafter\n",
    ),
    _row("a9", b"<!--" + b"a>b -- " * 3000 + b"--><p>after</p>", "after\n"),
    _row("a10", b"<![CDATA[" + b"]] > " * 3000 + b"]]><p>after</p>", "after\n"),
    _row(
        "a11",
        b"<!DOCTYPE html " + b'"a" ' * 3000 + b"><?xml " + b"x " * 5000 + b"?><p>after</p>",
        "after\n",
    ),
    _row(
        "a12",
        b"<body><title>" + b"t &lt; " * 3000 + b"</title><p>after</p>",
        "t < " * 2999 + "t <\nafter\n",
    ),
    _row(
        "a13",
        b"<style>"
        + b"p{x:y}" * 4000
        + b"</style><div style='display:none'>"
        + b"<b>h</b>" * 3000
        + b"</div><p>shown</p>",
        "shown\n",
    ),
    _ROW_A14,
    _row(
        "b1",
        b'<p>before <img alt="a>b" src="data:image/png;base64,' + Q + b'"> after</p>',
        "before after\n",
    ),
    _row(
        "b2",
        b'<div data-x="' + X + b'" style="display:none">hidden</div><p>shown</p>',
        "shown\n",
    ),
    _row(
        "b3",
        b'<div data-x="' + X + b'" style="display&colon;none">hidden</div><p>shown</p>',
        "shown\n",
    ),
    _row("b4", b'<div data-x="' + X + b'" style="color:red">shown</div>', "shown\n"),
    _row(
        "b5",
        b'<div data-x="' + X + b'" style="display:none"/>shown',
        "shown\n",
    ),
    _row(
        "b6",
        b'<div style=display:none data-x="' + X + b'" a=b/>hidden</div>shown',
        "shown\n",
    ),
    _row("b7", b"<p style='display:none'>hidden</p " + b"x " * 10000 + b"><p>shown</p>", "shown\n"),
    _row("b8", b"<p>before</p><a " + b"b " * 10000, "before\n"),
    _row(
        "b9",
        b"<p " + b"b=1 " * 5000 + b"style='display:none'>hidden</p><p>shown</p>",
        "shown\n",
    ),
    _row(
        "b10",
        b'<div style="background:url(data:image/png;base64,'
        + Q
        + b');display:none">hidden</div><p>shown</p>',
        "shown\n",
    ),
    _row(
        "b11",
        b'<div style="background:url(data:image/png;base64,' + Q + b')">shown</div>',
        "shown\n",
    ),
    _row(
        "b12",
        b"<p>a</p><script>x</script " + b"a " * 10000 + b"><p>shown</p>",
        "a\nshown\n",
    ),
    _row(
        "b13",
        EURO * 3000 + b'<img src="' + Q + b'">' + EURO + b" after",
        EURO_SIGN * 3001 + " after\n",
    ),
    _row(
        "b14",
        b'<meta charset="windows-1252"><p>caf\xe9 <img src="' + Q + b'"> \x80</p>',
        "caf" + E_ACUTE + " " + EURO_SIGN + "\n",
    ),
    _row("b15", b"<" + b"a" * 16384 + b">x", "x\n"),
    _row(
        "b16",
        b'<div style="' + b"x" * 16367 + b'&amp;display:none">hidden</div><p>shown</p>',
        "shown\n",
    ),
    _row(
        "b17",
        b'<DIV DATA-X="' + X + b'" STYLE="DISPLAY : NONE">hidden</DIV>shown',
        "shown\n",
    ),
    _row(
        "b18",
        b'<div style="color:red" data-x="' + X + b'" style="display:none">hidden</div>shown',
        "shown\n",
    ),
    _row(
        "b19",
        b"<p>a</p><script data-x='" + X + b"'>var hidden;</script><p>b</p>",
        "a\nb\n",
    ),
    _row(
        "b20",
        b"<textarea data-x='" + X + b"'>a &amp; <b></textarea><p>b</p>",
        "a & <b>\nb\n",
    ),
    _row("c1", b"".join(b"<n%d>" % i for i in range(4095)) + b"<p>x</p>", "x\n"),
    _row("d1", b"<p>&#" + b"0" * 29 + b"65;</p>", "A\n"),
    _row("d2", b"<p>&#x" + b"0" * 29 + b"41;</p>", "A\n"),
    _row(
        "e1",
        b"<div><p style='display:none'>hidden<span>deep</div>shown<p>next",
        "shown\nnext\n",
    ),
    _row("e2", b"<p style='display:none'>hidden</div></span>still hidden</p>shown", "shown\n"),
]


@pytest.mark.parametrize(("raw", "text"), _DRAFT_ROWS + _SECTION_11_ROWS)
def test_text_rows(raw: bytes, text: str) -> None:
    assert _read(raw) == text


_TOO_LONG_STYLE = "a style attribute longer than 16,384 characters that is not plain ASCII"
_REFUSAL_ROWS = [
    pytest.param(
        b"".join(b"<n%d>" % i for i in range(4096)) + b"<p>x</p>",
        "more than 4,096 different tag names",
        id="c2",
    ),
    pytest.param(b"<" + b"a" * 16385 + b">x", "a tag name longer than 16,384 characters", id="b21"),
    pytest.param(
        b'<div style="' + b"x" * 16368 + b'&amp;display:none">hidden</div><p>shown</p>',
        _TOO_LONG_STYLE,
        id="b22",
    ),
    pytest.param(
        b'<div style="' + b"x" * 20000 + b"\xc3\xa9" + b'">t</div>', _TOO_LONG_STYLE, id="b23"
    ),
]


@pytest.mark.parametrize(("raw", "reason"), _REFUSAL_ROWS)
def test_refusals(raw: bytes, reason: str) -> None:
    with pytest.raises(SourceUnreadable) as caught:
        _read(raw)
    assert str(caught.value) == "f.html: " + reason


_PIECE_ROWS = [
    pytest.param(
        b'<p title = "a>b">shown</p><div style = "display:none>x">hidden</div>',
        "shown\n",
        id="quoted-gt",
    ),
    pytest.param(
        b"<div style='display:none'>hidden<!--></div>revealed?<!-- c -->after",
        "",
        id="comment-gt",
    ),
]
_SETTINGS = [
    pytest.param((1, 34, 35), id="1"),
    pytest.param((5, 34, 39), id="5"),
    pytest.param((7, 34, 41), id="7"),
    pytest.param((64, 64, 128), id="64"),
    pytest.param((8192, 8192, 16384), id="8192"),
]


def _set(monkeypatch: pytest.MonkeyPatch, setting: tuple[int, int, int]) -> None:
    piece, held, parsed = setting
    monkeypatch.setattr(reader, "PIECE_BYTES", piece)
    monkeypatch.setattr(reader, "HELD_CHARACTERS", held)
    monkeypatch.setattr(reader, "PARSED_CHARACTERS", parsed)


@pytest.mark.parametrize("setting", _SETTINGS)
@pytest.mark.parametrize(("raw", "text"), _PIECE_ROWS)
def test_pieces_equal_whole(
    monkeypatch: pytest.MonkeyPatch, setting: tuple[int, int, int], raw: bytes, text: str
) -> None:
    _set(monkeypatch, setting)
    assert _read(raw) == text


@pytest.mark.parametrize(
    "setting",
    [pytest.param((1, 34, 35), id="1"), pytest.param((64, 64, 128), id="64")],
)
@pytest.mark.parametrize(("raw", "text"), [_ROW_A1, _ROW_A3, _ROW_A4, _ROW_A5, _ROW_A6, _ROW_A14])
def test_rows_in_small_pieces(
    monkeypatch: pytest.MonkeyPatch, setting: tuple[int, int, int], raw: bytes, text: str
) -> None:
    _set(monkeypatch, setting)
    assert _read(raw) == text


def test_parser_pin() -> None:
    def differs(which: str) -> str:
        return f"html.parser differs from 3.12.14 on Python {sys.version}: {which}"

    parser = html.parser
    # Not declared in typeshed: read by name from the module and the class.
    module = vars(parser)
    cls = vars(parser.HTMLParser)
    tag_end = _TAG_END.pattern.decode("ascii").replace(")*+", ")*", 1)
    assert tag_end == module["locatetagend"].pattern, differs("locatetagend")
    assert _TAG_END.flags & re.VERBOSE, differs("locatetagend flags")
    assert _TAG_NAME.pattern.decode("ascii") == module["tagfind_tolerant"].pattern, differs(
        "tagfind_tolerant"
    )
    assert _TAG_NAME.flags & ~re.UNICODE == module["tagfind_tolerant"].flags & ~re.UNICODE, differs(
        "tagfind_tolerant flags"
    )
    assert _ATTRIBUTE.pattern.decode("ascii") == module["attrfind_tolerant"].pattern, differs(
        "attrfind_tolerant"
    )
    assert _ATTRIBUTE.flags & re.VERBOSE, differs("attrfind_tolerant flags")
    assert module["attrfind_tolerant"].flags & re.VERBOSE, differs("attrfind_tolerant flags")
    assert _COMMENT_CLOSE.pattern == module["commentclose"].pattern, differs("commentclose")
    assert parser.HTMLParser.CDATA_CONTENT_ELEMENTS == (
        "script",
        "style",
        "xmp",
        "iframe",
        "noembed",
        "noframes",
    ), differs("CDATA_CONTENT_ELEMENTS")
    assert cls["RCDATA_CONTENT_ELEMENTS"] == ("textarea", "title"), differs(
        "RCDATA_CONTENT_ELEMENTS"
    )
    assert sys.version_info[:3] >= (3, 12, 14), differs("patch level")
