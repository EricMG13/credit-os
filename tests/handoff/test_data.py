import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from credit_os.handoff.basis import read_basis
from credit_os.handoff.blocks import ListItem, Paragraph
from credit_os.handoff.data import (
    Gap,
    passage_value,
    read_data_sections,
    read_registers,
    read_value,
    source_names,
    sources_table,
)
from credit_os.handoff.document import HandoffDocument, Section, parse
from credit_os.handoff.reader import read_reader
from credit_os.handoff.scan import Comment
from credit_os.handoff.tables import Table

HERE = Path(__file__).resolve().parent
HANDOFFS = HERE.parent / "fixtures" / "handoffs"
KEY = json.loads((HERE / "expected" / "data.json").read_text(encoding="utf-8"))
VIEWS = json.loads((HERE / "expected" / "data-views.json").read_text(encoding="utf-8"))
ALL_KEYS: dict[str, Any] = {**KEY, **VIEWS}
GAPS = [
    "",
    "—",
    "Insufficient Information",
    "Not reconstructed",
    "Not supplied",
    "Not supplied: no filing",
    "Not suppliedX",
    "Not calculable — no base",
]
NOT_GAPS = [
    "0",
    " ",
    "—.",
    "— (reported dash)",
    "**Not supplied**",
    "not supplied",
    " Not supplied",
    "Insufficient Information.",
    "Not assessable",
    "-",
]


@pytest.mark.parametrize("text", GAPS)
def test_gap_values(text: str) -> None:
    assert read_value(text) == Gap(text=text)


@pytest.mark.parametrize("text", NOT_GAPS)
def test_not_gap_values(text: str) -> None:
    result = read_value(text)
    assert isinstance(result, str)
    assert result == text


def test_gap_is_not_a_string() -> None:
    empty: object = ""
    assert Gap(text="") != empty


def test_passage_value() -> None:
    assert passage_value(Paragraph(line=1, lines=("Not supplied:", "no filing"))) == Gap(
        text="Not supplied: no filing"
    )
    assert passage_value(ListItem(line=1, marker="-", lines=("Fine.",))) == "Fine."


PASSAGES = [
    ("Insufficient Information\nBasis: context, page 1.\n", Gap(text="Insufficient Information")),
    ("Not reconstructed\nBasis: calculation C1.\n", Gap(text="Not reconstructed")),
    ("—\nBasis: context.\n", Gap(text="—")),
    ("Not supplied: no filing\nBasis: context, page 1.\n", Gap(text="Not supplied: no filing")),
    ("Insufficient Information\n", Gap(text="Insufficient Information")),
    ("Leverage is 5.2x.\nBasis: calculation C1.\n", "Leverage is 5.2x."),
]


@pytest.mark.parametrize(("passage", "want"), PASSAGES)
def test_passage_value_ignores_the_basis_line(passage: str, want: Gap | str) -> None:
    block = _doc("", "### Bottom line\n" + passage).sections[2].sections[0].blocks[0]
    assert isinstance(block, Paragraph)
    assert passage_value(block) == want


def _doc(sources: str, extra: str = "") -> HandoffDocument:
    text = (
        f"## Request\nr\n## Sources\n{sources}\n## Findings\n{extra}"
        "## Calculations\n## Gaps\n## Next module\n"
    )
    return parse(text.encode())


T1 = "\n| Name | Use |\n| --- | --- |\n| context | x |\n|  | y |\n| a.pdf | z |\n"
T2 = "\n| N | U |\n| --- | --- |\n| b | y |\n"


def test_sources_one_table() -> None:
    document = _doc(T1)
    table = sources_table(document)
    assert isinstance(table, Table)
    assert table.columns == ("Name", "Use")
    assert source_names(document) == ("context", "a.pdf")


@pytest.mark.parametrize(
    "sources", [T1 + T2, "### Sub\n" + T1, "text only\n"], ids=["two", "subsection", "none"]
)
def test_sources_not_readable(sources: str) -> None:
    document = _doc(sources)
    assert sources_table(document) is None
    assert source_names(document) == ()


def test_comments_keep_file_lines() -> None:
    text = "## Request\nr\n<!-- a -->\n## Sources\n<!-- b\nc -->\n## Findings\n"
    text += "## Calculations\n## Gaps\n## Next module\n"
    assert parse(text.encode()).comments == (
        Comment(start=3, end=3, text="a"),
        Comment(start=5, end=6, text="b\nc"),
    )


def test_comments_after_front_matter() -> None:
    text = "---\nk: v\n---\n## Request\n<!-- a -->\n## Sources\n## Findings\n"
    text += "## Calculations\n## Gaps\n## Next module\n"
    assert parse(text.encode()).comments == (Comment(start=5, end=5, text="a"),)


def _walk(sections: tuple[Section, ...]) -> list[Section]:
    out: list[Section] = []
    for section in sections:
        out.append(section)
        out.extend(_walk(section.sections))
    return out


def _gap_cells(document: HandoffDocument) -> int:
    tables = [b for s in _walk(document.sections) for b in s.blocks if isinstance(b, Table)]
    return sum(isinstance(read_value(c), Gap) for t in tables for r in t.rows for c in r.cells)


@pytest.mark.parametrize("name", sorted(ALL_KEYS))
def test_golden_data(name: str) -> None:
    want: Any = ALL_KEYS[name]
    document = parse((HANDOFFS / name).read_bytes())
    assert read_reader(document).blocked is want["blocked"]
    table = sources_table(document)
    assert [None if table is None else table.line, list(source_names(document))] == want["sources"]
    assert _gap_cells(document) == want["gap_cells"]
    assert [[c.start, c.end, c.text] for c in document.comments] == want["comments"]
    assert [
        [s.kind, s.name, s.section.line, None if s.table is None else s.table.line, _sha(s.text)]
        for s in read_data_sections(document)
    ] == want["sections"]
    assert [
        [r.id, r.source, r.line, None if r.table is None else r.table.line]
        for r in read_registers(document)
    ] == want["registers"]


@pytest.mark.parametrize("name", sorted(VIEWS))
def test_golden_data_views(name: str) -> None:
    want: Any = VIEWS[name]
    document = parse((HANDOFFS / name).read_bytes())
    reader = read_reader(document)
    assert reader.bottom_line is not None
    assert reader.contrary is not None
    assert reader.limitations is not None
    first = reader.bottom_line.blocks[0]
    assert isinstance(first, Paragraph | ListItem)
    basis = read_basis(first, known=source_names(document))
    assert basis is not None
    assert [[i.kind, i.text] for i in basis.items] == want["bottom_line_basis"]
    gap = reader.contrary.blocks[0]
    assert isinstance(gap, Paragraph | ListItem)
    value = passage_value(gap)
    assert isinstance(value, Gap)
    assert value.text == want["contrary_gap"]
    assert len(reader.limitations.blocks) == want["limitations_blocks"]


def _sha(text: str | None) -> str | None:
    return None if text is None else hashlib.sha256(text.encode("utf-8")).hexdigest()


TB = "\n| A | B |\n| --- | --- |\n| 1 | 2 |\n"
CI = "\n| Input | Value |\n| --- | --- |\n| x | 1 |\n| y | 2 |\n"
CS = "\n| Input | Score |\n| --- | --- |\n| x | 1 |\n"
JS = "```json\n" + '{"a": 1}\nnot json at all\n' + "```\n"
JSON_TEXT = '{"a": 1}\nnot json at all'


def _sections(extra: str, tail: str = "") -> list[tuple[str, str, bool, str | None]]:
    text = f"## Request\nr\n## Sources\n\n## Findings\n{extra}## Calculations\n## Gaps\n{tail}"
    document = parse((text + "## Next module\n").encode())
    return [(s.kind, s.name, s.table is not None, s.text) for s in read_data_sections(document)]


@pytest.mark.parametrize(
    ("extra", "want"),
    [
        ("### Chart data: leverage\n" + TB, [("chart", "leverage", True, None)]),
        (
            "### Outer\n#### Map:   holding chain  \n" + TB,
            [("map", "holding chain", True, None)],
        ),
        (
            "### Chart data:leverage\n### chart data: x\n### Events\n### Mapping: x\n",
            [],
        ),
        ("### Events: calendar\n" + TB + TB, [("events", "calendar", False, None)]),
        ("### Events: calendar\n", [("events", "calendar", False, None)]),
        ("### Confidence inputs\n" + CI, [("confidence", "", True, None)]),
        ("### Confidence inputs\n" + CS, [("confidence", "", False, None)]),
        ("### Confidence inputs (draft)\n" + CI, [("confidence", "(draft)", True, None)]),
        (
            "### Forecast inputs (machine-readable)\n" + JS,
            [("forecast", "(machine-readable)", False, JSON_TEXT)],
        ),
        (
            "### Forecast inputs\n```JSON\nx\n```\n",
            [("forecast", "", False, None)],
        ),
        ("### Forecast inputs\n```\nx\n```\n", [("forecast", "", False, None)]),
        (
            "### Forecast inputs\n" + JS + "```json\n{}\n```\n",
            [("forecast", "", False, None)],
        ),
        ("### Forecast inputs\ntext only\n", [("forecast", "", False, None)]),
        ("### Forecast inputs\n" + TB, [("forecast", "", False, None)]),
        ("### Chart data: x\n" + JS, [("chart", "x", False, None)]),
        ("### Forecast inputs\n```json\n{}\n", [("forecast", "", False, None)]),
        ("### Forecast inputs\nnote\n\n" + JS, [("forecast", "", False, JSON_TEXT)]),
    ],
)
def test_data_sections(extra: str, want: list[tuple[str, str, bool, str | None]]) -> None:
    assert _sections(extra) == want


def test_data_sections_order_and_gaps_section() -> None:
    assert _sections("### Map: a\n", "### Events: b\n") == [
        ("map", "a", False, None),
        ("events", "b", False, None),
    ]


def _regs(extra: str) -> list[tuple[str, str, int, int | None]]:
    return [
        (r.id, r.source, r.line, None if r.table is None else r.table.line)
        for r in read_registers(_doc("", extra))
    ]


@pytest.mark.parametrize(
    ("extra", "want"),
    [
        ("### T2R.10 — Missing evidence\n" + TB, [("T2R.10", "heading", 6, 8)]),
        ("### T3D.7 — Judgments\n", [("T3D.7", "heading", 6, None)]),
        ("### T3D.7 — Judgments\n" + TB + TB, [("T3D.7", "heading", 6, None)]),
        (
            ("### T2R — x\n### T2R.10 - x\n### T2R.10 —x\n### 2.1 — x\n")
            + "### U.S. — outlook\n### **T2R.10** — x\n",
            [],
        ),
        ("<!-- table-id: cp2g.drivers -->\n" + TB, [("cp2g.drivers", "tag", 6, 8)]),
        ("<!-- table-id: x -->\nwords\n" + TB, [("x", "tag", 6, 9)]),
        ("<!-- table-id: x -->\n**Label**\n" + TB, [("x", "tag", 6, 9)]),
        ("<!-- table-id: x -->\n- item\n" + TB, [("x", "tag", 6, 9)]),
        ("<!-- table-id: x -->\n```\nc\n```\n" + TB, [("x", "tag", 6, 11)]),
        ("<!-- table-id: x --> Some text\n" + TB, [("x", "tag", 6, 8)]),
        ("<!-- table-id: x -->\n" + TB + TB, [("x", "tag", 6, 8)]),
        (
            "#### T4.12 — Model comparator register\n<!-- table-id: m.cmp -->\n\n"
            "Annual comparison is full-year.\n" + TB,
            [("T4.12", "heading", 6, 11), ("m.cmp", "tag", 7, 11)],
        ),
        (
            "<!-- table-id: a -->\nwords\n<!-- table-id: b -->\n" + TB,
            [("a", "tag", 6, None), ("b", "tag", 8, 10)],
        ),
        ("<!-- table-id: x -->\nwords\n### H\n" + TB, [("x", "tag", 6, None)]),
        ("### T1 — Source inventory\n" + TB, [("T1", "heading", 6, 8)]),
        ("### P3 — Preparation record\n" + TB, [("P3", "heading", 6, 8)]),
        ("### T12 — x\n", [("T12", "heading", 6, None)]),
        (
            "### downstream_readiness — Consumer readiness\n" + TB,
            [("downstream_readiness", "heading", 6, 8)],
        ),
        ("### a_1 — x\n", [("a_1", "heading", 6, None)]),
        (
            (
                "### t1 — x\n### T1 - x\n### T1 —x\n### readiness — x\n### T1a — x\n"
                "### Downstream_readiness — x\n### _a_b — x\n### 1_a — x\n### T — x\n"
            ),
            [],
        ),
        (
            "".join(f"### T{n} — Register {n}\n" + TB for n in range(1, 9)),
            [(f"T{n}", "heading", 1 + 5 * n, 3 + 5 * n) for n in range(1, 9)],
        ),
        ("<!-- table-id: x -->\n### H\n" + TB, [("x", "tag", 6, None)]),
        (
            "<!-- table-id: a -->\n<!-- table-id: b -->\n" + TB,
            [("a", "tag", 6, None), ("b", "tag", 7, 9)],
        ),
        (
            "<!-- table-id: a --> <!-- table-id: b -->\n\n" + TB,
            [("a", "tag", 6, None), ("b", "tag", 6, 9)],
        ),
        (
            "<!-- table-id: a b -->\n<!-- table-id:x -->\n<!-- Table-id: x -->\n<!-- note -->\n",
            [],
        ),
        ("<!--   table-id: x.y   -->\n" + TB, [("x.y", "tag", 6, 8)]),
        (
            "### T1.a — t\n<!-- table-id: t1.a -->\n" + TB,
            [("T1.a", "heading", 6, 9), ("t1.a", "tag", 7, 9)],
        ),
        ("### Table T2.1 — x\n", []),
        (
            "### T1.a — t <!-- table-id: x -->\n" + TB,
            [("T1.a", "heading", 6, 8), ("x", "tag", 6, 8)],
        ),
        (
            "### A\n<!-- table-id: x -->\ntext\n### T1 — y\n" + TB,
            [("x", "tag", 7, None), ("T1", "heading", 9, 11)],
        ),
        ("<!--\ntable-id: x -->\n" + TB, [("x", "tag", 6, 9)]),
        ("text\n", []),
    ],
)
def test_registers(extra: str, want: list[tuple[str, str, int, int | None]]) -> None:
    assert _regs(extra) == want


def test_register_tag_last_in_file() -> None:
    text = "## Request\nr\n## Sources\n## Findings\n## Calculations\n## Gaps\n## Next module\n"
    document = parse((text + "<!-- table-id: z -->\n").encode())
    assert [(r.id, r.line, r.table) for r in read_registers(document)] == [("z", 8, None)]


def test_register_tag_before_first_section() -> None:
    text = "<!-- table-id: p -->\n## Request\nr\n## Sources\n## Findings\n## Calculations\n"
    document = parse((text + "## Gaps\n## Next module\n").encode())
    assert [(r.id, r.line, r.table) for r in read_registers(document)] == [("p", 1, None)]
