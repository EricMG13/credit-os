import json
from pathlib import Path
from typing import Any

import pytest

from credit_os.handoff.blocks import CodeBlock, Paragraph
from credit_os.handoff.document import Section, parse
from credit_os.handoff.errors import HandoffError
from credit_os.handoff.reader import Reader, ReaderSummary, SummaryFinding, read_reader
from credit_os.handoff.tables import Table

HERE = Path(__file__).resolve().parent
HANDOFFS = HERE.parent / "fixtures" / "handoffs"
FILES: dict[str, Any] = json.loads((HERE / "expected" / "reader.json").read_text("utf-8"))["files"]

T1 = "| Bottom line | Confidence | Main limitation |\n| --- | --- | --- |\n| B | Medium | L |\n"
T2 = (
    "| Finding | Creditor impact | Confidence |\n| --- | --- | --- |\n"
    "| f1 | i1 | High |\n| f2 | i2 | Low |\n"
)
BT = "`" * 3
LONG_TITLE = "Contrary evidence and what would change the view"


def _read(findings: str) -> Reader:
    text = (
        "## Request\n## Sources\n## Findings\n"
        + findings
        + "## Calculations\n## Gaps\n## Next module\n"
    )
    return read_reader(parse(text.encode()))


def _lines(section: Section | None) -> int | None:
    return None if section is None else section.line


def _passages(reader: Reader) -> list[int | None]:
    return [
        _lines(reader.bottom_line),
        _lines(reader.key_findings),
        _lines(reader.contrary),
        _lines(reader.limitations),
    ]


@pytest.mark.parametrize(
    "findings",
    ["", "text\n", "### Key findings\n- k\n### Bottom line\nx\n", "### bottom line\nx\n",
     "#### Bottom line\nx\n", f"{BT}\n### Bottom line\nx\n"],
)  # fmt: skip
def test_earlier_without_summary(findings: str) -> None:
    reader = _read(findings)
    assert reader.format == "earlier"
    assert _passages(reader) == [None, None, None, None]
    assert reader.summary is None


def test_new_single() -> None:
    reader = _read("### Bottom line\nx\n")
    assert reader.format == "new"
    assert _passages(reader) == [4, None, None, None]
    assert reader.summary is None
    assert reader.bottom_line is not None
    block = reader.bottom_line.blocks[0]
    assert len(reader.bottom_line.blocks) == 1
    assert isinstance(block, Paragraph)
    assert (block.line, block.lines) == (5, ("x",))


def test_new_all_four_any_order() -> None:
    reader = _read(
        f"### Bottom line\na\n### Limitations\n- l\n### Key findings\n- k\n### {LONG_TITLE}\nc\n"
        "### Extra\ne\n"
    )
    assert reader.format == "new"
    assert _passages(reader) == [4, 8, 10, 6]


def test_text_before_first_subsection_and_closed_fence() -> None:
    assert _read("intro\n\n### Bottom line\nx\n").format == "new"
    assert _read(f"{BT}\ncode\n{BT}\n### Bottom line\nx\n").format == "new"


@pytest.mark.parametrize(
    ("findings", "title"),
    [
        ("### Bottom line\na\n### Key findings\n- k\n### Bottom line\nb\n", "Bottom line"),
        ("### Bottom line\na\n### Limitations\n- x\n### Limitations\n- y\n", "Limitations"),
    ],
)
def test_repeated_passage_refused(findings: str, title: str) -> None:
    with pytest.raises(HandoffError) as caught:
        _read(findings)
    assert caught.value.line == 8
    assert caught.value.message == f"passage heading `{title}` is repeated"


def test_bold_label_stays_a_paragraph() -> None:
    reader = _read(
        "### Bottom line\n**Not assessable: no document.**\n\n| A | B |\n| --- | --- |\n| 1 | 2 |\n"
    )
    assert reader.bottom_line is not None
    first, second = reader.bottom_line.blocks
    assert isinstance(first, Paragraph)
    assert (first.line, first.lines) == (5, ("**Not assessable: no document.**",))
    assert isinstance(second, Table)
    assert (second.line, second.label, second.label_line) == (
        7,
        "Not assessable: no document.",
        5,
    )


def test_summary_read() -> None:
    reader = _read("### Reader summary\nintro\n\n" + T1 + "\n" + T2)
    assert reader.format == "earlier"
    assert _passages(reader) == [None, None, None, None]
    assert reader.summary == ReaderSummary(
        line=9,
        bottom_line="B",
        confidence="Medium",
        limitation="L",
        findings=(
            SummaryFinding(line=13, finding="f1", impact="i1", confidence="High"),
            SummaryFinding(line=14, finding="f2", impact="i2", confidence="Low"),
        ),
    )


def test_summary_section_need_not_be_first() -> None:
    reader = _read("### Other\nx\n### Reader summary\n" + T1 + "\n" + T2)
    assert reader.summary is not None
    assert reader.summary.line == 9


T1_TWO_ROWS = T1 + "| B2 | Low | L2 |\n"
T1_CASE = T1.replace("Bottom line", "Bottom Line")
T2_NO_ROW = "| Finding | Creditor impact | Confidence |\n| --- | --- | --- |\n"


@pytest.mark.parametrize(
    "findings",
    [
        "### Reader summary\n" + T1,
        "### Reader summary\n" + T2 + "\n" + T1,
        "### Reader summary\n" + T1 + "\n" + T2 + "\n" + T2,
        "### Reader summary\n" + T1_TWO_ROWS + "\n" + T2,
        "### Reader summary\n" + T1 + "\n" + T2_NO_ROW,
        "### Reader summary\n" + T1_CASE + "\n" + T2,
        f"{BT}\n### Reader summary\n" + T1 + "\n" + T2,
        "### Reader summary\n",
    ],
)
def test_malformed_summary_is_none(findings: str) -> None:
    reader = _read(findings)
    assert reader.format == "earlier"
    assert reader.summary is None


def test_new_format_has_no_summary() -> None:
    reader = _read("### Bottom line\nx\n### Reader summary\n" + T1 + "\n" + T2)
    assert reader.format == "new"
    assert reader.summary is None


def test_unclosed_fence_swallows_heading() -> None:
    reader = _read(f"### Bottom line\nx\n{BT}\n### Key findings\n- k\n")
    assert reader.format == "new"
    assert _passages(reader) == [4, None, None, None]
    assert reader.bottom_line is not None
    paragraph, code = reader.bottom_line.blocks
    assert isinstance(paragraph, Paragraph)
    assert paragraph.line == 5
    assert isinstance(code, CodeBlock)
    assert (code.line, code.unclosed) == (6, True)


@pytest.mark.parametrize("name", sorted(FILES))
def test_golden_file(name: str) -> None:
    expected = FILES[name]
    reader = read_reader(parse((HANDOFFS / name).read_bytes()))
    assert reader.format == expected["format"]
    if expected["format"] == "new":
        assert _passages(reader) == expected["passages"]
        assert reader.summary is None
        return
    assert _passages(reader) == [None, None, None, None]
    key = expected["summary"]
    assert reader.summary is not None
    assert reader.summary.line == key["line"]
    assert [
        reader.summary.bottom_line,
        reader.summary.confidence,
        reader.summary.limitation,
    ] == key["call"]
    assert [[f.line, f.finding, f.impact, f.confidence] for f in reader.summary.findings] == key[
        "findings"
    ]
