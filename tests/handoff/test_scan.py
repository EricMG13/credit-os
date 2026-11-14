import json
import time
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from credit_os.handoff.errors import HandoffError
from credit_os.handoff.lines import split_lines
from credit_os.handoff.scan import Comment, Fence, Heading, scan

HANDOFFS = Path(__file__).resolve().parent.parent / "fixtures" / "handoffs"
EXPECTED_DIR = Path(__file__).resolve().parent / "expected"
HEADING_KEY: dict[str, Any] = json.loads(
    (EXPECTED_DIR / "lines-and-headings.json").read_text(encoding="utf-8")
)
DETAIL_KEY: dict[str, Any] = json.loads(
    (EXPECTED_DIR / "scan-detail.json").read_text(encoding="utf-8")
)
BT = "`"


def _fixture_lines(relative: str) -> tuple[str, ...]:
    return split_lines((HANDOFFS / relative).read_bytes().decode("utf-8"))


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("## Request", [(2, "Request", 1)]),
        ("## Request   ", [(2, "Request", 1)]),
        ("###### Deep", [(6, "Deep", 1)]),
        ("## ", [(2, "", 1)]),
        ("## A ##", [(2, "A ##", 1)]),
        ("#1 risk", []),
        ("##", []),
        ("##\tX", []),
        (" ## X", []),
        ("####### X", []),
    ],
)
def test_headings(line: str, expected: list[tuple[int, str, int]]) -> None:
    assert [(h.level, h.title, h.line) for h in scan([line]).headings] == expected


def _fences(lines: list[str]) -> list[tuple[int, int | None, int, str, int, str]]:
    return [(f.open, f.close, f.end, f.char, f.length, f.info) for f in scan(lines).fences]


@pytest.mark.parametrize(
    ("lines", "expected"),
    [
        ([BT * 3, "# h1", "### h3", BT * 3], [(1, 4, 4, BT, 3, "")]),
        (["~~~", BT * 3, "~~~"], [(1, 3, 3, "~", 3, "")]),
        ([BT * 4, BT * 3, BT * 4], [(1, 3, 3, BT, 4, "")]),
        ([BT * 3, BT * 5], [(1, 2, 2, BT, 3, "")]),
        ([BT * 3 + "json", "x", BT * 3 + " json"], [(1, None, 3, BT, 3, "json")]),
        (["   ~~~", "x", "   ~~~"], [(1, 3, 3, "~", 3, "")]),
        (["    " + BT * 3], []),
        ([BT * 3 + "a" + BT + "b"], []),
        (["~~~a" + BT + "b", "~~~"], [(1, 2, 2, "~", 3, "a" + BT + "b")]),
        (["## Request", BT * 3, "code", "## Sources", "text"], [(2, None, 3, BT, 3, "")]),
        ([BT * 3, "code"], [(1, None, 2, BT, 3, "")]),
        ([BT * 3, "<!-- not a comment", BT * 3], [(1, 3, 3, BT, 3, "")]),
        ([BT * 3 + " <!-- x", "code", BT * 3], [(1, 3, 3, BT, 3, "<!-- x")]),
    ],
)
def test_fences(
    lines: list[str], expected: list[tuple[int, int | None, int, str, int, str]]
) -> None:
    assert _fences(lines) == expected


def test_fence_info_with_comment_opener_records_no_comment() -> None:
    assert scan([BT * 3 + " <!-- x", "code", BT * 3]).comments == ()


def test_fence_with_headings_inside_is_not_headings() -> None:
    assert scan([BT * 3, "# h1", "### h3", BT * 3]).headings == ()


def test_unclosed_fence_ended_by_level_two_heading_keeps_the_heading() -> None:
    result = scan(["## Request", BT * 3, "code", "## Sources", "text"])
    assert [(h.level, h.title, h.line) for h in result.headings] == [
        (2, "Request", 1),
        (2, "Sources", 4),
    ]


def test_fence_unclosed_property() -> None:
    open_fence, closed = scan([BT * 3, "x"]).fences[0], scan([BT * 3, BT * 3]).fences[0]
    assert open_fence.unclosed is True
    assert closed.unclosed is False


def test_comment_text_in_fence_is_not_a_comment_and_shown_unchanged() -> None:
    lines = [BT * 3, "<!-- not a comment", BT * 3]
    result = scan(lines)
    assert result.comments == ()
    assert result.shown == tuple(lines)


def _comments(lines: list[str]) -> list[tuple[int, int, str]]:
    return [(c.start, c.end, c.text) for c in scan(lines).comments]


@pytest.mark.parametrize(
    ("lines", "shown", "comments"),
    [
        (["a <!-- x --> b"], ("a  b",), [(1, 1, "x")]),
        (["<!-- table-id: T1 -->"], ("",), [(1, 1, "table-id: T1")]),
        (
            ["before <!-- one", "two", "three --> after"],
            ("before ", "", " after"),
            [(1, 3, "one\ntwo\nthree")],
        ),
        (["<!-- a --> x <!-- b -->"], (" x ",), [(1, 1, "a"), (1, 1, "b")]),
        (["<!-- a --> <!-- b", "c -->"], ("", ""), [(1, 1, "a"), (1, 2, "b\nc")]),
        (["<!---->"], ("",), [(1, 1, "")]),
        ([BT + "<!--" + BT + " is literal"], (BT + "<!--" + BT + " is literal",), []),
        (["x --> y"], ("x --> y",), []),
        (
            ["<!--", "## Hidden", BT * 3, "-->", "## Shown"],
            ("", "", "", "", "## Shown"),
            [(1, 4, "## Hidden\n" + BT * 3)],
        ),
        (["<!-- a", "b --> ## Not heading"], ("", " ## Not heading"), [(1, 2, "a\nb")]),
        (["<!-- x -->## Request"], ("## Request",), [(1, 1, "x")]),
        (
            ["<!-- " + BT + " --> <!-- y --> " + BT],
            ("  " + BT,),
            [(1, 1, BT), (1, 1, "y")],
        ),
        (
            [BT + "a" + BT + " <!-- x --> " + BT + "b" + BT],
            (BT + "a" + BT + "  " + BT + "b" + BT,),
            [(1, 1, "x")],
        ),
        (
            [BT + "<!--" + BT + " then <!-- real -->"],
            (BT + "<!--" + BT + " then ",),
            [(1, 1, "real")],
        ),
        (
            ["<!-- " + BT + " -->" + BT + "x <!-- y --> z" + BT],
            (BT + "x <!-- y --> z" + BT,),
            [(1, 1, BT)],
        ),
        (
            [BT * 2 + "a" + BT + " <!-- c -->"],
            (BT * 2 + "a" + BT + " ",),
            [(1, 1, "c")],
        ),
        (
            [BT * 2 + "x <!-- c --> y" + BT],
            (BT * 2 + "x  y" + BT,),
            [(1, 1, "c")],
        ),
        (
            [BT * 2 + " " + BT + "<!--" + BT + " " + BT * 2],
            (BT * 2 + " " + BT + "<!--" + BT + " " + BT * 2,),
            [],
        ),
        ([BT + "a <!-- x --> b" + BT], (BT + "a <!-- x --> b" + BT,), []),
        (
            ["<!-- a", "b --> " + BT + "c <!-- d" + BT + " <!-- e -->"],
            ("", " " + BT + "c <!-- d" + BT + " "),
            [(1, 2, "a\nb"), (2, 2, "e")],
        ),
    ],
)
def test_comments(
    lines: list[str], shown: tuple[str, ...], comments: list[tuple[int, int, str]]
) -> None:
    result = scan(lines)
    assert result.shown == shown
    assert _comments(lines) == comments


def test_backtick_runs_are_read_in_bounded_time() -> None:
    lots = BT * 8000
    started = time.perf_counter()
    plain = scan(["x" + lots])
    closed = scan(["x" + lots + " <!-- c -->"])
    pairs = scan([(BT + "a") * 4000 + "<!-- c -->"])
    elapsed = time.perf_counter() - started
    assert plain.comments == ()
    assert plain.shown == ("x" + lots,)
    assert [(c.start, c.end, c.text) for c in closed.comments] == [(1, 1, "c")]
    assert closed.shown == ("x" + lots + " ",)
    assert [(c.start, c.end, c.text) for c in pairs.comments] == [(1, 1, "c")]
    assert pairs.shown == ((BT + "a") * 4000,)
    assert elapsed < 1.0


def test_hidden_fence_and_heading_inside_a_comment_leave_the_shown_heading_only() -> None:
    result = scan(["<!--", "## Hidden", BT * 3, "-->", "## Shown"])
    assert [(h.level, h.title, h.line) for h in result.headings] == [(2, "Shown", 5)]
    assert result.fences == ()


def test_comment_continuation_line_is_never_a_heading_or_fence() -> None:
    result = scan(["<!-- a", "b --> ## Not heading"])
    assert result.headings == ()
    result = scan(["<!-- a", "b --> " + BT * 3])
    assert result.fences == ()


def test_heading_title_is_the_shown_text() -> None:
    assert [(h.level, h.title, h.line) for h in scan(["## A <!-- c --> B"]).headings] == [
        (2, "A  B", 1)
    ]


def test_heading_hidden_behind_a_comment_is_prose() -> None:
    assert scan(["<!-- x -->## Request"]).headings == ()


@pytest.mark.parametrize(
    ("lines", "line"),
    [(["<!-- never closed", "## Request"], 1), (["text", "tail <!-- open"], 2)],
)
def test_unclosed_comment_raises_at_its_opener(lines: list[str], line: int) -> None:
    with pytest.raises(HandoffError) as caught:
        scan(lines)
    assert caught.value.line == line
    assert str(caught.value) == f"line {line}: the HTML comment opened here is never closed by -->"


def test_nodes_are_immutable() -> None:
    heading = Heading(level=2, title="A", line=1)
    with pytest.raises(ValidationError):
        heading.title = "B"


def test_nodes_refuse_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        Comment.model_validate({"start": 1, "end": 1, "text": "", "extra": 1})
    with pytest.raises(ValidationError):
        Fence.model_validate(
            {"open": 1, "close": None, "end": 1, "char": BT, "length": 3, "info": "", "x": 1}
        )


@pytest.mark.parametrize("relative", sorted(HEADING_KEY))
def test_fixture_headings_match_the_key(relative: str) -> None:
    lines = _fixture_lines(relative)
    result = scan(lines)
    expected = HEADING_KEY[relative]
    assert len(result.shown) == expected["lines"] == len(lines)
    assert len(result.headings) == expected["headings"]
    assert [[h.title, h.line] for h in result.headings if h.level == 2] == expected["level2"]


@pytest.mark.parametrize("relative", sorted(DETAIL_KEY))
def test_fixture_scan_detail_matches_the_key(relative: str) -> None:
    result = scan(_fixture_lines(relative))
    expected = DETAIL_KEY[relative]
    assert [[h.level, h.title, h.line] for h in result.headings] == expected["headings"]
    assert [
        {
            "open": f.open,
            "close": f.close,
            "char": f.char,
            "length": f.length,
            "info": f.info,
            "unclosed": f.unclosed,
        }
        for f in result.fences
    ] == expected["fences"]
    assert [{"start": c.start, "end": c.end, "text": c.text} for c in result.comments] == expected[
        "comments"
    ]


def test_cp_2a_only_the_table_id_comment_line_is_hidden() -> None:
    lines = _fixture_lines("tdg-2026-11-09/CP-2A.md")
    shown = scan(lines).shown
    assert shown[111] == ""
    assert [s for i, s in enumerate(shown) if i != 111] == [
        s for i, s in enumerate(lines) if i != 111
    ]


@given(st.lists(st.text().filter(lambda s: "<!--" not in s and "\n" not in s and "\r" not in s)))
def test_without_comment_openers_scan_never_raises_and_shows_the_input(
    lines: list[str],
) -> None:
    assert scan(lines).shown == tuple(lines)
