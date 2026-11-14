"""Read the reader-facing passages of a handoff: the format, four passages or a summary.

The format is new when the first level-3 section under `Findings` is `Bottom line`. Only
real sections are read, never text inside a code block.

Passages exist only in the new format; a repeated passage heading is refused here, not by
`parse`. In the earlier format a repeated `Reader summary` heading is refused the same way, as
either one would be a guess; in the new format that title is not special. An earlier-format
summary has three states: no `Reader summary` section (`summary_section`
None); a section that does not hold exactly its two tables (`summary` None, `summary_section`
set: present but unreadable); or both set. In the new format both are None. Blocks under a deeper
heading inside a passage are in the passage's `sections`, not its `blocks`.
"""

from typing import Literal

from credit_os.handoff.blocks import Paragraph
from credit_os.handoff.document import HandoffDocument, Section
from credit_os.handoff.errors import HandoffError
from credit_os.handoff.scan import Node
from credit_os.handoff.tables import Table

_BOTTOM_LINE = "Bottom line"
_KEY_FINDINGS = "Key findings"
_CONTRARY = "Contrary evidence and what would change the view"
_LIMITATIONS = "Limitations"
_READER_SUMMARY = "Reader summary"
_BLOCKED = "Not assessable:"
_SUMMARY_CALL = ("Bottom line", "Confidence", "Main limitation")
_SUMMARY_FINDINGS = ("Finding", "Creditor impact", "Confidence")


class SummaryFinding(Node):
    line: int
    finding: str
    impact: str
    confidence: str


class ReaderSummary(Node):
    line: int
    bottom_line: str
    confidence: str
    limitation: str
    findings: tuple[SummaryFinding, ...]


class Reader(Node):
    format: Literal["new", "earlier"]
    bottom_line: Section | None
    key_findings: Section | None
    contrary: Section | None
    limitations: Section | None
    summary: ReaderSummary | None
    summary_section: Section | None

    @property
    def blocked(self) -> bool:
        """True when the new format's Bottom line opens with a paragraph `Not assessable:`.

        The test is on the paragraph's first line as the parser shows it (comments removed,
        surrounding whitespace stripped).
        """
        if self.format != "new" or self.bottom_line is None or not self.bottom_line.blocks:
            return False
        first = self.bottom_line.blocks[0]
        return isinstance(first, Paragraph) and first.lines[0].startswith(_BLOCKED)


def _passages(level_three: list[Section]) -> dict[str, Section]:
    found: dict[str, Section] = {}
    for section in level_three:
        if section.title not in (_BOTTOM_LINE, _KEY_FINDINGS, _CONTRARY, _LIMITATIONS):
            continue
        if section.title in found:
            raise HandoffError(section.line, f"passage heading `{section.title}` is repeated")
        found[section.title] = section
    return found


def _summary(section: Section | None) -> ReaderSummary | None:
    if section is None:
        return None
    tables = [block for block in section.blocks if isinstance(block, Table)]
    if len(tables) != 2:
        return None
    call, findings = tables
    if call.columns != _SUMMARY_CALL or len(call.rows) != 1:
        return None
    if findings.columns != _SUMMARY_FINDINGS or not findings.rows:
        return None
    row = call.rows[0]
    return ReaderSummary(
        line=row.line,
        bottom_line=row.cells[0],
        confidence=row.cells[1],
        limitation=row.cells[2],
        findings=tuple(
            SummaryFinding(
                line=item.line,
                finding=item.cells[0],
                impact=item.cells[1],
                confidence=item.cells[2],
            )
            for item in findings.rows
        ),
    )


def read_reader(document: HandoffDocument) -> Reader:
    level_three = [s for s in document.sections[2].sections if s.level == 3]
    if level_three and level_three[0].title == _BOTTOM_LINE:
        found = _passages(level_three)
        return Reader(
            format="new",
            bottom_line=found.get(_BOTTOM_LINE),
            key_findings=found.get(_KEY_FINDINGS),
            contrary=found.get(_CONTRARY),
            limitations=found.get(_LIMITATIONS),
            summary=None,
            summary_section=None,
        )
    sections = [s for s in level_three if s.title == _READER_SUMMARY]
    if len(sections) > 1:
        raise HandoffError(sections[1].line, f"heading `{_READER_SUMMARY}` is repeated")
    section = sections[0] if sections else None
    return Reader(
        format="earlier",
        bottom_line=None,
        key_findings=None,
        contrary=None,
        limitations=None,
        summary=_summary(section),
        summary_section=section,
    )
