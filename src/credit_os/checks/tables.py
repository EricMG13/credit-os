"""The period-table checks: the tables a module owes, as `CheckContext.owed_tables` names them.

Each check is a pure function of `(document, context)` returning a tuple of `Finding`; none
parses Markdown and none raises on content. For each owed heading with a specification, every
section titled exactly that heading, at any depth, is checked, and each must hold one table.
`table.absent` needs the reader view and finds nothing when the document is blocked or the
reader refuses it (`structure.reader` reports that); `table.header` and `table.cell` read the
sections alone. A value cell is a plain number (ASCII digits, commas only between groups of
three) or `Not supplied:` and a reason; no other gap form counts here. Every finding has
column 1; text from the handoff inside a reason is bounded by `echo`.
"""

import re

from credit_os.checks.findings import CheckContext, Finding, refusal
from credit_os.checks.structure import is_blocked
from credit_os.checks.table_specs import SPECS, TableSpec
from credit_os.checks.text import all_sections, try_reader
from credit_os.handoff.document import HandoffDocument, Section
from credit_os.handoff.errors import echo
from credit_os.handoff.tables import Row, Table

_PLAIN_NUMBER = re.compile(r"-?(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?")
_GAP = "Not supplied:"


def _specs(context: CheckContext) -> tuple[TableSpec, ...]:
    return tuple(SPECS[heading] for heading in dict.fromkeys(context.owed_tables))


def _tables_in(section: Section) -> list[Table]:
    return [block for block in section.blocks if isinstance(block, Table)]


def _written(document: HandoffDocument, spec: TableSpec) -> list[Section]:
    return [section for section in all_sections(document) if section.title == spec.heading]


def _needs(spec: TableSpec) -> str:
    return f"`### {spec.heading}` needs the table headed `| {' | '.join(spec.header)} |`."


def check_absent(document: HandoffDocument, context: CheckContext) -> tuple[Finding, ...]:
    reader = try_reader(document)
    if reader is None or reader.format != "new" or is_blocked(document, reader):
        return ()
    return tuple(
        refusal(
            "table.absent",
            document.sections[2].line,
            "Findings",
            f"Add `### {spec.heading}` inside ## Findings, with its table.",
        )
        for spec in _specs(context)
        if not _written(document, spec)
    )


def _header(spec: TableSpec, section: Section) -> Finding | None:
    found = _tables_in(section)
    if len(found) != 1:
        return refusal("table.header", section.line, section.title, _needs(spec))
    if found[0].columns != spec.header:
        return refusal("table.header", found[0].line, " | ".join(found[0].columns), _needs(spec))
    return None


def check_header(document: HandoffDocument, context: CheckContext) -> tuple[Finding, ...]:
    found = (
        _header(spec, section) for spec in _specs(context) for section in _written(document, spec)
    )
    return tuple(finding for finding in found if finding is not None)


def _is_gap(cell: str) -> bool:
    return cell.startswith(_GAP) and cell[len(_GAP) :].strip() != ""


def _value_findings(spec: TableSpec, row: Row) -> list[Finding]:
    count = len(spec.value_columns)
    period = echo(row.cells[0])
    unit = row.cells[1 + count]
    head = f"`### {spec.heading}` {period}:"
    found: list[Finding] = []
    unit_blank_reported = False
    for cell in row.cells[1 : 1 + count]:
        if _is_gap(cell):
            continue
        if _PLAIN_NUMBER.fullmatch(cell) is None:
            reason = f"{head} `{echo(cell)} |` must be a plain number or `Not supplied: <reason>`."
            found.append(refusal("table.cell", row.line, cell or row.cells[0], reason))
        elif unit == "":
            if not unit_blank_reported:
                reason = f"{head} Reporting unit is blank."
                found.append(refusal("table.cell", row.line, row.cells[0], reason))
                unit_blank_reported = True
        elif unit != spec.chart_unit:
            reason = (
                f"{head} a number in {echo(unit)} cannot be charted as {spec.chart_unit}; "
                f"write `Not supplied: reported in {echo(unit)}`."
            )
            found.append(refusal("table.cell", row.line, cell, reason))
    return found


def _row_findings(spec: TableSpec, row: Row) -> list[Finding]:
    found: list[Finding] = []
    if row.cells[-1] == "":
        reason = f"`### {spec.heading}` {echo(row.cells[0])}: Basis and limitation is blank."
        found.append(refusal("table.cell", row.line, row.cells[0], reason))
    return found + _value_findings(spec, row)


def check_cell(document: HandoffDocument, context: CheckContext) -> tuple[Finding, ...]:
    found: list[Finding] = []
    for spec in _specs(context):
        for section in _written(document, spec):
            if _header(spec, section) is not None:
                continue
            for row in _tables_in(section)[0].rows:
                found.extend(_row_findings(spec, row))
    return tuple(found)
