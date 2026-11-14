"""The confidence checks and the confidence score.

Both come from one reading of the document, `_read`, so a refusal and a value never disagree.
A module's `### Confidence inputs` section (a data section of kind `confidence`) is read when it is
the first one, a level-3 section directly under `Findings`, titled exactly `Confidence inputs`,
holding one table with the columns `Input` and `Value`. Its fourteen rows, each once in any order,
are the eight lineage counts, `Fields present`, `Fields total`, `Source gate`, `CRITICAL`,
`MATERIAL` and `MINOR`. A count is one to twenty ASCII digits, read as written (leading zeros
allowed), never as zero when it cannot be read.

A blocked module (`structure.is_blocked`, or on a reader error `module_status: blocked` alone) may
write the one row `Not assessable` with `Not supplied: <reason>` instead: no score, no finding.

The state is `refused` when any finding other than `confidence.absent` is made, `absent` when there
is no section, `blocked` for the one row, and otherwise `scored`. The score is exact: `int` and
`fractions.Fraction` only, rounded half to even. The earlier format is never scored: its outcome is `absent`, and `check_handoff` runs no
confidence check on it.
"""

from collections.abc import Mapping
from fractions import Fraction
from typing import Literal

from credit_os.checks.findings import CheckContext, Finding, refusal
from credit_os.checks.structure import front_matter_blocked, is_blocked
from credit_os.checks.text import is_earlier, try_reader
from credit_os.handoff.data import DataSection, read_data_sections
from credit_os.handoff.document import HandoffDocument
from credit_os.handoff.scan import Node
from credit_os.handoff.tables import Row, Table

_TITLE = "Confidence inputs"
_BLOCKED_ROW = "Not assessable"
_LINEAGE = (
    "Directly Sourced",
    "Calculated",
    "Assumption-Based",
    "Analyst Inference",
    "Weak Lineage",
    "Untraced",
    "Conflicting",
    "Insufficient Information",
)
_WEIGHTS = (
    Fraction(1),
    Fraction(9, 10),
    Fraction(1, 2),
    Fraction(2, 5),
    Fraction(3, 10),
    Fraction(0),
    Fraction(0),
    Fraction(0),
)
_FIELDS = ("Fields present", "Fields total")
_GATE = "Source gate"
_FINDINGS = ("CRITICAL", "MATERIAL", "MINOR")
_ROWS = (*_LINEAGE, *_FIELDS, _GATE, *_FINDINGS)
_GATES = {"pass": Fraction(1), "partial": Fraction(7, 10), "fail": Fraction(0)}
_FORBIDDEN = ("confidence_score", "confidence_band", "qa_status")
_MAX_DIGITS = 20


class ConfidenceOutcome(Node):
    state: Literal["scored", "blocked", "absent", "refused"]
    value: int | None = None
    band: Literal["High", "Medium", "Low", "Insufficient Information"] | None = None
    status: Literal["Passed", "Restricted", "Blocked"] | None = None


def _band(value: int) -> Literal["High", "Medium", "Low", "Insufficient Information"]:
    if value >= 80:
        return "High"
    if value >= 60:
        return "Medium"
    if value >= 40:
        return "Low"
    return "Insufficient Information"


def _score(counts: Mapping[str, int], gate: Fraction) -> ConfidenceOutcome:
    claims = sum(counts[name] for name in _LINEAGE)
    weighted = sum(weight * counts[name] for weight, name in zip(_WEIGHTS, _LINEAGE, strict=True))
    evidence = Fraction(100) * weighted * Fraction(1, claims) if claims else Fraction(0)
    completeness = Fraction(100 * counts["Fields present"], counts["Fields total"])
    raw = (
        (Fraction(3, 5) * evidence + Fraction(2, 5) * completeness) * gate
        - 40 * counts["CRITICAL"]
        - 15 * counts["MATERIAL"]
        - 3 * counts["MINOR"]
    )
    value = min(max(round(raw), 0), 100)
    if counts["CRITICAL"]:
        value = min(value, 39)
        return ConfidenceOutcome(state="scored", value=value, band=_band(value), status="Blocked")
    if counts["MATERIAL"]:
        value = min(value, 59)
        return ConfidenceOutcome(
            state="scored", value=value, band=_band(value), status="Restricted"
        )
    return ConfidenceOutcome(state="scored", value=value, band=_band(value), status="Passed")


def _is_count(cell: str) -> bool:
    return cell.isascii() and cell.isdigit() and len(cell) <= _MAX_DIGITS


def _reason_of_blocked_row(rows: tuple[Row, ...]) -> bool:
    if len(rows) != 1 or rows[0].cells[0] != _BLOCKED_ROW:
        return False
    cell = rows[0].cells[1]
    return cell.startswith("Not supplied:") and bool(cell[len("Not supplied:") :].strip())


def _front_matter(document: HandoffDocument) -> list[Finding]:
    if document.front_matter is None:
        return []
    return [
        refusal(
            "confidence.front-matter",
            entry.line,
            entry.key,
            "Remove the key: the score is computed from the inputs table, not written.",
        )
        for entry in document.front_matter.entries
        if entry.key in _FORBIDDEN
    ]


def _misplaced(document: HandoffDocument, found: DataSection) -> bool:
    under_findings = found.section in document.sections[2].sections
    placed = under_findings and found.section.level == 3
    return found.section.title != _TITLE or not placed


def _row_findings(table: Table) -> tuple[list[Finding], dict[str, Row]]:
    out: list[Finding] = []
    first: dict[str, Row] = {}
    for row in table.rows:
        name = row.cells[0]
        if name in _ROWS and name not in first:
            first[name] = row
            continue
        reason = "Write each of the fourteen rows once, with the names the method gives."
        out.append(refusal("confidence.rows", row.line, name, reason))
    missing = [name for name in _ROWS if name not in first]
    if missing:
        reason = "Add the missing rows: " + ", ".join(missing) + "."
        out.append(refusal("confidence.rows", table.line, "Input", reason))
    return out, first


def _count_findings(first: Mapping[str, Row]) -> tuple[list[Finding], dict[str, int]]:
    out: list[Finding] = []
    counts: dict[str, int] = {}
    for name, row in first.items():
        if name == _GATE:
            continue
        cell = row.cells[1]
        if _is_count(cell):
            counts[name] = int(cell)
        else:
            reason = f"Write {name} as a whole number of 1 to {_MAX_DIGITS} digits, not a gap."
            out.append(refusal("confidence.count", row.line, cell, reason))
    return out, counts


def _range_findings(first: Mapping[str, Row], counts: Mapping[str, int]) -> list[Finding]:
    out: list[Finding] = []
    present, total = _FIELDS
    if total in counts and counts[total] == 0:
        row = first[total]
        out.append(refusal("confidence.range", row.line, row.cells[1], "Write at least 1."))
    elif total in counts and present in counts and counts[present] > counts[total]:
        row = first[present]
        reason = "Write Fields present as no more than Fields total."
        out.append(refusal("confidence.range", row.line, row.cells[1], reason))
    gate = first.get(_GATE)
    if gate is not None and gate.cells[1].strip().casefold() not in _GATES:
        reason = "Write Source gate as pass, partial or fail."
        out.append(refusal("confidence.range", gate.line, gate.cells[1], reason))
    return out


def _read(
    document: HandoffDocument, context: CheckContext
) -> tuple[tuple[Finding, ...], ConfidenceOutcome]:
    found = [*_front_matter(document)]
    sections = [item for item in read_data_sections(document) if item.kind == "confidence"]
    if not sections:
        absent: list[Finding] = []
        if context.scored:
            line = document.sections[2].line
            reason = "Write the Confidence inputs table in the Findings section."
            absent = [refusal("confidence.absent", line, "Findings", reason)]
        return (*found, *absent), ConfidenceOutcome(state="refused" if found else "absent")
    for later in sections[1:]:
        reason = "Write the Confidence inputs section once."
        found.append(
            refusal("confidence.repeated", later.section.line, later.section.title, reason)
        )
    section = sections[0]
    table = section.table
    if table is None or _misplaced(document, section):
        reason = (
            "Make Confidence inputs a level-3 section under Findings holding one table "
            "with the columns Input and Value."
        )
        found.append(
            refusal("confidence.unreadable", section.section.line, section.section.title, reason)
        )
        return tuple(found), ConfidenceOutcome(state="refused")
    return _read_table(document, table, found)


def _read_table(
    document: HandoffDocument, table: Table, found: list[Finding]
) -> tuple[tuple[Finding, ...], ConfidenceOutcome]:
    reader = try_reader(document)
    blocked = front_matter_blocked(document) if reader is None else is_blocked(document, reader)
    if _reason_of_blocked_row(table.rows):
        if blocked:
            return tuple(found), ConfidenceOutcome(state="refused" if found else "blocked")
        row = table.rows[0]
        reason = "Write the fourteen input rows: only a blocked module writes Not assessable."
        found.append(refusal("confidence.blocked-row", row.line, _BLOCKED_ROW, reason))
        return tuple(found), ConfidenceOutcome(state="refused")
    rows, first = _row_findings(table)
    counted, counts = _count_findings(first)
    found += [*rows, *counted, *_range_findings(first, counts)]
    if found:
        return tuple(found), ConfidenceOutcome(state="refused")
    gate = _GATES[first[_GATE].cells[1].strip().casefold()]
    return (), _score(counts, gate)


def check_confidence(document: HandoffDocument, context: CheckContext) -> tuple[Finding, ...]:
    return _read(document, context)[0]


def confidence_outcome(document: HandoffDocument, context: CheckContext) -> ConfidenceOutcome:
    if is_earlier(try_reader(document)):
        return ConfidenceOutcome(state="absent")
    return _read(document, context)[1]
