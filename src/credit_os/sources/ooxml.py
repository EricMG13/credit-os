"""The zip half of the OOXML guards: a checked package and the bytes of its parts, in pieces.

Every failure of the standard library on a bad zip becomes a `SourceUnreadable` that names the
file, and the part where one is meant, and chains its cause. Limits are module constants read at
call time; a test lowers one with `monkeypatch`.
"""

import io
import struct
import unicodedata
import warnings
import zipfile
import zlib
from collections.abc import Iterator

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
