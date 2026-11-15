"""The trace of each traced passage, the Evidence trace table and the jump list.

A passage is traced when one of its blocks ends in a Basis line; the trace names the sources it
counts and the module-written calculation it cites. Everything shown is module-written text,
selected and placed: no analysis is added and nothing is computed. Every handoff text is a
value of a dict, never a key and never a template (a `{item}` in a heading stays literal).

R24 condition 1: a run whose Calculations section cannot be read as one table of the four
declared columns (two tables, another header, an empty ID or Calculation cell, an ID used
twice), an earlier-format document, an unknown or repeated module code, or a passage the 4b
builders refuse, cannot be written. The builder raises `DeliveryRefused`, naming the rule only
and never input text, and the caller leaves that run out with the reason.

Rows are numbered by position, module by module in input order: a module's traced passages
(bottom line, findings, contrary, change view, limitations), then its calculations.
"""

from collections.abc import Sequence
from typing import NamedTuple

from credit_os.delivery import names, passages
from credit_os.delivery.errors import DeliveryRefused
from credit_os.delivery.wording import Wording
from credit_os.handoff.basis import BasisItem, read_basis
from credit_os.handoff.blocks import Block, ListItem, Paragraph
from credit_os.handoff.data import source_names
from credit_os.handoff.document import HandoffDocument
from credit_os.handoff.errors import HandoffError
from credit_os.handoff.reader import Reader, read_reader
from credit_os.handoff.tables import Table

_COLUMNS = ("ID", "Calculation", "Steps", "Result")
_UNSET = ("", "—")
_CALCULATIONS = 3
_HEADS = ("id", "item", "value", "module", "kind", "sources")


class _Calculation(NamedTuple):
    id: str
    name: str
    node: dict[str, object]
    result: str


class _Passage(NamedTuple):
    slot: str
    heading: str
    statement: str
    blocks: tuple[Block, ...]


class _Held(NamedTuple):
    """The trace key (or None) of each item of one module, in the items map's shape."""

    bottom_line: str | None
    findings: list[str | None]
    contrary: str | None
    change_view: str | None
    limitations: list[str | None]

    def as_dict(self) -> dict[str, object]:
        return {
            "bottomLine": self.bottom_line,
            "findings": self.findings,
            "contrary": self.contrary,
            "changeView": self.change_view,
            "limitations": self.limitations,
        }


class _Built(NamedTuple):
    traces: dict[str, object]
    rows: list[dict[str, object]]
    jump: list[dict[str, object]]
    items: dict[str, object]


def _refuse(rule: str) -> DeliveryRefused:
    return DeliveryRefused(f"traces: {rule}")


def _unset(text: str) -> str | None:
    return None if text in _UNSET else text


def _node(label: str, value: str | None, note: str | None) -> dict[str, object]:
    return {"label": label, "value": value, "note": note, "children": []}


def _calculations(document: HandoffDocument) -> list[_Calculation]:
    tables = [b for b in document.sections[_CALCULATIONS].blocks if isinstance(b, Table)]
    if not tables:
        return []
    if len(tables) > 1:
        raise _refuse("more than one Calculations table")
    table = tables[0]
    if table.columns != _COLUMNS:
        raise _refuse("the Calculations table header is not ID, Calculation, Steps, Result")
    found: list[_Calculation] = []
    for row in table.rows:
        id_, name, steps, result = row.cells
        if not id_ or not name:
            raise _refuse("a calculation has no ID or no name")
        if any(item.id == id_ for item in found):
            raise _refuse("a calculation ID is used twice")
        found.append(_Calculation(id_, name, _node(name, _unset(result), _unset(steps)), result))
    return found


def _read(document: HandoffDocument) -> Reader:
    try:
        reader = read_reader(document)
    except HandoffError as error:
        raise _refuse("the passages cannot be read") from error
    if reader.format != "new":
        raise _refuse("the handoff is in the earlier format")
    return reader


def _shown(lead: object, rest: object) -> str:
    return f"{lead} {rest}" if rest else str(lead)


def _passages(reader: Reader, document: HandoffDocument, wording: Wording) -> list[_Passage]:
    """The shown items of one module in trace order; a blocked module has none."""
    if reader.blocked:
        return []
    known = source_names(document)
    bottom = passages.bottom_line(reader, known)
    found = passages.findings(reader, known)
    contrary, change = passages.contrary_and_change(reader, known)
    limits = passages.limitations(document, known)
    held = passages.item_blocks(reader, document)
    parts = [part for part in (contrary, change) if part is not None]
    if (
        len(held.findings) != len(found)
        or len(held.contrary) != len(parts)
        or len(held.limitations) != len(limits)
    ):
        raise _refuse("items do not match their blocks")
    out = [
        _Passage(
            "bottomLine",
            str(bottom["label"]),
            _shown(bottom["lead"], bottom["rest"]),
            held.bottom_line,
        )
    ]
    for item, blocks in zip(found, held.findings, strict=True):
        heading = wording.fill("trace.item.finding", {"number": str(item["number"])})
        out.append(_Passage("findings", heading, _shown(item["lead"], item["body"]), blocks))
    for slot, part, blocks in zip(("contrary", "changeView"), parts, held.contrary, strict=False):
        out.append(_Passage(slot, str(part["title"]), str(part["text"]), blocks))
    for index, (item, blocks) in enumerate(zip(limits, held.limitations, strict=True), start=1):
        heading = wording.fill("trace.item.limitation", {"number": f"{index:02d}"})
        out.append(_Passage("limitations", heading, str(item["text"]), blocks))
    return out


def _basis(blocks: tuple[Block, ...], known: Sequence[str]) -> list[BasisItem] | None:
    """The Basis items of all blocks in order; None when no block ends in a Basis line."""
    items: list[BasisItem] = []
    traced = False
    for block in blocks:
        basis = read_basis(block, known) if isinstance(block, Paragraph | ListItem) else None
        if basis is not None:
            traced = True
            items.extend(basis.items)
    return items if traced else None


def _derivation(
    items: list[BasisItem], rows: dict[str, _Calculation], wording: Wording
) -> dict[str, object] | None:
    """The row the first calculation item names; a stated gap when none matches."""
    for item in items:
        if item.kind == "calculation":
            found = rows.get(item.calculation or "")
            if found is None:
                return _node(item.text, None, wording.fill("trace.derivation.not_found", {}))
            return found.node
    return None


def _row_id(built: _Built) -> str:
    return f"T-{len(built.rows) + 1:04d}"


def _add_passage(
    built: _Built,
    module: names.Module,
    passage: _Passage,
    basis: list[BasisItem],
    known: Sequence[str],
    by_id: dict[str, _Calculation],
    date: str | None,
    wording: Wording,
) -> str:
    row_id = _row_id(built)
    sources = sum(1 for item in basis if item.kind == "source" and item.file in known)
    calc = _derivation(basis, by_id, wording)
    if date is None:
        subtitle = wording.fill("trace.subtitle_undated", {"module": module.name})
    else:
        subtitle = wording.fill("trace.subtitle", {"module": module.name, "date": date})
    none = _node(wording.fill("trace.derivation.none", {}), None, None)
    key = row_id.lower()
    built.traces[key] = {
        "title": wording.fill("trace.title", {"item": passage.heading}),
        "heading": passage.heading,
        "subtitle": subtitle,
        "statement": passage.statement,
        "derivation": none if calc is None else calc,
        "excerpt": None,
        "qualification": None,
        "evidenceItem": row_id,
    }
    built.rows.append(
        {
            "id": row_id,
            "item": passage.statement,
            "module": module.name,
            "moduleId": module.slug,
            "kind": wording.fill("trace.kind.passage", {}),
            "value": None,
            "sources": str(sources),
            "calc": calc,
            "note": None,
        }
    )
    return key


def _add_calculation(
    built: _Built, module: names.Module, calc: _Calculation, wording: Wording
) -> None:
    row_id = _row_id(built)
    built.rows.append(
        {
            "id": row_id,
            "item": calc.name,
            "module": module.name,
            "moduleId": module.slug,
            "kind": wording.fill("trace.kind.calculation", {}),
            "value": passages.cell(calc.result)[0],
            "sources": "0",
            "calc": calc.node,
            "note": None,
        }
    )
    built.jump.append(
        {
            "group": "Calculations",
            "label": calc.name,
            "detail": wording.fill("jump.detail", {"module": module.name, "id": row_id}),
            "target": {"tab": "trace", "item": row_id},
        }
    )


def _table(rows: list[dict[str, object]], wording: Wording) -> dict[str, object]:
    return {
        "title": wording.fill("evidence.trace.title", {}),
        "description": wording.fill("evidence.trace.description", {}),
        "emptyText": None if rows else wording.fill("evidence.trace.empty", {}),
        "columns": {h: wording.fill(f"evidence.trace.column.{h}", {}) for h in _HEADS},
        "rows": rows,
    }


def _add_module(
    built: _Built,
    module: names.Module,
    document: HandoffDocument,
    date: str | None,
    wording: Wording,
) -> None:
    reader = _read(document)
    calcs = _calculations(document)
    by_id = {calc.id: calc for calc in calcs}
    known = source_names(document)
    keys: dict[str, str | None] = {}
    findings: list[str | None] = []
    limitations: list[str | None] = []
    for passage in _passages(reader, document, wording):
        # 6-15: an item with no shown text has nothing to trace, Basis line or not.
        basis = _basis(passage.blocks, known) if passage.statement else None
        key = (
            None
            if basis is None
            else _add_passage(built, module, passage, basis, known, by_id, date, wording)
        )
        if passage.slot == "findings":
            findings.append(key)
        elif passage.slot == "limitations":
            limitations.append(key)
        else:
            keys[passage.slot] = key
    held = _Held(
        keys.get("bottomLine"),
        findings,
        keys.get("contrary"),
        keys.get("changeView"),
        limitations,
    )
    built.items[module.code] = held.as_dict()
    for calc in calcs:
        _add_calculation(built, module, calc, wording)


def build_traces(
    modules: Sequence[tuple[str, HandoffDocument]], as_of: str | None, wording: Wording
) -> dict[str, object]:
    """Traces, the trace table, the jump list and the items map of a run, from its handoffs.

    `modules` are (module code, parsed handoff) pairs in plan order; `as_of` is an ISO date or
    None. Returns {"traces", "table", "jump", "items"}. A calculation row's `value` follows
    `passages.cell`, so its `at` is a `Decimal`. Refuses with `DeliveryRefused` on R24
    condition 1 (see the module docstring); reads no disk and no clock.
    """
    date = None if as_of is None else wording.display_date(as_of)
    built = _Built({}, [], [], {})
    seen: set[str] = set()
    for code, document in modules:
        module = names.module(code)
        if code in seen:
            raise _refuse("a module code is given twice")
        seen.add(code)
        _add_module(built, module, document, date, wording)
    return {
        "traces": built.traces,
        "table": _table(built.rows, wording),
        "jump": built.jump,
        "items": built.items,
    }
