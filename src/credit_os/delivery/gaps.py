"""The Gaps table and jump entries: every gap a module recorded, with the effect it gave.

Rows are module-written text, selected and placed: no analysis is added and nothing is
computed. Every handoff text is a value of a dict, never a key and never a template, and
Markdown marks stay literal. Gaps are Evidence, so no source-reference scan is applied.

R24 condition 1: a run whose Gaps section cannot be read as nothing, a header-only table or one
direct table with the header Gap, Effect (any other direct block, a second table, a sub-section,
another header, an empty or dash Gap cell), an earlier-format document, or an unknown or
repeated module code, cannot be written. The builder raises `DeliveryRefused`, naming the rule
only and never input text, and the caller leaves that run out with the reason.

Rows are numbered G-0001 and up by position, module by module in input order, then by table row.
"""

from collections.abc import Sequence
from typing import NamedTuple

from credit_os.delivery import names
from credit_os.delivery.errors import DeliveryRefused
from credit_os.delivery.wording import Wording
from credit_os.handoff.document import HandoffDocument
from credit_os.handoff.errors import HandoffError
from credit_os.handoff.reader import read_reader
from credit_os.handoff.tables import Table

_COLUMNS = ("Gap", "Effect")
_UNSET = ("", "—")
_GAPS = 4
_HEADS = ("id", "gap", "module", "reason", "shownAs")


class _Cells(NamedTuple):
    gap: str
    effect: str


def _refuse(rule: str) -> DeliveryRefused:
    return DeliveryRefused(f"gaps: {rule}")


def _cells(document: HandoffDocument) -> list[_Cells]:
    section = document.sections[_GAPS]
    if section.sections:
        raise _refuse("the Gaps section has a sub-section")
    if not section.blocks:
        return []
    table = section.blocks[0]
    if len(section.blocks) > 1 or not isinstance(table, Table):
        raise _refuse("the Gaps section is not one table")
    if table.columns != _COLUMNS:
        raise _refuse("the Gaps table header is not Gap, Effect")
    found: list[_Cells] = []
    for row in table.rows:
        gap, effect = row.cells
        if gap in _UNSET:
            raise _refuse("a gap has no text")
        found.append(_Cells(gap, effect))
    return found


def _blocked(document: HandoffDocument) -> bool:
    try:
        reader = read_reader(document)
    except HandoffError as error:
        raise _refuse("the handoff cannot be read") from error
    if reader.format != "new":
        raise _refuse("the handoff is in the earlier format")
    return bool(reader.blocked)


def _row(
    number: int, module: names.Module, cells: _Cells, blocked: bool, wording: Wording
) -> dict[str, object]:
    unstated = wording.fill("evidence.gaps.effect_unstated", {})
    return {
        "id": f"G-{number:04d}",
        "gap": cells.gap,
        "module": module.name,
        "moduleId": module.slug,
        "reason": unstated if cells.effect in _UNSET else cells.effect,
        "shownAs": "blocked" if blocked else "gap",
        "where": {
            "page": "module",
            "label": wording.fill("evidence.gaps.where.module", {"module": module.name}),
        },
    }


def _jump(row: dict[str, object], module: names.Module, wording: Wording) -> dict[str, object]:
    row_id = str(row["id"])
    return {
        "group": "Gaps",
        "label": row["gap"],
        "detail": wording.fill("jump.detail", {"module": module.name, "id": row_id}),
        "target": {"tab": "gaps", "item": row_id},
    }


def _table(rows: list[dict[str, object]], wording: Wording) -> dict[str, object]:
    group = {"severity": None, "count": str(len(rows)), "rows": rows}
    return {
        "title": wording.fill("evidence.gaps.title", {}),
        "description": wording.fill("evidence.gaps.description", {}),
        "columns": {h: wording.fill(f"evidence.gaps.column.{h}", {}) for h in _HEADS},
        "groups": [group] if rows else [],
    }


def build_gaps(
    modules: Sequence[tuple[str, HandoffDocument]], wording: Wording
) -> dict[str, object]:
    """The Gaps table, its jump entries, the tab count and the rows per module of a run.

    `modules` are (module code, parsed handoff) pairs in plan order. Returns
    {"table", "jump", "count", "modules"}: `count` is the tab count as text and `modules` maps
    each module code to its number of gap rows, in input order. A blocked module's gaps are
    listed, shown as "blocked". Refuses with `DeliveryRefused` on R24 condition 1 (see the
    module docstring); reads no disk and no clock.
    """
    rows: list[dict[str, object]] = []
    jump: list[dict[str, object]] = []
    per_module: dict[str, int] = {}
    for code, document in modules:
        module = names.module(code)
        if code in per_module:
            raise _refuse("a module code is given twice")
        blocked = _blocked(document)
        cells = _cells(document)
        per_module[code] = len(cells)
        for item in cells:
            row = _row(len(rows) + 1, module, item, blocked, wording)
            rows.append(row)
            jump.append(_jump(row, module, wording))
    return {
        "table": _table(rows, wording),
        "jump": jump,
        "count": str(len(rows)),
        "modules": per_module,
    }
