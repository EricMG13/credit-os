"""Reader of HTML bytes: decoding without a decoded copy, the line writer and the reading engine."""

import codecs
import re
from array import array
from collections.abc import Iterator
from html import unescape
from html.parser import HTMLParser

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

# The legacy's: a charset is looked for in the first 4,096 bytes only.
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

# HIDDEN for bytes that are ASCII: \s written out as the ASCII characters str.isspace() accepts.
_HIDDEN_ASCII = re.compile(rb"display[\t-\r\x1c-\x1f ]*:[\t-\r\x1c-\x1f ]*none", re.IGNORECASE)
_NOT_PLAIN = re.compile(rb"[&\x80-\xff]")  # a reference, or a character outside ASCII
_TAG_OPEN = re.compile(r"</?[a-zA-Z]")
_QUOTED_END_TAG = re.compile(r"""</[a-zA-Z][^>'"]*['"]""")  # a quote before its first ">"
# html.parser.commentclose, read from html.parser's own str buffer.
_COMMENT_CLOSE = re.compile(r"--!?>")
# html.parser.RCDATA_CONTENT_ELEMENTS: content whose references are decoded.
_DECODED_CONTENT = ("textarea", "title")
# html.parser.locatetagend as bytes with its outer repeat made possessive ("*+"): the same end
# (nothing after the repeat can fail, so it never gives an attribute back) and no state per
# attribute.
_TAG_END = re.compile(
    rb"""
  [a-zA-Z][^\t\n\r\f />]*           # tag name
  [\t\n\r\f /]*                     # optional whitespace before attribute name
  (?:(?<=['"\t\n\r\f /])[^\t\n\r\f />][^\t\n\r\f /=>]*  # attribute name
    (?:[\t\n\r\f ]*=[\t\n\r\f ]*    # value indicator
      (?:'[^']*'                    # LITA-enclosed value
        |"[^"]*"                    # LIT-enclosed value
        |(?!['"])[^>\t\n\r\f ]*     # bare value
       )
     )?
    [\t\n\r\f /]*                   # possibly followed by a space
   )*+
   >?
""",
    re.VERBOSE,
)
# html.parser.tagfind_tolerant and attrfind_tolerant as bytes, unchanged.
_TAG_NAME = re.compile(rb"([a-zA-Z][^\t\n\r\f />]*)(?:[\t\n\r\f ]|/(?!>))*")
_ATTRIBUTE = re.compile(
    rb"""
  (
    (?<=['"\t\n\r\f /])[^\t\n\r\f />][^\t\n\r\f /=>]*  # attribute name
   )
  ([\t\n\r\f ]*=[\t\n\r\f ]*        # value indicator
    ('[^']*'                        # LITA-enclosed value
    |"[^"]*"                        # LIT-enclosed value
    |(?!['"])[^>\t\n\r\f ]*         # bare value
    )
   )?
  (?:[\t\n\r\f ]|/(?!>))*           # possibly followed by a space
""",
    re.VERBOSE,
)


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


class _Visible(HTMLParser):
    """The legacy converter's handlers over html.parser, fed a piece at a time.

    Text goes out as line pieces; the open-element stack is 2 bytes an element; html.parser waits
    wherever its reading of what it holds could differ from its reading of the whole document.
    """

    def __init__(self, name: str) -> None:
        super().__init__(convert_charrefs=True)
        self.name = name
        self.lines = _LineText()
        # What still lies in bytes html.parser has not been given: a comment end; quote characters.
        self.close_ahead = False
        self.quotes_ahead = ""
        self._ids: dict[str, int] = {}
        self._open: list[int] = []  # open elements per name id
        self._stack = array("H")  # per open element: name id * 2 + hidden
        self._skipping = 0

    def _break(self, tag: str) -> None:
        if tag in LINE_TAGS:
            self.lines.line_end()
        elif tag in BLOCK:
            self.lines.space()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "body":
            self.handle_endtag("head")
        self._break(tag)
        if tag in VOID:
            return
        hidden = tag in SKIP or any(k == "style" and HIDDEN.search(v or "") for k, v in attrs)
        ident = self._ids.get(tag)
        if ident is None:
            if len(self._ids) == MAX_TAG_NAMES:
                raise _refuse(self.name, f"more than {MAX_TAG_NAMES:,} different tag names")
            ident = self._ids[tag] = len(self._ids)
            self._open.append(0)
        self._open[ident] += 1
        self._stack.append(ident * 2 + hidden)
        self._skipping += hidden

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._break(tag)

    def handle_endtag(self, tag: str) -> None:
        self._break(tag)
        ident = self._ids.get(tag)
        if ident is None or not self._open[ident]:
            return
        while True:
            entry = self._stack.pop()
            self._open[entry >> 1] -= 1
            self._skipping -= entry & 1
            if entry >> 1 == ident:
                return

    def handle_data(self, data: str) -> None:
        if not self._skipping:
            self.lines.text(data)

    # -- html.parser waits where the whole document could read differently ----------------

    def parse_comment(self, i: int, report: bool = True) -> int:
        # html.parser ends "<!-->" at once only when no comment end follows in what it holds.
        # Fed whole, that is the rest of the document; fed in pieces, wait while one lies ahead.
        if self.close_ahead and not _COMMENT_CLOSE.search(self.rawdata, i + 4):
            return -1
        return super().parse_comment(i, report)

    def _waits(self, start: int, end: int) -> bool:
        """Whether the tag html.parser found whole in [start, end) may still grow.

        html.parser reads `b = "x>` as a whole tag when what it holds has no closing quote. Fed
        whole it would find one later in the document, so wait while one may still come.
        """
        held = self.rawdata
        return end >= 0 and any(
            held.find(quote, start, end) >= 0 and held.find(quote, end) < 0
            for quote in self.quotes_ahead
        )

    def check_for_whole_start_tag(self, i: int) -> int:
        end = super().check_for_whole_start_tag(i)
        return -1 if self._waits(i, end) else end

    def parse_endtag(self, i: int) -> int:
        # An end tag ends where a start tag would (html.parser uses the same pattern for both).
        quoted = self.quotes_ahead and _QUOTED_END_TAG.match(self.rawdata, i)
        if quoted and self._waits(i, super().check_for_whole_start_tag(i + 1)):
            return -1
        return super().parse_endtag(i)

    # -- what html.parser may hold between steps ------------------------------------------

    def release(self) -> bool:
        """Cut down what html.parser holds; return False when it holds a tag."""
        held = self.rawdata
        if self.cdata_elem is not None and not self.interesting.match(held):
            self._release_content(held, self.cdata_elem)
        elif not held.startswith("<"):
            cut = held.rfind("&")  # text held for the end of a reference: no reference holds "&"
            self.handle_data(unescape(held[:cut]))
            self.rawdata = held[cut:]
        elif _TAG_OPEN.match(held):
            return False
        else:
            # a comment, declaration or processing instruction: its body is never read
            self.rawdata = held[:9] + "x" + held[-3:]
        return True

    def _release_content(self, held: str, element: str) -> None:
        end = len(held) - len(element) - 2  # "</" and the name may be an end tag's start
        if element in _DECODED_CONTENT:
            amp = held.rfind("&", max(0, end - REFERENCE_WINDOW), end)
            if amp >= 0:
                end = amp
            self.handle_data(unescape(held[:end]))
        else:
            self.handle_data(held[:end])
        self.rawdata = held[end:]

    def replace(self, tag: str) -> None:
        """Forget what is held and read this whole tag in its place."""
        self.reset()
        self.close_ahead, self.quotes_ahead = False, ""  # nothing ahead can extend a whole tag
        self.rawdata = tag
        self.goahead(False)


def _bounded(raw: bytes, start: int, end: int, codec: str) -> str | None:
    """Decode raw[start:end], or None when it is more characters than html.parser is given."""
    if end - start <= 4 * PARSED_CHARACTERS:
        text = raw[start:end].decode(codec)
        if len(text) <= PARSED_CHARACTERS:
            return text
    return None


def _hidden_style(name: str, raw: bytes, found: re.Match[bytes], codec: str) -> bool:
    """Whether this attribute of a long tag is a style that hides its element."""
    start, end = found.span(1)
    if end - start != 5 or raw[start:end].lower() != b"style" or found.start(3) < 0:
        return False
    start, end = found.span(3)
    if end - start >= 2 and raw[start] in b"'\"" and raw[start] == raw[end - 1]:
        start, end = start + 1, end - 1
    value = _bounded(raw, start, end, codec)
    if value is not None:
        return bool(HIDDEN.search(unescape(value)))
    if _NOT_PLAIN.search(raw, start, end):
        raise _refuse(
            name,
            f"a style attribute longer than {PARSED_CHARACTERS:,} characters"
            " that is not plain ASCII",
        )
    return bool(_HIDDEN_ASCII.search(raw, start, end))


def _long_tag(name: str, raw: bytes, start: int, codec: str) -> tuple[str, int]:
    """Read a tag html.parser may not hold: the tag to give it instead, and where it ends.

    The legacy reads three things from a tag: its name, whether a style hides it, and whether
    it closes itself. They are read here from the bytes with html.parser's own patterns.
    """
    closing = raw.startswith(b"</", start)
    at = start + 2 if closing else start + 1
    found = _TAG_END.match(raw, at)
    name_found = _TAG_NAME.match(raw, at)
    if found is None or name_found is None or raw[found.end() - 1 : found.end()] != b">":
        return "", len(raw)  # never closed: the legacy drops the rest of the document
    end = found.end()
    tag = _bounded(raw, *name_found.span(1), codec)
    if tag is None:
        raise _refuse(name, f"a tag name longer than {PARSED_CHARACTERS:,} characters")
    if closing:
        return f"</{tag}>", end
    if tag.lower() in VOID:
        return f"<{tag}>", end
    hidden = False
    at = name_found.end()
    while at < end:
        attribute = _ATTRIBUTE.match(raw, at)
        if attribute is None:
            break
        hidden = hidden or _hidden_style(name, raw, attribute, codec)
        at = attribute.end()
    if raw[at:end].strip().endswith(b"/>"):
        return f"<{tag}/>", end
    return (f"<{tag} style=display:none>" if hidden else f"<{tag}>"), end


def _visible_text(name: str, raw: bytes, codec: str, position: int) -> Iterator[str]:
    """Feed html.parser the bytes from position a piece at a time; yield the lines in pieces."""
    last_close = max(raw.rfind(b"-->") + 3, raw.rfind(b"--!>") + 4)
    last_quote = {"'": raw.rfind(b"'"), '"': raw.rfind(b'"')}
    view = memoryview(raw)
    decoder = codecs.getincrementaldecoder(codec)()
    reader = _Visible(name)
    while position < len(raw):
        end = min(position + PIECE_BYTES, len(raw))
        reader.close_ahead = last_close > end
        reader.quotes_ahead = "".join(quote for quote, at in last_quote.items() if at >= end)
        reader.rawdata += decoder.decode(view[position:end])
        position = end
        reader.goahead(False)
        if len(reader.rawdata) > HELD_CHARACTERS and not reader.release():
            pending = decoder.getstate()[0]
            start = position - len(pending) - len(reader.rawdata.encode(codec))
            tag, position = _long_tag(name, raw, start, codec)
            decoder.reset()
            reader.replace(tag)
        yield from reader.lines.take()
    reader.close_ahead, reader.quotes_ahead = False, ""
    reader.close()
    reader.lines.line_end()
    yield from reader.lines.take()
