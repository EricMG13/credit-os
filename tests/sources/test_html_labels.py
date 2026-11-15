"""Declared labels per carrier, and C1 controls in the text read (1D PR 2b-5 answer key).

The HTML Standard (WHATWG Encoding: encodings.json and index-windows-1252, read 2026-11-15) gives
the labels below the encoding windows-1252. In it, byte 0x80 is U+20AC, 0x96 is U+2013 and 0x85
is U+2026; 0x81, 0x8D, 0x8F, 0x90 and 0x9D are left as C1 controls, which strict cp1252 refuses.
- A `charset=` declaration (meta, http-equiv) follows the standard.
- An XML declaration keeps its reading: ISO-8859-1 stays true latin-1.
- On every path, a character U+0080 to U+009F in the text read is refused by name.

The expected values are the standard's literals, not a codec's output.
"""

from collections.abc import Callable

import pytest

from credit_os.sources import Page, SourcePages, SourceUnreadable, html_pages

# encodings.json, the "labels" of "windows-1252", verbatim (sorted).
STANDARD_LABELS = (
    "ansi_x3.4-1968",
    "ascii",
    "cp1252",
    "cp819",
    "csisolatin1",
    "ibm819",
    "iso-8859-1",
    "iso-ir-100",
    "iso8859-1",
    "iso88591",
    "iso_8859-1",
    "iso_8859-1:1987",
    "l1",
    "latin1",
    "us-ascii",
    "windows-1252",
    "x-cp1252",
)
# A label is matched case-insensitively.
CASED_LABELS = ("ISO-8859-1", "US-ASCII", "Latin1")

BODY = b"<p>price \x80 5, change \x96 3, a\x85b</p>"
READ = "price \N{EURO SIGN} 5, change \N{EN DASH} 3, a\N{HORIZONTAL ELLIPSIS}b\n"
NOT_ACCEPTED = "declares a charset that is not accepted: "
C1_80 = "control character U+0080"


def _meta(label: str) -> bytes:
    return b'<meta charset="' + label.encode("ascii") + b'">' + BODY


def _http_equiv(label: str) -> bytes:
    content = b"text/html; charset=" + label.encode("ascii")
    return b'<meta http-equiv="Content-Type" content="' + content + b'">' + BODY


def _xml(label: str) -> bytes:
    return b"<?xml version='1.0' encoding='" + label.encode("ascii") + b"'?>" + BODY


def _read(raw: bytes, text: str, encoding: str) -> None:
    page = Page(number=1, text=text, state="text")
    assert html_pages("f.html", raw) == SourcePages(pages=(page,), encoding=encoding)


def _refused(raw: bytes, reason: str) -> SourceUnreadable:
    with pytest.raises(SourceUnreadable) as caught:
        html_pages("f.html", raw)
    assert str(caught.value) == "f.html: " + reason
    return caught.value


@pytest.mark.parametrize("carrier", [_meta, _http_equiv], ids=["meta", "http-equiv"])
@pytest.mark.parametrize("label", [*STANDARD_LABELS, *CASED_LABELS])
def test_a_charset_label_of_windows_1252_reads_windows_1252(
    label: str, carrier: Callable[[str], bytes]
) -> None:
    _read(carrier(label), READ, "windows-1252")


# An XML declaration keeps the reading it had before 2b-5: true ISO-8859-1 (its 0x80 is a C1
# control, refused in the text read), strict ASCII, windows-1252, or not accepted.
_XML_OUTCOMES: dict[str, str | None] = {
    "ansi_x3.4-1968": NOT_ACCEPTED + "'ansi_x3.4-1968'",
    "ascii": "not valid ascii",
    "cp1252": None,
    "cp819": NOT_ACCEPTED + "'cp819'",
    "csisolatin1": NOT_ACCEPTED + "'csisolatin1'",
    "ibm819": NOT_ACCEPTED + "'ibm819'",
    "iso-8859-1": C1_80,
    "iso-ir-100": NOT_ACCEPTED + "'iso-ir-100'",
    "iso8859-1": C1_80,
    "iso88591": NOT_ACCEPTED + "'iso88591'",
    "iso_8859-1": C1_80,
    "iso_8859-1:1987": NOT_ACCEPTED + "'iso_8859-1:1987'",
    "l1": NOT_ACCEPTED + "'l1'",
    "latin1": C1_80,
    "us-ascii": "not valid ascii",
    "windows-1252": None,
    "x-cp1252": NOT_ACCEPTED + "'x-cp1252'",
}


@pytest.mark.parametrize("label", STANDARD_LABELS)
def test_an_xml_declaration_keeps_its_reading(label: str) -> None:
    reason = _XML_OUTCOMES[label]
    if reason is None:
        _read(_xml(label), READ, "windows-1252")
    else:
        _refused(_xml(label), reason)


@pytest.mark.parametrize("label", ["iso-8859-1", "us-ascii"])
@pytest.mark.parametrize("byte", [0x81, 0x8D, 0x8F, 0x90, 0x9D], ids=["81", "8d", "8f", "90", "9d"])
def test_a_byte_windows_1252_leaves_undefined_is_refused(label: str, byte: int) -> None:
    raw = b'<meta charset="' + label.encode("ascii") + b'"><p>a' + bytes([byte]) + b"b</p>"
    assert isinstance(_refused(raw, "not valid windows-1252").__cause__, UnicodeDecodeError)


_C1_ROWS = [
    pytest.param(b"<p>a\xc2\x80b</p>", C1_80, id="utf-8-80"),
    pytest.param(b"<p>a\xc2\x85b</p>", "control character U+0085", id="utf-8-85"),
    pytest.param(b"\xef\xbb\xbf<p>a\xc2\x9fb</p>", "control character U+009F", id="bom-9f"),
    # text between tags that str.split() would collapse as whitespace
    pytest.param(b"<p>a</p>\xc2\x85<p>b</p>", "control character U+0085", id="between"),
    pytest.param(
        b"<?xml version='1.0' encoding='ISO-8859-1'?><p>a\x9fb</p>",
        "control character U+009F",
        id="xml-9f",
    ),
    # "latin-1" is not one of the standard's labels: it keeps its true ISO-8859-1 reading
    pytest.param(b'<meta charset="latin-1"><p>a\x80b</p>', C1_80, id="latin-1"),
    # a reference html.parser decodes to a C1 control
    pytest.param(b"<p>a&#x81;b</p>", "control character U+0081", id="ref-81"),
    pytest.param(b"<p>a&#157;b</p>", "control character U+009D", id="ref-157"),
    pytest.param(b"<p>a&#141;b</p>", "control character U+008D", id="ref-141"),
    pytest.param(b"<p>a&#143;b</p>", "control character U+008F", id="ref-143"),
    pytest.param(b"<p>a&#144;b</p>", "control character U+0090", id="ref-144"),
    # ruling item 5: the first declaration in the first 4,096 bytes wins, the order 2b-1 set
    pytest.param(
        b"<?xml version='1.0' encoding='ISO-8859-1'?><meta charset=\"windows-1252\"><p>price \x80 5</p>",
        C1_80,
        id="xml-first",
    ),
]


@pytest.mark.parametrize(("raw", "reason"), _C1_ROWS)
def test_a_c1_control_in_the_text_read_is_refused(raw: bytes, reason: str) -> None:
    assert _refused(raw, reason).__cause__ is None


_READ_ROWS = [
    # a true ISO-8859-1 file, XML-declared, with characters above U+00A0
    pytest.param(
        b"<?xml version='1.0' encoding='ISO-8859-1'?><p>caf\xe9 \xa4 \xff</p>",
        "caf\N{LATIN SMALL LETTER E WITH ACUTE} \N{CURRENCY SIGN} "
        "\N{LATIN SMALL LETTER Y WITH DIAERESIS}\n",
        "iso-8859-1",
        id="xml-latin-1",
    ),
    # U+00A0, one past the refused range
    pytest.param(b"<p>a\xc2\xa0b</p>", "a b\n", "utf-8", id="nbsp"),
    # references in 0x80 to 0x9F that html.parser maps to windows-1252 characters
    pytest.param(
        b"<p>&#x80; &#x9F;</p>",
        "\N{EURO SIGN} \N{LATIN CAPITAL LETTER Y WITH DIAERESIS}\n",
        "utf-8",
        id="ref-80",
    ),
    # the HTML Standard's numeric-reference table: 150 and 0x96 are U+2013, 128 is U+20AC and
    # 133 is U+2026, as a browser shows them (old filings write a minus sign this way)
    pytest.param(
        b"<p>&#150; &#x96; &#128; &#133;</p>",
        "\N{EN DASH} \N{EN DASH} \N{EURO SIGN} \N{HORIZONTAL ELLIPSIS}\n",
        "utf-8",
        id="refs-mapped",
    ),
    # only the text read is checked: a script's content is not read
    pytest.param(b"<script>\xc2\x85</script><p>ok</p>", "ok\n", "utf-8", id="script"),
    # ruling item 5, the other order: the meta declaration comes first and wins
    pytest.param(
        b'<meta charset="iso-8859-1"><?xml version="1.0" encoding="ISO-8859-1"?><p>price \x80 5</p>',
        "price \N{EURO SIGN} 5\n",
        "windows-1252",
        id="meta-first",
    ),
]


@pytest.mark.parametrize(("raw", "text", "encoding"), _READ_ROWS)
def test_the_text_read_keeps_what_it_should(raw: bytes, text: str, encoding: str) -> None:
    _read(raw, text, encoding)
