"""The Sources checks: what the table under `## Sources` must change before it is accepted.

The table is `data.sources_table`; a "stated" cell is one `data.read_value` does not read as a
gap. Each check is a pure function of `(document, context)` returning refusals; none raises on
content and every `column` is 1.

`sources.table` needs the reader view and finds nothing when `read_reader` refuses the document or
the format is the earlier one; a blocked module needs no table. The other three read the table
alone. A row's first cell, compared exactly, must name a pin, an `other_sources` entry or an
upstream module as `<name> (CP-X)`. The `sha256` and `Source type` columns are checked only when a
column has exactly that header (the first, if two do); a digest must equal the pin's or the
upstream document's, and a source named by `other_sources` has none. Text taken from the handoff
inside a reason is bounded by `echo`.
"""

import re

from credit_os.checks.findings import CheckContext, Finding, refusal
from credit_os.checks.structure import is_blocked
from credit_os.checks.text import try_reader
from credit_os.handoff.data import Gap, read_value, sources_table
from credit_os.handoff.document import HandoffDocument
from credit_os.handoff.errors import echo
from credit_os.handoff.tables import Row, Table

_MODULE = re.compile(r"(.+) \((CP-[A-Z0-9]+)\)")
_TYPES = (
    "Issuer filing",
    "Peer filing",
    "Regulator or official",
    "Rating agency",
    "Industry body",
    "Financial press",
    "Other",
)


def check_table(document: HandoffDocument, context: CheckContext) -> tuple[Finding, ...]:
    reader = try_reader(document)
    if reader is None or reader.format != "new" or sources_table(document) is not None:
        return ()
    if is_blocked(document, reader):
        return ()
    return (
        refusal(
            "sources.table",
            document.sections[1].line,
            "Sources",
            "Put exactly one table directly under `## Sources`, with one row for each source.",
        ),
    )


def _named(cell: str, context: CheckContext) -> bool:
    if cell in context.other_sources or any(pin.name == cell for pin in context.pins):
        return True
    module = _MODULE.fullmatch(cell)
    return module is not None and module.group(2) in context.upstream


def _digest(cell: str, context: CheckContext) -> str | None:
    """The digest a named source must show, or None when it has none."""
    for pin in context.pins:
        if pin.name == cell:
            return pin.sha256
    module = _MODULE.fullmatch(cell)
    if cell not in context.other_sources and module is not None:
        return context.upstream[module.group(2)].sha256
    return None


def _stated(table: Table, row: Row, header: str) -> str | None:
    if header not in table.columns:
        return None
    cell = row.cells[table.columns.index(header)]
    return None if isinstance(read_value(cell), Gap) else cell


def check_name(document: HandoffDocument, context: CheckContext) -> tuple[Finding, ...]:
    table = sources_table(document)
    if table is None:
        return ()
    return tuple(
        refusal(
            "sources.name",
            row.line,
            row.cells[0],
            f"Name this source as one of the source files, or as `name (CP-X)` for an "
            f"upstream module, not `{echo(row.cells[0])}`.",
        )
        for row in table.rows
        if not _named(row.cells[0], context)
    )


def check_sha256(document: HandoffDocument, context: CheckContext) -> tuple[Finding, ...]:
    table = sources_table(document)
    if table is None:
        return ()
    found: list[Finding] = []
    for row in table.rows:
        cell = _stated(table, row, "sha256")
        if cell is None or not _named(row.cells[0], context):
            continue
        expected = _digest(row.cells[0], context)
        if expected is None:
            reason = "Leave the sha256 empty; this source has no recorded digest."
        elif cell != expected:
            reason = "Write the sha256 exactly as recorded for this source."
        else:
            continue
        found.append(refusal("sources.sha256", row.line, cell, reason))
    return tuple(found)


def check_type(document: HandoffDocument, context: CheckContext) -> tuple[Finding, ...]:
    table = sources_table(document)
    if table is None:
        return ()
    reason = f"Use exactly one of: {', '.join(_TYPES)}."
    return tuple(
        refusal("sources.type", row.line, cell, reason)
        for row in table.rows
        if (cell := _stated(table, row, "Source type")) is not None and cell not in _TYPES
    )
