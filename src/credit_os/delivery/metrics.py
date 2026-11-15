"""The Overview's headline figures, read from a module's `Chart data:` tables.

Delivery adds no analysis: for each fixed (chart, column) the latest row of the one chart table
of that name gives one figure, shown as the module wrote it (`passages.cell`) with its period
and reporting unit as the note. A chart that cannot be read with certainty (no single table, a
missing column, a period that cannot be ordered, a unit that reads as a gap) gives no figure,
never a guessed one. Python does no arithmetic here: periods are only ordered.

A refusal means the run cannot be written (R24 condition 1): a chart name used twice, or a
source name or a module, table or digest code in a shown figure, period or unit. The caller
leaves that run out with the reason and never aborts the whole library. A message names the
rule, never the input text.

Values are plain dicts with the slice's camelCase keys; `trace` is None here, attached later.
"""

import datetime
import re
from collections.abc import Sequence

from credit_os.delivery.errors import DeliveryRefused
from credit_os.delivery.passages import cell, narrative_leaks
from credit_os.delivery.wording import Wording
from credit_os.handoff.data import DataSection, Gap, read_data_sections, read_value, source_names
from credit_os.handoff.document import HandoffDocument
from credit_os.handoff.tables import Row, Table

_PERIOD = "Period"
_UNIT = "Reporting unit"
# (chart name, reported column, adjusted twin column or None), in the order shown.
_FIXED: tuple[tuple[str, str, str | None], ...] = (
    ("leverage", "Total debt / EBITDA", "Total debt / adjusted EBITDA"),
    ("leverage", "Net debt / EBITDA", "Net debt / adjusted EBITDA"),
    ("interest cover", "EBITDA / cash interest", "Adjusted EBITDA / cash interest"),
    ("liquidity", "Cash", None),
    ("liquidity", "Undrawn committed facilities", None),
)
_YEAR = re.compile(r"FY([0-9]{4})", re.ASCII)
_DAY = re.compile(r"([0-9]{4})-([0-9]{2})-([0-9]{2})", re.ASCII)
_BOTH = re.compile(r"FY([0-9]{4}) / ([0-9]{4})-([0-9]{2})-([0-9]{2})", re.ASCII)
_FORM_YEAR = 1
_FORM_DATE = 2


def _refuse(rule: str) -> DeliveryRefused:
    return DeliveryRefused(f"overview metrics: {rule}")


def _day(year: str, month: str, day: str) -> datetime.date | None:
    try:
        return datetime.date(int(year), int(month), int(day))
    except ValueError:
        return None


def _order(period: str) -> tuple[int, int] | None:
    """(form, position) of a Period cell, or None when it has no order."""
    year = _YEAR.fullmatch(period)
    if year is not None:
        return _FORM_YEAR, int(year.group(1))
    plain = _DAY.fullmatch(period)
    if plain is not None:
        found = _day(*plain.groups())
        return None if found is None else (_FORM_DATE, found.toordinal())
    both = _BOTH.fullmatch(period)
    if both is None:
        return None
    found = _day(*both.groups()[1:])
    if found is None or found.year != int(both.group(1)):
        return None
    return _FORM_DATE, found.toordinal()


def _latest(table: Table, period: int) -> Row | None:
    """The row with the latest Period, or None unless every row has one order of one form."""
    keys: list[tuple[int, int]] = []
    for row in table.rows:
        key = _order(row.cells[period])
        if key is None:
            return None
        keys.append(key)
    if not keys or len({key[0] for key in keys}) != 1 or len(set(keys)) != len(keys):
        return None
    return table.rows[keys.index(max(keys))]


def _chart_table(sections: Sequence[DataSection], name: str) -> Table | None:
    found = [section for section in sections if section.kind == "chart" and section.name == name]
    if len(found) > 1:
        raise _refuse("chart name used twice")
    return found[0].table if found else None


def _held(table: Table, reported: str, twin: str | None) -> str | None:
    has = table.columns
    label = reported if reported in has or twin is None or twin not in has else twin
    return label if label in has else None


def _once(table: Table, label: str) -> int | None:
    return table.columns.index(label) if table.columns.count(label) == 1 else None


def _columns(table: Table, held: str) -> tuple[int, int, int] | None:
    period, unit, figure = _once(table, _PERIOD), _once(table, _UNIT), _once(table, held)
    if period is None or unit is None or figure is None:
        return None
    return period, unit, figure


def _shown(value: dict[str, object] | None) -> list[str]:
    if value is None:
        return []
    return [str(value["text"] if value["kind"] == "value" else value["reason"])]


def _metric(
    table: Table, reported: str, twin: str | None, wording: Wording, known: Sequence[str]
) -> dict[str, object] | None:
    held = _held(table, reported, twin)
    if held is None:
        return None
    indexes = _columns(table, held)
    if indexes is None:
        return None
    period_at, unit_at, held_at = indexes
    row = _latest(table, period_at)
    if row is None:
        return None
    period, unit = row.cells[period_at], row.cells[unit_at]
    if isinstance(read_value(unit), Gap):
        return None
    value = cell(row.cells[held_at])[0]
    if any(narrative_leaks(text, known) for text in [period, unit, *_shown(value)]):
        raise _refuse("source name or code in shown text")
    note = wording.fill("overview.metric_note", {"period": period, "unit": unit})
    return {"label": held, "value": value, "note": note, "trace": None}


def overview_metrics(document: HandoffDocument, wording: Wording) -> list[dict[str, object]]:
    """The headline figures of `document`, in the fixed order; a figure that cannot be read is left out.

    Raises `DeliveryRefused` when the run cannot be written (R24 condition 1): a chart name used
    twice, or a source name or a module, table or digest code in a figure, period or unit. The
    caller leaves that run out with the reason.
    """
    sections = read_data_sections(document)
    known = source_names(document)
    out: list[dict[str, object]] = []
    for chart, reported, twin in _FIXED:
        table = _chart_table(sections, chart)
        metric = None if table is None else _metric(table, reported, twin, wording, known)
        if metric is not None:
            out.append(metric)
    return out
