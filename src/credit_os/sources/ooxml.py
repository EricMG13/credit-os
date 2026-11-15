"""The OOXML guards: a checked zip package, the bytes of its parts in pieces, and XML parts read
through a bounded parser.

Zip half: every failure of the standard library on a bad zip becomes a `SourceUnreadable` that
names the file, and the part where one is meant, and chains its cause.

XML half (`Package.parse`): a part is never held whole. Each piece is checked on its bytes (a NUL
byte, a DOCTYPE or ENTITY declaration, an unfinished markup token over `MAX_TOKEN_BYTES`) and
decoded as UTF-8 before the parser is given it. Expat's own DOCTYPE handler is a second guard
behind the byte search. Expat reads names as written, with no namespace processing: the shape
binds the namespaces itself, after measuring each tag's declarations, and measures the depth, the
length and count of different names (namespace names included) and the namespace declarations
open at once as elements arrive. Expat's reparse deferral is left on and its allocation tracker is
set explicitly. Only `xml.parsers.expat` is used.

Limits are module constants read at call time; a test lowers one with `monkeypatch`.
"""

import codecs
import io
import re
import struct
import unicodedata
import warnings
import zipfile
import zlib
from collections.abc import Iterator
from typing import Protocol, cast
from xml.parsers import expat

from credit_os.sources.errors import SourceUnreadable, shown_name

# The sum of the declared sizes and the bytes actually expanded may not pass this.
MAX_EXPANDED_BYTES = 209_715_200
# zipfile makes an object per member before any member can be counted.
MAX_MEMBERS = 16_384
# zipfile copies the whole central directory and keeps every name, extra field and comment in it
# while the package lives.
MAX_DIRECTORY_BYTES = 4_194_304
# The most of a part held at once.
CHUNK_BYTES = 65_536
# expat keeps one unfinished markup token whole and makes every attribute of a start tag before any
# handler runs: up to 26 times this, 13.1 MiB (tracemalloc, macOS). No real-file evidence bounds
# this either way: a part with a longer tag is refused whole.
MAX_TOKEN_BYTES = 524_288
# expat keeps each open element's name, and the shape its name and bindings: 0.4 to 1.2 MiB at
# this depth with names at the cap, 0.9 MiB with 4,096 declarations open.
MAX_DEPTH = 256
# expat keeps every element and attribute name as written; the shape keeps every name as it binds
# it (`uri}local}prefix`), every `xmlns:` prefix name and every namespace name. The same cap holds
# the namespace declarations open at once.
MAX_NAMES = 4_096
# the shape binds every name on every tag; a name as written is never longer than the name
# counted. With MAX_NAMES it bounds the UTF-8 bytes of all names, namespace names included, to
# 255 x 4,096. OOXML's names are ASCII, under about 110 bytes.
MAX_NAME_LENGTH = 255
# expat's allocation tracker, set here and not left to the bundled expat (its documented defaults).
EXPAT_THRESHOLD = 67_108_864
EXPAT_AMPLIFICATION = 100.0

_OLE_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_LOCAL_SIGNATURE = b"PK\x03\x04"
_DIRECTORY_SIGNATURE = b"PK\x01\x02"
_END_SIGNATURE = b"PK\x05\x06"
_LOCATOR_SIGNATURE = b"PK\x06\x07"
_RECORD64_SIGNATURE = b"PK\x06\x06"
_END_SIZE = 22
_LOCATOR_SIZE = 20
_RECORD64_SIZE = 56
_MAX_COMMENT = 65_535
_STORED = 0
_DEFLATED = 8
_DECLARATION = re.compile(rb"<!(?:DOCTYPE|ENTITY)", re.IGNORECASE)
_DECLARATION_TAIL = 8
# One whole markup token: a comment, a processing instruction or XML declaration, a CDATA
# section, any other tag (quoted values may hold ">"), or a reference. Possessive: no backtracking.
_TOKEN_TEXT = (
    rb"<!--.*?-->|<\?.*?\?>|<!\[CDATA\[.*?\]\]>"
    rb"""|<(?!!--|\?|!\[CDATA\[)(?:[^<>"']++|"[^"]*+"|'[^']*+')*+>"""
    rb"|&[^;<&]*+;"
)
_TOKEN = re.compile(_TOKEN_TEXT, re.DOTALL)
_WHOLE = re.compile(rb"(?:[^<&]++|" + _TOKEN_TEXT + rb")*+", re.DOTALL)
_DECLARED = "a DOCTYPE or ENTITY declaration"
_XML = "http://www.w3.org/XML/1998/namespace"
_XMLNS = "http://www.w3.org/2000/xmlns/"
_NO_MEMORY = expat.errors.codes[expat.errors.XML_ERROR_NO_MEMORY]
_MEMORY = "XML that needs more memory than expat's allocation limit allows"
_UNBOUND = "an XML prefix that is not declared"
_TWICE = "an XML attribute twice in one namespace"
_RESERVED = "the xml or xmlns prefix or namespace name bound otherwise than XML allows"
_EMPTY = "an XML prefix bound to an empty namespace name"
_QNAME = "an XML name that is not a qualified name under XML namespaces"
_SEPARATOR = "an XML namespace name holding '}'"


def _end_record(raw: bytes) -> tuple[int, int, int] | None:
    """Return the directory offset, size and total entries that the end record states.

    Read where zipfile 3.12 reads them: the end record, then the ZIP64 record that replaces its
    values. Return None where zipfile finds no end record. Pure byte reading, never raises. A
    ZIP64 structure zipfile would refuse is not used: the stated values of the end record come
    back and zipfile's own refusal follows at the open.
    """
    if len(raw) < _END_SIZE:
        return None
    where = len(raw) - _END_SIZE
    if not (raw.startswith(_END_SIGNATURE, where) and raw.endswith(b"\x00\x00")):
        first = max(len(raw) - _MAX_COMMENT - _END_SIZE, 0)
        found = raw.rfind(_END_SIGNATURE, first)
        if found < 0 or len(raw) - found < _END_SIZE:
            return None
        where = found
    _, _, _, _, total, size, offset, _ = struct.unpack_from("<4s4H2LH", raw, where)
    stated = (offset, size, total)
    locator = where - _LOCATOR_SIZE
    if locator < 0 or not raw.startswith(_LOCATOR_SIGNATURE, locator):
        return stated
    _, _, relative, _ = struct.unpack_from("<4sLQL", raw, locator)
    last = locator - _RECORD64_SIZE
    if last < 0 or relative > last:
        return stated
    at = relative
    if not raw.startswith(_RECORD64_SIGNATURE, at) and relative != last:
        at = last
    if at + _RECORD64_SIZE > len(raw) or not raw.startswith(_RECORD64_SIGNATURE, at):
        return stated
    _, _, _, _, _, _, _, total64, size64, offset64 = struct.unpack_from("<4sQ2H2L4Q", raw, at)
    return (offset64, size64, total64)


class _Tracked(Protocol):
    """The parser's allocation tracker, which the pinned type stubs lack."""

    def SetAllocTrackerActivationThreshold(self, threshold: int, /) -> None: ...

    def SetAllocTrackerMaximumAmplification(self, factor: float, /) -> None: ...


class Target(Protocol):
    """What reads a part: called for each element start, end and piece of text."""

    def start(self, name: str, attributes: dict[str, str]) -> None:
        """An element opened; its name is `uri}local` where it has a namespace."""

    def end(self, name: str) -> None:
        """An element closed."""

    def text(self, data: str) -> None:
        """A piece of text; consecutive calls belong to one run, so a target joins them."""


class Package:
    """A zip that passed the structural checks; `pieces` reads one part of it."""

    def __init__(self, name: str, raw: bytes) -> None:
        self._name = name
        self._expanded = 0
        if raw.startswith(_OLE_SIGNATURE):
            raise self.refuse("an OLE file (an old or password-protected Office file), not a zip")
        if not raw.startswith(_LOCAL_SIGNATURE):
            raise self.refuse("does not start with a zip signature")
        if raw.count(_DIRECTORY_SIGNATURE) > MAX_MEMBERS:
            raise self.refuse(f"more than {MAX_MEMBERS:,} zip members")
        stated = _end_record(raw)
        # No end record found: zipfile finds none either and the open below refuses.
        if stated is not None and stated[1] > MAX_DIRECTORY_BYTES:
            raise self.refuse("a zip directory too large")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", UserWarning)
                archive = zipfile.ZipFile(io.BytesIO(raw))
        except (zipfile.BadZipFile, NotImplementedError, ValueError, UserWarning) as error:
            raise self.refuse("not a readable zip") from error
        self._archive = archive
        infos = archive.infolist()
        self._check_places(infos, len(raw))
        if not infos:
            raise self.refuse("a zip with no members")
        if stated is None or stated[0] != archive.start_dir or stated[2] != len(infos):
            raise self.refuse("a zip end record that disagrees with its directory")
        self._check_names(infos)
        if sum(info.file_size for info in infos) > MAX_EXPANDED_BYTES:
            raise self.refuse(f"declares more than {MAX_EXPANDED_BYTES:,} expanded bytes")
        self._members = {info.filename: info for info in infos}

    def _check_places(self, infos: list[zipfile.ZipInfo], size: int) -> None:
        if any(not 0 <= info.header_offset < size for info in infos):
            raise self.refuse("a zip member outside the file")
        if min((info.header_offset for info in infos), default=0) != 0:
            raise self.refuse("bytes before the first zip member")

    def _check_names(self, infos: list[zipfile.ZipInfo]) -> None:
        if any("\\" in info.orig_filename for info in infos):
            raise self.refuse("a zip member name with a backslash")
        if any(info.filename != info.orig_filename for info in infos):
            raise self.refuse("a zip member with two names")
        if len({info.header_offset for info in infos}) != len(infos):
            raise self.refuse("two zip members at the same place")
        if len({info.filename for info in infos}) != len(infos):
            raise self.refuse("two zip members with the same name")
        folded = {unicodedata.normalize("NFC", info.filename).casefold() for info in infos}
        if len(folded) != len(infos):
            raise self.refuse("zip members whose names differ only by case or form")

    def refuse(self, reason: str, part: str | None = None) -> SourceUnreadable:
        """Return the typed refusal for this package, naming the part when one is given."""
        if part is None:
            return SourceUnreadable(f"{shown_name(self._name)}: {reason}")
        return SourceUnreadable(f"{shown_name(self._name)}: {shown_name(part)!r}: {reason}")

    def has(self, part: str) -> bool:
        """Return whether the package has a member of that name."""
        return part in self._members

    def _typed(self, part: str, error: Exception) -> SourceUnreadable:
        if isinstance(error, zlib.error):
            return self.refuse("a damaged compressed stream", part)
        if isinstance(error, EOFError):
            return self.refuse("a truncated compressed stream", part)
        if isinstance(error, NotImplementedError):
            return self.refuse("a zip feature that is not supported", part)
        return self.refuse("a damaged zip member", part)

    def pieces(self, part: str) -> Iterator[bytes]:
        """Yield the expanded bytes of a part in pieces of at most `CHUNK_BYTES`.

        A generator: its refusals (missing, encrypted, method) are raised at the first `next()`,
        not at the call.
        """
        info = self._members.get(part)
        if info is None:
            raise self.refuse("the part is missing", part)
        if info.flag_bits & 0x1:
            raise self.refuse("the part is encrypted", part)
        if info.compress_type not in (_STORED, _DEFLATED):
            raise self.refuse("the part is compressed by a method other than deflate", part)
        try:
            member = self._archive.open(info)
        except (
            zipfile.BadZipFile,
            zlib.error,
            EOFError,
            NotImplementedError,
            ValueError,
        ) as error:
            raise self._typed(part, error) from error
        with member:
            while True:
                try:
                    chunk = member.read(CHUNK_BYTES)
                except (
                    zipfile.BadZipFile,
                    zlib.error,
                    EOFError,
                    NotImplementedError,
                    ValueError,
                ) as error:
                    raise self._typed(part, error) from error
                if not chunk:
                    return
                self._expanded += len(chunk)
                if self._expanded > MAX_EXPANDED_BYTES:
                    raise self.refuse(f"expands to more than {MAX_EXPANDED_BYTES:,} bytes")
                yield chunk

    def parse(self, part: str, target: Target) -> None:
        """Read one XML part into the target, refusing what the guards refuse."""
        shape = _Shape(self, part, target)
        parser = expat.ParserCreate(intern=None)
        parser.buffer_text = True
        parser.StartElementHandler = shape.start
        parser.EndElementHandler = shape.end
        parser.CharacterDataHandler = target.text
        parser.ProcessingInstructionHandler = shape.instruction
        parser.StartDoctypeDeclHandler = shape.doctype
        tracked = cast(_Tracked, parser)
        tracked.SetAllocTrackerActivationThreshold(EXPAT_THRESHOLD)
        tracked.SetAllocTrackerMaximumAmplification(EXPAT_AMPLIFICATION)
        decoder = codecs.getincrementaldecoder("utf-8-sig")()
        held = b""
        tail = b""
        try:
            for piece in self.pieces(part):
                self._check_bytes(part, tail + piece)
                tail = (tail + piece)[-_DECLARATION_TAIL:]
                held = self._unfinished(part, held + piece if held else piece, bool(held))
                parser.Parse(self._decoded(part, decoder, piece, False), False)
            parser.Parse(self._decoded(part, decoder, b"", True), True)
        except expat.ExpatError as error:
            if error.code == _NO_MEMORY:
                raise self.refuse(_MEMORY, part) from error
            raise self.refuse("not well-formed XML", part) from error

    def _check_bytes(self, part: str, seen: bytes) -> None:
        """Refuse a NUL byte or a declaration in the bytes of a piece, with the tail before it."""
        if b"\x00" in seen:
            raise self.refuse("a NUL byte (XML parts are read as UTF-8 only)", part)
        if _DECLARATION.search(seen):
            raise self.refuse(_DECLARED, part)

    def _decoded(
        self, part: str, decoder: codecs.IncrementalDecoder, piece: bytes, last: bool
    ) -> str:
        try:
            return decoder.decode(piece, last)
        except UnicodeDecodeError as error:
            raise self.refuse("not valid UTF-8", part) from error

    def _unfinished(self, part: str, data: bytes, continued: bool) -> bytes:
        """Return the unfinished markup token at the end of data, refusing one that is too long."""
        at = 0
        if continued:
            token = _TOKEN.match(data)
            if token is None or token.end() > MAX_TOKEN_BYTES:
                if len(data) > MAX_TOKEN_BYTES:
                    limit = f"{MAX_TOKEN_BYTES:,}"
                    raise self.refuse(
                        f"an XML tag, comment or reference longer than {limit} bytes", part
                    )
                return data
            at = token.end()
        return data[next(_WHOLE.finditer(data, at)).end() :]


def _starts_name(char: str) -> bool:
    """Return whether expat lets a name start with this character."""
    if char.isascii():
        return char.isalpha() or char == "_"
    try:
        expat.ParserCreate().Parse(f"<{char}/>", True)
    except expat.ExpatError:
        return False
    return True


class _Shape:
    """Between the parser and a target: binds namespaces and measures names, depth and bindings."""

    def __init__(self, package: Package, part: str, target: Target) -> None:
        self._package = package
        self._part = part
        self._target = target
        self._open = 0
        self._names: set[str] = set()
        self._uris: dict[str, str] = {}
        self._bound: dict[str, list[str]] = {"xml": [_XML]}
        self._elements: list[tuple[str, tuple[list[str], ...]]] = []

    def _refuse(self, reason: str) -> SourceUnreadable:
        return self._package.refuse(reason, self._part)

    def _measured(self, name: str) -> None:
        if len(name.encode()) > MAX_NAME_LENGTH:
            raise self._refuse(f"an XML name longer than {MAX_NAME_LENGTH} bytes")

    def _counted(self) -> None:
        if len(self._names) + len(self._uris) > MAX_NAMES:
            raise self._refuse(f"more than {MAX_NAMES:,} different XML names")

    def _known(self, name: str) -> None:
        self._measured(name)
        self._names.add(name)
        self._counted()

    def _split(self, name: str) -> tuple[str, str]:
        """Return the prefix and local part of a name; refuse what is not a qualified name."""
        prefix, colon, local = name.partition(":")
        if not colon:
            return "", name
        if not prefix or not local or ":" in local:
            raise self._refuse(_QNAME)
        return prefix, local

    def _declare(self, key: str, uri: str) -> tuple[str, str]:
        """Check one declaration; return its prefix and the one kept copy of its namespace name."""
        prefix = "" if key == "xmlns" else self._split(key)[1]
        self._open += 1
        if self._open > MAX_NAMES:
            raise self._refuse(f"more than {MAX_NAMES:,} namespace declarations open at once")
        if prefix and key not in self._names:
            if not _starts_name(prefix[0]):
                raise self._refuse(_QNAME)
            self._known(key)
        if "}" in uri:
            raise self._refuse(_SEPARATOR)
        if prefix == "xmlns" or uri == _XMLNS or (prefix == "xml") != (uri == _XML):
            raise self._refuse(_RESERVED)
        if not uri:
            if prefix:
                raise self._refuse(_EMPTY)
            return "", ""
        if uri not in self._uris:
            self._measured(uri)
            self._uris[uri] = uri
            self._counted()
        return prefix, self._uris[uri]

    def _resolve(self, name: str) -> str:
        """Return `uri}local` for an element name or a prefixed attribute name, counting it."""
        prefix, local = self._split(name)
        if prefix:
            scope = self._bound.get(prefix)
            if not scope or not scope[-1]:
                raise self._refuse(_UNBOUND)
            counted = f"{scope[-1]}}}{local}}}{prefix}"
            if counted not in self._names:
                if not _starts_name(local[0]):
                    raise self._refuse(_QNAME)
                self._known(counted)
            return counted[: -len(prefix) - 1]
        scope = self._bound.get("")
        if scope and scope[-1]:
            name = f"{scope[-1]}}}{local}"
        if name not in self._names:
            self._known(name)
        return name

    def _bind(self, attributes: dict[str, str], declared: list[str]) -> tuple[list[str], ...]:
        """Check every declaration of a tag, then bind them all; return the lists bound."""
        kept = [self._declare(key, attributes[key]) for key in declared]
        opened = []
        for prefix, uri in kept:
            scope = self._bound.setdefault(prefix, [])
            scope.append(uri)
            opened.append(scope)
        return tuple(opened)

    def _bare(self, attributes: dict[str, str]) -> dict[str, str]:
        """Return the attributes in order, declarations removed and prefixes expanded."""
        bare: dict[str, str] = {}
        for key, value in attributes.items():
            if key == "xmlns" or key.startswith("xmlns:"):
                continue
            if ":" in key:
                key = self._resolve(key)
                if key in bare:
                    raise self._refuse(_TWICE)
            elif key not in self._names:
                self._known(key)
            bare[key] = value
        return bare

    def start(self, name: str, attributes: dict[str, str]) -> None:
        if len(attributes) > MAX_NAMES + 1:
            raise self._refuse(f"more than {MAX_NAMES:,} different XML names")
        declared = [k for k in attributes if k == "xmlns" or k.startswith("xmlns:")]
        opened = self._bind(attributes, declared) if declared else ()
        if len(self._elements) >= MAX_DEPTH:
            raise self._refuse(f"XML nested deeper than {MAX_DEPTH} elements")
        expanded = self._resolve(name)
        bare = self._bare(attributes) if attributes else {}
        self._elements.append((expanded, opened))
        self._target.start(expanded, bare)

    def end(self, _name: str) -> None:
        expanded, opened = self._elements.pop()
        if opened:
            for scope in opened:
                scope.pop()
            self._open -= len(opened)
        self._target.end(expanded)

    def instruction(self, target: str, _data: str) -> None:
        if ":" in target:
            raise self._refuse(_QNAME)

    def doctype(self, *_declared: object) -> None:
        """The parser's own word that a DOCTYPE began: the second guard behind the byte search."""
        raise self._refuse(_DECLARED)
