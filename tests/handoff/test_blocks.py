import json
from pathlib import Path
from typing import Any

import pytest

from credit_os.handoff.blocks import CodeBlock, ListItem, Paragraph, read_blocks
from credit_os.handoff.errors import HandoffError
from credit_os.handoff.lines import split_lines
from credit_os.handoff.scan import scan
from credit_os.handoff.tables import Table

HANDOFFS = Path(__file__).resolve().parent.parent / "fixtures" / "handoffs"
KEY: dict[str, Any] = json.loads(
    (Path(__file__).resolve().parent / "expected" / "blocks.json").read_text(encoding="utf-8")
)
BT = "`" * 3
HEAD = "| A | B |"
SEP = "| --- | --- |"
KIND_NAMES = ("paragraph", "item", "table", "code")


def _kind(block: object) -> str:
    for kind, name in ((Paragraph, "paragraph"), (ListItem, "item"), (Table, "table")):
        if isinstance(block, kind):
            return name
    return "code"


def _shape(lines: list[str], first: int = 1, last: int | None = None) -> list[Any]:
    out: list[Any] = []
    for block in read_blocks(scan(lines), first, last):
        if isinstance(block, Paragraph):
            out.append(("P", block.line, block.lines))
        elif isinstance(block, ListItem):
            out.append(("I", block.line, block.marker, block.lines))
        elif isinstance(block, Table):
            out.append(("T", block.line, block.label, len(block.rows)))
        else:
            out.append(("K", block.line, block.end, block.info, block.lines, block.unclosed))
    return out


@pytest.mark.parametrize(
    ("lines", "expected"),
    [
        (["a", "b", "", "c"], [("P", 1, ("a", "b")), ("P", 4, ("c",))]),
        (["  a  b  ", "c"], [("P", 1, ("a  b", "c"))]),
        (
            ["- one", "more", "- two", "", "text"],
            [("I", 1, "-", ("one", "more")), ("I", 3, "-", ("two",)), ("P", 5, ("text",))],
        ),
        (
            ["1. a", "2) b", "* c", "+ d", "  - e"],
            [
                ("I", 1, "1.", ("a",)),
                ("I", 2, "2)", ("b",)),
                ("I", 3, "*", ("c",)),
                ("I", 4, "+", ("d",)),
                ("I", 5, "-", ("e",)),
            ],
        ),
        (
            ["-5% decline", "**bold** text", "1.5x", "2024. Then"],
            [("P", 1, ("-5% decline", "**bold** text", "1.5x", "2024. Then"))],
        ),
        (
            ["text", HEAD, SEP, "| 1 | 2 |", "after"],
            [("P", 1, ("text",)), ("T", 2, None, 1), ("P", 5, ("after",))],
        ),
        (["- item", HEAD, SEP], [("I", 1, "-", ("item",)), ("T", 2, None, 0)]),
        (["## H", "text", "### S", "more"], [("P", 2, ("text",)), ("P", 4, ("more",))]),
        (
            ["a", BT + "json", "{", "", "}", BT, "b"],
            [("P", 1, ("a",)), ("K", 2, 6, "json", ("{", "", "}"), False), ("P", 7, ("b",))],
        ),
        (
            ["## A", BT, "  x", "## B", "y"],
            [("K", 2, 3, "", ("  x",), True), ("P", 5, ("y",))],
        ),
        (["**Leverage**", "", HEAD, SEP, "| 1 | 2 |"], [("T", 3, "Leverage", 1)]),
        (["**Leverage**:", HEAD, SEP], [("T", 2, "Leverage", 0)]),
        (["**Leverage:**", HEAD, SEP], [("T", 2, "Leverage:", 0)]),
        (
            ["Intro", "**Leverage**", "", HEAD, SEP],
            [("P", 1, ("Intro", "**Leverage**")), ("T", 4, None, 0)],
        ),
        (
            ["**Bold** then text", "", HEAD, SEP],
            [("P", 1, ("**Bold** then text",)), ("T", 3, None, 0)],
        ),
        (
            ["**Label**", "", "text", "", HEAD, SEP],
            [("P", 1, ("**Label**",)), ("P", 3, ("text",)), ("T", 5, None, 0)],
        ),
        (
            ["**Label**", "## H", HEAD, SEP],
            [("P", 1, ("**Label**",)), ("T", 3, None, 0)],
        ),
        (["**Final bold line.**"], [("P", 1, ("**Final bold line.**",))]),
        (["<!-- table-id: T1 -->", HEAD, SEP], [("T", 2, None, 0)]),
        (
            [HEAD, SEP, "    | 1 | 2 |"],
            [("T", 1, None, 0), ("P", 3, ("| 1 | 2 |",))],
        ),
        (
            ["**Label**", "more", "", HEAD, SEP],
            [("P", 1, ("**Label**", "more")), ("T", 4, None, 0)],
        ),
        (["a", "   b   "], [("P", 1, ("a", "b"))]),
        (["-    one  ", "   more  "], [("I", 1, "-", ("one", "more"))]),
        (["**  Leverage  **", HEAD, SEP], [("T", 2, "Leverage", 0)]),
        (["a", "   ", "b"], [("P", 1, ("a",)), ("P", 3, ("b",))]),
        (["100. x", "1000. y"], [("I", 1, "100.", ("x", "1000. y"))]),
    ],
)
def test_examples(lines: list[str], expected: list[Any]) -> None:
    assert _shape(lines) == expected


def test_first_below_one_is_a_caller_error() -> None:
    with pytest.raises(ValueError, match="first must be at least 1"):
        read_blocks(scan(["a"]), first=0)


def test_refusal_propagates_with_its_line() -> None:
    with pytest.raises(HandoffError) as caught:
        read_blocks(scan(["text", "| A | B"]))
    assert caught.value.line == 2


@pytest.mark.parametrize(
    ("first", "last", "expected"),
    [(3, None, [("P", 3, ("b",)), ("P", 5, ("c",))]), (2, 3, [("P", 3, ("b",))])],
)
def test_range(first: int, last: int | None, expected: list[Any]) -> None:
    assert _shape(["a", "", "b", "", "c"], first, last) == expected


def test_label_before_first_is_not_looked_for() -> None:
    assert _shape(["**Label**", "", HEAD, SEP], first=2) == [("T", 3, None, 0)]


def _blocks(relative: str) -> tuple[Any, ...]:
    lines = split_lines((HANDOFFS / relative).read_bytes().decode("utf-8"))
    return read_blocks(scan(lines), first=KEY["counts"][relative]["from"])


@pytest.mark.parametrize("relative", sorted(KEY["counts"]))
def test_fixture_counts(relative: str) -> None:
    blocks = _blocks(relative)
    want = KEY["counts"][relative]
    got = {kind: sum(1 for b in blocks if _kind(b) == kind) for kind in KIND_NAMES}
    assert (got["table"], got["paragraph"], got["item"], got["code"]) == (
        want["tables"],
        want["paragraphs"],
        want["items"],
        want["code"],
    )


@pytest.mark.parametrize("relative", sorted(KEY["sequence"]))
def test_fixture_sequence(relative: str) -> None:
    got = [[_kind(b), b.line] for b in _blocks(relative)]
    assert got == KEY["sequence"][relative]


@pytest.mark.parametrize("relative", sorted(KEY["last_block"]))
def test_fixture_last_block(relative: str) -> None:
    last = _blocks(relative)[-1]
    assert [_kind(last), last.line] == KEY["last_block"][relative]


@pytest.mark.parametrize("entry", KEY["tables"], ids=lambda e: f"{e['file']}:{e['line']}")
def test_fixture_tables(entry: dict[str, Any]) -> None:
    (table,) = [
        b for b in _blocks(entry["file"]) if isinstance(b, Table) and b.line == entry["line"]
    ]
    assert list(table.columns) == entry["columns"]
    assert len(table.rows) == entry["rows"]
    for index, number in entry.get("row_lines", []):
        assert table.rows[index].line == number
    for row, column, text in entry["cells"]:
        assert table.rows[row].cells[column] == text


@pytest.mark.parametrize("entry", KEY["texts"], ids=lambda e: f"{e['file']}:{e['line']}")
def test_fixture_texts(entry: dict[str, Any]) -> None:
    (block,) = [
        b
        for b in _blocks(entry["file"])
        if isinstance(b, Paragraph | ListItem) and b.line == entry["line"]
    ]
    assert _kind(block) == entry["kind"]
    assert list(block.lines) == entry["lines"]
    if "marker" in entry:
        assert isinstance(block, ListItem)
        assert block.marker == entry["marker"]


@pytest.mark.parametrize("entry", KEY["code"], ids=lambda e: f"{e['file']}:{e['line']}")
def test_fixture_code(entry: dict[str, Any]) -> None:
    (block,) = [
        b for b in _blocks(entry["file"]) if isinstance(b, CodeBlock) and b.line == entry["line"]
    ]
    assert (block.end, block.info, block.unclosed) == (
        entry["end"],
        entry["info"],
        entry["unclosed"],
    )
    assert len(block.lines) == entry["count"]
    assert (block.lines[0], block.lines[-1]) == (entry["first"], entry["last"])


def test_range_starting_inside_a_fence_skips_it() -> None:
    assert _shape(["a", BT, "x", BT, "b"], first=3) == [("P", 5, ("b",))]
