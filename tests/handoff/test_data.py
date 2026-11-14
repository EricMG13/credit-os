import json
from pathlib import Path
from typing import Any

import pytest

from credit_os.handoff.blocks import ListItem, Paragraph
from credit_os.handoff.data import Gap, passage_value, read_value, source_names, sources_table
from credit_os.handoff.document import HandoffDocument, Section, parse
from credit_os.handoff.reader import read_reader
from credit_os.handoff.scan import Comment
from credit_os.handoff.tables import Table

HERE = Path(__file__).resolve().parent
HANDOFFS = HERE.parent / "fixtures" / "handoffs"
KEY = json.loads((HERE / "expected" / "data.json").read_text(encoding="utf-8"))
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


@pytest.mark.parametrize("name", sorted(KEY))
def test_golden_data(name: str) -> None:
    want: Any = KEY[name]
    document = parse((HANDOFFS / name).read_bytes())
    assert read_reader(document).blocked is want["blocked"]
    table = sources_table(document)
    assert [None if table is None else table.line, list(source_names(document))] == want["sources"]
    assert _gap_cells(document) == want["gap_cells"]
    assert [[c.start, c.end, c.text] for c in document.comments] == want["comments"]
