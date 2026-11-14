"""The zip half of the OOXML guards: a checked package and the bytes of its parts, in pieces.

Every failure of the standard library on a bad zip becomes a `SourceUnreadable` that names the
file, and the part where one is meant, and chains its cause. Limits are module constants read at
call time; a test lowers one with `monkeypatch`.
"""

import io
import zipfile
import zlib
from collections.abc import Iterator

from credit_os.sources.errors import SourceUnreadable, shown_name

# The sum of the declared sizes and the bytes actually expanded may not pass this.
MAX_EXPANDED_BYTES = 209_715_200
# zipfile makes an object per member before any member can be counted.
MAX_MEMBERS = 16_384
# The most of a part held at once.
CHUNK_BYTES = 65_536

_OLE_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_LOCAL_SIGNATURE = b"PK\x03\x04"
_DIRECTORY_SIGNATURE = b"PK\x01\x02"
_STORED = 0
_DEFLATED = 8


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
        try:
            archive = zipfile.ZipFile(io.BytesIO(raw))
        except (zipfile.BadZipFile, NotImplementedError, ValueError) as error:
            raise self.refuse("not a readable zip") from error
        self._archive = archive
        infos = archive.infolist()
        if any("\\" in info.orig_filename for info in infos):
            raise self.refuse("a zip member name with a backslash")
        if len({info.header_offset for info in infos}) != len(infos):
            raise self.refuse("two zip members at the same place")
        if len({info.filename for info in infos}) != len(infos):
            raise self.refuse("two zip members with the same name")
        if sum(info.file_size for info in infos) > MAX_EXPANDED_BYTES:
            raise self.refuse(f"declares more than {MAX_EXPANDED_BYTES:,} expanded bytes")
        self._members = {info.filename: info for info in infos}

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
