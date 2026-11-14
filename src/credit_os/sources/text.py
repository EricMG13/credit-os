"""Readers of text and csv bytes into pages. Pure functions of a name and bytes."""

import csv
import io
import re
import unicodedata

from credit_os.sources.errors import SourceUnreadable, shown_name
from credit_os.sources.pages import SourcePages, cut_pages, text_state_pages

PAGE_CHARACTERS = 12_000

_BOM = b"\xef\xbb\xbf"
_ALLOWED_CONTROLS = frozenset("\t\n\r\x0c")
_LINE_BREAK = re.compile(r"\r\n|\r|\n")


def _refuse(name: str, reason: str) -> SourceUnreadable:
    return SourceUnreadable(f"{shown_name(name)}: {reason}")


def _decode(name: str, raw: bytes) -> tuple[str, str]:
    """Return the text and its encoding, or refuse bytes that decode as neither."""
    if raw.startswith(_BOM):
        try:
            text, encoding = raw[len(_BOM) :].decode("utf-8"), "utf-8"
        except UnicodeDecodeError as error:
            raise _refuse(name, "not valid UTF-8 after its byte-order mark") from error
    else:
        try:
            text, encoding = raw.decode("utf-8"), "utf-8"
        except UnicodeDecodeError:
            try:
                text, encoding = raw.decode("windows-1252"), "windows-1252"
            except UnicodeDecodeError as error:
                raise _refuse(name, "not valid UTF-8 or windows-1252") from error
    for index, char in enumerate(text):
        if unicodedata.category(char) == "Cc" and char not in _ALLOWED_CONTROLS:
            line = 1 + len(_LINE_BREAK.findall(text, 0, index))
            raise _refuse(name, f"control character U+{ord(char):04X} on line {line}")
    return text, encoding


def text_pages(name: str, raw: bytes) -> SourcePages:
    """Read plain text: the decoded text unchanged, cut into pages."""
    text, encoding = _decode(name, raw)
    if not text.strip():
        raise _refuse(name, "has no text")
    return text_state_pages(cut_pages(text, PAGE_CHARACTERS), encoding)


def csv_pages(name: str, raw: bytes) -> SourcePages:
    """Read comma-separated text: one line per row, cells joined by " | ", cut into pages."""
    text, encoding = _decode(name, raw)
    try:
        rows = list(csv.reader(io.StringIO(text, newline=""), strict=True))
    except csv.Error as error:
        raise _refuse(name, "not valid csv") from error
    if not any(cell.strip() for row in rows for cell in row):
        raise _refuse(name, "has no text")
    lines = "".join(" | ".join(_LINE_BREAK.sub(" ", cell) for cell in row) + "\n" for row in rows)
    return text_state_pages(cut_pages(lines, PAGE_CHARACTERS), encoding)
