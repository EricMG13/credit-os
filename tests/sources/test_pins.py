"""Name, kind and pin rules of the sources layer."""

import string
from collections.abc import MutableMapping
from typing import cast

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from credit_os.sources.errors import (
    SourceChanged,
    SourceError,
    SourceRefused,
    SourceTooLarge,
    SourceUnreadable,
)
from credit_os.sources.pins import (
    SUFFIX_KINDS,
    SourceKind,
    SourcePin,
    check_kind,
    kind_of,
    validate_name,
)

README_SHA = "4157540c50a21d8eccdd85cc071e37f2b23dd35525473b1b671044125dd44f42"
README_JSON = '{"name":"readme.txt","sha256":"' + README_SHA + '","size_bytes":16,"kind":"text"}'

VALID_NAMES = [
    "console.txt",
    "null.pdf",
    "com10.csv",
    "\u0416\u4e2d.txt",
    "a.pdf",
    "notes/filing.html",
    "Résumé 2025.pdf",
    "a b/c-d_e.txt",
    "..hidden",
    "a..b.txt",
    "~$memo.docx",
]
INVALID_NAMES = [
    "Q3-report\u202efdp.txt",
    "a\u0085b.txt",
    "a\u2028b.txt",
    "a\u2029b.txt",
    "a\u200bb.txt",
    "a\u009bb.txt",
    "R\udce9sum\udce9.txt",
    "NUL.txt",
    "con.pdf",
    "COM1.html",
    "LPT1.csv",
    "aux.md",
    "notes/PRN.txt",
    "CONIN$.txt",
    "nul",
    "a<b.txt",
    "a>b.txt",
    'a"b.txt',
    "a|b.txt",
    "a?b.txt",
    "a*b.txt",
    "",
    ".",
    "..",
    "/etc/passwd",
    "../outside.txt",
    "a/../b.txt",
    "a/./b.txt",
    "a//b.txt",
    "a/",
    "C:\\x.txt",
    "C:x.txt",
    "C:/x.txt",
    "\\\\server\\share\\x.txt",
    "a\\b.txt",
    "a\x00b.txt",
    "a\nb.txt",
    "a\x1fb.txt",
    "a\x7fb.txt",
    "file.txt:stream",
    "a.txt.",
    "a.txt ",
    "dir./a.txt",
    "dir /a.txt",
]


@pytest.mark.parametrize("name", VALID_NAMES)
def test_validate_name_accepts(name: str) -> None:
    assert validate_name(name) == name


@pytest.mark.parametrize("name", INVALID_NAMES)
def test_validate_name_refuses(name: str) -> None:
    with pytest.raises(SourceRefused) as caught:
        validate_name(name)
    assert str(caught.value) == f"{name!r}: not a valid source name"


def test_error_hierarchy() -> None:
    assert issubclass(SourceRefused, ValueError)
    assert issubclass(SourceRefused, SourceError)
    assert issubclass(SourceTooLarge, SourceUnreadable)
    assert issubclass(SourceUnreadable, SourceError)
    assert issubclass(SourceChanged, SourceError)
    assert not issubclass(SourceChanged, SourceUnreadable)


_RESERVED = {"CON", "PRN", "AUX", "NUL"}
_RESERVED |= {f"COM{n}" for n in range(1, 10)} | {f"LPT{n}" for n in range(1, 10)}
_ALPHABET = string.ascii_letters + string.digits + "\u00e9\u00df\u0416\u4e2d" + "-_ ."


def _is_reserved(segment: str) -> bool:
    return segment.split(".")[0].rstrip(" ").upper() in _RESERVED


_SEGMENT = st.text(alphabet=_ALPHABET, min_size=1, max_size=8).filter(
    lambda s: s not in (".", "..") and not s.endswith((".", " ")) and not _is_reserved(s)
)
_NAMES = st.lists(_SEGMENT, min_size=1, max_size=4).map("/".join)


@given(_NAMES)
def test_property_valid_names_unchanged(name: str) -> None:
    assert validate_name(name) == name


@given(_NAMES, st.data())
def test_property_dotdot_segment_refused(name: str, data: st.DataObject) -> None:
    segments = name.split("/")
    at = data.draw(st.integers(min_value=0, max_value=len(segments)))
    bad = "/".join([*segments[:at], "..", *segments[at:]])
    with pytest.raises(SourceRefused):
        validate_name(bad)


@given(_NAMES, st.sampled_from(["\\", ":", "\x00", "\x1f", "\x7f"]), st.data())
def test_property_bad_character_refused(name: str, char: str, data: st.DataObject) -> None:
    at = data.draw(st.integers(min_value=0, max_value=len(name)))
    with pytest.raises(SourceRefused):
        validate_name(name[:at] + char + name[at:])


KIND_TABLE = [
    ("a.pdf", SourceKind.PDF),
    ("a.htm", SourceKind.HTML),
    ("a.html", SourceKind.HTML),
    ("a.docx", SourceKind.DOCX),
    ("a.txt", SourceKind.TEXT),
    ("a.md", SourceKind.TEXT),
    ("a.xlsx", SourceKind.XLSX),
    ("a.csv", SourceKind.CSV),
    ("a.PDF", SourceKind.PDF),
    ("a.HTM", SourceKind.HTML),
    ("a.HTML", SourceKind.HTML),
    ("a.DOCX", SourceKind.DOCX),
    ("a.TXT", SourceKind.TEXT),
    ("a.MD", SourceKind.TEXT),
    ("a.XLSX", SourceKind.XLSX),
    ("a.CSV", SourceKind.CSV),
    ("notes/Summary.MD", SourceKind.TEXT),
    ("a.tar.pdf", SourceKind.PDF),
]


@pytest.mark.parametrize(("name", "kind"), KIND_TABLE)
def test_kind_of(name: str, kind: SourceKind) -> None:
    assert kind_of(name) == kind


@pytest.mark.parametrize("name", ["noext", "a.png", ".pdf"])
def test_kind_of_none(name: str) -> None:
    assert kind_of(name) is None


def test_suffix_kinds_read_only() -> None:
    assert dict(SUFFIX_KINDS) == {
        ".pdf": SourceKind.PDF,
        ".htm": SourceKind.HTML,
        ".html": SourceKind.HTML,
        ".docx": SourceKind.DOCX,
        ".txt": SourceKind.TEXT,
        ".md": SourceKind.TEXT,
        ".xlsx": SourceKind.XLSX,
        ".csv": SourceKind.CSV,
    }
    writable = cast("MutableMapping[str, SourceKind]", SUFFIX_KINDS)
    with pytest.raises(TypeError):
        writable[".png"] = SourceKind.TEXT


PDF = b"%PDF-1.4\n"
ZIP = b"PK\x03\x04rest"


@pytest.mark.parametrize(
    ("name", "kind", "raw", "message"),
    [
        ("x.pdf", SourceKind.PDF, b"hello", "x.pdf: does not start with %PDF-"),
        ("x.pdf", SourceKind.PDF, b"", "x.pdf: does not start with %PDF-"),
        ("x.docx", SourceKind.DOCX, b"hello", "x.docx: does not start with a zip signature"),
        ("x.docx", SourceKind.DOCX, b"", "x.docx: does not start with a zip signature"),
        ("x.xlsx", SourceKind.XLSX, b"hello", "x.xlsx: does not start with a zip signature"),
        ("x.xlsx", SourceKind.XLSX, b"", "x.xlsx: does not start with a zip signature"),
        ("x.html", SourceKind.HTML, PDF, "x.html: starts with a PDF signature"),
        ("x.csv", SourceKind.CSV, PDF, "x.csv: starts with a PDF signature"),
        ("x.txt", SourceKind.TEXT, PDF, "x.txt: starts with a PDF signature"),
        ("x.html", SourceKind.HTML, ZIP, "x.html: starts with a zip signature"),
        ("x.csv", SourceKind.CSV, ZIP, "x.csv: starts with a zip signature"),
        ("x.txt", SourceKind.TEXT, ZIP, "x.txt: starts with a zip signature"),
        ("a.pdf", SourceKind.PDF, b"%PDF1.4\n", "a.pdf: does not start with %PDF-"),
        (
            "a.docx",
            SourceKind.DOCX,
            b"PK\x05\x06" + b"\x00" * 18,
            "a.docx: does not start with a zip signature",
        ),
        (
            "x.bin",
            cast("SourceKind", "pdf"),
            b"MZ\x90\x00not a pdf",
            "x.bin: does not start with %PDF-",
        ),
    ],
)
def test_check_kind_refuses(name: str, kind: SourceKind, raw: bytes, message: str) -> None:
    with pytest.raises(SourceUnreadable) as caught:
        check_kind(name, kind, raw)
    assert str(caught.value) == message


@pytest.mark.parametrize(
    ("name", "kind", "raw"),
    [
        ("x.pdf", SourceKind.PDF, PDF),
        ("x.docx", SourceKind.DOCX, ZIP),
        ("x.xlsx", SourceKind.XLSX, ZIP),
        ("x.html", SourceKind.HTML, b"<p>x</p>"),
        ("x.csv", SourceKind.CSV, b"a,b\n"),
        ("x.txt", SourceKind.TEXT, b"note"),
        ("x.txt", SourceKind.TEXT, b""),
        ("x.html", SourceKind.HTML, b""),
        ("x.csv", SourceKind.CSV, b""),
        ("a.csv", SourceKind.CSV, b"PK,name\n"),
        ("a.txt", SourceKind.TEXT, b"%PDF is a format\n"),
    ],
)
def test_check_kind_accepts(name: str, kind: SourceKind, raw: bytes) -> None:
    check_kind(name, kind, raw)


def _readme() -> SourcePin:
    return SourcePin(name="readme.txt", sha256=README_SHA, size_bytes=16, kind=SourceKind.TEXT)


def test_pin_json_round_trip() -> None:
    pin = _readme()
    assert pin.model_dump_json() == README_JSON
    assert SourcePin.model_validate_json(README_JSON) == pin


def test_pin_is_frozen() -> None:
    with pytest.raises(ValidationError):
        _readme().size_bytes = 1


def test_pin_accepts_zero_size() -> None:
    pin = SourcePin(name="readme.txt", sha256=README_SHA, size_bytes=0, kind=SourceKind.TEXT)
    assert pin.size_bytes == 0


@pytest.mark.parametrize(
    "fields",
    [
        {"name": "../readme.txt"},
        {"sha256": README_SHA.upper()},
        {"sha256": README_SHA[:63]},
        {"sha256": README_SHA + "0"},
        {"size_bytes": -1},
        {"size_bytes": True},
        {"kind": SourceKind.PDF},
        {"name": "image.png"},
        {"extra": "x"},
    ],
)
def test_pin_rejects(fields: dict[str, object]) -> None:
    base: dict[str, object] = {
        "name": "readme.txt",
        "sha256": README_SHA,
        "size_bytes": 16,
        "kind": SourceKind.TEXT,
    }
    with pytest.raises(ValidationError):
        SourcePin.model_validate({**base, **fields})


def test_check_kind_refuses_a_value_that_is_no_kind() -> None:
    with pytest.raises(ValueError):
        check_kind("x.bin", cast("SourceKind", "pptx"), b"hello")
