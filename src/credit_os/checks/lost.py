"""What a repair dropped: the values of a refused draft that the next draft no longer holds.

`lost_values(previous, new, named)` is a pure function of two parsed documents and the findings
of the previous one; it adds no check id and returns no `Finding` (a `LostValue` is a record of
two drafts). It raises nothing on content: a fault is a bug, and the write path's fail-open is
what catches it. Each document is read once, node by node (the title, front-matter values, section
titles, paragraph, list and code lines, table cells), figures with `figures.read_figures`; a
table cell is a node, so nothing is read across cells.

Kept: the key of every figure read (dates not masked) and of every `DATE` match in any node of
`new`, comments included. A figure's key is its value (a `Decimal`, so 4.10 is 4.1), sign, unit
and currency; a date's key is its text, casefolded, with its whitespace folded.

Tracked, in the nodes of `previous` (comments are not read), figures read with dates and period
labels masked: an amount (a currency, a unit, a decimal part, a thousands separator or three
significant digits; at the start of its node or after a space, `(` or `:`, the currency written
before the number counting as its start; not written in brackets as a note; not a bare year; not
after `note`, `page`, `row`, `item`, `step`, `section`, `table` or a period word), a bracketed
negative of three digits or more or with a decimal point, a bare number alone in a table cell,
and every date.

Excused: a tracked value on line L whose number (or date) is read in the `quoted` text of a
finding of `named` at line L. A finding's line is never a value and its reason is never read.

Lost: tracked, not kept, not excused, and the first of its key. Order: line, then cell, then
column. Left out of the predecessor and named: the readers of issue prose, the same-shape twin
excuse and the fraction-to-percentage rule.
"""

import re
from collections.abc import Hashable, Iterable, Sequence
from typing import NamedTuple

from pydantic import Field, field_validator

from credit_os.checks.figures import DATE, Figure, _currency_span, read_figures
from credit_os.checks.findings import Finding, _one_line
from credit_os.checks.prose import nodes
from credit_os.checks.text import all_sections
from credit_os.handoff.document import HandoffDocument
from credit_os.handoff.errors import echo
from credit_os.handoff.scan import Node
from credit_os.handoff.tables import Table

_BARE_CELL = re.compile(r"-?[0-9]+(?:\.[0-9]+)?")
_REFERENCE = re.compile(
    r"\b(?:notes?|pages?|pp?\.|rows?|items?|steps?|sections?|tables?)\s*$", re.IGNORECASE
)
_PERIOD_BEFORE = re.compile(
    r"\b(?:FY|CY|LTM|YTD|Q[1-4]|H[12]|[1-4]Q|[12]H|years?|yr)\s?$", re.IGNORECASE
)
_FIRST_DIGIT = re.compile(r"[0-9.]")
# The longest word the two patterns above match is `sections` (8), plus one space: 40 characters
# before the number cover it, so a figure never reads the whole text before it.
_LOOK_BEHIND = 40
_AFTER = "(:"
_MIN_DIGITS = 3


class LostValue(Node):
    """One value an earlier draft held and the next does not."""

    line: int = Field(ge=1, description="The line in the earlier draft.")
    value: str = Field(description="The figure as shown (with its currency code), or the date.")
    label: str = Field(description="A table row's first cell, else the line.")

    @field_validator("value", "label")
    @classmethod
    def _cut(cls, text: str) -> str:
        return echo(_one_line(text))


class _Tracked(NamedTuple):
    column: int
    key: Hashable
    value: str
    excuse: Hashable


def _date_key(text: str) -> str:
    return " ".join(text.split()).casefold()


def _key(figure: Figure) -> Hashable:
    return (figure.value, figure.negative, figure.unit, figure.currency)


def _kept(document: HandoffDocument) -> set[Hashable]:
    kept: set[Hashable] = set()
    for _, text in nodes(document):
        kept.update(_key(figure) for figure in read_figures(text, passage=False))
        kept.update(_date_key(found[0]) for found in DATE.finditer(text))
    return kept


def _excuses(named: Sequence[Finding]) -> dict[int, set[Hashable]]:
    excuses: dict[int, set[Hashable]] = {}
    for finding in named:
        read = excuses.setdefault(finding.line, set())
        read.update(f.value for f in read_figures(finding.quoted, passage=False))
        read.update(_date_key(found[0]) for found in DATE.finditer(finding.quoted))
    return excuses


def _row_label(cells: Sequence[str]) -> str:
    return cells[0] if cells and cells[0] else " | ".join(cells)


class _Tables(NamedTuple):
    labels: dict[int, str]
    cells: set[tuple[int, str]]


def _tables(document: HandoffDocument) -> _Tables:
    labels: dict[int, str] = {}
    cells: set[tuple[int, str]] = set()
    for section in all_sections(document):
        for block in section.blocks:
            if isinstance(block, Table):
                labels[block.line] = _row_label(block.columns)
                for row in block.rows:
                    labels[row.line] = _row_label(row.cells)
                    cells.update((row.line, cell) for cell in row.cells)
    return _Tables(labels, cells)


def _ends_at(pattern: re.Pattern[str], text: str, end: int) -> bool:
    first = end
    while first > 0 and text[first - 1].isspace():
        first -= 1
    return pattern.search(text, max(first - _LOOK_BEHIND, 0), end) is not None


def _number_start(text: str, figure: Figure) -> int:
    start = figure.column - 1
    found = _FIRST_DIGIT.search(figure.shown)
    return start + (0 if found is None else found.start())


def _starts_well(text: str, figure: Figure) -> bool:
    """The figure, or the currency written before it, is at the start or after a space, `(`, `:`."""
    start = figure.column - 1
    span = _currency_span(text, start)
    if span is not None and span[1] == figure.currency and span[0] < start:
        start = span[0]
    return start == 0 or text[start - 1].isspace() or text[start - 1] in _AFTER


def _bare_year(figure: Figure) -> bool:
    digits = figure.value.as_tuple().digits
    whole = figure.value.as_tuple().exponent == 0 and "," not in figure.shown
    return whole and figure.unit is None and len(digits) == 4 and 1900 <= figure.value <= 2099


def _carries(figure: Figure) -> bool:
    exponent = figure.value.as_tuple().exponent
    return (
        figure.unit is not None
        or figure.currency is not None
        or (isinstance(exponent, int) and exponent < 0)
        or "," in figure.shown
        or len(figure.value.as_tuple().digits) >= _MIN_DIGITS
    )


def _is_amount(text: str, figure: Figure) -> bool:
    if figure.shown.startswith("(") or not _carries(figure) or _bare_year(figure):
        return False
    if not _starts_well(text, figure):
        return False
    before = _number_start(text, figure)
    return not (_ends_at(_REFERENCE, text, before) or _ends_at(_PERIOD_BEFORE, text, before))


def _is_bracketed_negative(figure: Figure) -> bool:
    exponent = figure.value.as_tuple().exponent
    wide = len(figure.value.as_tuple().digits) >= _MIN_DIGITS
    return figure.bracketed and (wide or (isinstance(exponent, int) and exponent < 0))


def _as_shown(figure: Figure) -> str:
    """The figure as written, with its currency code before it when what is written holds none."""
    if figure.currency in (None, "unrecognised"):
        return figure.shown
    alone = read_figures(figure.shown, passage=False)
    if alone and alone[0].currency is not None:
        return figure.shown
    return f"{figure.currency} {figure.shown}"


def _tracked_figures(text: str, *, bare: bool) -> Iterable[Figure]:
    figures = read_figures(text, passage=True)
    chosen = [f for f in figures if _is_amount(text, f) or _is_bracketed_negative(f)]
    if bare and figures and _BARE_CELL.fullmatch(text.strip()) and figures[0] not in chosen:
        chosen.append(figures[0])
    return chosen


def _tracked(text: str, *, bare: bool) -> list[_Tracked]:
    found = [
        _Tracked(f.column, _key(f), _as_shown(f), f.value)
        for f in _tracked_figures(text, bare=bare)
    ]
    for match in DATE.finditer(text):
        key = _date_key(match[0])
        found.append(_Tracked(match.start() + 1, key, match[0], key))
    return sorted(found, key=lambda tracked: tracked.column)


def lost_values(
    previous: HandoffDocument, new: HandoffDocument, named: Sequence[Finding]
) -> tuple[LostValue, ...]:
    """The values `previous` held that `new` does not, that no finding of `named` quoted."""
    kept = _kept(new)
    excuses = _excuses(named)
    tables = _tables(previous)
    seen: set[Hashable] = set()
    lost: list[LostValue] = []
    for line, text in sorted(nodes(previous, comments=False), key=lambda node: node[0]):
        label: str | None = None
        for tracked in _tracked(text, bare=(line, text) in tables.cells):
            if tracked.key in kept or tracked.key in seen:
                continue
            if tracked.excuse in excuses.get(line, ()):
                continue
            seen.add(tracked.key)
            if label is None:
                # Cleaned and cut once per node; the field's own cut leaves a cut label as it is.
                label = echo(_one_line(tables.labels.get(line, text)))
            lost.append(LostValue(line=line, value=tracked.value, label=label))
    return tuple(lost)
