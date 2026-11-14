"""Peak memory of the text and csv readers on bounded inputs."""

import tracemalloc
from collections.abc import Callable

import pytest

from credit_os.sources import SourceUnreadable
from credit_os.sources.pages import SourcePages
from credit_os.sources.text import csv_pages, text_pages

SIZE = 262_144
LIMIT = 12 * 262_144 + 32 * 1_048_576


def _exact(raw: bytes) -> bytes:
    """Pad with spaces to SIZE bytes, so every shape is the same size."""
    return raw.ljust(SIZE, b" ")


ASTRAL = "\U0001f600".encode()

CASES = [
    pytest.param(
        text_pages,
        _exact(ASTRAL + b"\n" + b"word word\n" * ((SIZE - 5) // 10)),
        None,
        id="text-astral",
    ),
    pytest.param(text_pages, _exact(b"\r\n" * ((SIZE - 1) // 2) + b"x"), None, id="text-crlf"),
    pytest.param(
        text_pages,
        b"a\r\n" * ((SIZE - 1) // 3) + b"\x1b",
        "t.txt: control character U+001B on line 87382",
        id="text-crlf-then-control",
    ),
    pytest.param(text_pages, _exact(b"caf\xe9 \n" * (SIZE // 6)), None, id="text-windows-1252"),
    pytest.param(csv_pages, b"x\n" + b"\n" * (SIZE - 2), None, id="csv-blank-rows"),
    pytest.param(csv_pages, b"a\n" * (SIZE // 2), None, id="csv-short-cells"),
    pytest.param(
        csv_pages, _exact(b"x\r\n" + b"\r\n" * ((SIZE - 3) // 2)), None, id="csv-crlf-blank"
    ),
    pytest.param(csv_pages, _exact(b"ab," * 87_380 + b"z\n"), None, id="csv-one-wide-row"),
]


@pytest.mark.parametrize(("reader", "raw", "refusal"), CASES)
def test_peak_memory_is_bounded(
    reader: Callable[[str, bytes], SourcePages], raw: bytes, refusal: str | None
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
    assert peak <= LIMIT
    if refusal is None:
        assert result is not None
        assert result.pages
    else:
        assert message == refusal
