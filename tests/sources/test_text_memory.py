"""Peak memory of the text and csv readers on bounded inputs."""

import tracemalloc
from collections.abc import Callable
from typing import Any

import pytest

from credit_os.sources import SourceUnreadable
from credit_os.sources.pages import SourcePages
from credit_os.sources.text import csv_pages, text_pages

SIZE = 262_144
Reader = Callable[[str, bytes], SourcePages]
TL = 12 * 262_144 + 4 * 1_048_576
DL = 16 * 262_144 + 2 * 1_048_576
WL = 12 * 262_144 + 32 * 1_048_576
ASTRAL = "\U0001f600".encode()
EURO = "\N{EURO SIGN}".encode()
CONTROL = "t.txt: control character U+001B on line 87382"


def _exact(raw: bytes) -> bytes:
    """Pad with spaces to SIZE bytes, so every shape is the same size."""
    return raw.ljust(SIZE, b" ")


def _dense(first: bytes) -> bytes:
    """A first line, then rows of 999 commas and "a" (2,999 characters written each)."""
    return _exact(first + (b"," * 999 + b"a\n") * ((SIZE - len(first)) // 1_001))


def _case(
    id_: str, reader: Reader, raw: bytes, limit: int, pages: int, characters: int, refusal: str = ""
) -> Any:
    return pytest.param(reader, raw, limit, refusal or None, pages, characters, id=id_)


# Pages and characters come from each shape's construction: page 1 of text-astral holds the
# first line and 1,199 rows; the dense shapes hold the first line and four rows, then four
# rows to a page.
TXT, CSV = text_pages, csv_pages
CASES = [
    _case(
        "text-astral",
        TXT,
        _exact(ASTRAL + b"\n" + b"word word\n" * ((SIZE - 5) // 10)),
        TL,
        22,
        2 + 26_213 * 10 + 9,
    ),
    _case("text-crlf", TXT, _exact(b"\r\n" * ((SIZE - 1) // 2) + b"x"), TL, 22, 131_071 * 2 + 2),
    _case("text-crlf-then-control", TXT, b"a\r\n" * ((SIZE - 1) // 3) + b"\x1b", TL, 0, 0, CONTROL),
    _case("text-windows-1252", TXT, _exact(b"caf\xe9 \n" * (SIZE // 6)), TL, 22, 43_690 * 6 + 4),
    _case("csv-blank-rows", CSV, b"x\n" + b"\n" * (SIZE - 2), TL, 22, SIZE),
    _case("csv-short-cells", CSV, b"a\n" * (SIZE // 2), TL, 22, SIZE),
    _case(
        "csv-crlf-blank",
        CSV,
        _exact(b"x\r\n" + b"\r\n" * ((SIZE - 3) // 2)),
        TL,
        11,
        2 + 131_070 + 2,
    ),
    _case(
        "csv-one-wide-row",
        CSV,
        _exact(b"ab," * 87_380 + b"z\n"),
        WL,
        37,
        87_380 * 2 + 1 + 87_380 * 3 + 1 + 3,
    ),
    _case("csv-dense-astral", CSV, _dense(ASTRAL + b"\n"), DL, 66, 2 + 261 * 2_999 + 879),
    _case("csv-dense-euro", CSV, _dense(EURO + b"\n"), DL, 66, 2 + 261 * 2_999 + 880),
]


@pytest.mark.parametrize(("reader", "raw", "limit", "refusal", "pages", "characters"), CASES)
def test_peak_memory_is_bounded(
    reader: Reader,
    raw: bytes,
    limit: int,
    refusal: str | None,
    pages: int,
    characters: int,
) -> None:
    assert len(raw) == SIZE
    name = "t.txt" if reader is text_pages else "t.csv"
    result: SourcePages | None = None
    message: str | None = None
    tracemalloc.start()
    try:
        try:
            result = reader(name, raw)
        except SourceUnreadable as error:
            message = str(error)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak <= limit
    assert message == refusal
    if refusal is None:
        assert result is not None
        assert len(result.pages) == pages
        assert sum(len(page.text) for page in result.pages) == characters
