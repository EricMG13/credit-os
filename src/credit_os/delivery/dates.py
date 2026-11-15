"""The Overview's dates, read from a module's `Events:` tables.

Delivery adds no analysis: each row of an events table becomes one item (the event and its
credit relevance word for word, the date as the wording shows it), ordered by the last day of
its period and marked Past, Next or Later against the as-of date. Dates are read with the
standard library (`datetime`, `calendar`) only.

A table whose every cell reads as a gap gives no items. A refusal means the run cannot be
written (R24 condition 1): the caller leaves that run out with the reason and never aborts the
whole library. Refused are: an as-of that is not a real date, an events section without exactly
one table of the fixed header and at least one row, a row that breaks the row rule, a source
name or a module, table or digest code in a shown text, and two items with one date and title.
A message names the rule, never the input text.

Values are plain dicts with the slice's camelCase keys.
"""

import calendar
import datetime
import re
from collections.abc import Sequence
from typing import NamedTuple

from credit_os.delivery.errors import DeliveryRefused
from credit_os.delivery.passages import narrative_leaks
from credit_os.delivery.wording import Wording
from credit_os.handoff.data import DataSection, Gap, read_data_sections, read_value, source_names
from credit_os.handoff.document import HandoffDocument
from credit_os.handoff.tables import Table

_HEADER = (
    "Event date",
    "Date precision",
    "Published",
    "Event",
    "Status",
    "Source",
    "Credit relevance",
)
_DATE, _PRECISION, _PUBLISHED, _EVENT, _STATUS, _RELEVANCE = 0, 1, 2, 3, 4, 6
_DASH = "—"
_DAY = re.compile(r"([0-9]{4})-([0-9]{2})-([0-9]{2})", re.ASCII)
_MONTH = re.compile(r"([0-9]{4})-(0[1-9]|1[0-2])", re.ASCII)
_QUARTER = re.compile(r"([0-9]{4})-Q([1-4])", re.ASCII)
_YEAR = re.compile(r"[0-9]{4}", re.ASCII)
_STATUS_START = re.compile(r"(?:Historical|Scheduled|Scenario) — \S|User reminder(?: — \S|$)")


class _Item(NamedTuple):
    last: datetime.date
    date: str
    title: str
    text: str


def _refuse(rule: str) -> DeliveryRefused:
    return DeliveryRefused(f"overview dates: {rule}")


def _real(year: str, month: str, day: str) -> datetime.date | None:
    try:
        return datetime.date(int(year), int(month), int(day))
    except ValueError:
        return None


def _last_day(text: str, precision: str) -> datetime.date | None:
    """The last day of the period `text` names in the form `precision` requires, else None."""
    if precision == "day":
        match = _DAY.fullmatch(text)
        return None if match is None else _real(*match.groups())
    if precision == "month":
        month = _MONTH.fullmatch(text)
        if month is None or int(month.group(1)) < 1:
            return None
        year, number = int(month.group(1)), int(month.group(2))
        return datetime.date(year, number, calendar.monthrange(year, number)[1])
    if precision == "quarter":
        quarter = _QUARTER.fullmatch(text)
        if quarter is None or int(quarter.group(1)) < 1:
            return None
        end = 3 * int(quarter.group(2))
        year = int(quarter.group(1))
        return datetime.date(year, end, calendar.monthrange(year, end)[1])
    if precision == "year" and _YEAR.fullmatch(text) and int(text) >= 1:
        return datetime.date(int(text), 12, 31)
    return None


def _shown_date(text: str, precision: str, wording: Wording) -> str:
    if precision == "day":
        return wording.display_date(text)
    if precision == "month":
        return wording.month_year(f"{text}-01")
    return text


def _published_ok(text: str) -> bool:
    if text == _DASH or isinstance(read_value(text), Gap):
        return True
    match = _DAY.fullmatch(text)
    return match is not None and _real(*match.groups()) is not None


def _row_ok(cells: Sequence[str]) -> bool:
    if any(isinstance(read_value(c), Gap) for i, c in enumerate(cells) if i != _PUBLISHED):
        return False
    return (
        _last_day(cells[_DATE], cells[_PRECISION]) is not None
        and _published_ok(cells[_PUBLISHED])
        and _STATUS_START.match(cells[_STATUS]) is not None
    )


def _table(section: DataSection) -> Table:
    table = section.table
    if table is None or table.columns != _HEADER or not table.rows:
        raise _refuse("an events section needs one table of the fixed header and a row")
    return table


def _all_gaps(table: Table) -> bool:
    return all(isinstance(read_value(c), Gap) for row in table.rows for c in row.cells)


def _items(section: DataSection, wording: Wording, known: Sequence[str]) -> list[_Item]:
    table = _table(section)
    if _all_gaps(table):
        return []
    items: list[_Item] = []
    for row in table.rows:
        cells = row.cells
        if not _row_ok(cells):
            raise _refuse("a row breaks the row rule")
        last = _last_day(cells[_DATE], cells[_PRECISION])
        if last is None:
            raise _refuse("a row breaks the row rule")
        title, text = cells[_EVENT], cells[_RELEVANCE]
        if narrative_leaks(title, known) or narrative_leaks(text, known):
            raise _refuse("source name or code in shown text")
        shown = _shown_date(cells[_DATE], cells[_PRECISION], wording)
        items.append(_Item(last, shown, title, text))
    return items


def _as_of(text: str) -> datetime.date:
    match = _DAY.fullmatch(text)
    found = None if match is None else _real(*match.groups())
    if found is None:
        raise _refuse("the as-of date must be a real YYYY-MM-DD date")
    return found


def _state(last: datetime.date, today: datetime.date, upcoming: list[datetime.date]) -> str:
    """Past on or before `today`; Next when `last` is the earliest day after it; else Later."""
    if last <= today:
        return "Past"
    return "Next" if last == upcoming[0] else "Later"


def overview_dates(
    document: HandoffDocument, as_of: str, wording: Wording
) -> list[dict[str, object]] | None:
    """The dated items of `document`'s events sections, or None when it has no such section.

    Items are ordered by the last day of their period, ties in source order. An item is Past when
    its last day is on or before `as_of`; of the rest, those with the earliest last day are Next
    and the others Later. Raises `DeliveryRefused` when the run cannot be written (R24 condition
    1); the caller leaves that run out with the reason.
    """
    sections = [s for s in read_data_sections(document) if s.kind == "events"]
    if not sections:
        return None
    today = _as_of(as_of)
    known = source_names(document)
    items = [item for section in sections for item in _items(section, wording, known)]
    items.sort(key=lambda item: item.last)
    if len({(item.date, item.title) for item in items}) != len(items):
        raise _refuse("two items share a date and a title")
    upcoming = [item.last for item in items if item.last > today]
    return [
        {
            "date": item.date,
            "state": _state(item.last, today, upcoming),
            "title": item.title,
            "text": item.text,
        }
        for item in items
    ]
