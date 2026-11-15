"""The passage and cell builders of delivery, compared row by row with the controller's key."""

import decimal
import json
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

from credit_os.checks.figures import CODE
from credit_os.delivery import passages
from credit_os.delivery.errors import DeliveryRefused
from credit_os.handoff.data import source_names
from credit_os.handoff.document import HandoffDocument, parse
from credit_os.handoff.reader import Reader, read_reader

ROOT = Path(__file__).resolve().parents[2]
KEY = json.loads((Path(__file__).parent / "expected" / "passages.json").read_text("utf-8"))
FIXTURES = ROOT / KEY["fixtures"]


def ids(rows: list[dict[str, object]]) -> list[str]:
    return [str(row.get("id", i)) for i, row in enumerate(rows)]


def read_document(text: str) -> HandoffDocument:
    return parse(text.encode("utf-8"))


def read_fixture(name: str) -> HandoffDocument:
    return read_document((FIXTURES / name).read_text("utf-8"))


def edited(name: str, replace: list[list[str]]) -> HandoffDocument:
    text = (FIXTURES / name).read_text("utf-8")
    for old, new in replace:
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    return read_document(text)


def run_builder(builder: str, document: HandoffDocument) -> object:
    reader: Reader = read_reader(document)
    names = source_names(document)
    if builder == "bottomLine":
        return passages.bottom_line(reader, names)
    if builder == "findings":
        return passages.findings(reader, names)
    if builder == "contrary":
        return passages.contrary_and_change(reader, names)
    if builder == "limitations":
        return passages.limitations(document, names)
    if builder == "blocked":
        return passages.blocked_reason(reader, names)
    raise AssertionError(builder)


def expect(builder: str, expected: object) -> object:
    if builder == "findings":
        return tuple(expected) if isinstance(expected, list) else expected
    if builder == "limitations":
        return tuple(cast(list[object], expected))
    if builder == "contrary":
        return tuple(cast(list[object], expected))
    return expected


def attempt(call: Callable[[], object]) -> object:
    try:
        return call()
    except DeliveryRefused:
        return "refused"


@pytest.mark.parametrize("row", KEY["documents"], ids=ids(KEY["documents"]))
def test_documents(row: dict[str, object]) -> None:
    document = read_fixture(str(row["file"]))
    reader = read_reader(document)
    names = source_names(document)
    want_bottom = row["bottomLine"]
    assert attempt(lambda: passages.bottom_line(reader, names)) == want_bottom
    assert passages.findings(reader, names) == tuple(cast(list[object], row["findings"]))
    assert passages.contrary_and_change(reader, names) == (row["contrary"], row["changeView"])
    assert passages.limitations(document, names) == tuple(cast(list[object], row["limitations"]))
    assert attempt(lambda: passages.blocked_reason(reader, names)) == row["blocked"]


@pytest.mark.parametrize("row", KEY["marked"], ids=ids(KEY["marked"]))
def test_marked(row: dict[str, object]) -> None:
    document = edited(str(row["file"]), cast(list[list[str]], row["replace"]))
    got = run_builder(str(row["builder"]), document)
    assert got == expect(str(row["builder"]), row["expected"])


@pytest.mark.parametrize("row", KEY["refused"], ids=ids(KEY["refused"]))
def test_refused(row: dict[str, object]) -> None:
    document = edited(str(row["file"]), cast(list[list[str]], row["replace"]))
    with pytest.raises(DeliveryRefused) as raised:
        run_builder(str(row["builder"]), document)
    assert str(raised.value)


@pytest.mark.parametrize("row", KEY["cells"], ids=[str(i) for i in range(len(KEY["cells"]))])
def test_cells(row: list[object]) -> None:
    text, want, scale = row
    got, got_scale = passages.cell(cast(str, text))
    if want is None:
        assert got is None
    else:
        want_cell = dict(cast(dict[str, object], want))
        at = want_cell.get("at", "absent")
        assert got is not None
        if at != "absent":
            want_cell["at"] = None if at is None else Decimal(cast(str, at))
            assert got["at"] is None or isinstance(got["at"], Decimal)
        assert got == want_cell
    assert got_scale == (None if scale is None else tuple(cast(list[object], scale)))


@pytest.mark.parametrize("row", KEY["leaks"], ids=[str(i) for i in range(len(KEY["leaks"]))])
def test_leaks(row: list[object]) -> None:
    text, names, want = row
    got = passages.narrative_leaks(cast(str, text), cast(list[str], names))
    assert got == tuple(cast(list[str], want))


def test_empty_names_are_ignored() -> None:
    assert passages.narrative_leaks("plain text", ("",)) == ()


def test_non_str_cell_raises() -> None:
    call = cast(Callable[..., object], passages.cell)
    with pytest.raises(TypeError):
        call(5)


def test_leak_message_never_holds_the_name() -> None:
    document = edited(
        "SYNTHETIC-CP-1A.md",
        [
            [
                "rests on that company's cash generation.",
                "rests on that company's cash generation (NBG_2025-03-31_annual-report.pdf).",
            ]
        ],
    )
    with pytest.raises(DeliveryRefused) as raised:
        passages.bottom_line(read_reader(document), source_names(document))
    assert "NBG_2025" not in str(raised.value)


@given(st.text())
def test_cell_never_raises_and_never_floats(text: str) -> None:
    shown, scale = passages.cell(text)
    if shown is not None and shown["kind"] == "value":
        assert shown["at"] is None or isinstance(shown["at"], Decimal)
    assert scale is None or shown is not None


@given(
    st.text(alphabet="0123456789 .,-%x", min_size=1, max_size=12),
    st.characters(categories=("Nd", "Nl", "No"), exclude_characters="0123456789").filter(
        lambda c: c.isnumeric()
    ),
    st.integers(min_value=0, max_value=12),
)
def test_cell_with_a_numeric_character_other_than_0_to_9_has_no_at(
    base: str, inserted: str, position: int
) -> None:
    at = min(position, len(base))
    text = base[:at] + inserted + base[at:]
    assert passages.cell(text) == ({"kind": "value", "text": text, "at": None}, None)


@given(
    st.text(alphabet="abc xyz.", max_size=20),
    st.text(alphabet="ABCDEFGH_-.pdf", min_size=1, max_size=12),
    st.text(alphabet="abc xyz.", max_size=20),
)
def test_inserted_name_is_found(before: str, name: str, after: str) -> None:
    found = passages.narrative_leaks(before + name + after, (name,))
    assert name in found
    assert all(item in found for item in [m.group(0) for m in CODE.finditer(before + name + after)])


CONTEXTS = {
    "prec5-up": decimal.Context(prec=5, rounding=decimal.ROUND_UP),
    "prec3-trap": decimal.Context(prec=3, traps=[decimal.Rounded, decimal.Inexact]),
    "prec1-small": decimal.Context(prec=1, Emin=-3, Emax=3, traps=[], flags=[]),
}


@pytest.mark.parametrize("name", list(CONTEXTS))
@pytest.mark.parametrize("row", KEY["cells"], ids=[str(i) for i in range(len(KEY["cells"]))])
def test_cells_exact_in_any_context(name: str, row: list[object]) -> None:
    text, want, _scale = row
    with decimal.localcontext(CONTEXTS[name]):
        got, _ = passages.cell(cast(str, text))
    if isinstance(want, dict) and want.get("at") is not None:
        assert got is not None
        at = cast(Decimal, got["at"])
        assert at.as_tuple() == Decimal(cast(str, want["at"])).as_tuple()


DASH_LIKE_SIGNS = (
    0x2010,
    0x2011,
    0x2012,
    0x2013,
    0x2014,
    0x2015,
    0xFE58,
    0xFE63,
    0xFF0D,
    0x207B,
    0x208B,
    0x2796,
    0x02D7,
)


@st.composite
def _digits_with_sign(draw: st.DrawFn) -> str:
    base = draw(st.text(alphabet="0123456789.,", min_size=1))
    sign = chr(draw(st.sampled_from(DASH_LIKE_SIGNS)))
    at = draw(st.integers(min_value=0, max_value=len(base)))
    return base[:at] + sign + base[at:]


@given(_digits_with_sign())
def test_cell_dash_like_sign_gives_no_at(text: str) -> None:
    assert passages.cell(text) == ({"kind": "value", "text": text, "at": None}, None)


_ALLOWED_OUTSIDE = "".join(chr(point) for point in (0x00A0, 0x2212, 0x20AC, 0x00A3, 0x00A5))


@given(
    st.characters(
        min_codepoint=0x80,
        max_codepoint=0xFFFF,
        exclude_categories=["Cs"],
        exclude_characters=_ALLOWED_OUTSIDE,
    ),
    st.sampled_from(["{c}5", "5{c}", "USD {c}5"]),
)
def test_cell_with_a_stray_character_outside_the_figure_has_no_at(c: str, shape: str) -> None:
    text = shape.format(c=c)
    assert passages.cell(text) == ({"kind": "value", "text": text, "at": None}, None)
