"""Prose checks 6 and 7, and the limitation helpers step 5A reads.

`prose.register-id`: an id is a table cell, any table at any depth, in a column headed `id` or
ending ` id` (case-folded), that holds a letter and a digit once backticks, asterisks and spaces
are stripped from its two ends. Each whole-token occurrence of an id in passage text is one
refusal (it may not touch a letter, digit, `_` or `-`); `column` is the 1-based position of the
match in the text line.

A limitation is one paragraph or list item of the Limitations passage, nested sections included,
data sections excluded, without its Basis line, its lines joined by single spaces; an item left
with no line is no item. `normalise_limitation` is the key by which two are the same.
`prose.limitation-repeat` refuses, at its first line, each item whose key an accepted module or
an earlier item of this document already has; an empty key is skipped.

Both checks read the reader view and find nothing when `read_reader` refuses the document or the
format is the earlier one. Text taken from the handoff inside a reason is bounded by `echo`.
"""

import re
from collections.abc import Iterable

from credit_os.checks.findings import CheckContext, Finding, refusal
from credit_os.checks.text import all_sections, passage_text, section_blocks, try_reader
from credit_os.handoff.basis import read_basis
from credit_os.handoff.document import HandoffDocument
from credit_os.handoff.errors import echo
from credit_os.handoff.scan import Node
from credit_os.handoff.tables import Table


class _Item(Node):
    line: int
    first: str
    text: str


def _is_id(cell: str) -> bool:
    return any(char.isalpha() for char in cell) and any(char.isdigit() for char in cell)


def _id_cells(table: Table) -> Iterable[str]:
    for index, name in enumerate(table.columns):
        header = name.casefold()
        if header == "id" or header.endswith(" id"):
            for row in table.rows:
                yield row.cells[index].strip("`* ")


def _ids(document: HandoffDocument) -> tuple[str, ...]:
    tables = (
        block
        for section in all_sections(document)
        for block in section.blocks
        if isinstance(block, Table)
    )
    return tuple(
        dict.fromkeys(cell for table in tables for cell in _id_cells(table) if _is_id(cell))
    )


def check_register_id(document: HandoffDocument, context: CheckContext) -> tuple[Finding, ...]:
    reader = try_reader(document)
    if reader is None or reader.format != "new":
        return ()
    patterns = [
        (id_, re.compile(rf"(?<![\w-]){re.escape(id_)}(?![\w-])")) for id_ in _ids(document)
    ]
    return tuple(
        refusal(
            "prose.register-id",
            line.line,
            id_,
            f"Remove the register id `{echo(id_)}` from the text; ids belong in the tables.",
            found.start() + 1,
        )
        for line in passage_text(document, reader)
        for id_, pattern in patterns
        for found in pattern.finditer(line.text)
    )


def _items(document: HandoffDocument) -> tuple[_Item, ...]:
    reader = try_reader(document)
    if reader is None or reader.limitations is None:
        return ()
    items: list[_Item] = []
    for block in section_blocks(document, reader.limitations):
        lines = block.lines[:-1] if read_basis(block) is not None else block.lines
        if lines:
            items.append(_Item(line=block.line, first=lines[0], text=" ".join(lines)))
    return tuple(items)


def limitation_texts(document: HandoffDocument) -> tuple[str, ...]:
    return tuple(item.text for item in _items(document))


def normalise_limitation(text: str) -> str:
    kept = "".join(char for char in text.lower() if char.isalnum() or char.isspace())
    return " ".join(kept.split())


def check_limitation_repeat(
    document: HandoffDocument, context: CheckContext
) -> tuple[Finding, ...]:
    seen = {
        normalise_limitation(text)
        for accepted in context.accepted.values()
        for text in limitation_texts(accepted)
    }
    found: list[Finding] = []
    for item in _items(document):
        key = normalise_limitation(item.text)
        if not key:
            continue
        if key in seen:
            found.append(
                refusal(
                    "prose.limitation-repeat",
                    item.line,
                    item.first,
                    "Replace this limitation with one specific to this module; it repeats one "
                    "already given.",
                )
            )
        seen.add(key)
    return tuple(found)
