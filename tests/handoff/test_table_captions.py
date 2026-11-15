"""A table's caption line (R57, R59a): the paragraph directly before it, read in `handoff/`."""

import json
from pathlib import Path
from typing import Any

import pytest

from credit_os.handoff.blocks import read_blocks
from credit_os.handoff.lines import split_lines
from credit_os.handoff.scan import scan
from credit_os.handoff.tables import Table, read_table

HANDOFFS = Path(__file__).resolve().parent.parent / "fixtures" / "handoffs"
EXPECTED = Path(__file__).resolve().parent / "expected"
KEY: dict[str, Any] = json.loads((EXPECTED / "captions.json").read_text(encoding="utf-8"))
BLOCKS: dict[str, Any] = json.loads((EXPECTED / "blocks.json").read_text(encoding="utf-8"))
BT = "`" * 3
HEAD = "| A | B |"
SEP = "| --- | --- |"
ROW = "| 1 | 2 |"
TOGETHER = "caption and caption_line are given together or not at all"


def _captions(lines: list[str], first: int = 1) -> list[tuple[tuple[str, ...], int | None]]:
    tables = [b for b in read_blocks(scan(lines), first) if isinstance(b, Table)]
    return [(table.caption, table.caption_line) for table in tables]


NONE: tuple[tuple[str, ...], None] = ((), None)


@pytest.mark.parametrize(
    ("lines", "expected"),
    [
        (["text", HEAD, SEP], [(("text",), 1)]),
        (["text", "", HEAD, SEP], [(("text",), 1)]),
        (["text", "", "", HEAD, SEP], [(("text",), 1)]),
        (["", "a", "  b  ", HEAD, SEP], [(("a", "b"), 2)]),
        (["  a  b  ", "c", "", HEAD, SEP], [(("a  b", "c"), 1)]),
        (["**Leverage**", "", HEAD, SEP], [(("**Leverage**",), 1)]),
        (["**Leverage**:", HEAD, SEP], [(("**Leverage**:",), 1)]),
        (["**Leverage:**", HEAD, SEP], [(("**Leverage:**",), 1)]),
        (["**  Leverage  **", HEAD, SEP], [(("**  Leverage  **",), 1)]),
        (["**Bold** then text", "", HEAD, SEP], [(("**Bold** then text",), 1)]),
        (["Intro", "**Leverage**", HEAD, SEP], [(("Intro", "**Leverage**"), 1)]),
        (["## H", "text", HEAD, SEP], [(("text",), 2)]),
        (["## H", "", "text", "", HEAD, SEP], [(("text",), 3)]),
        (["text", "<!-- table-id: T1 -->", HEAD, SEP], [(("text",), 1)]),
        (["text", HEAD, SEP, "", HEAD, SEP], [(("text",), 1), NONE]),
        ([HEAD, SEP, "x", HEAD, SEP], [NONE, (("x",), 3)]),
        (["one", "", "two", "", HEAD, SEP], [(("two",), 3)]),
        (["one", "", "two", HEAD, SEP], [(("two",), 3)]),
        ([HEAD, SEP], [NONE]),
    ],
    ids=[
        "directly above",
        "one blank line between",
        "two blank lines between",
        "two lines above, stripped",
        "two lines above, inner spaces kept",
        "bold label",
        "bold label with colon",
        "bold label with the colon inside",
        "bold label with spaces inside",
        "bold then text",
        "paragraph ending in a bold line",
        "after a heading",
        "after a heading and blanks",
        "a comment line between",
        "table after a captioned table",
        "table after another table, caption for the second",
        "two paragraphs above",
        "two paragraphs, second directly above",
        "no block before",
    ],
)
def test_caption_is_the_paragraph_directly_above(
    lines: list[str], expected: list[tuple[tuple[str, ...], int | None]]
) -> None:
    assert _captions(lines) == expected


@pytest.mark.parametrize(
    "lines",
    [
        ["text", "## H", HEAD, SEP],
        ["text", "", "### H", "", HEAD, SEP],
        ["# H", HEAD, SEP],
        ["- item", HEAD, SEP],
        ["- item", "", HEAD, SEP],
        ["text", "- item", HEAD, SEP],
        ["- item", "more", HEAD, SEP],
        ["1. item", "", HEAD, SEP],
        ["text", BT, "x", BT, HEAD, SEP],
        ["text", "", BT, "x", BT, "", HEAD, SEP],
        [BT, "x", BT, HEAD, SEP],
    ],
    ids=[
        "heading between",
        "heading between, blanks around",
        "heading only above",
        "list item above",
        "list item above, blank between",
        "list item between paragraph and table",
        "list item continuation above",
        "numbered item above",
        "code block between",
        "code block between, blanks around",
        "code block above",
    ],
)
def test_no_caption_when_another_block_or_a_heading_is_between(lines: list[str]) -> None:
    tables = _captions(lines)
    assert tables[-1] == NONE


def test_a_table_after_a_table_has_no_caption_and_rows_that_run_on_stay_one_table() -> None:
    # A second header directly under the first table's rows is one more row of that table, so
    # the one table keeps the caption of the paragraph above it; a blank line makes two tables.
    assert _captions(["text", HEAD, SEP, ROW, "", HEAD, SEP, ROW]) == [(("text",), 1), NONE]
    assert _captions(["text", HEAD, SEP, ROW, HEAD, SEP, ROW]) == [(("text",), 1)]


def test_caption_before_first_is_not_looked_for() -> None:
    assert _captions(["text", "", HEAD, SEP], first=2) == [NONE]
    assert _captions(["text", "", HEAD, SEP], first=3) == [NONE]
    assert _captions(["a", "", "text", HEAD, SEP], first=3) == [(("text",), 3)]
    assert _captions(["a", "", "text", HEAD, SEP], first=4) == [NONE]


def test_label_and_caption_come_together_for_a_bold_label() -> None:
    blocks = read_blocks(scan(["**Leverage**:", "", HEAD, SEP]))
    table = blocks[-1]
    assert isinstance(table, Table)
    assert (table.label, table.label_line) == ("Leverage", 1)
    assert (table.caption, table.caption_line) == (("**Leverage**:",), 1)


def test_a_multi_line_paragraph_is_a_caption_not_a_label() -> None:
    table = read_blocks(scan(["Intro", "**Leverage**", "", HEAD, SEP]))[-1]
    assert isinstance(table, Table)
    assert (table.label, table.label_line) == (None, None)
    assert (table.caption, table.caption_line) == (("Intro", "**Leverage**"), 1)


def test_a_table_holds_no_caption_unless_given() -> None:
    table = Table(line=1, label=None, label_line=None, columns=("A", "B"), rows=())
    assert (table.caption, table.caption_line) == ((), None)


ROWS = [(1, HEAD), (2, SEP), (3, ROW)]


def test_read_table_without_a_caption_holds_none() -> None:
    table = read_table(ROWS)
    assert (table.caption, table.caption_line) == ((), None)
    table = read_table(ROWS, None, None, (), None)
    assert (table.caption, table.caption_line) == ((), None)


def test_read_table_holds_the_caption_it_is_given() -> None:
    table = read_table(ROWS, "L", 4, ("a", "b"), 7)
    assert (table.label, table.label_line) == ("L", 4)
    assert (table.caption, table.caption_line) == (("a", "b"), 7)
    table = read_table(ROWS, caption=("c",), caption_line=2)
    assert (table.label, table.label_line) == (None, None)
    assert (table.caption, table.caption_line) == (("c",), 2)


@pytest.mark.parametrize(
    ("caption", "caption_line"),
    [(("a",), None), ((), 3), ((), 0)],
    ids=["caption only", "empty caption with a line", "empty caption with a line of zero"],
)
def test_read_table_refuses_one_of_caption_and_caption_line(
    caption: tuple[str, ...], caption_line: int | None
) -> None:
    with pytest.raises(ValueError, match=TOGETHER):
        read_table(ROWS, None, None, caption, caption_line)
    with pytest.raises(ValueError, match=TOGETHER):
        read_table(ROWS, caption=caption, caption_line=caption_line)


def _tables(relative: str) -> list[Table]:
    lines = split_lines((HANDOFFS / relative).read_bytes().decode("utf-8"))
    first = KEY["files"][relative]["from"]
    return [b for b in read_blocks(scan(lines), first=first) if isinstance(b, Table)]


def test_the_key_covers_the_files_test_blocks_reads() -> None:
    assert sorted(KEY["files"]) == sorted(BLOCKS["counts"])
    for relative, counts in BLOCKS["counts"].items():
        assert KEY["files"][relative]["from"] == counts["from"]
        assert len(KEY["files"][relative]["tables"]) == counts["tables"]


@pytest.mark.parametrize("relative", sorted(KEY["files"]), ids=lambda name: name)
def test_fixture_captions(relative: str) -> None:
    got = [
        {
            "line": table.line,
            "columns": list(table.columns),
            "caption": (
                None
                if table.caption_line is None
                else {"line": table.caption_line, "lines": list(table.caption)}
            ),
        }
        for table in _tables(relative)
    ]
    assert got == KEY["files"][relative]["tables"]


@pytest.mark.parametrize("relative", sorted(KEY["files"]), ids=lambda name: name)
def test_fixture_caption_and_line_come_together(relative: str) -> None:
    for table in _tables(relative):
        assert (table.caption == ()) == (table.caption_line is None)
