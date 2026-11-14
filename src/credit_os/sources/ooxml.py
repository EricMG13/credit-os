"""The OOXML guards: a checked zip package, the bytes of its parts in pieces, and XML parts read
through a bounded parser.

Zip half: every failure of the standard library on a bad zip becomes a `SourceUnreadable` that
names the file, and the part where one is meant, and chains its cause.

XML half (`Package.parse`): a part is never held whole. Each piece is checked on its bytes (a NUL
byte, a DOCTYPE or ENTITY declaration, an unfinished markup token over `MAX_TOKEN_BYTES`) and
decoded as UTF-8 before the parser is given it; expat's own DOCTYPE handler is a second guard
behind the byte search, and the depth, the length and count of different names (namespace names
included) and the namespace declarations open at once are measured as elements arrive. Expat's reparse deferral is left on. Only `xml.parsers.expat` is used.

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
from typing import Protocol
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
# expat keeps one unfinished markup token whole; a tag of this size costs it 24 times that.
MAX_TOKEN_BYTES = 1_048_576
# expat keeps a copy of each open element's name and its namespace bindings: 0.89 to 1.47 MiB at
# this depth with 255-character names (tracemalloc, macOS).
MAX_DEPTH = 256
# expat keeps every different element, attribute and `xmlns:` prefix name, and every namespace
# name, for the life of a part; the same cap holds the namespace declarations open at once.
MAX_NAMES = 4_096
# expat builds and binds every name on every tag, so a long name costs time and memory per tag and
# per open element, paid per UTF-8 byte; OOXML's are ASCII, under about 110 bytes. With MAX_NAMES
# it bounds the UTF-8 bytes of all names, namespace names included, to 255 x 4,096.
MAX_NAME_LENGTH = 255

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
        """Yield the expanded bytes of a part in pieces of at most `CHUNK_BYTES`."""
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
        parser = expat.ParserCreate(None, "}")
        parser.buffer_text = True
        # Names arrive as `uri}local}prefix`, as expat keeps them, so that each is counted; the
        # shape gives the target the name without its prefix.
        parser.namespace_prefixes = True
        parser.StartElementHandler = shape.start
        parser.EndElementHandler = shape.end
        parser.CharacterDataHandler = target.text
        parser.StartNamespaceDeclHandler = shape.prefix
        parser.EndNamespaceDeclHandler = shape.unprefix
        parser.StartDoctypeDeclHandler = shape.doctype
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
        whole = _WHOLE.match(data, at)
        return data[whole.end() :] if whole else data[at:]


def _bare(name: str) -> str:
    """Return a name without its `}prefix` part: `uri}local}prefix` becomes `uri}local`.

    expat refuses a namespace name that holds `}`, so a name has at most two of them.
    """
    if name.count("}") < 2:
        return name
    return name.rpartition("}")[0]


class _Shape:
    """Between the parser and a target: the depth, the names and the open namespace declarations."""

    def __init__(self, package: Package, part: str, target: Target) -> None:
        self._package = package
        self._part = part
        self._target = target
        self._depth = 0
        self._open = 0
        self._names: set[str] = set()
        self._uris: set[str] = set()

    def _known(self, name: str, kept: set[str]) -> None:
        if len(name.encode()) > MAX_NAME_LENGTH:
            raise self._package.refuse(
                f"an XML name longer than {MAX_NAME_LENGTH} bytes", self._part
            )
        kept.add(name)
        if len(self._names) + len(self._uris) > MAX_NAMES:
            raise self._package.refuse(f"more than {MAX_NAMES:,} different XML names", self._part)

    def start(self, name: str, attributes: dict[str, str]) -> None:
        self._depth += 1
        if self._depth > MAX_DEPTH:
            raise self._package.refuse(f"XML nested deeper than {MAX_DEPTH} elements", self._part)
        if name not in self._names:
            self._known(name, self._names)
        if attributes and not self._names.issuperset(attributes):
            for attribute in attributes:
                if attribute not in self._names:
                    self._known(attribute, self._names)
        bare = {_bare(key): value for key, value in attributes.items()}
        self._target.start(_bare(name), bare)

    def end(self, name: str) -> None:
        self._depth -= 1
        self._target.end(_bare(name))

    def doctype(self, *_declared: object) -> None:
        """The parser's own word that a DOCTYPE began: the second guard behind the byte search."""
        raise self._package.refuse(_DECLARED, self._part)

    def prefix(self, name: str | None, uri: str | None) -> None:
        self._open += 1
        if self._open > MAX_NAMES:
            raise self._package.refuse(
                f"more than {MAX_NAMES:,} namespace declarations open at once", self._part
            )
        if name is not None and "xmlns:" + name not in self._names:
            self._known("xmlns:" + name, self._names)
        if uri is not None and uri not in self._uris:
            self._known(uri, self._uris)

    def unprefix(self, _name: str | None) -> None:
        self._open -= 1
