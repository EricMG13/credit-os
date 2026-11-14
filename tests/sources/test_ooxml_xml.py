"""The XML half of the OOXML guards (`Package.parse`) and the expat pins it relies on.

Every fixture is built here from literals; expected values are literals or built as the brief
writes them, never by the code under test. A failing comparison of a long value reports lengths
and the first difference, not the whole repr.
"""

import io
import re
import sys
import tracemalloc
import zipfile
from collections.abc import Iterator
from typing import Any
from xml.parsers import expat

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from credit_os.sources import ooxml
from credit_os.sources.errors import SourceUnreadable
from credit_os.sources.ooxml import Package

PART = "xl/a.xml"
MIB = 1_048_576
PREFIX = "b.xlsx: 'xl/a.xml': "
DECLARATION = "a DOCTYPE or ENTITY declaration"
NUL = "a NUL byte (XML parts are read as UTF-8 only)"
LONG = "an XML tag, comment or reference longer than 1,048,576 bytes"
NAMES = "more than 4,096 different XML names"
DEEP = "XML nested deeper than 256 elements"
MALFORMED = "not well-formed XML"
E_ACUTE = "\N{LATIN SMALL LETTER E WITH ACUTE}"


def zipped(parts: dict[str, bytes], method: int = zipfile.ZIP_STORED) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", method) as archive:
        for name, data in parts.items():
            archive.writestr(name, data)
    return buffer.getvalue()


class Recorder:
    """A target that records what it is given; consecutive text is joined."""

    def __init__(self) -> None:
        self.events: list[object] = []

    def start(self, name: str, attributes: dict[str, str]) -> None:
        self.events.append(("start", name, attributes))

    def end(self, name: str) -> None:
        self.events.append(("end", name))

    def text(self, data: str) -> None:
        if self.events and isinstance(self.events[-1], str):
            self.events[-1] += data
        else:
            self.events.append(data)


def _parse(data: bytes) -> Recorder:
    target = Recorder()
    Package("b.xlsx", zipped({PART: data}, zipfile.ZIP_DEFLATED)).parse(PART, target)
    return target


def _first_difference(actual: object, expected: object) -> str:
    if isinstance(actual, list) and isinstance(expected, list):
        for index, (one, other) in enumerate(zip(actual, expected, strict=False)):
            if one != other:
                return f"item {index}: {_first_difference(one, other)}"
        return f"lengths {len(actual)} and {len(expected)}"
    if isinstance(actual, str) and isinstance(expected, str):
        for index, (one, other) in enumerate(zip(actual, expected, strict=False)):
            if one != other:
                return f"lengths {len(actual)} and {len(expected)}, first difference at {index}"
        return f"lengths {len(actual)} and {len(expected)}"
    if isinstance(actual, tuple) and isinstance(expected, tuple) and len(actual) == len(expected):
        for one, other in zip(actual, expected, strict=True):
            if one != other:
                return _first_difference(one, other)
    if isinstance(actual, dict) and isinstance(expected, dict):
        for key in actual.keys() | expected.keys():
            if actual.get(key) != expected.get(key):
                return f"key {key!r}: " + _first_difference(actual.get(key), expected.get(key))
    return f"{str(actual)[:60]!r} != {str(expected)[:60]!r}"


def _expect_events(data: bytes, expected: list[Any]) -> None:
    events = _parse(data).events
    if events != expected:
        pytest.fail(_first_difference(events, expected))


def _expect_refusal(data: bytes, reason: str, cause: type[BaseException] | None) -> None:
    with pytest.raises(SourceUnreadable) as caught:
        _parse(data)
    assert str(caught.value) == PREFIX + reason
    if cause is None:
        assert caught.value.__cause__ is None
    else:
        assert type(caught.value.__cause__) is cause


def _case(
    id_: str, data: bytes, expected: list[Any] | None, reason: str = "", cause: Any = None
) -> Any:
    return pytest.param(data, expected, reason, cause, id=id_)


def _chain(depth: int) -> bytes:
    return b"<a>" * depth + b"</a>" * depth


def _siblings(count: int) -> bytes:
    return b"<r>" + b"".join(b"<n%d/>" % i for i in range(count)) + b"</r>"


def _attributes(count: int) -> bytes:
    return b"<r " + b" ".join(b'k%d=""' % i for i in range(count)) + b"/>"


def _prefixes(count: int) -> bytes:
    return b"<r>" + b"".join(b'<a xmlns:p%d="u"/>' % i for i in range(count)) + b"</r>"


def _start(name: str) -> tuple[str, str, dict[str, str]]:
    return ("start", name, {})


XM1 = [
    ("start", "u}a", {"v}k": "1", "k": "2"}),
    "t",
    ("start", "u}b", {}),
    ("end", "u}b"),
    "u",
    ("end", "u}a"),
]
XM29 = (
    [_start("r")]
    + [event for i in range(4_095) for event in (_start(f"n{i}"), ("end", f"n{i}"))]
    + [("end", "r")]
)
XM2 = b"<!DOCTYPE a><a/>"
XM3 = b'<!DOCTYPE a [<!ENTITY e "x">]><a>&e;</a>'
XM20 = b'<a k="' + b"y" * 1_048_567 + b'"/>'
XM21 = b'<a k="' + b"y" * 1_048_568 + b'"/>'
XM26 = b"<a>" + b"y" * 2_097_152 + b"</a>"
XM31 = _attributes(4_096)
XM32 = _prefixes(4_095)
ROWS = [
    _case("xm1", b'<a xmlns="u" xmlns:p="v" p:k="1" k="2">t<b/>u</a>', XM1),
    _case("xm2", XM2, None, DECLARATION),
    _case("xm3", XM3, None, DECLARATION),
    _case("xm4", b"<a><!-- <!dOcTyPe --></a>", None, DECLARATION),
    _case("xm5", b"<a><![CDATA[<!ENTITY]]></a>", None, DECLARATION),
    _case("xm6", b"<a>&lt;!DOCTYPE</a>", [_start("a"), "<!DOCTYPE", ("end", "a")]),
    _case("xm7", b"<a>\x00</a>", None, NUL),
    _case("xm8", "<a/>".encode("utf-16"), None, NUL),
    _case("xm9", b"<a>\xff</a>", None, "not valid UTF-8", UnicodeDecodeError),
    _case("xm10", b"<a/>\xe2\x82", None, "not valid UTF-8", UnicodeDecodeError),
    _case("xm11", b"\xef\xbb\xbf<a>t</a>", [_start("a"), "t", ("end", "a")]),
    _case(
        "xm12",
        b'<?xml version="1.0" encoding="ISO-8859-1"?><a>\xc3\xa9</a>',
        [_start("a"), E_ACUTE, ("end", "a")],
    ),
    _case("xm13", b"<a><b></a>", None, MALFORMED, expat.ExpatError),
    _case("xm14", b"<a>&nbsp;</a>", None, MALFORMED, expat.ExpatError),
    _case("xm15", b"<a><p:b/></a>", None, MALFORMED, expat.ExpatError),
    _case("xm16", b'<a k="1" k="2"/>', None, MALFORMED, expat.ExpatError),
    _case("xm17", b"<a>&#xD800;</a>", None, MALFORMED, expat.ExpatError),
    _case("xm18", b"<a/>x", None, MALFORMED, expat.ExpatError),
    _case("xm19", b"", None, MALFORMED, expat.ExpatError),
    _case("xm20", XM20, [("start", "a", {"k": "y" * 1_048_567}), ("end", "a")]),
    _case("xm21", XM21, None, LONG),
    _case("xm22", b"<a><!--" + b"<>" * 524_300 + b"--></a>", None, LONG),
    _case("xm23", b"<a><?p " + b"y" * 1_048_577 + b"?></a>", None, LONG),
    _case("xm24", b"<a>&" + b"y" * 1_048_577 + b"</a>", None, LONG),
    _case("xm25", b'<a k="' + b">" * 1_048_577 + b'"/>', None, LONG),
    _case("xm26", XM26, [_start("a"), "y" * 2_097_152, ("end", "a")]),
    _case("xm27", _chain(256), [_start("a")] * 256 + [("end", "a")] * 256),
    _case("xm28", _chain(257), None, DEEP),
    _case("xm29", _siblings(4_095), XM29),
    _case("xm30", _siblings(4_096), None, NAMES),
    _case("xm31", XM31, None, NAMES),
    _case("xm32", XM32, None, NAMES),
]


U = b"u" * 1_048_000
LENGTH = "an XML name longer than 255 bytes"
OPEN = "more than 4,096 namespace declarations open at once"
H3_NAMES = [
    e for _ in range(2) for i in range(2048) for e in (_start(f"u}}n{i}"), ("end", f"u}}n{i}"))
]
HIDDEN = [
    _case("h1", b'<r xmlns:p="' + U + b'"><p:a/><p:b/></r>', None, LENGTH),
    _case(
        "h2",
        b'<r xmlns:p="u" xmlns:q="u">'
        + b"".join(b"<p:n%d/>" % i for i in range(2048))
        + b"".join(b"<q:n%d/>" % i for i in range(2048))
        + b"</r>",
        None,
        NAMES,
    ),
    _case(
        "h3",
        b'<r xmlns:p="u">' + b"".join(b"<p:n%d/>" % i for i in range(2048)) * 2 + b"</r>",
        [_start("r")] + H3_NAMES + [("end", "r")],
    ),
    _case("h4", b"<r><" + b"n" * 600_000 + b"/><" + b"m" * 600_000 + b"/></r>", None, LENGTH),
    _case("h5", b'<a xmlns="x}y"/>', None, MALFORMED, expat.ExpatError),
    _case(
        "h6",
        b'<a xmlns="u" xmlns:p="v" xmlns:q="v" p:k="1" k="2"><p:b q:j="3"/><q:b/></a>',
        [
            ("start", "u}a", {"v}k": "1", "k": "2"}),
            ("start", "v}b", {"v}j": "3"}),
            ("end", "v}b"),
            ("start", "v}b", {}),
            ("end", "v}b"),
            ("end", "u}a"),
        ],
    ),
]


def _declarations(count: int) -> bytes:
    return b" ".join(b'xmlns:p%d="u"' % i for i in range(count))


N4 = b"<a " + _declarations(2048) + b"><b " + _declarations(2049) + b"/></a>"
N5 = b"<a " + _declarations(2048) + b"><b " + _declarations(2048) + b"/></a>"


def _namespaces(count: int) -> bytes:
    # names r, a, xmlns:p and each namespace name: 4,096 at 4,093 namespace names
    return b"<r>" + b"".join(b'<a xmlns:p="u%d"/>' % i for i in range(count)) + b"</r>"


def _closed(last: int) -> bytes:
    held = b"<a " + _declarations(4_093) + b">" + b'<a xmlns:p0="u"/>' * 3
    return held + b"<a " + _declarations(last) + b"/></a>"


E = [_start("e"), ("end", "e")]
CJK = "\N{CJK UNIFIED IDEOGRAPH-4E00}"
R4 = [_start("r")] + [_start("a"), ("end", "a")] * 4_093 + [("end", "r")]
R5 = [_start("a")] + [_start("a"), ("end", "a")] * 4 + [("end", "a")]
NAME_ROWS = [
    _case("n1", b"<" + b"n" * 255 + b"/>", [_start("n" * 255), ("end", "n" * 255)]),
    _case("n2", b"<" + b"n" * 256 + b"/>", None, LENGTH),
    _case(
        "n3",
        b"<r>" + b"".join(b'<a xmlns="u%d"/>' % i for i in range(4096)) + b"</r>",
        None,
        NAMES,
    ),
    _case("n4", N4, None, OPEN),
    _case("n5", N5, [_start("a"), _start("b"), ("end", "b"), ("end", "a")]),
    _case(
        "n6",
        b"<r>" + b'<a xmlns:p="u"/>' * 10_000 + b"</r>",
        [_start("r")] + [_start("a"), ("end", "a")] * 10_000 + [("end", "r")],
    ),
    _case("n7", b"\xef\xbb\xbf\xef\xbb\xbf<a>t</a>", [_start("a"), "t", ("end", "a")]),
    _case(
        "n8",
        b'<a xmlns="u"><b xmlns=""/></a>',
        [_start("u}a"), _start("b"), ("end", "b"), ("end", "u}a")],
    ),
    _case("n9", f"<{CJK * 85}/>".encode(), [_start(CJK * 85), ("end", CJK * 85)]),
    _case("n10", f"<{CJK * 86}/>".encode(), None, LENGTH),
    _case("r1", b"<e xmlns:" + b"p" * 249 + b'="u"/>', E),
    _case("r2", b"<e xmlns:" + b"p" * 250 + b'="u"/>', None, LENGTH),
    _case("r3", b'<e xmlns:p="' + b"u" * 255 + b'"/>', E),
    _case("r3b", b'<e xmlns:p="' + b"u" * 256 + b'"/>', None, LENGTH),
    _case("r4", _namespaces(4_093), R4),
    _case("r4b", _namespaces(4_094), None, NAMES),
    _case("r5", _closed(3), R5),
    _case("r5b", _closed(4), None, OPEN),
]


@pytest.mark.parametrize(("data", "expected", "reason", "cause"), ROWS + HIDDEN + NAME_ROWS)
def test_xml_rows(
    data: bytes, expected: list[Any] | None, reason: str, cause: type[BaseException] | None
) -> None:
    if expected is not None:
        _expect_events(data, expected)
    else:
        _expect_refusal(data, reason, cause)


@pytest.mark.parametrize(
    "data", [b"<a><!-- <!dOcTyPe --></a>", b"<a><![CDATA[<!ENTITY]]></a>"], ids=["t1", "t2"]
)
def test_declaration_across_pieces_of_16_bytes(
    data: bytes, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ooxml, "CHUNK_BYTES", 16)
    _expect_refusal(data, DECLARATION, None)


class _Calls:
    def __init__(self) -> None:
        self.texts: list[str] = []

    def start(self, name: str, attributes: dict[str, str]) -> None:
        pass

    def end(self, name: str) -> None:
        pass

    def text(self, data: str) -> None:
        self.texts.append(data)


def _raw(data: bytes) -> bytes:
    return zipped({PART: data}, zipfile.ZIP_DEFLATED)


def test_a_run_of_text_with_a_reference_is_one_call() -> None:
    target = _Calls()
    Package("b.xlsx", _raw(b"<a>one &amp; two\nthree</a>")).parse(PART, target)
    assert target.texts == ["one & two\nthree"]


@pytest.mark.parametrize("chunk", [1, 40])
def test_an_unfinished_tag_of_exactly_the_limit_at_the_end_is_not_well_formed(
    chunk: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ooxml, "MAX_TOKEN_BYTES", 40)
    monkeypatch.setattr(ooxml, "CHUNK_BYTES", chunk)
    unfinished = b'<e k="' + b"v" * 34
    assert len(unfinished) == 40
    with pytest.raises(SourceUnreadable) as caught:
        Package("b.xlsx", _raw(b"<r>" + unfinished)).parse(PART, _Calls())
    assert str(caught.value) == "b.xlsx: 'xl/a.xml': not well-formed XML"
    assert type(caught.value.__cause__) is expat.ExpatError


def test_an_end_below_the_root_restores_the_depth_by_one() -> None:
    data = b"<r><a><x/>" + b"<b>" * 255 + b"</b>" * 255 + b"</a></r>"
    with pytest.raises(SourceUnreadable) as caught:
        Package("b.xlsx", _raw(data)).parse(PART, _Calls())
    assert str(caught.value) == "b.xlsx: 'xl/a.xml': XML nested deeper than 256 elements"
    assert caught.value.__cause__ is None


def test_the_limits() -> None:
    assert ooxml.CHUNK_BYTES <= ooxml.MAX_TOKEN_BYTES
    assert ooxml.MAX_NAME_LENGTH == 255


@pytest.mark.parametrize("data", [XM2, XM3], ids=["xm2", "xm3"])
def test_second_guard_is_expats_own_handler(data: bytes, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ooxml, "_DECLARATION", re.compile(rb"(?!)"))
    _expect_refusal(data, DECLARATION, None)


def test_refusal_inside_a_handler_is_the_same_source_unreadable() -> None:
    # xm28 is raised from expat's start handler: no ExpatError wrapper, no cause.
    with pytest.raises(SourceUnreadable) as caught:
        _parse(_chain(257))
    assert type(caught.value) is SourceUnreadable
    assert caught.value.__cause__ is None


def test_limits_are_read_at_call_time(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ooxml, "MAX_DEPTH", 2)
    monkeypatch.setattr(ooxml, "MAX_NAMES", 2)
    _expect_refusal(_chain(3), "XML nested deeper than 2 elements", None)
    _expect_refusal(b"<a><b/><c/></a>", "more than 2 different XML names", None)


def test_part_is_read_through_pieces_only(monkeypatch: pytest.MonkeyPatch) -> None:
    sizes: list[int] = []
    original = Package.pieces

    def recording(self: Package, part: str) -> Iterator[bytes]:
        for piece in original(self, part):
            sizes.append(len(piece))
            yield piece

    monkeypatch.setattr(Package, "pieces", recording)
    monkeypatch.setattr(ooxml, "CHUNK_BYTES", 5)
    assert _parse(b"<a>text</a>").events == [_start("a"), "text", ("end", "a")]
    assert sizes == [5, 5, 1]


def _fail(what: str, value: object, expected: object) -> str:
    return f"{what}: {value!r} != {expected!r} on {sys.version}"


def test_pin9_a_str_ignores_the_declared_encoding_and_names_are_uri_local() -> None:
    events: list[object] = []
    parser = expat.ParserCreate(None, "}")
    parser.StartElementHandler = lambda name, attributes: events.append((name, attributes))
    parser.Parse(
        '<?xml version="1.0" encoding="UTF-16"?><a xmlns="u" xmlns:p="v" p:k="' + E_ACUTE + '"/>',
        True,
    )
    expected = [("u}a", {"v}k": E_ACUTE})]
    assert events == expected, _fail("events", events, expected)


def test_pin10_buffered_text_comes_whole_up_to_the_next_tag() -> None:
    pieces: list[str] = []
    parser = expat.ParserCreate(None, "}")
    parser.buffer_text = True
    parser.CharacterDataHandler = pieces.append
    for piece in ("<a>one &amp; ", "two<!-- c --> three<b/>", "four</a>"):
        parser.Parse(piece, False)
    parser.Parse("", True)
    expected = ["one & ", "two three", "four"]
    assert pieces == expected, _fail("pieces", pieces, expected)


def test_pin11_reparse_deferral_is_on_by_default() -> None:
    parser = expat.ParserCreate(None, "}")
    assert parser.GetReparseDeferralEnabled() is True, sys.version


def test_pin12_a_namespace_name_holding_the_separator_is_refused() -> None:
    parser = expat.ParserCreate(None, "}")
    try:
        parser.Parse('<a xmlns="x}y"/>', True)
    except expat.ExpatError:
        return
    pytest.fail(f"expat accepted a namespace name holding the separator on {sys.version}")


def _peak(data: bytes, reason: str) -> int:
    """Peak traced memory of one parse, after one warm-up call; the recorder is counted."""
    raw = zipped({PART: data}, zipfile.ZIP_DEFLATED)
    for _ in range(2):
        package = Package("b.xlsx", raw)
        target = Recorder()
        tracemalloc.start()
        try:
            try:
                package.parse(PART, target)
                outcome = ""
            except SourceUnreadable as error:
                outcome = str(error).removeprefix(PREFIX)
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
        assert outcome == reason, f"outcome {outcome!r} != {reason!r} on {sys.version}"
    return peak


MEMORY = {
    "xm20": (XM20, 6, ""),
    "xm21": (XM21, 6, LONG),
    "xm26": (XM26, 7, ""),
    "xm31": (XM31, 4, NAMES),
    "xm32": (XM32, 4, NAMES),
}


@pytest.mark.parametrize(("data", "ceiling", "reason"), list(MEMORY.values()), ids=list(MEMORY))
def test_memory_rows(data: bytes, ceiling: int, reason: str) -> None:
    peak = _peak(data, reason)
    sys.stdout.write(f"peak {peak / MIB:.2f} MiB of {ceiling} MiB\n")
    assert peak <= ceiling * MIB, f"peak {peak / MIB:.2f} MiB over {ceiling} MiB on {sys.version}"


def _outcome(data: bytes, size: int) -> tuple[Any, ...]:
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(ooxml, "MAX_TOKEN_BYTES", 40)
        patch.setattr(ooxml, "CHUNK_BYTES", size)
        target = Recorder()
        try:
            Package("b.xlsx", zipped({PART: data}, zipfile.ZIP_DEFLATED)).parse(PART, target)
        except SourceUnreadable as error:
            return ("refused", str(error), type(error.__cause__))
        return ("read", target.events)


# Whole fragments only, never one cut mid-token; every tag, comment, instruction and reference
# among the good ones is at most 40 bytes.
GOOD = [
    b"<b>x</b>",
    b"<b></b>",
    b"<c/>",
    b"text ",
    b"&amp;",
    b"&#65;",
    b"<!-- c -->",
    b"<?p i?>",
    b"<![CDATA[ <y> ]]>",
    b"<d k=\"a>b\" j='c>d'/>",
    b"<n:a xmlns:n='u'/>",
    b"\xc3\xa9",
    b">",
    b"'",
]
# At most one fault per part: with two, which is reported depends on where the pieces fall. A
# declaration is placed where XML allows one (before the root): inside an element expat refuses
# its first bytes as not well-formed before the byte search has seen all of "<!DOCTYPE".
PROLOG = b'<!DOCTYPE r [<!ENTITY e "x">]>'
FAULTS = [
    b"\x00",
    b"\xff",
    b"</z>",
    b"&nope;",
    b"<e k='" + b"v" * 40 + b"'/>",
    b"<!--" + b"c" * 40 + b"-->",
    b"&" + b"n" * 40 + b";",
    b"<![CDATA[" + b"z" * 40 + b"]]>",
]


@st.composite
def _parts(draw: st.DrawFn) -> bytes:
    body = draw(st.lists(st.sampled_from(GOOD), max_size=40))
    fault = draw(st.one_of(st.none(), st.just(PROLOG), st.sampled_from(FAULTS)))
    if fault is not None and fault != PROLOG:
        body.insert(draw(st.integers(0, len(body))), fault)
    return (PROLOG if fault == PROLOG else b"") + b"<r>" + b"".join(body) + b"</r>"


@st.composite
def _any_parts(draw: st.DrawFn) -> bytes:
    """Any number of faults anywhere, DOCTYPE and ENTITY inside elements included."""
    loose = [b"<!DOCTYPE a>", b"<!entity e>", PROLOG]
    pieces = draw(st.lists(st.sampled_from(GOOD + FAULTS + loose), max_size=40))
    wrap = draw(st.booleans())
    return b"<r>" + b"".join(pieces) + b"</r>" if wrap else b"".join(pieces)


@settings(max_examples=1_000, deadline=None)
@given(_any_parts())
def test_read_or_refused_alike_at_every_piece_size(data: bytes) -> None:
    assert len(data) < 4_096
    outcomes = [_outcome(data, size) for size in (1, 3, 16, 40)]
    if outcomes[0][0] == "read":
        assert all(outcome == outcomes[0] for outcome in outcomes), "read differently by size"
    else:
        assert all(outcome[0] == "refused" for outcome in outcomes), "read at one size only"


@settings(max_examples=1_000, deadline=None)
@given(_parts())
def test_one_fault_gives_the_same_refusal_at_every_piece_size(data: bytes) -> None:
    assert len(data) < 4_096
    first = _outcome(data, 40)
    for size in (1, 3, 16):
        assert _outcome(data, size) == first, f"piece size {size} differs from 40"


@st.composite
def _documents(draw: st.DrawFn) -> tuple[bytes, bool]:
    """A well-formed part and whether a tag, comment, instruction or reference passes 40 bytes."""
    longest = 0
    out = [b"<r>"]
    for _ in range(draw(st.integers(0, 12))):
        kind = draw(st.sampled_from(["element", "empty", "comment", "pi", "reference", "text"]))
        size = draw(st.integers(0, 60))
        tokens: list[int] = []
        if kind == "element":
            start = b'<e k="' + b"v" * size + b'">'
            out += [start, draw(st.sampled_from([b"", b"t", b"&amp;"])), b"</e>"]
            tokens = [len(start)]
        elif kind == "empty":
            out.append(b"<e k='" + b">" * size + b"'/>")
            tokens = [len(out[-1])]
        elif kind == "comment":
            out.append(b"<!--" + b"c" * size + b"-->")
            tokens = [len(out[-1])]
        elif kind == "pi":
            out.append(b"<?p " + b"i" * size + b"?>")
            tokens = [len(out[-1])]
        elif kind == "reference":
            out.append(b"&#x" + b"0" * size + b"41;")
            tokens = [len(out[-1])]
        else:
            out.append(b"t" * (size * 3))
        longest = max([longest, *tokens])
    out.append(b"</r>")
    return b"".join(out), longest > 40


@settings(max_examples=1_000, deadline=None)
@given(_documents(), st.sampled_from([1, 3, 16, 40]))
def test_refused_exactly_when_a_token_passes_the_limit(
    document: tuple[bytes, bool], size: int
) -> None:
    data, too_long = document
    assert len(data) < 4_096
    outcome = _outcome(data, size)
    if too_long:
        message = "b.xlsx: 'xl/a.xml': an XML tag, comment or reference longer than 40 bytes"
        assert outcome == ("refused", message, type(None))
    else:
        assert outcome[0] == "read", outcome
