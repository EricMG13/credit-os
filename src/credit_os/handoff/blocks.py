"""Read the blocks of a scanned handoff: paragraphs, list items, code blocks and tables.

Blocks are read from `Scan.shown`. A fence is one code block; headings and blank lines end
the block before them; a run of table rows is one table, labelled by a one-line bold
paragraph directly above it. Lists are flat.
"""

import re

from credit_os.handoff.errors import HandoffError
from credit_os.handoff.scan import Fence, Node, Scan
from credit_os.handoff.tables import Table, is_table_row, read_table

_LIST_MARKER = re.compile(r"^[ \t]*([-*+]|\d{1,3}[.)])[ \t](.*)$")
_LABEL = re.compile(r"^\*\*([^*]+)\*\*:?$")


class Paragraph(Node):
    line: int
    lines: tuple[str, ...]


class ListItem(Node):
    line: int
    marker: str
    lines: tuple[str, ...]


class CodeBlock(Node):
    line: int
    end: int
    info: str
    lines: tuple[str, ...]
    unclosed: bool


Block = Paragraph | ListItem | CodeBlock | Table


class _Reader:
    def __init__(self, scan: Scan) -> None:
        self.shown = scan.shown
        self.heading_lines = {heading.line for heading in scan.headings}
        self.blocks: list[Block] = []
        self.open_text: tuple[int, str | None, list[str]] | None = None
        self.after_heading = False

    def flush(self) -> None:
        if self.open_text is not None:
            line, marker, lines = self.open_text
            if marker is None:
                self.add(Paragraph(line=line, lines=tuple(lines)))
            else:
                self.add(ListItem(line=line, marker=marker, lines=tuple(lines)))
            self.open_text = None

    def add(self, block: Block) -> None:
        self.blocks.append(block)
        self.after_heading = False

    def end_by_heading(self) -> None:
        self.flush()
        self.after_heading = True

    def code(self, fence: Fence) -> None:
        self.flush()
        stop = fence.end if fence.close is None else fence.close - 1
        self.add(
            CodeBlock(
                line=fence.open,
                end=fence.end,
                info=fence.info,
                lines=self.shown[fence.open : stop],
                unclosed=fence.unclosed,
            )
        )

    def label(self) -> tuple[str | None, int | None]:
        previous = self.blocks[-1] if self.blocks else None
        if self.after_heading or not isinstance(previous, Paragraph) or len(previous.lines) != 1:
            return None, None
        found = _LABEL.match(previous.lines[0])
        if found is None:
            return None, None
        return found.group(1).strip(), previous.line

    def table(self, first: int, last: int) -> int:
        """Read the run of table rows starting at `first`; return the line after it."""
        self.flush()
        end = first
        while end <= last and is_table_row(self.shown[end - 1]):
            end += 1
        rows = [(number, self.shown[number - 1]) for number in range(first, end)]
        label, label_line = self.label()
        self.add(read_table(rows, label, label_line))
        return end

    def text(self, number: int, shown: str) -> None:
        marked = _LIST_MARKER.match(shown)
        if marked is not None:
            self.flush()
            self.open_text = (number, marked.group(1), [marked.group(2).strip()])
        elif self.open_text is not None:
            self.open_text[2].append(shown.strip())
        else:
            self.open_text = (number, None, [shown.strip()])


def read_blocks(scan: Scan, first: int = 1, last: int | None = None) -> tuple[Block, ...]:
    """Read blocks of lines `first` to `last`; ranges must start and end on block boundaries.

    Pass whole heading-to-heading ranges. A fence that opens in range is returned whole. A
    label paragraph before `first` is not looked for.
    """
    if first < 1:
        raise ValueError("first must be at least 1")
    reader = _Reader(scan)
    stop = len(scan.shown) if last is None else min(last, len(scan.shown))
    fences = {fence.open: fence for fence in scan.fences}
    inside = {number for fence in scan.fences for number in range(fence.open + 1, fence.end + 1)}
    number = first
    while number <= stop:
        shown = scan.shown[number - 1]
        if number in fences:
            reader.code(fences[number])
            number = fences[number].end + 1
        elif number in inside:
            number += 1
        elif number in reader.heading_lines:
            reader.end_by_heading()
            number += 1
        elif not shown.strip():
            reader.flush()
            number += 1
        elif is_table_row(shown):
            number = reader.table(number, stop)
        elif shown.lstrip().startswith("|"):
            raise HandoffError(
                number,
                "a line starting with | after a tab, a no-break space or more than three spaces "
                "is not a table row",
            )
        else:
            reader.text(number, shown)
            number += 1
    reader.flush()
    return tuple(reader.blocks)
