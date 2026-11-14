"""The text and csv readers."""

import csv

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
        (
            (b"x" * 99 + b"\n") * 130,
            (("x" * 99 + "\n") * 120, ("x" * 99 + "\n") * 10),
            "utf-8",
        ),
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
        (
            "a" * 130 + ".txt",
            b"\x00",
            "a" * 120 + "\N{HORIZONTAL ELLIPSIS}: control character U+0000 on line 1",
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
        (b"x," + b"y" * 131_073 + b"\n", "t.csv: not valid csv"),
        (b"a,\x00b\n", "t.csv: control character U+0000 on line 1"),
        (b"a,b\nc,\x1bd\n", "t.csv: control character U+001B on line 2"),
        (b",,\n,\n", "t.csv: has no text"),
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
