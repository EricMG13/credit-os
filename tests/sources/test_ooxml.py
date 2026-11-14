"""The zip half of the OOXML guards (`ooxml.Package`) and the zipfile pins it relies on.

Every fixture is built here with zipfile writing and byte edits at fixed header offsets, never
by the code under test. Expected messages are literals.
"""

import io
import struct
import sys
import warnings
import zipfile
import zlib
from typing import Any
from xml.parsers import expat

import pytest

from credit_os.sources import ooxml
from credit_os.sources.errors import SourceUnreadable
from credit_os.sources.ooxml import Package

PART = "xl/a.xml"
GOOD = b"<a>text</a>"


def zipped(parts: dict[str, bytes], method: int = zipfile.ZIP_STORED) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", method) as archive:
        for name, data in parts.items():
            archive.writestr(name, data)
    return buffer.getvalue()


def central(raw: bytes, index: int = 0) -> int:
    """Offset of the central-directory entry of the index-th member."""
    at = raw.index(b"PK\x01\x02")
    for _ in range(index):
        at = raw.index(b"PK\x01\x02", at + 4)
    return at


def patched(raw: bytes, at: int, value: bytes) -> bytes:
    return raw[:at] + value + raw[at + len(value) :]


def _zip64_offset(offset: int) -> bytes:
    """ONE with its central entry's header offset moved into a ZIP64 extra field."""
    cd = central(ONE)
    name_len = struct.unpack("<H", ONE[cd + 28 : cd + 30])[0]
    extra = struct.pack("<HHQ", 0x0001, 8, offset)
    entry = bytearray(ONE[cd : cd + 46 + name_len])
    entry[30:32] = struct.pack("<H", len(extra))
    entry[42:46] = b"\xff\xff\xff\xff"
    end = bytearray(ONE[EOCD:])
    end[12:16] = struct.pack("<I", struct.unpack("<I", end[12:16])[0] + len(extra))
    return ONE[:cd] + bytes(entry) + extra + bytes(end)


def _unicode_path_entry(raw: bytes, at: int, stored: str, new: bytes) -> tuple[bytes, int]:
    """The central entry at `at` with a 0x7075 field naming it `new`, and the next entry's offset."""
    n, m, k = struct.unpack("<HHH", raw[at + 28 : at + 34])
    body = struct.pack("<BI", 1, zlib.crc32(stored.encode())) + new
    extra = struct.pack("<HH", 0x7075, len(body)) + body
    entry = bytearray(raw[at : at + 46 + n])
    entry[30:32] = struct.pack("<H", len(extra))
    return bytes(entry) + extra, at + 46 + n + m + k


def _unicode_path_zip(renames: list[tuple[str, bytes]], data: dict[str, bytes]) -> bytes:
    """A zip of `data` whose central entries carry the 0x7075 names in `renames`, in order."""
    raw = zipped(data)
    cd = raw.index(b"PK\x01\x02")
    out = bytearray(raw[:cd])
    at = cd
    for name, new in renames:
        entry, at = _unicode_path_entry(raw, at, name, new)
        out += entry
    end = bytearray(raw[raw.rindex(b"PK\x05\x06") :])
    end[12:16] = struct.pack("<I", len(out) - cd)
    return bytes(out) + bytes(end)


def _hidden_end_record() -> bytes:
    """A zip whose end-record comment holds a second directory and end record into a member."""
    inner = zipped({"xl/h1.xml": GOOD, "xl/h2.xml": GOOD, "xl/h3.xml": GOOD})
    raw = zipped({PART: GOOD, "xl/blob.bin": inner})
    start = raw.index(inner)
    inner_end = inner.rindex(b"PK\x05\x06")
    size_cd, offset_cd = struct.unpack("<II", inner[inner_end + 12 : inner_end + 20])
    directory = bytearray(inner[offset_cd : offset_cd + size_cd])
    at = 0
    while at < len(directory):
        n, m, k = struct.unpack("<HHH", directory[at + 28 : at + 34])
        old = struct.unpack("<I", directory[at + 42 : at + 46])[0]
        directory[at + 42 : at + 46] = struct.pack("<I", old + start)
        at += 46 + n + m + k
    end = raw.rindex(b"PK\x05\x06")
    fake = b"PK\x05\x06" + struct.pack("<HHHHIIH", 0, 0, 3, 3, len(directory), end + 22, 0)
    comment = bytes(directory) + fake
    tail = bytearray(raw[end : end + 22])
    tail[20:22] = struct.pack("<H", len(comment))
    return raw[:end] + bytes(tail) + comment


def _zip64(raw: bytes, dirsize: int | None = None, sentinel: bool = True) -> bytes:
    e = raw.rindex(b"PK\x05\x06")
    n, size, off = struct.unpack_from("<HLL", raw, e + 10)
    rec = struct.pack(
        "<4sQHHLLQQQQ",
        b"PK\x06\x06",
        44,
        45,
        45,
        0,
        0,
        n,
        n,
        size if dirsize is None else dirsize,
        off,
    )
    loc = struct.pack("<4sLQL", b"PK\x06\x07", 0, e, 1)
    tail = bytearray(raw[e:])
    if sentinel:
        tail[8:20] = struct.pack("<HHLL", 0xFFFF, 0xFFFF, 0xFFFFFFFF, 0xFFFFFFFF)
    return raw[:e] + rec + loc + bytes(tail)


def _eocd_size(raw: bytes, size: int) -> bytes:
    return patched(raw, raw.rindex(b"PK\x05\x06") + 12, size.to_bytes(4, "little"))


def _commented(comment: bytes) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.comment = comment
        archive.writestr(PART, GOOD)
    return buffer.getvalue()


ONE = zipped({PART: GOOD})
TWO = zipped({PART: GOOD, "xl/b.xml": GOOD})
DEFLATED = zipped({PART: b"<a>" + b"text " * 200 + b"</a>"}, zipfile.ZIP_DEFLATED)
EOCD = ONE.rindex(b"PK\x05\x06")
SHIFTED = patched(
    patched(
        ONE,
        EOCD + 16,
        (int.from_bytes(ONE[EOCD + 16 : EOCD + 20], "little") + 8).to_bytes(4, "little"),
    ),
    central(ONE) + 42,
    (8).to_bytes(4, "little"),
)
SMALL = _eocd_size(_zip64(ONE, sentinel=False), 0)

_TWO_NAMES = "a zip member with two names"
_E_ACUTE_NAME = "\N{LATIN SMALL LETTER E WITH ACUTE}.xml"
_MIB_200 = 200 * 1024 * 1024
_OLE_MESSAGE = "an OLE file (an old or password-protected Office file), not a zip"
_SIGNATURE_MESSAGE = "does not start with a zip signature"
_UNREADABLE = "not a readable zip"
_DAMAGED = "'xl/a.xml': a damaged zip member"
_METHOD = "'xl/a.xml': the part is compressed by a method other than deflate"

# (id, raw, part, message after "b.xlsx: " or None when the part is read, cause class name)
ZIP_ROWS: list[tuple[str, bytes, str, str | None, str]] = [
    ("z1", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 504, PART, _OLE_MESSAGE, "none"),
    ("z2", b"%PDF-1.7\n", PART, _SIGNATURE_MESSAGE, "none"),
    ("z3", zipped({}), PART, _SIGNATURE_MESSAGE, "none"),
    ("z4", b"PK\x03\x04 is not a workbook", PART, _UNREADABLE, "BadZipFile"),
    (
        "z5",
        patched(ONE, central(ONE) + 6, b"\xff\xff"),
        PART,
        _UNREADABLE,
        "NotImplementedError",
    ),
    (
        "z6",
        zipped({_E_ACUTE_NAME: GOOD}).replace(b"\xc3\xa9", b"\xff\xfe"),
        PART,
        _UNREADABLE,
        "UnicodeDecodeError",
    ),
    (
        "z7",
        zipped({"xl/a.xml": GOOD}).replace(b"xl/a.xml", b"xl\\a.xml"),
        PART,
        "a zip member name with a backslash",
        "none",
    ),
    (
        "z8",
        patched(TWO, central(TWO, 1) + 42, b"\x00\x00\x00\x00"),
        PART,
        "two zip members at the same place",
        "none",
    ),
    (
        "z9",
        TWO.replace(b"xl/b.xml", b"xl/a.xml"),
        PART,
        "two zip members with the same name",
        "none",
    ),
    (
        "z10",
        patched(ONE, central(ONE) + 24, (_MIB_200 + 1).to_bytes(4, "little")),
        PART,
        "declares more than 209,715,200 expanded bytes",
        "none",
    ),
    ("z11", patched(ONE, central(ONE) + 24, _MIB_200.to_bytes(4, "little")), PART, None, "none"),
    ("z12", ONE, "xl/none.xml", "'xl/none.xml': the part is missing", "none"),
    (
        "z13",
        patched(ONE, central(ONE) + 8, b"\x01\x00"),
        PART,
        "'xl/a.xml': the part is encrypted",
        "none",
    ),
    ("z14", patched(ONE, central(ONE) + 10, b"\x0c\x00"), PART, _METHOD, "none"),
    ("z15", patched(ONE, central(ONE) + 10, b"\x63\x00"), PART, _METHOD, "none"),
    (
        "z16",
        patched(ONE, central(ONE) + 8, b"\x20\x00"),
        PART,
        "'xl/a.xml': a zip feature that is not supported",
        "NotImplementedError",
    ),
    (
        "z17",
        ONE.replace(b"<a>text</a>", b"<a>tex!</a>", 1),
        PART,
        _DAMAGED,
        "BadZipFile",
    ),
    (
        "z18",
        patched(DEFLATED, 30 + len(PART), b"\xff\xff\xff\xff"),
        PART,
        "'xl/a.xml': a damaged compressed stream",
        "error",
    ),
    (
        "z19",
        patched(
            ONE,
            EOCD + 16,
            (int.from_bytes(ONE[EOCD + 16 : EOCD + 20], "little") + 5).to_bytes(4, "little"),
        ),
        PART,
        "a zip member outside the file",
        "none",
    ),
    ("z20", patched(ONE, 30, b"xl/b.xml"), PART, _DAMAGED, "BadZipFile"),
    ("z21", ONE[:-10], PART, _UNREADABLE, "BadZipFile"),
    (
        "z22",
        patched(ONE, central(ONE) + 20, (len(GOOD) + 1).to_bytes(4, "little")),
        PART,
        _DAMAGED,
        "BadZipFile",
    ),
    (
        "z28",
        patched(
            patched(ONE, 6, (int.from_bytes(ONE[6:8], "little") | 0x0800).to_bytes(2, "little")),
            37,
            b"\xff",
        ),
        PART,
        _DAMAGED,
        "UnicodeDecodeError",
    ),
    ("z23", _zip64_offset(2**63), PART, "a zip member outside the file", "none"),
    ("z24", b"PK\x03\x04junk" + ONE, PART, "bytes before the first zip member", "none"),
    ("z25", _hidden_end_record(), PART, "bytes before the first zip member", "none"),
    (
        "z26",
        _unicode_path_zip([("xl/x.xml", b"xl\\a.xml")], {"xl/x.xml": GOOD}),
        PART,
        _TWO_NAMES,
        "none",
    ),
    (
        "z27",
        _unicode_path_zip(
            [(PART, b"xl/moved.xml"), ("zz/b.xml", PART.encode())],
            {PART: GOOD, "zz/b.xml": b"<a>stored as zz/b.xml</a>"},
        ),
        PART,
        _TWO_NAMES,
        "none",
    ),
]


_TOO_LARGE = "a zip directory too large"
_DISAGREES = "a zip end record that disagrees with its directory"
_FOLDED = "zip members whose names differ only by case or form"
_PREFIXED = b"PK\x03\x04junk"

# (id, raw, cap or None for the module's, message after "b.xlsx: " or None when read, cause)
DIRECTORY_ROWS: list[tuple[str, bytes, int | None, str | None, str]] = [
    ("d1", ONE, 54, None, "none"),
    ("d2", ONE, 53, _TOO_LARGE, "none"),
    ("d3", _zip64(ONE), None, None, "none"),
    ("d4", _zip64(ONE, sentinel=False), None, None, "none"),
    ("d5", _zip64(ONE), 53, _TOO_LARGE, "none"),
    ("d6", SMALL, None, None, "none"),
    ("d7", SMALL, 53, _TOO_LARGE, "none"),
    ("d8", _PREFIXED + SMALL, 53, _TOO_LARGE, "none"),
    ("d9", _PREFIXED + SMALL, None, "bytes before the first zip member", "none"),
    ("d10", _eocd_size(ONE, 0xFFFFFFFF), None, _TOO_LARGE, "none"),
    ("d11", _eocd_size(ONE, 53), None, _UNREADABLE, "BadZipFile"),
    ("d12", _eocd_size(ONE, 55), None, _UNREADABLE, "BadZipFile"),
    ("d13", _zip64(ONE, 2**40), None, _TOO_LARGE, "none"),
    ("d14", _zip64(ONE, 55), None, _UNREADABLE, "BadZipFile"),
    ("d15", _commented(b"note"), None, None, "none"),
    ("d16", _commented(b"n" * 65_535), None, None, "none"),
    ("d17", patched(ONE, EOCD + 8, b"\x00\x00\x00\x00"), None, _DISAGREES, "none"),
    ("d18", patched(ONE, EOCD + 10, b"\x02\x00"), None, _DISAGREES, "none"),
    ("d19", SHIFTED, None, _DISAGREES, "none"),
    ("d21", zipped({PART: GOOD, "XL/A.xml": GOOD}), None, _FOLDED, "none"),
    (
        "d22",
        zipped({_E_ACUTE_NAME: GOOD, "e\N{COMBINING ACUTE ACCENT}.xml": GOOD}),
        None,
        _FOLDED,
        "none",
    ),
]


def _expect(raw: bytes, message: str | None, cause: str) -> None:
    if message is None:
        assert _read(raw) == GOOD
        return
    with pytest.raises(SourceUnreadable) as caught:
        _read(raw)
    assert str(caught.value) == f"b.xlsx: {message}"
    expected = None if cause == "none" else cause
    actual = caught.value.__cause__
    assert (None if actual is None else type(actual).__name__) == expected


@pytest.mark.parametrize(
    ("raw", "cap", "message", "cause"),
    [pytest.param(*row[1:], id=row[0]) for row in DIRECTORY_ROWS],
)
def test_directory_rows(
    monkeypatch: pytest.MonkeyPatch, raw: bytes, cap: int | None, message: str | None, cause: str
) -> None:
    if cap is not None:
        monkeypatch.setattr(ooxml, "MAX_DIRECTORY_BYTES", cap)
    _expect(raw, message, cause)


def test_d20_no_end_record_found_disagrees(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ooxml, "_end_record", lambda _raw: None)
    _expect(ONE, _DISAGREES, "none")


def test_directory_cap_is_four_mib() -> None:
    assert ooxml.MAX_DIRECTORY_BYTES == 4 * 1024 * 1024


def _read(raw: bytes, part: str = PART) -> bytes:
    return b"".join(Package("b.xlsx", raw).pieces(part))


@pytest.mark.parametrize(
    ("raw", "part", "message", "cause"),
    [pytest.param(*row[1:], id=row[0]) for row in ZIP_ROWS],
)
def test_zip_rows(raw: bytes, part: str, message: str | None, cause: str) -> None:
    if message is None:
        assert _read(raw, part) == GOOD
        return
    with pytest.raises(SourceUnreadable) as caught:
        _read(raw, part)
    assert str(caught.value) == f"b.xlsx: {message}"
    expected = None if cause == "none" else cause
    actual = caught.value.__cause__
    assert (None if actual is None else type(actual).__name__) == expected


def test_empty_unicode_path_warning_is_typed() -> None:
    raw = _unicode_path_zip([(PART, b"")], {PART: GOOD})
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with pytest.raises(SourceUnreadable) as caught:
            Package("b.xlsx", raw)
    assert str(caught.value) == "b.xlsx: not a readable zip"
    assert type(caught.value.__cause__) is UserWarning


def test_pieces_are_at_most_chunk_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ooxml, "CHUNK_BYTES", 4)
    assert [len(piece) for piece in Package("b.xlsx", ONE).pieces(PART)] == [4, 4, 3]


def test_expanded_cap_allows_exactly_the_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ooxml, "MAX_EXPANDED_BYTES", 22)
    package = Package("b.xlsx", TWO)
    assert b"".join(package.pieces(PART)) == GOOD
    assert b"".join(package.pieces("xl/b.xml")) == GOOD
    with pytest.raises(SourceUnreadable) as caught:
        b"".join(package.pieces(PART))
    assert str(caught.value) == "b.xlsx: expands to more than 22 bytes"
    assert caught.value.__cause__ is None


def test_z18_cause_is_zlib_error() -> None:
    raw = patched(DEFLATED, 30 + len(PART), b"\xff\xff\xff\xff")
    with pytest.raises(SourceUnreadable) as caught:
        _read(raw)
    assert type(caught.value.__cause__) is zlib.error


def test_truncated_stream_by_simulation(monkeypatch: pytest.MonkeyPatch) -> None:
    def raising(*_args: Any, **_kwargs: Any) -> bytes:
        raise EOFError

    monkeypatch.setattr(zipfile.ZipExtFile, "read", raising)
    with pytest.raises(SourceUnreadable) as caught:
        _read(ONE)
    assert str(caught.value) == "b.xlsx: 'xl/a.xml': a truncated compressed stream"
    assert type(caught.value.__cause__) is EOFError


def test_refuse_names_the_package_and_the_part() -> None:
    package = Package("b.xlsx", ONE)
    assert str(package.refuse("why")) == "b.xlsx: why"
    assert str(package.refuse("why", PART)) == "b.xlsx: 'xl/a.xml': why"


def test_has() -> None:
    package = Package("b.xlsx", TWO)
    assert package.has(PART)
    assert package.has("xl/b.xml")
    assert not package.has("xl/none.xml")


def test_member_cap_lowered(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ooxml, "MAX_MEMBERS", 3)
    assert _read(zipped({PART: GOOD, "b": b"", "c": b""})) == GOOD
    for raw in (
        zipped({PART: GOOD, "b": b"", "c": b"", "d": b""}),
        zipped({PART: GOOD, "b": b"PK\x01\x02", "c": b""}),
    ):
        with pytest.raises(SourceUnreadable) as caught:
            Package("b.xlsx", raw)
        assert str(caught.value) == "b.xlsx: more than 3 zip members"
        assert caught.value.__cause__ is None


def test_expanded_cap_lowered_counts_every_read(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ooxml, "MAX_EXPANDED_BYTES", 30)
    package = Package("b.xlsx", TWO)
    assert b"".join(package.pieces(PART)) == GOOD
    assert b"".join(package.pieces(PART)) == GOOD
    with pytest.raises(SourceUnreadable) as caught:
        b"".join(package.pieces(PART))
    assert str(caught.value) == "b.xlsx: expands to more than 30 bytes"
    assert caught.value.__cause__ is None


def _fail(what: str, value: object, expected: object) -> str:
    return f"{what}: {value!r} != {expected!r} on {sys.version}"


def test_pin1_interpreter_and_bundled_libraries() -> None:
    sys.stdout.write(f"zlib {zlib.ZLIB_RUNTIME_VERSION}, {expat.EXPAT_VERSION}\n")
    assert sys.version_info[:3] >= (3, 12, 14), sys.version


def test_pin2_declared_smaller_than_actual_fails_before_any_byte() -> None:
    big = zipped({PART: b"y" * 100_000}, zipfile.ZIP_DEFLATED)
    low = patched(big, central(big) + 24, (1_000).to_bytes(4, "little"))
    got = 0
    with (
        zipfile.ZipFile(io.BytesIO(low)) as archive,
        archive.open(PART) as member,
        pytest.raises(zipfile.BadZipFile) as caught,
    ):
        while chunk := member.read(300):
            got += len(chunk)
    assert got == 0, _fail("bytes read", got, 0)
    assert str(caught.value) == "Bad CRC-32 for file 'xl/a.xml'", sys.version


def test_pin3_declared_larger_than_actual_reads_the_actual() -> None:
    big = zipped({PART: b"y" * 100_000}, zipfile.ZIP_DEFLATED)
    high = patched(big, central(big) + 24, (5_000_000).to_bytes(4, "little"))
    with zipfile.ZipFile(io.BytesIO(high)) as archive, archive.open(PART) as member:
        got = sum(len(chunk) for chunk in iter(lambda: member.read(65_536), b""))
    assert got == 100_000, _fail("bytes read", got, 100_000)


def test_pin4_a_read_never_returns_more_than_asked() -> None:
    big = zipped({PART: b"y" * 100_000}, zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(io.BytesIO(big)) as archive, archive.open(PART) as member:
        sizes = [len(chunk) for chunk in iter(lambda: member.read(30_000), b"")]
    assert sizes == [30000, 30000, 30000, 10000], _fail("sizes", sizes, [30000] * 3 + [10000])


def test_pin5_duplicate_names_are_visible() -> None:
    with zipfile.ZipFile(io.BytesIO(TWO.replace(b"xl/b.xml", b"xl/a.xml"))) as archive:
        assert len(archive.infolist()) == 2, sys.version
        assert archive.namelist() == ["xl/a.xml", "xl/a.xml"], sys.version


def test_pin6_orig_filename_keeps_the_backslash() -> None:
    raw = zipped({"xl/a.xml": GOOD}).replace(b"xl/a.xml", b"xl\\a.xml")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        name = archive.infolist()[0].orig_filename
    assert name == "xl\\a.xml", _fail("orig_filename", name, "xl\\a.xml")


def test_pin7_two_entries_at_one_offset_only_warn() -> None:
    same = patched(TWO, central(TWO, 1) + 42, b"\x00\x00\x00\x00")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with (
            zipfile.ZipFile(io.BytesIO(same)) as archive,
            archive.open(archive.infolist()[0]) as member,
        ):
            data = member.read()
    messages = [str(w.message) for w in caught]
    assert data == b"<a>text</a>", _fail("data", data, b"<a>text</a>")
    assert messages == ["Overlapped entries: 'xl/a.xml' (possible zip bomb)"], sys.version


def test_pin8_an_encrypted_member_raises_runtime_error() -> None:
    enc = patched(ONE, central(ONE) + 8, b"\x01\x00")
    with zipfile.ZipFile(io.BytesIO(enc)) as archive, pytest.raises(RuntimeError) as caught:
        archive.open(PART)
    expected = "File 'xl/a.xml' is encrypted, password required for extraction"
    assert str(caught.value) == expected, sys.version
