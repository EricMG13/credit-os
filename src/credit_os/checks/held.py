"""Held figures, `figure.not-held` and `figure.mismatch`.

A new-format document only; nothing when the reader view cannot be read.

Held figures are the figures (`read_figures(text, passage=False)`) of every text node of the document
(the nodes `prose.provider-marker` reads: title, front matter values, section titles, paragraph and
list lines with their Basis lines, table column names and cells, code lines, comments) except: every
node inside the four reader passages at any depth, Basis lines included, but a data section nested in
a passage that is not `Forecast inputs` still holds; every node of a `Forecast inputs` section; a table
cell that is a gap; and a paragraph or list item whose text is a gap (its Basis line with it). Held
figures are kept in file line order (cells left to right, a comment after the text of its line)
and grouped by value once per document.

Judged figures are the figures `read_figures(text, passage=True)` reads in each line of passage text,
whatever `figure.form` says, one per distinct (value, sign, brackets, unit, currency, shown) per line.
A held figure is equal when its value is equal (`Decimal` equality). It is compatible when equal and
the sign agrees (same `negative`, or the held figure has a minus and no brackets and the judged figure
is positive), and the unit and currency agree (the same recognised value, or one is None and the other
is not `unrecognised`). `figure.not-held`: no held figure is equal. `figure.mismatch`: some are equal,
none compatible; the reason names up to three distinct held spellings, in document order.
"""

from bisect import bisect_right
from collections.abc import Iterable
from decimal import Decimal
from itertools import islice
from typing import Literal

from credit_os.checks.figures import Figure, read_figures
from credit_os.checks.findings import CheckContext, Finding, refusal
from credit_os.checks.prose import block_nodes
from credit_os.checks.text import passage_text, try_reader
from credit_os.handoff.blocks import Block, ListItem, Paragraph
from credit_os.handoff.data import Gap, passage_value, read_data_sections, read_value
from credit_os.handoff.document import HandoffDocument, Section
from credit_os.handoff.errors import echo
from credit_os.handoff.reader import Reader
from credit_os.handoff.tables import Table

_NOT_HELD = (
    "Add the figure to a table, calculation or finding outside the four passages, "
    "or remove it from the passage."
)
_MISMATCH = "Keep the sign, unit and currency as the handoff writes it: "
_SPELLINGS = 3

_Kind = tuple[bool, bool, str | None, str | None]
_State = Literal["held", "passage", "dead"]


def _sections(document: HandoffDocument, reader: Reader) -> list[tuple[Section, bool]]:
    """Every section in file order, and whether the nodes it owns are held."""
    kinds = {found.section.line: found.kind for found in read_data_sections(document)}
    passages = (reader.bottom_line, reader.key_findings, reader.contrary, reader.limitations)
    lines = frozenset(section.line for section in passages if section is not None)
    found: list[tuple[Section, bool]] = []

    def walk(sections: tuple[Section, ...], state: _State) -> None:
        for section in sections:
            kind = kinds.get(section.line)
            here: _State = state
            if state == "dead" or kind == "forecast":
                here = "dead"
            elif kind is not None:
                here = "held"
            elif section.line in lines:
                here = "passage"
            found.append((section, here == "held"))
            walk(section.sections, here)

    walk(document.sections, "held")
    return found


def _table_nodes(table: Table) -> Iterable[tuple[int, str]]:
    for name in table.columns:
        yield table.line, name
    for row in table.rows:
        for cell in row.cells:
            if not isinstance(read_value(cell), Gap):
                yield row.line, cell


def _block_nodes(block: Block) -> Iterable[tuple[int, str]]:
    if isinstance(block, Table):
        return _table_nodes(block)
    if isinstance(block, Paragraph | ListItem) and isinstance(passage_value(block), Gap):
        return ()
    return block_nodes(block)


def _nodes(document: HandoffDocument, reader: Reader) -> Iterable[tuple[int, str]]:
    if document.title is not None:
        yield document.title.line, document.title.title
    if document.front_matter is not None:
        for entry in document.front_matter.entries:
            yield entry.line, entry.value
    sections = _sections(document, reader)
    for section, kept in sections:
        if kept:
            yield section.line, section.title
            for block in section.blocks:
                yield from _block_nodes(block)
    starts = [section.line for section, _ in sections]
    for comment in document.comments:
        owner = bisect_right(starts, comment.start) - 1
        if owner < 0 or sections[owner][1]:
            yield comment.start, comment.text


def _held(document: HandoffDocument, reader: Reader) -> list[Figure]:
    found = [
        (line, figure)
        for line, text in _nodes(document, reader)
        for figure in read_figures(text, passage=False)
    ]
    # A figure's column is the column inside its node, so columns of different cells do not compare.
    # `_nodes` yields cells left to right and comments last; a stable sort on the line keeps that order.
    found.sort(key=lambda item: item[0])
    return [figure for _, figure in found]


def _judged(document: HandoffDocument, reader: Reader) -> Iterable[tuple[int, Figure]]:
    for line in passage_text(document, reader):
        seen: set[tuple[Decimal, bool, bool, str | None, str | None, str]] = set()
        for figure in read_figures(line.text, passage=True):
            key = (
                figure.value,
                figure.negative,
                figure.bracketed,
                figure.unit,
                figure.currency,
                figure.shown,
            )
            if key not in seen:
                seen.add(key)
                yield line.line, figure


def _agree(held: str | None, judged: str | None) -> bool:
    if held is None or judged is None:
        return "unrecognised" not in (held, judged)
    return held == judged and held != "unrecognised"


def _compatible(held: _Kind, judged: Figure) -> bool:
    negative, bracketed, unit, currency = held
    sign = negative == judged.negative or (negative and not bracketed and not judged.negative)
    return sign and _agree(unit, judged.unit) and _agree(currency, judged.currency)


def _findings(document: HandoffDocument) -> tuple[tuple[Finding, ...], tuple[Finding, ...]]:
    reader = try_reader(document)
    if reader is None or reader.format != "new":
        return (), ()
    groups: dict[Decimal, tuple[dict[_Kind, None], dict[str, None]]] = {}
    for figure in _held(document, reader):
        kinds, spellings = groups.setdefault(figure.value, ({}, {}))
        kinds[(figure.negative, figure.bracketed, figure.unit, figure.currency)] = None
        spellings[figure.shown] = None
    not_held: list[Finding] = []
    mismatch: list[Finding] = []
    for line, figure in _judged(document, reader):
        group = groups.get(figure.value)
        if group is None:
            not_held.append(
                refusal("figure.not-held", line, figure.shown, _NOT_HELD, figure.column)
            )
        elif not any(_compatible(kind, figure) for kind in group[0]):
            written = ", ".join(echo(shown) for shown in islice(group[1], _SPELLINGS))
            mismatch.append(
                refusal(
                    "figure.mismatch",
                    line,
                    figure.shown,
                    f"{_MISMATCH}{written}.",
                    figure.column,
                )
            )
    return tuple(not_held), tuple(mismatch)


def check_not_held(document: HandoffDocument, context: CheckContext) -> tuple[Finding, ...]:
    return _findings(document)[0]


def check_mismatch(document: HandoffDocument, context: CheckContext) -> tuple[Finding, ...]:
    return _findings(document)[1]
