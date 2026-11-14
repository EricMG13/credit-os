import json
from pathlib import Path

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from credit_os.handoff.errors import HandoffError
from credit_os.handoff.lines import split_lines

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "handoffs"
EXPECTED = json.loads(
    (Path(__file__).resolve().parent / "expected" / "lines-and-headings.json").read_text(
        encoding="utf-8"
    )
)
TERMINATORS = ("\r\n", "\n", "\r")


def test_error_carries_line_and_message() -> None:
    error = HandoffError(7, "bad heading")
    assert error.line == 7
    assert error.message == "bad heading"
    assert str(error) == "line 7: bad heading"
    assert isinstance(error, ValueError)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("a\r\nb", ("a", "b")),
        ("a\nb", ("a", "b")),
        ("a\rb", ("a", "b")),
        ("a\n\rb", ("a", "", "b")),
        ("a\r\n\r\nb", ("a", "", "b")),
    ],
)
def test_the_three_terminators(text: str, expected: tuple[str, ...]) -> None:
    assert split_lines(text) == expected


@pytest.mark.parametrize(
    "char",
    ["\u2028", "\u2029", "\x0c", "\x0b", "\x85", "\x1c", "\x1d", "\x1e"],
)
def test_other_separators_stay_inside_the_line(char: str) -> None:
    assert split_lines(f"a{char}b\nc") == (f"a{char}b", "c")


def test_leading_bom_dropped_once() -> None:
    assert split_lines("\ufeffa") == ("a",)
    assert split_lines("\ufeff\ufeffa") == ("\ufeffa",)


def test_bom_elsewhere_kept() -> None:
    assert split_lines("a\ufeffb\n\ufeffc") == ("a\ufeffb", "\ufeffc")


@pytest.mark.parametrize(
    ("text", "expected"),
    [("a\n", ("a",)), ("a\n\n", ("a", "")), ("a", ("a",)), ("", ()), ("\n", ("",))],
)
def test_final_terminator_adds_no_line(text: str, expected: tuple[str, ...]) -> None:
    assert split_lines(text) == expected


def test_lone_bom_is_empty() -> None:
    assert split_lines("\ufeff") == ()


@pytest.mark.parametrize("path", sorted(EXPECTED))
def test_golden_line_counts(path: str) -> None:
    text = (FIXTURES / path).read_bytes().decode("utf-8")
    assert len(split_lines(text)) == EXPECTED[path]["lines"]


_line = st.text(alphabet=st.characters(blacklist_characters="\r\n"))


@given(st.lists(_line, min_size=1), st.data())
def test_join_then_split_round_trips(lines: list[str], data: st.DataObject) -> None:
    lines[0] = lines[0].lstrip("\ufeff")
    if lines[-1] == "":
        lines[-1] = "z"  # a trailing empty line would just be a final terminator
    seps = [data.draw(st.sampled_from(TERMINATORS)) for _ in lines[1:]]
    for before, line, after in zip(seps, lines[1:], seps[1:], strict=False):
        # an empty line between a CR and an LF reads as one CRLF: not a distinct input
        assume(not (before == "\r" and line == "" and after == "\n"))
    text = lines[0] + "".join(s + line for s, line in zip(seps, lines[1:], strict=True))
    assert split_lines(text) == tuple(lines)


@given(st.text())
def test_no_line_contains_a_terminator_character(text: str) -> None:
    for line in split_lines(text):
        assert "\n" not in line
        assert "\r" not in line


@given(
    st.lists(
        st.sampled_from(["a", "\u2028", "\u2029", "\x85", "\x0c", "\ufeff", "\r\n", "\n", "\r"])
    ).map("".join)
)
def test_line_count_matches_terminator_count(text: str) -> None:
    if text.startswith("\ufeff"):
        return
    terminators = text.count("\r\n") + text.replace("\r\n", "").count("\n")
    terminators += text.replace("\r\n", "").count("\r")
    extra = 1 if text and not text.endswith(("\n", "\r")) else 0
    assert len(split_lines(text)) == terminators + extra
