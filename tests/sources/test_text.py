"""The text and csv readers."""

import csv
import unicodedata

import pytest

from credit_os.sources import SourceUnreadable
from credit_os.sources.pages import Page, SourcePages
from credit_os.sources.text import csv_pages, text_pages


def _p(number: int, text: str) -> Page:
    return Page(number=number, text=text, state="text")


@pytest.mark.parametrize(
    ("raw", "pages", "encoding"),
    [
        (b"Synthetic note.\nSecond line.\n", ("Synthetic note.\nSecond line.\n",), "utf-8"),
        (b"\xef\xbb\xbfcaf\xc3\xa9\n", ("caf\N{LATIN SMALL LETTER E WITH ACUTE}\n",), "utf-8"),
        (
            b"caf\xe9 \x80 100\n",
            ("caf\N{LATIN SMALL LETTER E WITH ACUTE} \N{EURO SIGN} 100\n",),
            "windows-1252",
        ),
        (b"a\r\nb\r\n", ("a\r\nb\r\n",), "utf-8"),
        (b"a\tb\x0cc\n", ("a\tb\x0cc\n",), "utf-8"),
        pytest.param(
            (b"x" * 99 + b"\n") * 130,
            (("x" * 99 + "\n") * 120, ("x" * 99 + "\n") * 10),
            "utf-8",
            id="13000-bytes-two-pages",
        ),
        (
            b"a\xe2\x80\x8bb\xef\xbb\xbfc\n",
            ("a\N{ZERO WIDTH SPACE}b\N{ZERO WIDTH NO-BREAK SPACE}c\n",),
            "utf-8",
        ),
        pytest.param(b"x" * 12_001, ("x" * 12_000, "x"), "utf-8", id="12001-bytes-two-pages"),
    ],
)
def test_text_pages_rows(raw: bytes, pages: tuple[str, ...], encoding: str) -> None:
    expected = SourcePages(
        pages=tuple(_p(n, t) for n, t in enumerate(pages, start=1)), encoding=encoding
    )
    assert text_pages("notes.txt", raw) == expected


@pytest.mark.parametrize(
    ("name", "raw", "message"),
    [
        ("notes.txt", b"a\x00b\n", "notes.txt: control character U+0000 on line 1"),
        ("notes.txt", b"a\x1bb", "notes.txt: control character U+001B on line 1"),
        ("notes.txt", b"a\xc2\x85b", "notes.txt: control character U+0085 on line 1"),
        (
            "notes.txt",
            b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 8,
            "notes.txt: control character U+0011 on line 1",
        ),
        ("notes.txt", b"MZ\x90\x00\x03", "notes.txt: not valid UTF-8 or windows-1252"),
        ("notes.txt", b"\x81", "notes.txt: not valid UTF-8 or windows-1252"),
        (
            "notes.txt",
            b"\xef\xbb\xbf\xff",
            "notes.txt: not valid UTF-8 after its byte-order mark",
        ),
        ("notes.txt", b"", "notes.txt: has no text"),
        ("notes.txt", b" \n\t\r\n", "notes.txt: has no text"),
        pytest.param(
            "a" * 130 + ".txt",
            b"\x00",
            "a" * 120 + "\N{HORIZONTAL ELLIPSIS}: control character U+0000 on line 1",
            id="long-name",
        ),
        (
            "notes.txt",
            b"one\ntwo\r\nthree\rfo\x1bur\n",
            "notes.txt: control character U+001B on line 4",
        ),
        ("notes.txt", b"a\x00\n\x00b\x00", "notes.txt: control character U+0000 on line 1"),
        ("notes.txt", b"\xff\xfea\x00", "notes.txt: control character U+0000 on line 1"),
    ],
)
def test_text_pages_refusals(name: str, raw: bytes, message: str) -> None:
    with pytest.raises(SourceUnreadable) as caught:
        text_pages(name, raw)
    assert str(caught.value) == message


@pytest.mark.parametrize("raw", [b"\x81", b"\xef\xbb\xbf\xff"])
def test_decode_refusal_cause(raw: bytes) -> None:
    with pytest.raises(SourceUnreadable) as caught:
        text_pages("notes.txt", raw)
    assert isinstance(caught.value.__cause__, UnicodeDecodeError)


@pytest.mark.parametrize(
    ("raw", "text", "encoding"),
    [
        (b"period,revenue\nFY2025,100\n", "period | revenue\nFY2025 | 100\n", "utf-8"),
        (
            b'name,note\n"Acme, Inc.","said ""hi"""\n',
            'name | note\nAcme, Inc. | said "hi"\n',
            "utf-8",
        ),
        (b'a,"line1\nline2"\r\nb,"x\r\ny"\r\n', "a | line1 line2\nb | x y\n", "utf-8"),
        (b"a,b\n\nc,d\n", "a | b\n\nc | d\n", "utf-8"),
        (b"a,b,c\nd\n", "a | b | c\nd\n", "utf-8"),
        (b"x,001.50,1e3, padded \n", "x | 001.50 | 1e3 |  padded \n", "utf-8"),
        (
            b"nom,prix\ncaf\xe9,\x80 5\n",
            "nom | prix\ncaf\N{LATIN SMALL LETTER E WITH ACUTE} | \N{EURO SIGN} 5\n",
            "windows-1252",
        ),
        (b"a;b\n1;2\n", "a;b\n1;2\n", "utf-8"),
        (b"a,b", "a | b\n", "utf-8"),
        (b"\xef\xbb\xbfa,b\n", "a | b\n", "utf-8"),
        (b"a,b\rc,d\r", "a | b\nc | d\n", "utf-8"),
    ],
)
def test_csv_pages_rows(raw: bytes, text: str, encoding: str) -> None:
    assert csv_pages("t.csv", raw) == SourcePages(pages=(_p(1, text),), encoding=encoding)


def test_csv_pages_paging() -> None:
    raw = b"".join(b"%04d,x\n" % i for i in range(1500))
    rows = [f"{i:04d} | x\n" for i in range(1500)]
    expected = SourcePages(
        pages=(_p(1, "".join(rows[:1333])), _p(2, "".join(rows[1333:]))), encoding="utf-8"
    )
    assert len("".join(rows[:1333])) == 11_997
    assert csv_pages("t.csv", raw) == expected


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        (b'a,"b\n', "t.csv: not valid csv"),
        (b'"a"b,c\n', "t.csv: not valid csv"),
        pytest.param(b"x," + b"y" * 131_073 + b"\n", "t.csv: not valid csv", id="field-limit"),
        (b"a,\x00b\n", "t.csv: control character U+0000 on line 1"),
        (b"a,b\nc,\x1bd\n", "t.csv: control character U+001B on line 2"),
        (b",,\n,\n", "t.csv: has no text"),
        (b" , \n", "t.csv: has no text"),
        pytest.param(
            b"a," * 524_289 + b"b\n",
            "t.csv: a row is longer than 1,048,576 characters",
            id="row-over-cap",
        ),
        pytest.param(
            b'"' + (b"x" * 99 + b"\n") * 1_400 + b'"\n',
            "t.csv: not valid csv",
            id="quoted-row-over-field-limit",
        ),
        (b"", "t.csv: has no text"),
        (b"\x81,a\n", "t.csv: not valid UTF-8 or windows-1252"),
    ],
)
def test_csv_pages_refusals(raw: bytes, message: str) -> None:
    with pytest.raises(SourceUnreadable) as caught:
        csv_pages("t.csv", raw)
    assert str(caught.value) == message


def test_csv_error_is_the_cause_and_limit_is_untouched() -> None:
    with pytest.raises(SourceUnreadable) as caught:
        csv_pages("t.csv", b'a,"b\n')
    assert isinstance(caught.value.__cause__, csv.Error)
    with pytest.raises(SourceUnreadable):
        csv_pages("t.csv", b"x," + b"y" * 131_073 + b"\n")
    assert csv.field_size_limit() == 131072


def test_csv_many_cells_in_one_row_is_one_page() -> None:
    expected = SourcePages(pages=(_p(1, "a | " * 1_000 + "b\n"),), encoding="utf-8")
    assert csv_pages("t.csv", b"a," * 1_000 + b"b\n") == expected


def test_csv_row_cap_counts_one_row_at_a_time() -> None:
    at_cap = csv_pages("t.csv", b"a," * 524_287 + b"bb")
    assert "".join(p.text for p in at_cap.pages) == "a | " * 524_287 + "bb\n"
    with pytest.raises(SourceUnreadable) as caught:
        csv_pages("t.csv", b"a," * 524_287 + b"bbb")
    assert str(caught.value) == "t.csv: a row is longer than 1,048,576 characters"
    many_rows = csv_pages("t.csv", b"a\n" * 524_289)
    assert "".join(p.text for p in many_rows.pages) == "a\n" * 524_289


def test_csv_row_cap_counts_lines_and_line_ends() -> None:
    cell = b'"' + (b"x" * 99 + b"\n") * 1_000 + b'y"'
    with pytest.raises(SourceUnreadable) as caught:
        csv_pages("t.csv", b",".join([cell] * 11) + b"\n")
    assert str(caught.value) == "t.csv: a row is longer than 1,048,576 characters"
    with pytest.raises(SourceUnreadable) as caught:
        csv_pages("t.csv", b"a," * 524_287 + b"bb\n")
    assert str(caught.value) == "t.csv: a row is longer than 1,048,576 characters"
    accepted = csv_pages("t.csv", b"a," * 524_287 + b"b\n")
    assert len(accepted.pages) > 0
    assert accepted.pages[0].text.startswith("a | a | ")


@pytest.mark.parametrize(
    ("raw", "line"),
    [(b"a\x1b\r\nb\r", 1), (b"a\r\x1b", 2), (b"a\r\x1b\n", 2)],
)
def test_control_line_after_a_carriage_return(raw: bytes, line: int) -> None:
    with pytest.raises(SourceUnreadable) as caught:
        text_pages("n.txt", raw)
    assert str(caught.value) == f"n.txt: control character U+001B on line {line}"


def test_csv_text_in_an_earlier_row_counts() -> None:
    assert csv_pages("t.csv", b"a\n , \n") == SourcePages(
        pages=(_p(1, "a\n  |  \n"),), encoding="utf-8"
    )


def test_control_scan_refuses_exactly_the_cc_characters_but_four() -> None:
    for code in range(0x300):
        char = chr(code)
        refused = unicodedata.category(char) == "Cc" and char not in "\t\n\r\x0c"
        try:
            text_pages("n.txt", ("a" + char + "b").encode())
        except SourceUnreadable:
            assert refused, hex(code)
        else:
            assert not refused, hex(code)


def test_node_ids_fit_the_windows_environment_value(request: pytest.FixtureRequest) -> None:
    ids = [
        item.nodeid
        for item in request.session.items
        if "tests/sources" in item.nodeid.replace("\\", "/")
    ]
    assert ids
    assert all(len(nodeid) <= 3_000 for nodeid in ids)
