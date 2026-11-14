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
    "a\u3000b.txt",
    "a\u00a0b.txt",
    "clock.txt",
    "myclock$.txt",
    "CLOCK$x.txt",
    "a" * 251 + ".txt",
    "\u00e9" * 125 + ".txt",
    "/".join(["a" * 204] * 5),
    "CLOCK$\u00a0.txt",
    "CLOCK$X.txt",
    "COM00.txt",
    "COM0x.txt",
    "xCOM0.txt",
    "LPT.txt",
]
INVALID_NAMES = [
    ("Q3-report\u202efdp.txt", "forbidden character U+202E"),
    ("a\u0085b.txt", "forbidden character U+0085"),
    ("a\u2028b.txt", "forbidden character U+2028"),
    ("a\u2029b.txt", "forbidden character U+2029"),
    ("a\u200bb.txt", "forbidden character U+200B"),
    ("a\u009bb.txt", "forbidden character U+009B"),
    ("R\udce9sum\udce9.txt", "forbidden character U+DCE9"),
    ("NUL.txt", "reserved device name"),
    ("con.pdf", "reserved device name"),
    ("COM1.html", "reserved device name"),
    ("LPT1.csv", "reserved device name"),
    ("aux.md", "reserved device name"),
    ("notes/PRN.txt", "reserved device name"),
    ("CONIN$.txt", "reserved device name"),
    ("nul", "reserved device name"),
    ("a<b.txt", "forbidden character U+003C"),
    ("a>b.txt", "forbidden character U+003E"),
    ('a"b.txt', "forbidden character U+0022"),
    ("a|b.txt", "forbidden character U+007C"),
    ("a?b.txt", "forbidden character U+003F"),
    ("a*b.txt", "forbidden character U+002A"),
    ("", "empty or dot segment"),
    (".", "empty or dot segment"),
    ("..", "empty or dot segment"),
    ("/etc/passwd", "empty or dot segment"),
    ("../outside.txt", "empty or dot segment"),
    ("a/../b.txt", "empty or dot segment"),
    ("a/./b.txt", "empty or dot segment"),
    ("a//b.txt", "empty or dot segment"),
    ("a/", "empty or dot segment"),
    ("C:\\x.txt", "forbidden character U+003A"),
    ("C:x.txt", "forbidden character U+003A"),
    ("C:/x.txt", "forbidden character U+003A"),
    ("file.txt:stream", "forbidden character U+003A"),
    ("\\\\server\\share\\x.txt", "forbidden character U+005C"),
    ("a\\b.txt", "forbidden character U+005C"),
    ("a\x00b.txt", "forbidden character U+0000"),
    ("a\nb.txt", "forbidden character U+000A"),
    ("a\x1fb.txt", "forbidden character U+001F"),
    ("a\x7fb.txt", "forbidden character U+007F"),
    ("a.txt.", "segment starts or ends with a space or ends with a dot"),
    ("a.txt ", "segment starts or ends with a space or ends with a dot"),
    ("dir./a.txt", "segment starts or ends with a space or ends with a dot"),
    ("dir /a.txt", "segment starts or ends with a space or ends with a dot"),
    ("\ue000.txt", "forbidden character U+E000"),
    ("a\U000f0000.txt", "forbidden character U+F0000"),
    ("\ufdd0.txt", "forbidden character U+FDD0"),
    ("a\ufffe.txt", "forbidden character U+FFFE"),
    # unassigned in Unicode 15.0; depends on the interpreter's Unicode table
    ("a\u0378.txt", "forbidden character U+0378"),
    ("a.txt\u3000", "segment starts or ends with a space or ends with a dot"),
    ("\u00a0a.txt", "segment starts or ends with a space or ends with a dot"),
    (" a.txt", "segment starts or ends with a space or ends with a dot"),
    ("dir\u2003/a.txt", "segment starts or ends with a space or ends with a dot"),
    ("a/ b.txt", "segment starts or ends with a space or ends with a dot"),
    ("CLOCK$", "reserved device name"),
    ("clock$.txt", "reserved device name"),
    ("notes/Clock$.csv", "reserved device name"),
    ("CLOCK$ .tar.txt", "reserved device name"),
    ("a" * 252 + ".txt", "segment longer than 255 bytes"),
    ("\u00e9" * 126 + ".txt", "segment longer than 255 bytes"),
    ("/".join(["a" * 204] * 4 + ["a" * 205]), "longer than 1,024 bytes"),
    ("a" * 1100, "longer than 1,024 bytes"),
    ("a\x00b.txt ", "forbidden character U+0000"),
    ("a\x00" + "b" * 2000, "forbidden character U+0000"),
    ("NUL.txt.", "segment starts or ends with a space or ends with a dot"),
    ("../" + "a" * 300, "empty or dot segment"),
    ("ok.txt/" + "a" * 300, "segment longer than 255 bytes"),
    ("/".join(["\u00e9" * 127] * 5), "longer than 1,024 bytes"),
    ("con/a.txt", "reserved device name"),
    ("CLOCK$/a.txt", "reserved device name"),
    ("COM0", "reserved device name"),
    ("LPT0", "reserved device name"),
    ("COM0.txt", "reserved device name"),
    ("lpt0.csv", "reserved device name"),
    ("com0", "reserved device name"),
    ("a/COM0/b.txt", "reserved device name"),
    ("LPT0 .tar.txt", "reserved device name"),
    ("NUL." + "a" * 300, "reserved device name"),
    ("a" * 300 + ".", "segment starts or ends with a space or ends with a dot"),
]


@pytest.mark.parametrize("name", VALID_NAMES)
def test_validate_name_accepts(name: str) -> None:
    assert validate_name(name) == name


@pytest.mark.parametrize(("name", "reason"), INVALID_NAMES)
def test_validate_name_refuses(name: str, reason: str) -> None:
    with pytest.raises(SourceRefused) as caught:
        validate_name(name)
    shown = name if len(name) <= 120 else name[:120] + "\u2026"
    assert str(caught.value) == f"{shown!r}: {reason}"


def test_error_hierarchy() -> None:
    assert issubclass(SourceRefused, ValueError)
    assert issubclass(SourceRefused, SourceError)
    assert issubclass(SourceTooLarge, SourceUnreadable)
    assert issubclass(SourceUnreadable, SourceError)
    assert issubclass(SourceChanged, SourceError)
    assert not issubclass(SourceChanged, SourceUnreadable)


_RESERVED = {"CON", "PRN", "AUX", "NUL"}
_RESERVED |= {f"COM{n}" for n in range(10)} | {f"LPT{n}" for n in range(10)}
_ALPHABET = string.ascii_letters + string.digits + "\u00e9\u00df\u0416\u4e2d" + "-_ ."


def _is_reserved(segment: str) -> bool:
    return segment.split(".")[0].rstrip(" ").upper() in _RESERVED


_SEGMENT = st.text(alphabet=_ALPHABET, min_size=1, max_size=8).filter(
    lambda s: (
        s not in (".", "..")
        and not s.endswith((".", " "))
        and not s.startswith(" ")
        and not _is_reserved(s)
    )
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


@given(_NAMES, st.sampled_from(["\\", ":", "\x00", "\x1f", "\x7f", "\ue000", "\ufdd0"]), st.data())
def test_property_bad_character_refused(name: str, char: str, data: st.DataObject) -> None:
    at = data.draw(st.integers(min_value=0, max_value=len(name)))
    with pytest.raises(SourceRefused):
        validate_name(name[:at] + char + name[at:])


@given(_NAMES, st.integers(min_value=256, max_value=400))
def test_property_long_segment_refused(name: str, n: int) -> None:
    with pytest.raises(SourceRefused):
        validate_name(f"{name}/{'a' * n}")


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


CUT = "a" * 120 + "\u2026"


@pytest.mark.parametrize(
    ("name", "message"),
    [
        ("a" * 2000, "'" + CUT + "': longer than 1,024 bytes"),
        ("a" * 130 + "\x00", "'" + CUT + "': forbidden character U+0000"),
        (
            "a" * 120 + ".",
            "'" + CUT + "': segment starts or ends with a space or ends with a dot",
        ),
        (
            "a" * 119 + ".",
            "'" + "a" * 119 + ".': segment starts or ends with a space or ends with a dot",
        ),
        (
            "é" * 100 + ".",
            "'" + "é" * 100 + ".': segment starts or ends with a space or ends with a dot",
        ),
    ],
)
def test_validate_name_shows_at_most_120_characters(name: str, message: str) -> None:
    with pytest.raises(SourceRefused) as caught:
        validate_name(name)
    assert str(caught.value) == message


@pytest.mark.parametrize(
    ("name", "kind", "raw", "message"),
    [
        ("a" * 130 + ".pdf", SourceKind.PDF, b"hello", CUT + ": does not start with %PDF-"),
        (
            "a" * 130 + ".docx",
            SourceKind.DOCX,
            b"hello",
            CUT + ": does not start with a zip signature",
        ),
        ("a" * 130 + ".txt", SourceKind.TEXT, b"%PDF-1.4\n", CUT + ": starts with a PDF signature"),
        (
            "a" * 130 + ".csv",
            SourceKind.CSV,
            b"PK\x03\x04rest",
            CUT + ": starts with a zip signature",
        ),
    ],
)
def test_check_kind_shows_at_most_120_characters(
    name: str, kind: SourceKind, raw: bytes, message: str
) -> None:
    with pytest.raises(SourceUnreadable) as caught:
        check_kind(name, kind, raw)
    assert str(caught.value) == message


def test_pin_kind_mismatch_shows_at_most_120_characters() -> None:
    with pytest.raises(ValidationError) as caught:
        SourcePin.model_validate(
            {
                "name": "a" * 130 + ".txt",
                "sha256": README_SHA,
                "size_bytes": 16,
                "kind": SourceKind.PDF,
            }
        )
    assert "'" + CUT + "': kind 'pdf' does not match the name" in str(caught.value)
