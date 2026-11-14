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
from html import escape, unescape
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
# R31. Total characters of element and attribute names as the feed spells them (prefix and colon
# included, one count per occurrence). pyexpat keeps every distinct name for the whole parse, and
# a Python string holds at most 4 bytes a character, so this bounds the name table to about
# 4 MiB of text. Names are the body's own characters, so the total cannot exceed the body; this
# is the share of a feed that names may take. A feed of 1,000 entries of 100 XHTML elements
# has about 0.2 million; a name-only flood has all of it.
MAX_NAME_CHARS = 1024 * 1024
# R31. Longest namespace URI declared. The parser resolves prefixes itself and never joins a
# URI to a name, so a URI costs only its own characters; real namespace URIs are under 100.
MAX_NAMESPACE_CHARS = 2048
# R37. The most characters html.parser may hold unparsed (a tag, comment or reference that is
# still open, or the content of script, style, textarea and the like); beyond it the construct
# is released (see _Markup). Text reaches html.parser _FEED_CHARS at a time, so it never parses
# more than MAX_HELD_CHARS + _FEED_CHARS = 4,096 characters at once: a tag of at most about
# 2,048 attributes (html.parser keeps about 280 bytes for each), and a character reference of
# fewer digits than the 4,300 int() reads.
MAX_HELD_CHARS = 2048
_FEED_CHARS = 2048
TITLE_LIMIT = 500
LINK_LIMIT = 2048
# R37. Longest date read, blanks at either end not counted; a longer one is no date.
DATE_LIMIT = 256
# R37. Bytes handed to expat per call, so no character-data callback carries more than this.
_XML_CHUNK = 16384
ERROR_TEXT_LIMIT = 120
_HOST_CHARS = frozenset(string.ascii_letters + string.digits + "-")
_HEX_NUMBER = re.compile(r"0x[0-9a-f]*", re.ASCII | re.IGNORECASE)


_DTD_MESSAGE = "feed declares a DTD or entities"
_NOT_XML = "feed is not valid XML"
_NOT_NAME_START = frozenset("-.0123456789\u00b7\u203f\u2040")
_XML_NAMESPACE = "http://www.w3.org/XML/1998/namespace"
_XMLNS_NAMESPACE = "http://www.w3.org/2000/xmlns/"


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
    An item or entry keeps, for each field read from it, the text its sink made of everything
    below it in ``fields``, and, for an Atom entry, the href of its first alternate link in
    ``link``.
    """

    kind: str
    children: list["_Node"] = field(default_factory=list)
    fields: dict[str, str] = field(default_factory=dict)
    link: str | None = None


@dataclass(eq=False, slots=True)
class _Field:
    """The field being read: where its text goes as it arrives (R37: no field is kept whole)."""

    owner: _Node
    key: str
    markup: bool  # Atom xhtml: the text is the rebuilt markup, in order
    sink: "_Fold | _Markup | _Head"


# R24: the tree keeps only what parse_feed reads. R31: an element is named by its namespace URI
# and local name, as a pair that is looked up and never joined into one string; "" is no
# namespace.
_ATOM = "http://www.w3.org/2005/Atom"
_ROOTS = {("", "rss"): "rss", (_ATOM, "feed"): "feed"}
_CHILD = {
    "rss": (("", "channel"), "channel"),
    "channel": (("", "item"), "item"),
    "feed": ((_ATOM, "entry"), "entry"),
}
_FIELD_KEYS = {
    "item": {("", key): key for key in ("title", "link", "pubDate", "description")},
    "entry": {(_ATOM, key): key for key in ("published", "updated", "title", "summary", "link")},
}
_SLICE = 4096
_TEXT_CONSTRUCTS = ("title", "summary")


def _xhtml_tag(local: str) -> str | None:
    """The tag written for an element inside Atom xhtml, or None: the element's text only."""
    if len(local) > _LONGEST_TAG or not local.isascii():
        return None
    local = local.lower()
    return local if local in _XHTML_TAGS else None


class _Scope:
    """The namespace prefixes bound at the current element (XML Namespaces 1.0).

    ``""`` is the default namespace, which applies to elements and not to attributes. Each
    prefix keeps a stack of its URIs, so entering and leaving an element costs only the
    declarations it makes. ``xml`` is always bound.
    """

    def __init__(self) -> None:
        self._bound: dict[str, list[str]] = {}

    def declare(self, prefix: str, uri: str) -> bool:
        """Bind ``prefix``; False if the declaration is ``xmlns:xml``, which binds nothing new."""
        if len(uri) > MAX_NAMESPACE_CHARS:
            message = f"feed has a namespace URI of more than {MAX_NAMESPACE_CHARS} characters"
            raise FeedError(message)
        if prefix == "xml":
            if uri != _XML_NAMESPACE:
                raise FeedError(_NOT_XML)
            return False
        # Reserved names, and a prefix bound to no URI, are errors in XML Namespaces 1.0.
        if prefix == "xmlns" or uri in (_XML_NAMESPACE, _XMLNS_NAMESPACE) or (prefix and not uri):
            raise FeedError(_NOT_XML)
        self._bound.setdefault(prefix, []).append(uri)
        return True

    def leave(self, prefix: str) -> None:
        uris = self._bound[prefix]
        uris.pop()
        if not uris:
            del self._bound[prefix]

    def uri(self, prefix: str) -> str:
        """The URI bound to ``prefix`` here; an unbound prefix is an error, an unbound default is
        no namespace."""
        if prefix == "xml":
            return _XML_NAMESPACE
        uris = self._bound.get(prefix)
        if uris:
            return uris[-1]
        if prefix:
            raise FeedError(_NOT_XML)
        return ""


def _split(name: str) -> tuple[str, str]:
    """(prefix, local part) of a name; no colon is no prefix.

    A name with a colon first or last, with two, or whose local part starts with a character
    that is a name character but not a name-start character, is not a qualified name (XML
    Namespaces 1.0): expat in namespace mode refused it.
    """
    prefix, colon, local = name.partition(":")
    if not colon:
        return "", name
    if not prefix or not local or ":" in local or _name_continues_only(local[0]):
        raise FeedError(_NOT_XML)
    return prefix, local


def _name_continues_only(char: str) -> bool:
    """A character XML allows inside a name but not at its start."""
    return char in _NOT_NAME_START or "\u0300" <= char <= "\u036f"


class _TreeBuilder:
    """Builds a _Node tree from expat events; comments and processing instructions are dropped.

    ``document`` is a nameless parent of the root element. Every element is counted and its
    depth checked; only those parse_feed reads become nodes. Elements inside a field add their
    text to the field (R24: no node per element). Namespaces are resolved here (R31): expat is
    not told to expand names, so it builds no name longer than the one in the feed.
    """

    def __init__(self) -> None:
        self.document = _Node("document")
        # One entry per open element: its node or field, the closing tag to write for an xhtml
        # element, or None for an element that is not kept.
        self._open: list[_Node | _Field | str | None] = []
        # Parallel to _open: the prefixes the element declared, to unbind when it closes.
        self._declared: list[tuple[str, ...]] = []
        self._scope = _Scope()
        self._field: _Field | None = None
        self._elements = 0
        self._name_chars = 0

    def start(self, name: str, attrs: dict[str, str]) -> None:
        if len(self._open) >= MAX_DEPTH:
            raise FeedError(f"feed is nested deeper than {MAX_DEPTH} elements")
        self._elements += 1
        if self._elements > MAX_ELEMENTS:
            raise FeedError(f"feed has more than {MAX_ELEMENTS} elements")
        self._name_chars += len(name) + sum(map(len, attrs))
        if self._name_chars > MAX_NAME_CHARS:
            raise FeedError("feed element names are too long")
        self._declared.append(self._bind(attrs) if attrs else ())
        prefix, local = _split(name)
        self._open.append(self._enter(self._scope.uri(prefix), local, attrs))

    def _bind(self, attrs: dict[str, str]) -> tuple[str, ...]:
        """Bind the element's namespace declarations, then check its other attributes.

        The declarations are not attributes (they are not counted against MAX_ATTRIBUTES), and
        an attribute with a prefix must have a bound one and, with its URI, be unique on the
        element. An attribute with no prefix is in no namespace, whatever the default is.
        """
        declared: list[str] = []
        prefixed: list[tuple[str, str]] = []
        count = 0
        for key, value in attrs.items():
            prefix, local = _split(key)
            if key == "xmlns" or prefix == "xmlns":
                count += 1
                bound = local if prefix else ""
                if self._scope.declare(bound, value):
                    declared.append(bound)
            elif prefix:
                prefixed.append((prefix, local))
        if len(attrs) - count > MAX_ATTRIBUTES:
            raise FeedError(f"feed has an element with more than {MAX_ATTRIBUTES} attributes")
        self._check_prefixed(prefixed)
        return tuple(declared)

    def _check_prefixed(self, names: list[tuple[str, str]]) -> None:
        seen = set()
        for prefix, local in names:
            expanded = (self._scope.uri(prefix), local)
            if expanded in seen:
                raise FeedError(_NOT_XML)
            seen.add(expanded)

    def _enter(self, uri: str, local: str, attrs: dict[str, str]) -> _Node | _Field | str | None:
        if self._field is not None:
            return self._enter_field_content(self._field, local)
        parent = self._open[-1] if self._open else self.document
        if not isinstance(parent, _Node):
            return None
        if parent.kind == "document":
            return self._attach(parent, _Node(_ROOTS.get((uri, local), "other")))
        keys = _FIELD_KEYS.get(parent.kind)
        if keys is not None:
            return self._enter_field(parent, keys.get((uri, local)), attrs)
        wanted = _CHILD.get(parent.kind)
        if wanted is not None and wanted[0] == (uri, local):
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
                record.link = _Head.of(attrs.get("href") or "", LINK_LIMIT)
            return None
        if key in record.fields:  # the first of two fields of a name wins
            return None
        kind = attrs.get("type", "") if record.kind == "entry" and key in _TEXT_CONSTRUCTS else ""
        kind = kind if kind in ("html", "xhtml") else ""
        self._field = _Field(record, key, kind == "xhtml", _sink(key, kind))
        return self._field

    @staticmethod
    def _enter_field_content(current: _Field, local: str) -> str | None:
        if not current.markup:
            return None
        tag = _xhtml_tag(local)
        if tag is None:
            return None
        current.sink.add(_OPEN_TAG[tag])
        return _CLOSE_TAG[tag]

    def end(self, name: str) -> None:
        for prefix in self._declared.pop():
            self._scope.leave(prefix)
        top = self._open.pop()
        if isinstance(top, str) and self._field is not None:
            self._field.sink.add(top)
        elif isinstance(top, _Field):
            top.owner.fields[top.key] = top.sink.value()
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
            self._field.sink.add(escape(text, quote=False) if self._field.markup else text)


def _new_parser(builder: _TreeBuilder) -> expat.XMLParserType:
    parser = expat.ParserCreate()
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
    parser = _new_parser(builder)
    view = memoryview(body).cast("B")
    for start in range(0, len(view), _XML_CHUNK):
        parser.Parse(view[start : start + _XML_CHUNK], False)
    # The last call raises ExpatError unless the body holds exactly one root element.
    parser.Parse(b"", True)
    return builder.document.children[0]


@dataclass(frozen=True)
class Entry:
    title: str
    link: str
    published: datetime | None
    summary: str


def _plain(raw: str) -> str:
    """Control and format characters dropped (white space is kept for the caller to fold)."""
    return "".join(ch for ch in raw if ch.isspace() or unicodedata.category(ch) not in ("Cc", "Cf"))


class _Fold:
    """The first ``limit`` characters of ``" ".join(_plain(text).split())``, text given in pieces.

    R24/R37. Cleaning goes a slice at a time and stops once ``limit`` characters of folded text
    exist, so it holds at most one slice and ``limit`` characters, however long the field. The
    result is exact: a character is dropped or kept on its own, and a word that ends a piece is
    joined to the next piece.
    """

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.words: list[str] = []
        self.size = 0  # characters in " ".join(words), plus one
        self.word = ""  # the last word read, which the next piece may continue

    @property
    def full(self) -> bool:
        return self.size + len(self.word) > self.limit

    def add(self, text: str) -> None:
        for start in range(0, len(text), _SLICE):
            if self.full:
                return
            chunk = self.word + _plain(text[start : start + _SLICE])
            found = chunk.split()
            self.word = found.pop() if found and not chunk[-1].isspace() else ""
            self.words.extend(found)
            self.size += sum(len(w) + 1 for w in found)

    def value(self) -> str:
        return " ".join([*self.words, self.word] if self.word else self.words)[: self.limit]


class _Head:
    """A field's text with blanks at either end removed, or "" if that is more than ``limit``.

    R37. Only ``limit`` characters are kept; text after them only says whether there is more.
    """

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.kept: list[str] = []
        self.size = 0
        self.over = False

    @classmethod
    def of(cls, text: str, limit: int) -> str:
        head = cls(limit)
        for start in range(0, len(text), _SLICE):
            head.add(text[start : start + _SLICE])
        return head.value()

    def add(self, text: str) -> None:
        if self.over:
            return
        if not self.kept:
            text = text.lstrip()
        room = self.limit - self.size
        if text and room > 0:
            self.kept.append(text[:room])
            self.size += min(room, len(text))
            text = text[room:]
        if text and not text.isspace():
            self.over = True

    def value(self) -> str:
        return "" if self.over else "".join(self.kept).rstrip()


class _Enough(Exception):
    """Raised inside html.parser once the field has all the text its entry can use."""


# What ends a construct html.parser held too long: a comment ends at "-->" or "--!>", a CDATA
# section at "]]>", anything else (a tag, a declaration, an instruction) at the next ">".
_CONSTRUCT_ENDS = (("<!--", re.compile("--!?>")), ("<![CDATA[", re.compile(r"\]\]>")))
_NEXT_GT = re.compile(">")


class _Markup(HTMLParser):
    """The text of an HTML field, read as it arrives into a _Fold (R17, R18, R20, R37).

    html.parser is given ``_FEED_CHARS`` at a time and stopped once the fold is full. What it
    holds unparsed never passes MAX_HELD_CHARS after a step; a part held longer is released by
    its kind: (a) the content of script, style, textarea and the like is read up to the
    characters that could begin its end tag (decoded, and never cut inside a reference, for
    textarea and title); (b) held text ends at a character reference html.parser waits to see
    whole, and no reference holds an ``&``, so everything before the last one is read; (c) a held
    tag, comment or declaration is dropped, read as one space, and the input skipped to its end
    (see _CONSTRUCT_ENDS), so nothing after it joins what came before. A tag that is open past
    the limit therefore ends at the next ``>``, even one inside a quoted value. ``rawdata``,
    ``cdata_elem`` and ``goahead`` are html.parser's (CPython 3.12.14); the tests pin each
    release path against html.parser itself.
    """

    def __init__(self, limit: int, *, strip: bool = False) -> None:
        super().__init__(convert_charrefs=True)
        self.text = _Fold(limit)
        self._strip = strip  # an RSS description is read with blanks at its ends removed
        self._skip = 0
        self._until: re.Pattern[str] | None = None  # the end of the construct being skipped
        self._tail = ""  # the last characters seen of it, in case its end spans two pieces
        self._done = False
        self._out: list[str] = []
        self._out_size = 0

    def add(self, data: str) -> None:
        for start in range(0, len(data), _FEED_CHARS):
            if self._done:
                return
            self._read(data[start : start + _FEED_CHARS])

    def value(self) -> str:
        if not self._done and self._until is None:
            if self._strip:
                self.rawdata = self.rawdata.rstrip()
            self._guarded(self.close)
        if not self._done:
            self._guarded(self._flush)
        return self.text.value()

    def _read(self, piece: str) -> None:
        if self._until is not None:
            piece = self._past_end(self._until, piece)
        if piece:
            self.rawdata += piece
            self._guarded(self._parse)

    def _guarded(self, step: Callable[[], None]) -> None:
        try:
            step()
        except _Enough:
            # The only use of this exception: the fold is full and the rest cannot matter.
            self._done = True
        except AssertionError as exc:
            # Standard libraries before the 2025 html.parser fixes assert on some markup (R20).
            raise FeedError("feed text could not be read") from exc

    def _parse(self) -> None:
        self.goahead(False)
        while len(self.rawdata) > MAX_HELD_CHARS:
            self._release(self.rawdata)

    def _release(self, held: str) -> None:
        if self.cdata_elem:
            self._release_content(held, self.cdata_elem)
        elif held.startswith("<"):
            self._release_construct(held)
        else:
            amp = held.rfind("&")
            cut = amp if amp > 0 else len(held)
            self.rawdata = held[cut:]
            self.handle_data(unescape(held[:cut]))

    def _release_content(self, held: str, element: str) -> None:
        # Keep what could begin the end tag ("</" and the name); in textarea and title, whose
        # references html.parser decodes, do not cut a reference in two.
        cut = len(held) - len(element) - 2
        decoded = element in ("textarea", "title")  # html.parser's RCDATA content elements
        if decoded and "&" in held[cut - 34 : cut]:
            cut = held.rfind("&", 0, cut)
        self.rawdata = held[cut:]
        self.handle_data(unescape(held[:cut]) if decoded else held[:cut])

    def _release_construct(self, held: str) -> None:
        self.rawdata = ""
        self._add(" ")
        ends = (end for start, end in _CONSTRUCT_ENDS if held.startswith(start))
        self._until = next(ends, _NEXT_GT)
        rest = self._past_end(self._until, held[1:])
        if rest:
            self.rawdata = rest
            self.goahead(False)

    def _past_end(self, until: re.Pattern[str], piece: str) -> str:
        """What follows the end of the construct being skipped, or "" if it has not ended."""
        text = self._tail + piece
        found = until.search(text)
        if found is None:
            self._tail = text[-3:]
            return ""
        self._until, self._tail = None, ""
        return text[found.end() :]

    def _add(self, text: str) -> None:
        # Pieces are gathered up to a slice before folding: a block tag is one space each.
        self._out.append(text)
        self._out_size += len(text)
        if self._out_size >= _SLICE:
            self._flush()

    def _flush(self) -> None:
        self.text.add("".join(self._out))
        self._out.clear()
        self._out_size = 0
        if self.text.full:
            raise _Enough

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style"):
            self._skip += 1
        elif tag in _BLOCKS:
            self._add(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self._skip:
            self._skip -= 1
        elif tag in _BLOCKS:
            self._add(" ")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self._add(data)


def _sink(key: str, kind: str) -> _Fold | _Markup | _Head:
    """Where a field's text goes (R18: an Atom html or xhtml text construct is markup; an RSS
    description is markup; an RSS title or an Atom text construct of no type is literal)."""
    if key == "link":
        return _Head(LINK_LIMIT)
    if key in ("pubDate", "published", "updated"):
        return _Head(DATE_LIMIT)
    limit = TITLE_LIMIT if key == "title" else SUMMARY_LIMIT + 1
    if key == "description":
        return _Markup(limit, strip=True)
    return _Markup(limit) if kind else _Fold(limit)


def _summary(head: str) -> str:
    """The folded head (SUMMARY_LIMIT + 1 characters at most) cut to SUMMARY_LIMIT on a word
    boundary."""
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
    return record.fields.get(key, "")


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


def _make(title: str, link: str, date: datetime | None, summary: str) -> Entry | None:
    # R8b: a title is stripped again after the 500-character cut.
    title = title.strip()
    if not title or not _usable_link(link):
        return None
    return Entry(title, link, date, _summary(summary))


def _rss_entry(item: _Node) -> Entry | None:
    pub = _text(item, "pubDate")
    date = _rss_date(pub) if pub else None
    return _make(_text(item, "title"), _text(item, "link"), date, _text(item, "description"))


def _atom_entry(entry: _Node) -> Entry | None:
    stamp = _text(entry, "published") or _text(entry, "updated")
    date = _iso_date(stamp) if stamp else None
    return _make(_text(entry, "title"), entry.link or "", date, _text(entry, "summary"))


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

    R26/R31: anything but bytes, bytearray or a contiguous memoryview of bytes (format "B"; the
    predecessor's byte search accepted these; the annotation stays ``bytes``, as its was) is a
    TypeError, before the size check: a str is measured in characters, not in the bytes expat
    would encode it to.
    """
    if not isinstance(body, bytes | bytearray | memoryview):
        raise TypeError("feed body must be bytes")
    if isinstance(body, memoryview) and not (body.contiguous and body.format == "B"):
        raise TypeError("feed body must be contiguous bytes")
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
