import json
from pathlib import Path
from typing import Any

import pytest

from credit_os.handoff.errors import HandoffError
from credit_os.handoff.frontmatter import read_front_matter
from credit_os.handoff.lines import split_lines

HANDOFFS = Path(__file__).resolve().parent.parent / "fixtures" / "handoffs"
KEY: dict[str, Any] = json.loads(
    (Path(__file__).resolve().parent / "expected" / "document.json").read_text(encoding="utf-8")
)
NOT_KV = "front matter line is not `key: value`"


def _entries(lines: list[str]) -> list[tuple[str, str, int]]:
    found = read_front_matter(lines)
    assert found is not None
    return [(e.key, e.value, e.line) for e in found.entries]


@pytest.mark.parametrize(
    "lines",
    [[], ["## Request", "---", "a: 1", "---"], ["----", "a: 1", "---"]],
)
def test_none(lines: list[str]) -> None:
    assert read_front_matter(lines) is None


def test_empty_block() -> None:
    found = read_front_matter(["---", "---"])
    assert found is not None
    assert (found.line, found.end, found.entries) == (1, 2, ())


def test_marker_with_trailing_blanks() -> None:
    found = read_front_matter(["--- \t", "a: 1", "---  ", "x"])
    assert found is not None
    assert found.end == 3
    assert _entries(["--- \t", "a: 1", "---  ", "x"]) == [("a", "1", 2)]


def test_values_kept_exact() -> None:
    lines = [
        "---",
        "run_id: tdg-2024",
        "score:",
        "note:\t a: b  ",
        "list: [A, B]",
        'q: "x"',
        "n: 0",
        "---",
    ]
    found = read_front_matter(lines)
    assert found is not None
    assert found.end == 8
    assert _entries(lines) == [
        ("run_id", "tdg-2024", 2),
        ("score", "", 3),
        ("note", "a: b", 4),
        ("list", "[A, B]", 5),
        ("q", '"x"', 6),
        ("n", "0", 7),
    ]


@pytest.mark.parametrize(
    ("lines", "line", "message"),
    [
        (["---", "a: 1"], 1, "the front matter opened here is never closed by ---"),
        (["---", "a: 1", "", "b: 2", "---"], 3, NOT_KV),
        (["---", "a:1", "---"], 2, NOT_KV),
        (["---", " a: 1", "---"], 2, NOT_KV),
        (["---", "1a: x", "---"], 2, NOT_KV),
        (["---", "# note", "---"], 2, NOT_KV),
        (["---", "a: 1", "b: 2", "a: 3", "---"], 4, "front matter key `a` is repeated"),
        (
            ["---", "k" * 81 + ": 1", "k" * 81 + ": 2", "---"],
            3,
            "front matter key `" + "k" * 80 + "\u2026` is repeated",
        ),
        (
            ["---", "k" * 80 + ": 1", "k" * 80 + ": 2", "---"],
            3,
            "front matter key `" + "k" * 80 + "` is repeated",
        ),
    ],
)
def test_refusals(lines: list[str], line: int, message: str) -> None:
    with pytest.raises(HandoffError) as caught:
        read_front_matter(lines)
    assert caught.value.line == line
    assert caught.value.message == message


@pytest.mark.parametrize("name", sorted(KEY["files"]))
def test_fixture_rows(name: str) -> None:
    text = (HANDOFFS / name).read_text(encoding="utf-8")
    found = read_front_matter(split_lines(text))
    want = KEY["files"][name]["front_matter"]
    if want is None:
        assert found is None
        return
    assert found is not None
    assert found.end == want["end"]
    assert [e.key for e in found.entries] == want["keys"]
    rows = [(r[1], r[2], r[3]) for r in KEY["front_matter_entries"] if r[0] == name]
    got = [(e.line, e.key, e.value) for e in found.entries]
    assert all(row in got for row in rows)


def test_marker_line_holding_a_newline_is_not_a_marker() -> None:
    assert read_front_matter(["---\n", "---"]) is None


def test_entry_line_holding_a_newline_is_refused() -> None:
    with pytest.raises(HandoffError) as caught:
        read_front_matter(["---", "a: x\n", "---"])
    assert (caught.value.line, caught.value.message) == (2, NOT_KV)
