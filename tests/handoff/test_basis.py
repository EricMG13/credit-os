import json
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from credit_os.handoff.basis import Basis, BasisItem, read_basis
from credit_os.handoff.blocks import ListItem, Paragraph
from credit_os.handoff.document import Section, parse

HERE = Path(__file__).resolve().parent
HANDOFFS = HERE.parent / "fixtures" / "handoffs"
KEY = json.loads((HERE / "expected" / "reader.json").read_text(encoding="utf-8"))


def src(file: str, *pages: tuple[int, int], text: str | None = None) -> BasisItem:
    return BasisItem(kind="source", text=text or file, file=file, pages=pages)


def txt(text: str) -> BasisItem:
    return BasisItem(kind="text", text=text)


def calc(ident: str) -> BasisItem:
    return BasisItem(kind="calculation", text=f"calculation {ident}", calculation=ident)


def mod(name: str, code: str) -> BasisItem:
    return BasisItem(kind="module", text=f"{name} ({code})", name=name, code=code)


def _items(x: str) -> tuple[BasisItem, ...]:
    result = read_basis(Paragraph(line=10, lines=("Body.", "Basis: " + x)))
    assert result is not None
    assert result.line == 11
    assert result.body == ("Body.",)
    return result.items


CASES: list[tuple[str, tuple[BasisItem, ...]]] = [
    ("a.pdf, page 3.", (src("a.pdf", (3, 3), text="a.pdf, page 3"),)),
    ("a.pdf, pages 3-5, 9", (src("a.pdf", (3, 5), (9, 9), text="a.pdf, pages 3-5, 9"),)),
    ("a.pdf, pages 43–45", (src("a.pdf", (43, 45), text="a.pdf, pages 43–45"),)),
    ("a.pdf, page 3 – 5", (src("a.pdf", (3, 5), text="a.pdf, page 3 – 5"),)),
    ("a.pdf, pages 3", (src("a.pdf", (3, 3), text="a.pdf, pages 3"),)),
    ("a.pdf, page 3, 5", (txt("a.pdf, page 3, 5"),)),
    ("a.pdf, page 3—5", (txt("a.pdf, page 3—5"),)),
    ("a.pdf, page iv", (txt("a.pdf, page iv"),)),
    ("a.pdf, p. 3", (txt("a.pdf, p. 3"),)),
    ("a.pdf", (src("a.pdf"),)),
    (
        "report.final.pdf, page 2",
        (src("report.final.pdf", (2, 2), text="report.final.pdf, page 2"),),
    ),
    ("v1.2 notes", (txt("v1.2 notes"),)),
    ("a.pdf..", (txt("a.pdf."),)),
    ("Annual report 2024, page 3", (txt("Annual report 2024, page 3"),)),
    ("calculation K1", (calc("K1"),)),
    ("calculation K 1", (txt("calculation K 1"),)),
    ("calculation", (txt("calculation"),)),
    ("Calculation K1", (txt("Calculation K1"),)),
    ("Financial foundation (CP-1)", (mod("Financial foundation", "CP-1"),)),
    ("Liquidity (old) (CP-2D)", (mod("Liquidity (old)", "CP-2D"),)),
    ("x (CP-1a)", (txt("x (CP-1a)"),)),
    ("(CP-1)", (txt("(CP-1)"),)),
    ("management statement", (txt("management statement"),)),
    (
        "a.pdf, page 41; calculation K1.",
        (src("a.pdf", (41, 41), text="a.pdf, page 41"), calc("K1")),
    ),
    ("a.pdf; ; b.pdf;  c.pdf ", (src("a.pdf"), src("b.pdf"), src("c.pdf"))),
    (
        "a.pdf, page 12; a.pdf, page 12",
        (src("a.pdf", (12, 12), text="a.pdf, page 12"),) * 2,
    ),
    ("a.pdf;b.pdf", (src("a.pdf;b.pdf"),)),
    ("a.pdf, pages x.pdf", (txt("a.pdf, pages x.pdf"),)),
    (".", ()),
    (".pdf", (txt(".pdf"),)),
    (".pdf, page 3", (txt(".pdf, page 3"),)),
    (".a.pdf, page 3", (src(".a.pdf", (3, 3), text=".a.pdf, page 3"),)),
    (
        "a.pdf, page 123456789",
        (src("a.pdf", (123456789, 123456789), text="a.pdf, page 123456789"),),
    ),
    ("a.pdf, page 1234567890", (txt("a.pdf, page 1234567890"),)),
    ("a.pdf, pages 1-1234567890", (txt("a.pdf, pages 1-1234567890"),)),
    ("a.pdf, page " + "1" * 5000, (txt("a.pdf, page " + "1" * 5000),)),
    ("a.pdf, page 3\t-\t5", (txt("a.pdf, page 3\t-\t5"),)),
    ("a.pdf, page 3\u00a0–\u00a05", (txt("a.pdf, page 3\u00a0–\u00a05"),)),
    ("a.abcde", (src("a.abcde"),)),
    ("a.abcdef", (txt("a.abcdef"),)),
    ("a.abcdef, page 3", (txt("a.abcdef, page 3"),)),
    ("a.b2c3d, page 3", (src("a.b2c3d", (3, 3), text="a.b2c3d, page 3"),)),
    ("v1.2", (txt("v1.2"),)),
    ("report.2024, page 3", (txt("report.2024, page 3"),)),
    ("section 4.2", (txt("section 4.2"),)),
]


@pytest.mark.parametrize(("x", "items"), CASES)
def test_expected_rows(x: str, items: tuple[BasisItem, ...]) -> None:
    assert _items(x) == items


def test_other_rows() -> None:
    assert read_basis(Paragraph(line=10, lines=("Basis: a.pdf",))) == Basis(
        line=10, body=(), items=(src("a.pdf"),)
    )
    item = ListItem(line=4, marker="-", lines=("One", "two", "Basis: calculation K1"))
    assert read_basis(item) == Basis(line=6, body=("One", "two"), items=(calc("K1"),))
    for lines in (
        ("Basis: a.pdf", "more"),
        ("Body.", "basis: a.pdf"),
        ("Body.", "Basis:a.pdf"),
        ("Body.", "Basis:"),
        ("Body.", "See Basis: a.pdf"),
    ):
        assert read_basis(Paragraph(line=10, lines=lines)) is None


def _walk(sections: tuple[Section, ...]) -> list[Section]:
    out: list[Section] = []
    for section in sections:
        out.append(section)
        out.extend(_walk(section.sections))
    return out


def _found(name: str) -> dict[int, Basis]:
    found: dict[int, Basis] = {}
    for section in _walk(parse((HANDOFFS / name).read_bytes()).sections):
        for block in section.blocks:
            if isinstance(block, Paragraph | ListItem):
                result = read_basis(block)
                if result is not None:
                    found[block.line] = result
    return found


def _shape(item: BasisItem) -> list[Any]:
    if item.kind == "source":
        return ["source", item.file, [list(span) for span in item.pages]]
    if item.kind == "calculation":
        return ["calculation", item.calculation]
    return [item.kind, item.name, item.code]


def test_fixture_rows() -> None:
    by_file: dict[str, dict[int, Basis]] = {}
    for name, block_line, basis_line, items in KEY["basis"]:
        found = by_file.setdefault(name, _found(name))
        assert found[block_line].line == basis_line
        assert [_shape(item) for item in found[block_line].items] == items


def test_fixture_totals() -> None:
    named = {row[0] for row in KEY["basis"]}
    counts = {name: len(_found(name)) for name in KEY["files"]}
    assert len(counts) == 25  # 27 fixtures less the two fragments parse refuses
    assert sum(counts[name] for name in named) == KEY["basis_blocks_total"]
    assert all(count == 0 for name, count in counts.items() if name not in named)


@given(st.lists(st.text(), min_size=1).map(tuple))
def test_property_body_and_no_raise(lines: tuple[str, ...]) -> None:
    result = read_basis(Paragraph(line=3, lines=lines))
    assert result is None or result.body == lines[:-1]


_FRAGMENTS = st.sampled_from(
    ["a.pdf", ".", "..", "x.b2", ", page ", ", pages ", "-", "–", " ", ", ", "; ", "7"]
    + ["calculation ", "K1", " (CP-1)", "name", "\t", "calculation K1"]
    + ["Financial foundation (CP-1)", "a.pdf, pages 3-5", "management statement"]
) | st.text(alphabet="0123456789", min_size=1, max_size=20)


@given(st.lists(_FRAGMENTS, max_size=14), st.lists(st.text(), max_size=2))
def test_property_basis_line_reaches_items(fragments: list[str], body: list[str]) -> None:
    lines = (*body, "Basis: " + "; ".join(fragments))
    result = read_basis(Paragraph(line=3, lines=lines))
    assert result is not None
    assert result.body == lines[:-1]
    assert all(item.text for item in result.items)


KNOWN = ("context", "context notes", "Annual report (CP-0)", "calculation C9", "a; b")


def _known(x: str, known: tuple[str, ...] = KNOWN) -> tuple[BasisItem, ...]:
    result = read_basis(Paragraph(line=10, lines=("Body.", "Basis: " + x)), known=known)
    assert result is not None
    return result.items


@pytest.mark.parametrize(
    ("x", "items"),
    [
        ("context, page 1", (src("context", (1, 1), text="context, page 1"),)),
        ("context.", (src("context"),)),
        ("context notes", (src("context notes"),)),
        (
            "context notes, pages 2-3, 7",
            (src("context notes", (2, 3), (7, 7), text="context notes, pages 2-3, 7"),),
        ),
        ("context notesx", (txt("context notesx"),)),
        ("Context, page 1", (txt("Context, page 1"),)),
        ("context , page 1", (txt("context , page 1"),)),
        ("context, page", (txt("context, page"),)),
        ("context, page 1, 2", (txt("context, page 1, 2"),)),
        ("Annual report (CP-0)", (mod("Annual report", "CP-0"),)),
        ("calculation C9", (calc("C9"),)),
        ("Annual report (CP-1)", (mod("Annual report", "CP-1"),)),
        ("a; b", (txt("a"), txt("b"))),
        ("x.pdf, page 2; calculation C1", (src("x.pdf", (2, 2), text="x.pdf, page 2"), calc("C1"))),
    ],
)
def test_known_source_names(x: str, items: tuple[BasisItem, ...]) -> None:
    assert _known(x) == items


def test_no_known_names_is_the_earlier_reading() -> None:
    assert _known("context, page 1", ()) == (txt("context, page 1"),)
    assert _items("context, page 1") == (txt("context, page 1"),)


def test_known_name_holding_a_page_phrase_is_the_whole_name() -> None:
    assert _known("a, page 1", ("a", "a, page 1")) == (
        BasisItem(kind="source", text="a, page 1", file="a, page 1"),
    )
