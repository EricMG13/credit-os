"""Parse RSS 2.0 and Atom feed bytes into entries. Standard library only.

Feed bytes are untrusted. The XML is read with ``xml.parsers.expat`` directly, and a document
type declaration, any entity declaration and any external entity reference are refused, so no
entity is ever defined, expanded or fetched. No article body is fetched; only the feed's own
title, link, date and summary are read.
"""

import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from typing import NoReturn
from urllib.parse import urlsplit
from xml.parsers import expat

SUMMARY_LIMIT = 300
_ATOM = "{http://www.w3.org/2005/Atom}"
_DTD = re.compile(rb"<!(DOCTYPE|ENTITY)", re.IGNORECASE)


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
        """All text below this element, in document order (iterative: nesting is unbounded)."""
        parts: list[str] = []
        stack: list[Iterator[str | _Node]] = [iter(self.content)]
        while stack:
            for item in stack[-1]:
                if isinstance(item, str):
                    parts.append(item)
                else:
                    stack.append(iter(item.content))
                    break
            else:
                stack.pop()
        return "".join(parts)


def _qualified(name: str) -> str:
    # expat, given "}" as namespace separator, reports "uri}local"; spell it "{uri}local".
    return "{" + name if "}" in name else name


class _TreeBuilder:
    """Builds a _Node tree from expat events; comments and processing instructions are dropped."""

    def __init__(self) -> None:
        self.root: _Node | None = None
        self._open: list[_Node] = []

    def start(self, name: str, attrs: dict[str, str]) -> None:
        node = _Node(_qualified(name), {_qualified(k): v for k, v in attrs.items()})
        if self._open:
            self._open[-1].children.append(node)
            self._open[-1].content.append(node)
        elif self.root is None:
            self.root = node
        self._open.append(node)

    def end(self, name: str) -> None:
        self._open.pop()

    def data(self, text: str) -> None:
        if self._open:
            self._open[-1].content.append(text)


def _read_xml(body: bytes) -> _Node:
    builder = _TreeBuilder()
    parser = expat.ParserCreate(None, "}")
    parser.buffer_text = True
    parser.StartElementHandler = builder.start
    parser.EndElementHandler = builder.end
    parser.CharacterDataHandler = builder.data
    # No DTD of any kind is accepted. A DTD in UTF-16 or UTF-32 bytes passes the byte search in
    # parse_feed, so the parser itself refuses it; the entity and external-entity handlers
    # cover what a declaration could still reach.
    parser.StartDoctypeDeclHandler = _refuse
    parser.EntityDeclHandler = _refuse
    parser.ExternalEntityRefHandler = _refuse
    parser.UnparsedEntityDeclHandler = _refuse
    parser.NotationDeclHandler = _refuse
    parser.Parse(body, True)
    if builder.root is None:
        raise expat.ExpatError("no element found")
    return builder.root


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

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)


def _summary(raw: str) -> str:
    parser = _TextOnly()
    parser.feed(raw)
    parser.close()
    text = " ".join("".join(parser.parts).split())
    if len(text) <= SUMMARY_LIMIT:
        return text
    head = text[: SUMMARY_LIMIT + 1]
    if " " not in head:
        return text[:SUMMARY_LIMIT]
    return head.rsplit(" ", 1)[0].rstrip()


def _utc(moment: datetime) -> datetime:
    # A date with no zone is read as UTC.
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


def _iso_date(text: str) -> datetime | None:
    try:
        return _utc(datetime.fromisoformat(text.strip()))
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


def _usable_link(link: str) -> bool:
    """An http(s) link whose host is present and whose port, if any, parses."""
    if not link.lower().startswith(("http://", "https://")):
        return False
    try:
        parts = urlsplit(link)
        return bool(parts.hostname) and (parts.port is None or parts.port > 0)
    except ValueError:
        return False


def _make(title: str, link: str, date: datetime | None, summary: str) -> Entry | None:
    if not title or not _usable_link(link):
        return None
    return Entry(title, link, date, _summary(summary))


def _rss_entry(item: _Node) -> Entry | None:
    pub = _text(item, "pubDate")
    date = _rss_date(pub) if pub else None
    return _make(
        " ".join(_text(item, "title").split()),
        _text(item, "link"),
        date,
        _text(item, "description"),
    )


def _atom_link(entry: _Node) -> str:
    for link in entry.children_named(f"{_ATOM}link"):
        if link.attrib.get("rel") in (None, "alternate"):
            return (link.attrib.get("href") or "").strip()
    return ""


def _atom_entry(entry: _Node) -> Entry | None:
    stamp = _text(entry, f"{_ATOM}published") or _text(entry, f"{_ATOM}updated")
    date = _iso_date(stamp) if stamp else None
    return _make(
        " ".join(_text(entry, f"{_ATOM}title").split()),
        _atom_link(entry),
        date,
        _text(entry, f"{_ATOM}summary"),
    )


def parse_feed(body: bytes) -> list[Entry]:
    """Return the readable entries of an RSS 2.0 or Atom feed, in feed order."""
    if _DTD.search(body):
        raise FeedError(_DTD_MESSAGE)
    try:
        root = _read_xml(body)
    except expat.ExpatError as exc:
        raise FeedError("feed is not valid XML") from exc
    except FeedError:
        raise
    except (ValueError, LookupError) as exc:
        raise FeedError(f"feed uses an unsupported text encoding ({exc})") from exc
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
