"""Read one Markdown table from its consecutive row lines.

A row is its text without leading spaces and trailing whitespace, between two boundary
pipes; the closing one must not be escaped. Cells split on every `|` not preceded by a
backslash (backticks do not protect a pipe), are stripped, then `\\|` becomes `|`.
"""

import re
from collections.abc import Sequence

from credit_os.handoff.errors import HandoffError
from credit_os.handoff.scan import Node

_ROW_START = re.compile(r" {0,3}\|")
_UNESCAPED_PIPE = re.compile(r"(?<!\\)\|")
_SEPARATOR_CELL = re.compile(r":?-{3,}:?")
_SEPARATOR_MESSAGE = "the table header is not followed by a separator row of --- cells"


class Row(Node):
    line: int
    cells: tuple[str, ...]


class Table(Node):
    line: int
    label: str | None
    label_line: int | None
    columns: tuple[str, ...]
    rows: tuple[Row, ...]


def is_table_row(text: str) -> bool:
    return _ROW_START.match(text) is not None


def _cells(number: int, text: str) -> tuple[str, ...]:
    row = text.lstrip(" ").rstrip()
    if len(row) < 2 or not row.endswith("|") or row.endswith("\\|"):
        raise HandoffError(number, "the table row needs a closing pipe")
    return tuple(cell.strip().replace("\\|", "|") for cell in _UNESCAPED_PIPE.split(row[1:-1]))


def read_table(
    lines: Sequence[tuple[int, str]], label: str | None = None, label_line: int | None = None
) -> Table:
    """Read a table; the caller passes only lines for which `is_table_row` is true."""
    if (label is None) != (label_line is None):
        raise ValueError("label and label_line are given together or not at all")
    first, header_text = lines[0]
    header = _cells(first, header_text)
    if len(lines) < 2:
        raise HandoffError(first, _SEPARATOR_MESSAGE)
    separator = _cells(*lines[1])
    if not all(_SEPARATOR_CELL.fullmatch(cell) for cell in separator):
        raise HandoffError(first, _SEPARATOR_MESSAGE)
    if len(separator) != len(header):
        raise HandoffError(
            first,
            f"the table header has {len(header)} cells and its separator row has {len(separator)}",
        )
    if len(header) < 2:
        raise HandoffError(first, "a table needs at least two columns")
    rows: list[Row] = []
    for number, text in lines[2:]:
        cells = _cells(number, text)
        if len(cells) != len(header):
            raise HandoffError(
                number,
                f"the table row has {len(cells)} cells and the header has {len(header)}",
            )
        rows.append(Row(line=number, cells=cells))
    return Table(line=first, label=label, label_line=label_line, columns=header, rows=tuple(rows))
