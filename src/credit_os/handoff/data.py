"""Typed readings of values and the Sources table of a parsed handoff.

A gap is a value the module wrote to say content is missing; the parser marks no cell itself,
the caller applies `read_value` to the cells it means. `sources_table` and `source_names` read
the table directly under `## Sources` and never refuse.
"""

from credit_os.handoff.blocks import ListItem, Paragraph
from credit_os.handoff.document import HandoffDocument
from credit_os.handoff.scan import Node
from credit_os.handoff.tables import Table

_GAP_EXACT = ("", "—", "Insufficient Information", "Not reconstructed")
_GAP_PREFIX = ("Not supplied", "Not calculable")


class Gap(Node):
    text: str


def read_value(text: str) -> Gap | str:
    if text in _GAP_EXACT or text.startswith(_GAP_PREFIX):
        return Gap(text=text)
    return text


def passage_value(block: Paragraph | ListItem) -> Gap | str:
    return read_value(" ".join(block.lines))


def sources_table(document: HandoffDocument) -> Table | None:
    tables = [block for block in document.sections[1].blocks if isinstance(block, Table)]
    return tables[0] if len(tables) == 1 else None


def source_names(document: HandoffDocument) -> tuple[str, ...]:
    table = sources_table(document)
    if table is None:
        return ()
    return tuple(row.cells[0] for row in table.rows if row.cells[0])
