"""Parse RSS 2.0 and Atom feed bytes into entries. Standard library only.

Feed bytes are untrusted. The XML is read with ``xml.parsers.expat`` directly, and a document
type declaration, any entity declaration and any external entity reference are refused, so no
entity is ever defined, expanded or fetched. No article body is fetched; only the feed's own
title, link, date and summary are read.
"""

import re
import string
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html import escape
from html.parser import HTMLParser
from typing import NoReturn
from urllib.parse import urlsplit
from xml.parsers import expat

SUMMARY_LIMIT = 300
MAX_BYTES = 2 * 1024 * 1024
MAX_DEPTH = 64
# R24. A feed of 1,000 entries each with 100 elements of XHTML has about 110,000 elements; no
# 2 MiB feed of real markup has more than 262,144 (the shortest element with text, "<b>x</b>",
# is 8 bytes), so a feed of more than 200,000 is a flood of empty elements.
MAX_ELEMENTS = 200_000
# R24. Atom and RSS elements carry at most a handful of attributes and HTML elements about ten.
MAX_ATTRIBUTES = 256
# R24. Total characters of element names: pyexpat builds each name in full (a 16 KiB namespace
# URI on each of 16,000 elements is 268 MB of copying), so the time of a feed whose names are
# long grows with the product of their length and number. A feed of 1,000 entries of 100
# namespaced XHTML elements has about 4 million; 16 Mi leaves four times that.
MAX_NAME_CHARS = 16 * 1024 * 1024
# R24. Characters of one field handed to the HTML stripper (see _strip_markup).
MAX_HTML_CHARS = 128 * 1024
TITLE_LIMIT = 500
LINK_LIMIT = 2048
ERROR_TEXT_LIMIT = 120
_HOST_CHARS = frozenset(string.ascii_letters + string.digits + "-")
_HEX_NUMBER = re.compile(r"0x[0-9a-f]*", re.ASCII | re.IGNORECASE)


_DTD_MESSAGE = "feed declares a DTD or entities"


class FeedError(ValueError):
    """The feed cannot be read; the message is shown to the owner."""


def _refuse(*_args: object) -> NoReturn:
    raise FeedError(_DTD_MESSAGE)


# R17: a block-level element starts and ends a new run of text, so adjacent blocks never fuse.
_BLOCKS = frozenset(
    (
        *("p", "br", "div", "li", "ul", "ol", "dl", "dt", "dd", "table", "tr", "td", "th"),
        *("thead", "tbody", "tfoot", "caption", "h1", "h2", "h3", "h4", "h5", "h6"),
        *("blockquote", "pre", "hr", "section", "article", "header", "footer", "figure"),
        "figcaption",
    )
)
_XHTML_TAGS = _BLOCKS | {"script", "style"}
_LONGEST_TAG = max(map(len, _XHTML_TAGS))
_OPEN_TAG = {tag: f"<{tag}>" for tag in _XHTML_TAGS}
_CLOSE_TAG = {tag: f"</{tag}>" for tag in _XHTML_TAGS}


@dataclass(eq=False, slots=True)
class _Node:
    """A kept element. ``kind`` is its place in the feed: ``rss``, ``feed`` or ``other`` for the
    root, then ``channel``, ``item`` and ``entry``. ``children`` are the kept elements below it.
    An item or entry keeps, for each field read from it, the field's kind and all text below it
    in ``fields``, and, for an Atom entry, the href of its first alternate link in ``link``.
    """

    kind: str
    children: list["_Node"] = field(default_factory=list)
    fields: dict[str, tuple[str, str]] = field(default_factory=dict)
    link: str | None = None


@dataclass(eq=False, slots=True)
class _Field:
    """The field being read: its text, or, for Atom xhtml, the rebuilt markup, in order."""

    owner: _Node
    key: str
    kind: str
    parts: list[str] = field(default_factory=list)

    @property
    def markup(self) -> bool:
        return self.kind == "xhtml"


# R24: the tree keeps only what parse_feed reads. Names are expat's, "uri}local" for a name in a
# namespace, so a name is compared as expat spells it and never rebuilt (a body-filling
# namespace URI is then never copied per element).
_ATOM = "http://www.w3.org/2005/Atom}"
_ROOTS = {"rss": "rss", f"{_ATOM}feed": "feed"}
_CHILD = {
    "rss": ("channel", "channel"),
    "channel": ("item", "item"),
    "feed": (f"{_ATOM}entry", "entry"),
}
_FIELD_KEYS = {
    "item": {key: key for key in ("title", "link", "pubDate", "description")},
    "entry": {f"{_ATOM}{key}": key for key in ("published", "updated", "title", "summary", "link")},
}
_NO_FIELD = ("", "")
_SLICE = 4096
_TEXT_CONSTRUCTS = ("title", "summary")


def _xhtml_tag(name: str) -> str | None:
    """The tag written for an element inside Atom xhtml, or None: the element's text only."""
    local = name[name.rfind("}") + 1 :]
    if len(local) > _LONGEST_TAG or not local.isascii():
        return None
    local = local.lower()
    return local if local in _XHTML_TAGS else None


class _TreeBuilder:
    """Builds a _Node tree from expat events; comments and processing instructions are dropped.

    ``document`` is a nameless parent of the root element. Every element is counted and its
    depth checked; only those parse_feed reads become nodes. Elements inside a field add their
    text to the field (R24: no node per element).
    """

    def __init__(self) -> None:
        self.document = _Node("document")
        # One entry per open element: its node or field, the closing tag to write for an xhtml
        # element, or None for an element that is not kept.
        self._open: list[_Node | _Field | str | None] = []
        self._field: _Field | None = None
        self._elements = 0
        self._name_chars = 0

    def start(self, name: str, attrs: dict[str, str]) -> None:
        if len(self._open) >= MAX_DEPTH:
            raise FeedError(f"feed is nested deeper than {MAX_DEPTH} elements")
        self._elements += 1
        if self._elements > MAX_ELEMENTS:
            raise FeedError(f"feed has more than {MAX_ELEMENTS} elements")
        self._name_chars += len(name)
        if self._name_chars > MAX_NAME_CHARS:
            raise FeedError("feed element names are too long")
        if len(attrs) > MAX_ATTRIBUTES:
            raise FeedError(f"feed has an element with more than {MAX_ATTRIBUTES} attributes")
        self._open.append(self._enter(name, attrs))

    def _enter(self, name: str, attrs: dict[str, str]) -> _Node | _Field | str | None:
        if self._field is not None:
            return self._enter_field_content(self._field, name)
        parent = self._open[-1] if self._open else self.document
        if not isinstance(parent, _Node):
            return None
        if parent.kind == "document":
            return self._attach(parent, _Node(_ROOTS.get(name, "other")))
        keys = _FIELD_KEYS.get(parent.kind)
        if keys is not None:
            return self._enter_field(parent, keys.get(name), attrs)
        wanted = _CHILD.get(parent.kind)
        if wanted is not None and wanted[0] == name:
            return self._attach(parent, _Node(wanted[1]))
        return None

    @staticmethod
    def _attach(parent: _Node, node: _Node) -> _Node:
        parent.children.append(node)
        return node

    def _enter_field(self, record: _Node, key: str | None, attrs: dict[str, str]) -> _Field | None:
        if key is None:
            return None
        if key == "link" and record.kind == "entry":
            # The first alternate link counts, whether or not it has an href (RFC 4287, 4.2.7.2).
            if record.link is None and attrs.get("rel") in (None, "alternate"):
                record.link = (attrs.get("href") or "").strip()
            return None
        if key in record.fields:  # the first of two fields of a name wins
            return None
        kind = attrs.get("type", "") if record.kind == "entry" and key in _TEXT_CONSTRUCTS else ""
        self._field = _Field(record, key, kind if kind in ("html", "xhtml") else "")
        return self._field

    @staticmethod
    def _enter_field_content(current: _Field, name: str) -> str | None:
        if not current.markup:
            return None
        tag = _xhtml_tag(name)
        if tag is None:
            return None
        current.parts.append(_OPEN_TAG[tag])
        return _CLOSE_TAG[tag]

    def end(self, name: str) -> None:
        top = self._open.pop()
        if isinstance(top, str) and self._field is not None:
            self._field.parts.append(top)
        elif isinstance(top, _Field):
            top.owner.fields[top.key] = (top.kind, "".join(top.parts))
            self._field = None
        elif isinstance(top, _Node) and top.kind in ("item", "entry"):
            self._drop_if_unread(top)

    def _drop_if_unread(self, record: _Node) -> None:
        # A record with no field read cannot make an entry; a feed of empty items costs nothing.
        parent = self._open[-1]
        if isinstance(parent, _Node) and not record.fields and record.link is None:
            parent.children.pop()

    def data(self, text: str) -> None:
        if self._field is not None:
            self._field.parts.append(escape(text, quote=False) if self._field.markup else text)


def _new_parser(builder: _TreeBuilder) -> expat.XMLParserType:
    parser = expat.ParserCreate(None, "}")
    parser.buffer_text = True
    parser.StartElementHandler = builder.start
    parser.EndElementHandler = builder.end
    parser.CharacterDataHandler = builder.data
    # No DTD of any kind is accepted: the parser itself refuses a declaration in any encoding,
    # and the entity and external-entity handlers cover what a declaration could still reach.
    parser.StartDoctypeDeclHandler = _refuse
    parser.EntityDeclHandler = _refuse
    parser.ExternalEntityRefHandler = _refuse
    parser.UnparsedEntityDeclHandler = _refuse
    parser.NotationDeclHandler = _refuse
    return parser


def _read_xml(body: bytes) -> _Node:
    builder = _TreeBuilder()
    # Parse raises ExpatError unless the body holds exactly one root element.
    _new_parser(builder).Parse(body, True)
    return builder.document.children[0]


@dataclass(frozen=True)
class Entry:
    title: str
    link: str
    published: datetime | None
    summary: str


class _TextOnly(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style"):
            self._skip += 1
        elif tag in _BLOCKS:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self._skip:
            self._skip -= 1
        elif tag in _BLOCKS:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)


def _html_window(raw: str) -> str:
    """The first MAX_HTML_CHARS characters of ``raw``, ending before a tag they would cut short.

    R24. What html.parser reads is bounded because its memory is not: one start tag with a
    million attributes costs about 280 bytes an attribute, and only a prefix of the markup can
    reach the summary (cut to SUMMARY_LIMIT) or the title (cut to TITLE_LIMIT). The prefix
    changes the result only when the first MAX_HTML_CHARS characters of one field hold fewer
    than SUMMARY_LIMIT characters of text, all markup, white space or hidden script and style.
    """
    if len(raw) <= MAX_HTML_CHARS:
        return raw
    cut = raw.rfind("<", 0, MAX_HTML_CHARS)
    return raw[: cut if cut >= 0 else MAX_HTML_CHARS]


def _strip_markup(raw: str) -> str:
    """The text of an HTML fragment, markup removed and character references decoded."""
    parser = _TextOnly()
    try:
        parser.feed(_html_window(raw))
        parser.close()
    except AssertionError as exc:
        # Standard libraries before the 2025 html.parser fixes assert on some markup (R20).
        raise FeedError("feed text could not be read") from exc
    return "".join(parser.parts)


def _plain(raw: str) -> str:
    """Control and format characters dropped (white space is kept for the caller to fold)."""
    return "".join(ch for ch in raw if ch.isspace() or unicodedata.category(ch) not in ("Cc", "Cf"))


def _folded(text: str, limit: int) -> str:
    """The first ``limit`` characters of ``" ".join(_plain(text).split())``, whole text unread.

    R24. Cleaning goes a slice at a time and stops once ``limit`` characters of folded text
    exist, so it builds at most one slice of one-character strings (not one per character of a
    2 MiB field) and reads no further than the result needs. The result is exact: a character
    is dropped or kept on its own, and a word that ends a slice is joined to the next slice.
    """
    words: list[str] = []
    size = 0  # characters in " ".join(words), plus one
    word = ""  # the last word of the slices read, which the next slice may continue
    for start in range(0, len(text), _SLICE):
        chunk = word + _plain(text[start : start + _SLICE])
        found = chunk.split()
        word = found.pop() if found and not chunk[-1].isspace() else ""
        words.extend(found)
        size += sum(len(w) + 1 for w in found)
        if size + len(word) > limit:
            break
    if word:
        words.append(word)
    return " ".join(words)[:limit]


def _summary(text: str) -> str:
    """Plain text folded to single spaces, then cut to SUMMARY_LIMIT on a word boundary."""
    head = _folded(text, SUMMARY_LIMIT + 1)
    if len(head) <= SUMMARY_LIMIT:
        return head
    if " " not in head:
        return head[:SUMMARY_LIMIT]
    return head.rsplit(" ", 1)[0].rstrip()


def _utc(moment: datetime) -> datetime:
    # A date with no zone is read as UTC.
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


def _iso_date(text: str) -> datetime | None:
    try:
        return _utc(datetime.fromisoformat(text))
    except (ValueError, OverflowError):
        return None


def _rss_date(text: str) -> datetime | None:
    try:
        return _utc(parsedate_to_datetime(text))
    except (ValueError, OverflowError):
        return _iso_date(text)


def _text(record: _Node, key: str) -> str:
    return record.fields.get(key, _NO_FIELD)[1].strip()


def _title(text: str) -> str:
    """Plain text with control and format characters dropped, folded, cut, then stripped."""
    return _folded(text, TITLE_LIMIT).strip()


def _dns_name(host: str) -> bool:
    """ASCII letters, digits and hyphens in dot-joined labels; two or more labels.

    The last label must contain a letter and must not be ``0x`` followed by hex digits (or
    none): a browser reads a host ending in a number, as ``127.0.0.0x1`` does, as an IPv4
    address. That refuses dotted-decimal, octal and integer spellings, a trailing hex number
    and a single-label host. A host the rule cannot spell (IPv6, ``[`` or a character outside
    the set) fails on the character set.
    """
    labels = host.split(".")
    return (
        len(labels) >= 2
        and all(label and _HOST_CHARS.issuperset(label) for label in labels)
        and any(ch.isalpha() for ch in labels[-1])
        and _HEX_NUMBER.fullmatch(labels[-1]) is None
    )


def _usable_link(link: str) -> bool:
    """A short http(s) link whose host is a DNS name and whose port parses.

    A backslash, ``@``, ``%`` or ``[`` or a non-ASCII character in the authority is refused: Python
    and a browser read the host of such a link differently.
    """
    if len(link) > LINK_LIMIT or not link.lower().startswith(("http://", "https://")):
        return False
    try:
        parts = urlsplit(link)
        if not parts.netloc.isascii() or any(c in parts.netloc for c in "\\@%["):
            return False
        return _dns_name(parts.hostname or "") and (parts.port is None or parts.port > 0)
    except ValueError:
        return False


def _make(title: str, link: str, date: datetime | None, summary: Callable[[], str]) -> Entry | None:
    if not title or not _usable_link(link):
        return None
    return Entry(title, link, date, _summary(summary()))


def _rss_entry(item: _Node) -> Entry | None:
    pub = _text(item, "pubDate")
    date = _rss_date(pub) if pub else None
    return _make(
        _title(_text(item, "title")),
        _text(item, "link"),
        date,
        lambda: _strip_markup(_text(item, "description")),
    )


def _atom_text(entry: _Node, key: str) -> str:
    # R18. An Atom text construct (RFC 4287, 3.1.1) says what it holds: type "html" is escaped
    # HTML and "xhtml" is child elements (rebuilt as markup by the tree builder), so both go
    # through the text-only stripper; no type, or "text", is literal text and is not stripped.
    # RSS differs: a title is literal and a description is HTML.
    kind, text = entry.fields.get(key, _NO_FIELD)
    return _strip_markup(text) if kind else text


def _atom_entry(entry: _Node) -> Entry | None:
    stamp = _text(entry, "published") or _text(entry, "updated")
    date = _iso_date(stamp) if stamp else None
    return _make(
        _title(_atom_text(entry, "title")),
        entry.link or "",
        date,
        lambda: _atom_text(entry, "summary"),
    )


def _entries(root: _Node) -> list[Entry]:
    if root.kind == "rss":
        found = (_rss_entry(item) for channel in root.children for item in channel.children)
    elif root.kind == "feed":
        found = (_atom_entry(entry) for entry in root.children)
    else:
        raise FeedError("document is neither an RSS 2.0 nor an Atom feed")
    return [entry for entry in found if entry is not None]


def parse_feed(body: bytes) -> list[Entry]:
    """Return the readable entries of an RSS 2.0 or Atom feed, in feed order.

    R26: anything but bytes, bytearray or memoryview (the predecessor's byte search accepted
    these; the annotation stays ``bytes``, as its was) is a TypeError, before the size check: a str is measured in characters, not
    in the bytes expat would encode it to.
    """
    if not isinstance(body, bytes | bytearray | memoryview):
        raise TypeError("feed body must be bytes")
    if memoryview(body).nbytes > MAX_BYTES:
        raise FeedError("feed is larger than 2 MiB")
    try:
        root = _read_xml(body)
    except expat.ExpatError as exc:
        raise FeedError("feed is not valid XML") from exc
    except FeedError:
        raise
    except (ValueError, LookupError) as exc:
        detail = str(exc)[:ERROR_TEXT_LIMIT]
        raise FeedError(f"feed uses an unsupported text encoding ({detail})") from exc
    return _entries(root)
