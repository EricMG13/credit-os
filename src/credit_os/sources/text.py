"""Readers of text and csv bytes into pages. Pure functions of a name and bytes."""

import csv
import io
import re
from collections.abc import Iterator

from credit_os.sources.errors import SourceUnreadable, shown_name
from credit_os.sources.pages import SourcePages, cut_pages, text_state_pages

PAGE_CHARACTERS = 12_000
# The csv module builds a whole row before it returns it, so a row is capped: the characters
# of one row's lines may not pass this, which bounds what the module holds for one row.
MAX_ROW_CHARACTERS = 1_048_576

_BOM = b"\xef\xbb\xbf"
# Category Cc is U+0000 to U+001F and U+007F to U+009F; tab, line feed, form feed and
# carriage return are the four left out.
_REFUSED_CONTROL = re.compile("[\x00-\x08\x0b\x0e-\x1f\x7f-\x9f]")
_LINE_BREAK = re.compile(r"\r\n|\r|\n")


def _refuse(name: str, reason: str) -> SourceUnreadable:
    return SourceUnreadable(f"{shown_name(name)}: {reason}")


def _decode(name: str, raw: bytes) -> tuple[str, str]:
    """Return the text and its encoding, or refuse bytes that decode as neither.

    Also refuses a control character, naming it and its line.
    """
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
    found = _REFUSED_CONTROL.search(text)
    if found:
        index = found.start()
        line = 1 + text.count("\n", 0, index) + text.count("\r", 0, index)
        line -= text.count("\r\n", 0, index)
        raise _refuse(name, f"control character U+{ord(found.group()):04X} on line {line}")
    return text, encoding


def text_pages(name: str, raw: bytes) -> SourcePages:
    """Read plain text: the decoded text unchanged, cut into pages."""
    text, encoding = _decode(name, raw)
    if not text or text.isspace():
        raise _refuse(name, "has no text")
    return text_state_pages(cut_pages(text, PAGE_CHARACTERS), encoding)


class _RowTooLong(Exception):
    """The lines of one csv row passed MAX_ROW_CHARACTERS."""


def csv_pages(name: str, raw: bytes) -> SourcePages:
    """Read comma-separated text: one line per row, cells joined by " | ", cut into pages."""
    text, encoding = _decode(name, raw)
    held = 0

    def lines() -> Iterator[str]:
        nonlocal held
        for line in io.StringIO(text, newline=""):
            held += len(line)
            if held > MAX_ROW_CHARACTERS:
                raise _RowTooLong
            yield line

    out = io.StringIO()
    has_text = False
    try:
        for row in csv.reader(lines(), strict=True):
            held = 0
            has_text = has_text or any(cell.strip() for cell in row)
            out.write(" | ".join(_LINE_BREAK.sub(" ", cell) for cell in row) + "\n")
    except csv.Error as error:
        raise _refuse(name, "not valid csv") from error
    except _RowTooLong as error:
        raise _refuse(name, f"a row is longer than {MAX_ROW_CHARACTERS:,} characters") from error
    if not has_text:
        raise _refuse(name, "has no text")
    return text_state_pages(cut_pages(out.getvalue(), PAGE_CHARACTERS), encoding)
