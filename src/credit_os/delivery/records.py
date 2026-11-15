"""Record blocks of a module's chart tables, and the gaps that stand where a table cannot be read.

Delivery adds no analysis: a `Chart data:` table whose header is one of the fixed forms becomes
a `chartTable` block with its cells as written; every other header gives no block. A section with
no readable table (none, two or more, no rows, a blank row label or a repeated column label)
becomes a `gap` block with the owner's wording. Figures are read by `passages.cell`; the "Basis
and limitation" column keeps the module's own qualifications and drops citations. No row check
or arithmetic is done here.

A refusal means the run cannot be written (a source name or code in a shown text, a title used
twice, an empty title): the caller leaves that run out with the reason and never aborts the
whole library. A message names the rule, never the input text.

Values are plain dicts with the slice's camelCase keys; `trace` is None here, attached later.
`at` is a `Decimal`, never a float.
"""

from collections.abc import Sequence
from typing import cast

from credit_os.delivery.errors import DeliveryRefused
from credit_os.delivery.passages import cell, narrative_leaks
from credit_os.delivery.wording import Wording
from credit_os.handoff.basis import read_cell
from credit_os.handoff.data import DataSection, read_data_sections, source_names
from credit_os.handoff.document import HandoffDocument
from credit_os.handoff.tables import Table

_UNIT = "Reporting unit"
_BASIS = "Basis and limitation"
_LEFT_COLUMNS = 8  # the first columns the library's table styling can draw left-aligned
_IDENTITY = tuple[str | None, str | None, str]

# header -> (chart, figure column indexes); the "columns" chart is matched by shape instead.
_HEADERS: dict[tuple[str, ...], tuple[str, tuple[int, ...]]] = {
    ("Step", "Amount", _UNIT, _BASIS): ("bridge", (1,)),
    (
        "Facility",
        "Ranking",
        "Secured",
        "Amount",
        "Cumulative leverage",
        _UNIT,
        _BASIS,
    ): ("stack", (3, 4)),
    (
        "Test",
        "Threshold",
        "Current",
        "Headroom",
        "Direction",
        _UNIT,
        _BASIS,
    ): ("bullet", (1, 2, 3)),
    (
        "Agency",
        "Trigger",
        "Threshold",
        "Current",
        "Direction",
        _UNIT,
        _BASIS,
    ): ("bullet", (2, 3)),
    (
        "Metric",
        "Issuer",
        "Peer low",
        "Peer median",
        "Peer high",
        "Peer count",
        _UNIT,
        _BASIS,
    ): ("range", (1, 2, 3, 4, 5)),
    (
        "Instrument",
        "Maturity date",
        "Yield",
        "Spread",
        "Quote date",
        "Source class",
        _UNIT,
        _BASIS,
    ): ("scatter", (2, 3)),
}


def _refuse(rule: str) -> DeliveryRefused:
    return DeliveryRefused(f"chart records: {rule}")


def _kind(header: tuple[str, ...]) -> tuple[str, tuple[int, ...]] | None:
    fixed = _HEADERS.get(header)
    if fixed is not None:
        return fixed
    if len(header) >= 4 and header[0] == "Period" and header[-2] == _UNIT and header[-1] == _BASIS:
        return "columns", tuple(range(1, len(header) - 2))
    return None


def _readable(table: Table) -> bool:
    labels = table.columns
    return (
        bool(table.rows)
        and all(row.cells[0] for row in table.rows)
        and all(labels)
        and len(set(labels)) == len(labels)
    )


def _basis(text: str, known: Sequence[str]) -> str | None:
    """The cell's qualifications: module, calculation and pinned-source items are citations."""
    items = read_cell(text, known)
    if not items:
        return None
    kept = [
        item
        for item in items
        if item.kind == "text" or (item.kind == "source" and item.file not in known)
    ]
    if len(kept) == len(items):
        return text
    return "; ".join(item.text for item in kept) if kept else None


def _figure_cells(
    table: Table, figures: tuple[int, ...]
) -> list[dict[int, tuple[dict[str, object] | None, _IDENTITY | None]]]:
    last_unit = len(table.columns) - 2
    out: list[dict[int, tuple[dict[str, object] | None, _IDENTITY | None]]] = []
    for row in table.rows:
        read: dict[int, tuple[dict[str, object] | None, _IDENTITY | None]] = {}
        for index in figures:
            value, kind = cell(row.cells[index])
            identity = None if kind is None else (kind[0], kind[1], row.cells[last_unit])
            read[index] = (value, identity)
        out.append(read)
    return out


def _mixed(
    read: list[dict[int, tuple[dict[str, object] | None, _IDENTITY | None]]], index: int
) -> bool:
    identities = {item[index][1] for item in read if item[index][1] is not None}
    return len(identities) >= 2


def _shown(value: dict[str, object] | None, mixed: bool) -> dict[str, object] | None:
    if value is None or not mixed or value["kind"] != "value":
        return value
    return {**value, "at": None}


def _texts(block: dict[str, object]) -> list[str]:
    """Every title, column label, string cell, value text and gap reason a block shows."""
    found = [str(block["title"])]
    if block["kind"] == "gap":
        return found + [str(block["reason"])]
    found.extend(column["label"] for column in cast(list[dict[str, str]], block["columns"]))
    for row in cast(list[dict[str, list[object]]], block["rows"]):
        for item in row["cells"]:
            if isinstance(item, str):
                found.append(item)
            elif isinstance(item, dict):
                found.append(str(item["text"] if item["kind"] == "value" else item["reason"]))
    return found


def _chart_table(
    section: DataSection, table: Table, chart: str, figures: tuple[int, ...], known: Sequence[str]
) -> dict[str, object]:
    width = len(table.columns)
    read = _figure_cells(table, figures)
    mixed = {index: _mixed(read, index) for index in figures}
    rows: list[dict[str, object]] = []
    for row, shown in zip(table.rows, read, strict=True):
        cells: list[object] = [row.cells[0]]
        for index in range(1, width):
            text = row.cells[index]
            if index in figures:
                cells.append(_shown(shown[index][0], mixed[index]))
            elif index == width - 1:
                cells.append(_basis(text, known))
            else:
                cells.append(text or None)
        rows.append({"cells": cells, "emphasis": False})
    columns = [
        {
            "label": label,
            "align": "left"
            if index == 0 or (index < _LEFT_COLUMNS and index not in figures)
            else "right",
        }
        for index, label in enumerate(table.columns)
    ]
    return {
        "kind": "chartTable",
        "nav": None,
        "title": section.name,
        "chart": chart,
        "note": None,
        "columns": columns,
        "rows": rows,
        "footnotes": [],
        "trace": None,
    }


def _block(
    section: DataSection, wording: Wording, known: Sequence[str]
) -> dict[str, object] | None:
    table = section.table
    fixed = None if table is None else _kind(table.columns)
    if table is not None and fixed is None:
        return None
    if table is None or fixed is None or not _readable(table):
        reason = wording.fill("records.chart_gap", {})
        return {"kind": "gap", "nav": None, "title": section.name, "reason": reason}
    return _chart_table(section, table, fixed[0], fixed[1], known)


def chart_records(document: HandoffDocument, wording: Wording) -> tuple[dict[str, object], ...]:
    """The chart-table and gap blocks of `document`, in the order its chart sections appear.

    Raises `DeliveryRefused` when the run cannot be written (R24 condition 1): a source name or
    a module, table or digest code in a title, column label, text or gap reason, a title used by
    two chart sections, or an empty title. The caller leaves that run out with the reason.
    """
    known = source_names(document)
    blocks: list[dict[str, object]] = []
    titles: set[str] = set()
    for section in read_data_sections(document):
        if section.kind != "chart":
            continue
        if not section.name:
            raise _refuse("empty title")
        if section.name in titles:
            raise _refuse("title used twice")
        titles.add(section.name)
        block = _block(section, wording, known)
        if block is None:
            continue
        if any(narrative_leaks(text, known) for text in _texts(block)):
            raise _refuse("source name or code in shown text")
        blocks.append(block)
    return tuple(blocks)
