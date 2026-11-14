"""Parse RSS 2.0 and Atom feed bytes into entries. Standard library only.

Feed bytes are untrusted. The XML is read with ``xml.parsers.expat`` directly, and a document
type declaration, any entity declaration and any external entity reference are refused, so no
entity is ever defined, expanded or fetched. No article body is fetched; only the feed's own
title, link, date and summary are read.
"""

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
TITLE_LIMIT = 500
LINK_LIMIT = 2048
ERROR_TEXT_LIMIT = 120
_ATOM = "{http://www.w3.org/2005/Atom}"
_HOST_CHARS = frozenset(string.ascii_letters + string.digits + "-")


_DTD_MESSAGE = "feed declares a DTD or entities"


class FeedError(ValueError):
    """The feed cannot be read; the message is shown to the owner."""


def _refuse(*_args: object) -> NoReturn:
    raise FeedError(_DTD_MESSAGE)


@dataclass(eq=False)
class _Node:
    """One element: its tag, attributes, child elements and its text and children in order."""

    tag: str
    attrib: dict[str, str]
    children: list["_Node"] = field(default_factory=list)
    content: list["str | _Node"] = field(default_factory=list)

    def child(self, tag: str) -> "_Node | None":
        return next((c for c in self.children if c.tag == tag), None)

    def children_named(self, tag: str) -> list["_Node"]:
        return [c for c in self.children if c.tag == tag]

    def text(self) -> str:
        """All text below this element, in document order (nesting is capped at MAX_DEPTH)."""
        return "".join(i if isinstance(i, str) else i.text() for i in self.content)

    def inner_html(self) -> str:
        """The content as HTML: element names without attributes, text escaped."""
        return "".join(
            escape(i, quote=False) if isinstance(i, str) else i.html() for i in self.content
        )

    def html(self) -> str:
        name = self.tag.rsplit("}", 1)[-1]
        return f"<{name}>{self.inner_html()}</{name}>"


def _qualified(name: str) -> str:
    # expat, given "}" as namespace separator, reports "uri}local"; spell it "{uri}local".
    return "{" + name if "}" in name else name


class _TreeBuilder:
    """Builds a _Node tree from expat events; comments and processing instructions are dropped.

    ``document`` is a nameless parent of the root element, so every element has a parent.
    """

    def __init__(self) -> None:
        self.document = _Node("", {})
        self._open: list[_Node] = [self.document]

    def start(self, name: str, attrs: dict[str, str]) -> None:
        if len(self._open) > MAX_DEPTH:
            raise FeedError(f"feed is nested deeper than {MAX_DEPTH} elements")
        node = _Node(_qualified(name), {_qualified(k): v for k, v in attrs.items()})
        self._open[-1].children.append(node)
        self._open[-1].content.append(node)
        self._open.append(node)

    def end(self, name: str) -> None:
        self._open.pop()

    def data(self, text: str) -> None:
        self._open[-1].content.append(text)


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


# R17: a block-level element starts and ends a new run of text, so adjacent blocks never fuse.
_BLOCKS = frozenset(
    (
        *("p", "br", "div", "li", "ul", "ol", "dl", "dt", "dd", "table", "tr", "td", "th"),
        *("thead", "tbody", "tfoot", "caption", "h1", "h2", "h3", "h4", "h5", "h6"),
        *("blockquote", "pre", "hr", "section", "article", "header", "footer", "figure"),
        "figcaption",
    )
)


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


def _strip_markup(raw: str) -> str:
    """The text of an HTML fragment, markup removed and character references decoded."""
    parser = _TextOnly()
    try:
        parser.feed(raw)
        parser.close()
    except AssertionError as exc:
        # Standard libraries before the 2025 html.parser fixes assert on some markup (R20).
        raise FeedError("feed text could not be read") from exc
    return "".join(parser.parts)


def _plain(raw: str) -> str:
    """Control and format characters dropped (white space is kept for the caller to fold)."""
    return "".join(ch for ch in raw if ch.isspace() or unicodedata.category(ch) not in ("Cc", "Cf"))


def _summary(text: str) -> str:
    """Plain text folded to single spaces, then cut to SUMMARY_LIMIT on a word boundary."""
    folded = " ".join(_plain(text).split())
    if len(folded) <= SUMMARY_LIMIT:
        return folded
    head = folded[: SUMMARY_LIMIT + 1]
    if " " not in head:
        return folded[:SUMMARY_LIMIT]
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


def _text(parent: _Node, tag: str) -> str:
    child = parent.child(tag)
    return child.text().strip() if child is not None else ""


def _title(text: str) -> str:
    """Plain text with control and format characters dropped, folded, cut, then stripped."""
    return " ".join(_plain(text).split())[:TITLE_LIMIT].strip()


def _dns_name(host: str) -> bool:
    """ASCII letters, digits and hyphens in dot-joined labels; two or more, the last with a letter.

    This refuses every spelling of an IP address (dotted, hex, octal, integer, IPv6) and a
    single-label host.
    """
    labels = host.split(".")
    return (
        len(labels) >= 2
        and all(label and _HOST_CHARS.issuperset(label) for label in labels)
        and any(ch.isalpha() for ch in labels[-1])
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


def _atom_link(entry: _Node) -> str:
    for link in entry.children_named(f"{_ATOM}link"):
        if link.attrib.get("rel") in (None, "alternate"):
            return (link.attrib.get("href") or "").strip()
    return ""


def _atom_text(entry: _Node, name: str) -> str:
    # R18. An Atom text construct (RFC 4287, 3.1.1) says what it holds: type "html" is escaped
    # HTML and "xhtml" is child elements, so both go through the text-only stripper; no type, or
    # "text", is literal text and is not stripped. RSS differs: a title is literal and a
    # description is HTML.
    node = entry.child(f"{_ATOM}{name}")
    if node is None:
        return ""
    kind = node.attrib.get("type")
    if kind == "html":
        return _strip_markup(node.text())
    if kind == "xhtml":
        return _strip_markup(node.inner_html())
    return node.text()


def _atom_entry(entry: _Node) -> Entry | None:
    stamp = _text(entry, f"{_ATOM}published") or _text(entry, f"{_ATOM}updated")
    date = _iso_date(stamp) if stamp else None
    return _make(
        _title(_atom_text(entry, "title")),
        _atom_link(entry),
        date,
        lambda: _atom_text(entry, "summary"),
    )


def _entries(root: _Node) -> list[Entry]:
    if root.tag == "rss":
        found = (
            _rss_entry(item)
            for channel in root.children_named("channel")
            for item in channel.children_named("item")
        )
    elif root.tag == f"{_ATOM}feed":
        found = (_atom_entry(entry) for entry in root.children_named(f"{_ATOM}entry"))
    else:
        raise FeedError("document is neither an RSS 2.0 nor an Atom feed")
    return [entry for entry in found if entry is not None]


def parse_feed(body: bytes) -> list[Entry]:
    """Return the readable entries of an RSS 2.0 or Atom feed, in feed order."""
    if len(body) > MAX_BYTES:
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
