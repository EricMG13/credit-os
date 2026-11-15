"""Read the bold lead label that opens a paragraph or list item.

A lead is `**label**` at the very start of the block's first line, optionally followed by one
`:` that belongs to the mark. The lines considered are the block's body without its Basis line.
Nothing is guessed: only the first line is read, and anything that does not fit is no lead.

The trailing Basis line is left out of `rest`; the caller reads it with `read_basis`. The label is
exactly the text inside the marks, not trimmed or normalised afterwards.

Known limits: only the `**` form counts (not `__`); a label holding `*` is no lead, so nested
emphasis and `***x***` are refused; a bold span that does not close on the first line is no
lead; a second bold span stays ordinary text in `rest`.
"""

from credit_os.handoff.basis import read_basis
from credit_os.handoff.blocks import ListItem, Paragraph
from credit_os.handoff.scan import Node

_MARK = "**"


class Lead(Node):
    line: int
    label: str
    rest: tuple[str, ...]


def read_lead(block: Paragraph | ListItem) -> Lead | None:
    basis = read_basis(block)
    lines = block.lines if basis is None else basis.body
    if not lines:
        return None
    first = lines[0]
    if not first.startswith(_MARK):
        return None
    close = first.find(_MARK, len(_MARK))
    if close < 0:
        return None
    label = first[len(_MARK) : close]
    if not label or "*" in label or label[0].isspace() or label[-1].isspace():
        return None
    after = first[close + len(_MARK) :].removeprefix(":")
    if after and after[0] not in " \t":
        return None
    remainder = after.lstrip()
    rest = (remainder,) if remainder else ()
    return Lead(line=block.line, label=label, rest=rest + tuple(lines[1:]))
