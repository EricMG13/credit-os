"""Reader of HTML bytes into pages: decoding without a decoded copy, and the line writer."""

import codecs
import re

from credit_os.sources.errors import SourceUnreadable, shown_name

# Characters of one page of text.
PAGE_CHARACTERS = 3_000
# Bytes decoded and given to the parser per step; a step never brings more characters than bytes.
PIECE_BYTES = 8_192
# Characters the parser may keep unparsed between steps.
HELD_CHARACTERS = 8_192
# The most the parser ever parses at once, and the limit in both long-tag refusals.
PARSED_CHARACTERS = HELD_CHARACTERS + PIECE_BYTES
# Distinct tag names kept; a flood of different names would otherwise grow memory without bound.
MAX_TAG_NAMES = 4_096
# The parser keeps a reference together across steps only inside its last 34 characters.
REFERENCE_WINDOW = 34
# `&#x` and 31 digits fit that window; a reference of 32 or more digits could be cut by a step.
REFERENCE_DIGITS = 32

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "wbr"}
SKIP = {"script", "style", "head", "ix:header"}
BLOCK = {
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
HIDDEN = re.compile(r"display\s*:\s*none", re.IGNORECASE)
_ZERO_WIDTH = dict.fromkeys((0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF))

# These tags start and end a line; every other block tag, including div, gives a space.
LINE_TAGS = frozenset({"p", "tr", "li", "br", "h1", "h2", "h3", "h4", "h5", "h6"})

_SNIFF_BYTES = 4096
_CHARSET = re.compile(rb"""(?:charset|encoding)\s*=\s*["']?\s*([A-Za-z0-9_.:\-]+)""", re.IGNORECASE)
# codecs.lookup(...).name -> the name reported for the source
_ACCEPTED = {
    "utf-8": "utf-8",
    "cp1252": "windows-1252",
    "iso8859-1": "iso-8859-1",
    "ascii": "ascii",
}
_BOM = b"\xef\xbb\xbf"


def _refuse(name: str, reason: str) -> SourceUnreadable:
    return SourceUnreadable(f"{shown_name(name)}: {reason}")


def _decodes(raw: bytes, start: int, codec: str) -> UnicodeDecodeError | None:
    """Return the error decoding raw[start:] strictly gives, or None; keeps no decoded text."""
    decoder = codecs.getincrementaldecoder(codec)()
    view = memoryview(raw)
    try:
        for at in range(start, len(raw), PIECE_BYTES):
            decoder.decode(view[at : at + PIECE_BYTES])
        decoder.decode(b"", True)
    except UnicodeDecodeError as error:
        return error
    return None


def _encoding(name: str, raw: bytes) -> tuple[str, str, int]:
    """Return the codec, the name reported and the first text byte, or refuse the bytes."""
    if raw.startswith(_BOM):
        error = _decodes(raw, len(_BOM), "utf-8")
        if error is not None:
            raise _refuse(name, "not valid UTF-8 after its byte-order mark") from error
        return "utf-8", "utf-8", len(_BOM)
    utf8_error = _decodes(raw, 0, "utf-8")
    if utf8_error is None:
        return "utf-8", "utf-8", 0
    found = _CHARSET.search(raw, 0, _SNIFF_BYTES)
    if found is None:
        raise _refuse(
            name, "not valid UTF-8 and declares no charset in its first 4,096 bytes"
        ) from utf8_error
    declared = found.group(1).decode("ascii")
    lookup_error: LookupError | None = None
    codec = ""
    try:
        codec = codecs.lookup(declared).name
    except LookupError as error:
        lookup_error = error
    if codec not in _ACCEPTED:
        raise _refuse(
            name, f"declares a charset that is not accepted: {declared[:40]!r}"
        ) from lookup_error
    reported = _ACCEPTED[codec]
    codec_error = _decodes(raw, 0, codec)
    if codec_error is not None:
        raise _refuse(name, f"not valid {reported}") from codec_error
    return codec, reported, 0


class _LineText:
    """The legacy's lines, written as the text arrives, holding no line."""

    def __init__(self) -> None:
        self._pieces: list[str] = []
        self._in_line = False
        self._space = False

    def text(self, data: str) -> None:
        if not data.isascii():
            data = data.translate(_ZERO_WIDTH)
        words = data.split()
        if not words:
            self._space = self._space or bool(data)
            return
        if self._in_line and (self._space or data[0].isspace()):
            self._pieces.append(" ")
        self._pieces.append(" ".join(words))
        self._in_line = True
        self._space = data[-1].isspace()

    def space(self) -> None:
        self._space = True

    def line_end(self) -> None:
        if self._in_line:
            self._pieces.append("\n")
        self._in_line = False
        self._space = False

    def take(self) -> list[str]:
        pieces, self._pieces = self._pieces, []
        return pieces
