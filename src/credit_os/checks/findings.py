"""Findings returned by the checks, the closed list of check ids and the context checks read.

A finding names one check, the 1-based file line and column of the offending text, that text
as written (cut to 80 code points by `echo`) and one sentence saying what to change.
`ordered` sorts by line, then the position of the check in `CHECKS`, then column.
"""

from collections.abc import Iterable
from typing import Literal

from pydantic import Field, field_validator

from credit_os.handoff.document import HandoffDocument
from credit_os.handoff.errors import echo
from credit_os.handoff.scan import Node
from credit_os.sources.pins import SourcePin

CHECKS = (
    "structure.format",
    "structure.reader-summary",
    "structure.reader",
    "structure.passages",
    "structure.fence",
    "structure.register-id",
    "structure.registers",
    "prose.bottom-line",
    "prose.bottom-line-length",
    "prose.module-code",
    "prose.page",
    "prose.hash",
    "prose.bracket",
    "prose.pipeline-wording",
    "prose.provider-marker",
    "prose.register-id",
    "prose.limitation-repeat",
    "sources.table",
    "sources.name",
    "sources.sha256",
    "sources.type",
    "figure.form",
    "figure.not-held",
    "figure.mismatch",
    "confidence.absent",
    "confidence.repeated",
    "confidence.unreadable",
    "confidence.blocked-row",
    "confidence.front-matter",
    "confidence.rows",
    "confidence.count",
    "confidence.range",
)


class Finding(Node):
    check: str
    severity: Literal["refusal", "warning"]
    line: int = Field(ge=1)
    column: int = Field(default=1, ge=1)
    quoted: str
    reason: str = Field(min_length=1)

    @field_validator("check")
    @classmethod
    def _known_check(cls, check: str) -> str:
        if check not in CHECKS:
            raise ValueError(f"unknown check id {echo(check)!r}")
        return check

    @field_validator("quoted")
    @classmethod
    def _cut(cls, quoted: str) -> str:
        return echo(quoted)

    @property
    def message(self) -> str:
        return f'{self.check}, line {self.line}: "{self.quoted}": {self.reason}'


def _position(finding: Finding) -> tuple[int, int, int]:
    return (finding.line, CHECKS.index(finding.check), finding.column)


def ordered(findings: Iterable[Finding]) -> tuple[Finding, ...]:
    return tuple(sorted(findings, key=_position))


class CheckContext(Node):
    kind: Literal["prose", "data"]
    scored: bool = False
    pins: tuple[SourcePin, ...] = ()
    other_sources: tuple[str, ...] = ()
    upstream: dict[str, HandoffDocument] = Field(default_factory=dict)
    accepted: dict[str, HandoffDocument] = Field(default_factory=dict)
    required_registers: tuple[str, ...] = ()
