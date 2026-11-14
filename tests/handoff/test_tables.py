import pytest
from hypothesis import given
from hypothesis import strategies as st

from credit_os.handoff.errors import HandoffError
from credit_os.handoff.tables import is_table_row, read_table

HEAD = "| A | B | C | D | E | F | G |"
SEP7 = "|---|---|---|---|---|---|---|"
SEP8 = "|---|---|---|---|---|---|---|---|"
ROW = "| 1 | 2 | 3 | 4 | 5 | 6 | 7 |"
SEPARATOR_MESSAGE = "the table header is not followed by a separator row of --- cells"
CLOSING_MESSAGE = "the table row needs a closing pipe"


def _numbered(texts: list[str], start: int) -> list[tuple[int, str]]:
    return list(enumerate(texts, start))


@pytest.mark.parametrize(
    ("texts", "start", "line", "message"),
    [
        (
            [HEAD, SEP8, ROW],
            231,
            231,
            "the table header has 7 cells and its separator row has 8",
        ),
        ([HEAD, ROW, ROW], 231, 231, SEPARATOR_MESSAGE),
        (
            [HEAD, SEP7, ROW, "| 1 | 2 |"],
            40,
            43,
            "the table row has 2 cells and the header has 7",
        ),
        ([HEAD, SEP7, "| 1 | 2 | 3"], 40, 42, CLOSING_MESSAGE),
        ([HEAD], 12, 12, SEPARATOR_MESSAGE),
        (["| A |", "| --- |"], 1, 1, "a table needs at least two columns"),
        (["| A | B", "| --- | --- |"], 1, 1, CLOSING_MESSAGE),
        (["| A | B |", "| --- | --- "], 1, 2, CLOSING_MESSAGE),
        (["| A | B |", "| -- | --- |"], 1, 1, SEPARATOR_MESSAGE),
        (
            ["| A | B |", "| --- | --- |", "| `a|b` | c |"],
            1,
            3,
            "the table row has 3 cells and the header has 2",
        ),
        (
            ["| A | B |", "| --- | --- |", "| x | y \\|"],
            1,
            3,
            CLOSING_MESSAGE,
        ),
        (["|", "| --- | --- |"], 1, 1, CLOSING_MESSAGE),
    ],
)
def test_refusals(texts: list[str], start: int, line: int, message: str) -> None:
    with pytest.raises(HandoffError) as caught:
        read_table(_numbered(texts, start))
    assert caught.value.line == line
    assert caught.value.message == message


def test_empty_first_cell_is_accepted() -> None:
    table = read_table(_numbered([HEAD, SEP7, "|  | 2 | 3 | 4 | 5 | 6 | 7 |"], 40))
    assert table.rows[0].line == 42
    assert table.rows[0].cells == ("", "2", "3", "4", "5", "6", "7")


def test_header_and_separator_only() -> None:
    table = read_table(_numbered([HEAD, SEP7], 12))
    assert table.line == 12
    assert table.columns == ("A", "B", "C", "D", "E", "F", "G")
    assert table.rows == ()


def test_escaped_pipe_is_one_cell() -> None:
    table = read_table(_numbered(["| A | B |", "| :--- | ---: |", "| x \\| y | z |"], 1))
    assert table.columns == ("A", "B")
    assert table.rows[0].cells == ("x | y", "z")


def test_leading_and_trailing_spaces_stripped() -> None:
    table = read_table(
        _numbered(["   | A | B |   ", "   |---|:---:|", "   | 1,390 | — (reported dash) |"], 1)
    )
    assert table.columns == ("A", "B")
    assert table.rows[0].cells == ("1,390", "— (reported dash)")


def test_later_dash_row_is_ordinary() -> None:
    table = read_table(_numbered(["| A | B |", "| --- | --- |", "| --- | --- |"], 1))
    assert table.rows[0].cells == ("---", "---")


def test_label() -> None:
    lines = _numbered(["| A | B |", "| --- | --- |"], 1)
    assert read_table(lines, label="Leverage").label == "Leverage"
    assert read_table(lines).label is None


@pytest.mark.parametrize("text", ["| a |", "   | a", "|"])
def test_is_table_row_true(text: str) -> None:
    assert is_table_row(text)


@pytest.mark.parametrize("text", ["    | a |", "a | b", "", " x|"])
def test_is_table_row_false(text: str) -> None:
    assert not is_table_row(text)


_CELL = st.text(
    alphabet=st.characters(exclude_characters="\\\n\r", exclude_categories=["Cs"]),
    max_size=8,
).map(str.strip)


@st.composite
def _tables(draw: st.DrawFn) -> tuple[list[str], list[list[str]]]:
    width = draw(st.integers(min_value=2, max_value=6))
    columns = draw(st.lists(_CELL, min_size=width, max_size=width))
    rows = draw(st.lists(st.lists(_CELL, min_size=width, max_size=width), max_size=4))
    return columns, rows


def _render(cells: list[str]) -> str:
    return "| " + " | ".join(cell.replace("|", "\\|") for cell in cells) + " |"


@given(_tables())
def test_round_trip(table: tuple[list[str], list[list[str]]]) -> None:
    columns, rows = table
    texts = [_render(columns), "|" + "---|" * len(columns), *map(_render, rows)]
    read = read_table(_numbered(texts, 1))
    assert read.columns == tuple(columns)
    assert [list(row.cells) for row in read.rows] == rows


@given(_tables(), st.data())
def test_wrong_cell_count_refused(
    table: tuple[list[str], list[list[str]]], data: st.DataObject
) -> None:
    columns, rows = table
    if not rows:
        rows = [list(columns)]
    index = data.draw(st.integers(min_value=0, max_value=len(rows) - 1))
    bad = list(rows[index])
    if data.draw(st.booleans()):
        bad.append("x")
    else:
        bad.pop()
    rows = [*rows[:index], bad, *rows[index + 1 :]]
    texts = [_render(columns), "|" + "---|" * len(columns), *map(_render, rows)]
    with pytest.raises(HandoffError) as caught:
        read_table(_numbered(texts, 1))
    assert caught.value.line == index + 3
