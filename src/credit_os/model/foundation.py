"""Check each base operand's named cell, its unit and the currency against the foundation.

The operand's amount must be the one number at the cell it names, under the sign rule, and the
named row must not print the other unit than the block's. The foundation must name the block's
currency. Every rule is a plain function; numbers are read and compared exactly, never under the
ambient decimal context (`Decimal(text)`, `copy_negate`, `copy_abs` and `==` do not round).
"""

import re
from collections.abc import Mapping
from decimal import Decimal

from credit_os.handoff.blocks import Block, ListItem, Paragraph
from credit_os.handoff.data import read_data_sections
from credit_os.handoff.document import HandoffDocument, Section
from credit_os.handoff.errors import echo
from credit_os.handoff.reader import read_reader
from credit_os.handoff.tables import Row, Table
from credit_os.model.inputs import OPERANDS, ForecastInputs, Operand
from credit_os.model.refusals import ForecastRefused, RefusalKind

_DIGITS = r"(?P<digits>[0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)"
_SIGNED = re.compile(r"(?:\+|(?P<minus>[-−]))?" + _DIGITS)
_BRACKETED = re.compile(r"\(" + _DIGITS + r"\)")
_MAGNITUDES = ("interest", "taxes", "capex")
_SHOWN = 5

_SIGN = r"(?:US\$|USD|EUR|GBP|[$€£])"
_THOUSANDS = re.compile(rf"\bthousands?\b|[$'’]000s?\b|{_SIGN}\s?k\b", re.IGNORECASE)
_MILLIONS = re.compile(rf"\b(?:millions?|billions?)\b|{_SIGN}\s?(?:m|mm|mn|bn)\b", re.IGNORECASE)
_SIGNS = {"USD": r"(?i:(?<![A-Za-z])US\$)", "EUR": "€", "GBP": "£"}

_LOCATED = "base {key} states no amount, so it names no row, period or column"
_NAMED = (
    "base {key} must name the `row` label and either the `period` header "
    "or the `column` header it was read from"
)
_NONE = "base {key}: no table cell of CP-1 is at {where}"
_MANY = "base {key}: {where} is not one number in CP-1 ({count} cells: {shown}{more})"
_UNIT = (
    "base {key}: row `{row}` states its {what} as `{cell}`, not the block's unit ({unit}); "
    "state a reason instead of an amount"
)
_CURRENCY = (
    "CP-1 nowhere names `{currency}`: state `currency` as the three-letter code of the "
    "currency CP-1 reports its figures in."
)
_OTHER = "base {key} {amount} is not CP-1's cell at {where} ({cell})"
_NEGATIVE = "; wc is stated as the negative of its cell"
_MAGNITUDE = "; {key} is stated as a magnitude, without a sign"


def _plain(text: str) -> str:
    return text.strip().strip("*_`").strip()


def _number(cell: str) -> Decimal | None:
    text = _plain(cell)
    bracketed = _BRACKETED.fullmatch(text)
    if bracketed is not None:
        return Decimal(bracketed["digits"].replace(",", "")).copy_negate()
    signed = _SIGNED.fullmatch(text)
    if signed is None:
        return None
    value = Decimal(signed["digits"].replace(",", ""))
    return value.copy_negate() if signed["minus"] else value


def _agrees(key: str, value: Decimal, amount: Decimal) -> bool:
    if key == "wc":
        return value.copy_negate() == amount
    if key in _MAGNITUDES:
        return value.copy_abs() == amount
    return value == amount


def _left_out(document: HandoffDocument) -> set[int]:
    lines = {document.sections[1].line}
    lines.update(
        item.section.line for item in read_data_sections(document) if item.kind == "forecast"
    )
    reader = read_reader(document)
    passages = (reader.bottom_line, reader.key_findings, reader.contrary, reader.limitations)
    lines.update(section.line for section in passages if section is not None)
    return lines


def _walk(sections: tuple[Section, ...], left_out: set[int]) -> list[Block]:
    found: list[Block] = []
    for section in sections:
        if section.line in left_out:
            continue
        found.extend(section.blocks)
        found.extend(_walk(section.sections, left_out))
    return found


def _kept(document: HandoffDocument) -> list[Block]:
    return _walk(document.sections, _left_out(document))


def foundation_tables(document: HandoffDocument) -> tuple[Table, ...]:
    """Every table of the foundation except Sources, forecast sections and reader passages."""
    return tuple(block for block in _kept(document) if isinstance(block, Table))


def _block_text(block: Block) -> list[str]:
    if isinstance(block, Table):
        label = [] if block.label is None else [block.label]
        return label + list(block.columns) + [cell for row in block.rows for cell in row.cells]
    if isinstance(block, Paragraph | ListItem):
        return list(block.lines)
    return []


def foundation_text(document: HandoffDocument) -> tuple[str, ...]:
    """The pieces of text of the same sections: table cells and prose, never headings or code."""
    return tuple(piece for block in _kept(document) for piece in _block_text(block))


def units_named(text: str) -> frozenset[str]:
    """The units, `thousands` and `millions`, the text names; it may name both or neither."""
    named = {"thousands": _THOUSANDS, "millions": _MILLIONS}
    return frozenset(name for name, pattern in named.items() if pattern.search(text))


def names_currency(text: str, currency: str) -> bool:
    """Whether the text names the code, alone or with a scale suffix, or the code's own sign."""
    forms = [rf"(?<![A-Za-z]){currency}(?i:mm|mn|bn|m|k|000s?)?(?![A-Za-z0-9])"]
    if currency in _SIGNS:
        forms.append(_SIGNS[currency])
    return re.search("|".join(forms), text) is not None


def _matches(table: Table, row: str, header: str) -> tuple[list[int], list[Row]]:
    """The columns (not the first) headed `header` and the rows labelled `row`, plain-compared."""
    columns = [
        index
        for index, column in enumerate(table.columns)
        if index >= 1 and _plain(column) == _plain(header)
    ]
    return columns, [line for line in table.rows if _plain(line.cells[0]) == _plain(row)]


def _cells(tables: tuple[Table, ...], row: str, header: str) -> list[str]:
    found: set[str] = set()
    for table in tables:
        columns, lines = _matches(table, row, header)
        for line in lines:
            found.update(line.cells[column] for column in columns)
    return list(found)


def _many(key: str, where: str, cells: list[str]) -> str:
    shown = sorted(echo(cell) for cell in cells)
    more = f" and {len(shown) - _SHOWN} more" if len(shown) > _SHOWN else ""
    return _MANY.format(key=key, where=where, count=len(cells), shown=shown[:_SHOWN], more=more)


def _named(operand: Operand) -> tuple[str, str, str] | None:
    """The operand's row, header and header kind, or None when either is missing or blank."""
    header = operand.period if operand.period is not None else operand.column
    row = operand.row
    if row is None or header is None or not _plain(row) or not _plain(header):
        return None
    return row, header, "period" if operand.period is not None else "column"


def _problem(
    key: str, amount: str, named: tuple[str, str, str], tables: tuple[Table, ...]
) -> str | None:
    row, header, kind = named
    where = f"row `{echo(row)}`, {kind} `{echo(header)}`"
    cells = _cells(tables, row, header)
    if not cells:
        return _NONE.format(key=key, where=where)
    values = {_number(cell) for cell in cells}
    only = next(iter(values))
    if len(values) > 1 or only is None:
        return _many(key, where, cells)
    if _agrees(key, only, Decimal(amount)):
        return None
    message = _OTHER.format(key=key, amount=amount, where=where, cell=echo(min(cells)))
    return message + _sign_clause(key, only, Decimal(amount))


def _sign_clause(key: str, cell: Decimal, amount: Decimal) -> str:
    if cell.copy_abs() != amount.copy_abs():
        return ""
    if key == "wc":
        return _NEGATIVE
    if key in _MAGNITUDES:
        return _MAGNITUDE.format(key=key)
    return ""


def _group(table: Table, column: int, line: Row, kind: str) -> list[tuple[str, str]]:
    group = [(f"{kind} header", table.columns[column]), ("first header cell", table.columns[0])]
    group.extend(
        (_plain(table.columns[index]), cell)
        for index, cell in enumerate(line.cells)
        if index != column
    )
    return group


def _group_issues(group: list[tuple[str, str]], unit: str) -> list[tuple[str, str]]:
    other = "thousands" if unit == "millions" else "millions"
    if any(unit in units_named(cell) for _, cell in group):
        return []
    return [(what, cell) for what, cell in group if other in units_named(cell)]


def _table_issues(table: Table, named: tuple[str, str, str], unit: str) -> list[tuple[str, str]]:
    row, header, kind = named
    columns, lines = _matches(table, row, header)
    issues: list[tuple[str, str]] = []
    for column in columns:
        for line in lines:
            issues.extend(_group_issues(_group(table, column, line, kind), unit))
    return issues


def _issues(
    named: tuple[str, str, str], unit: str, tables: tuple[Table, ...]
) -> list[tuple[str, str]]:
    return [issue for table in tables for issue in _table_issues(table, named, unit)]


def _unit_problem(
    key: str, named: tuple[str, str, str], inputs: ForecastInputs, tables: tuple[Table, ...]
) -> str | None:
    unit = "millions" if inputs.scale == 1 else "thousands"
    issues = _issues(named, unit, tables)
    if not issues:
        return None
    what, cell = min(issues)
    label = f"{inputs.currency} {unit}, scale {inputs.scale}"
    return _UNIT.format(
        key=key,
        row=echo(_plain(named[0])),
        what=echo(what),
        cell=echo(_plain(cell)),
        unit=label,
    )


def _refusal(
    key: str, inputs: ForecastInputs, stated: Mapping[str, str], tables: tuple[Table, ...]
) -> tuple[RefusalKind, str] | None:
    operand = inputs.base[key]
    if operand.amount is None:
        located = (operand.row, operand.period, operand.column) != (None, None, None)
        return (RefusalKind.CELL, _LOCATED.format(key=key)) if located else None
    named = _named(operand)
    if named is None:
        return RefusalKind.CELL, _NAMED.format(key=key)
    amount = stated[f"base {key}"] if inputs.scale == 1000 else operand.amount
    message = _problem(key, amount, named, tables)
    if message is not None:
        return RefusalKind.CELL, message
    message = _unit_problem(key, named, inputs, tables)
    return None if message is None else (RefusalKind.UNIT, message)


def check_base(
    inputs: ForecastInputs, stated: Mapping[str, str], foundation: HandoffDocument
) -> None:
    """Refuse the first base operand whose amount is not the foundation's cell it names.

    A named row printed in the other unit than the block's is refused as well.
    """
    tables = foundation_tables(foundation)
    for key in OPERANDS:
        refusal = _refusal(key, inputs, stated, tables)
        if refusal is not None:
            raise ForecastRefused(refusal[0], f"base {key}", refusal[1])


def check_currency(inputs: ForecastInputs, foundation: HandoffDocument) -> None:
    """Refuse a foundation that nowhere names the block's currency."""
    currency = inputs.currency
    if any(names_currency(piece, currency) for piece in foundation_text(foundation)):
        return
    message = _CURRENCY.format(currency=currency)
    raise ForecastRefused(RefusalKind.CURRENCY, "currency", message)


def check_foundation(
    inputs: ForecastInputs, stated: Mapping[str, str], foundation: HandoffDocument
) -> None:
    """The base checks, then the currency check; the first refusal is raised."""
    check_base(inputs, stated, foundation)
    check_currency(inputs, foundation)
