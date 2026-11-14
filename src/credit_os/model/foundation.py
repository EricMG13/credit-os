"""Check each base operand's named cell against the financial foundation's tables.

The operand's amount must be the one number at the cell it names, under the sign rule. Every
rule is a plain function; numbers are read and compared exactly, never under the ambient
decimal context (`Decimal(text)`, `copy_negate`, `copy_abs` and `==` do not round).
"""

import re
from collections.abc import Mapping
from decimal import Decimal

from credit_os.handoff.data import read_data_sections
from credit_os.handoff.document import HandoffDocument, Section
from credit_os.handoff.errors import echo
from credit_os.handoff.reader import read_reader
from credit_os.handoff.tables import Table
from credit_os.model.inputs import OPERANDS, ForecastInputs, Operand
from credit_os.model.refusals import ForecastRefused, RefusalKind

_DIGITS = r"(?P<digits>[0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)"
_SIGNED = re.compile(r"(?:\+|(?P<minus>[-−]))?" + _DIGITS)
_BRACKETED = re.compile(r"\(" + _DIGITS + r"\)")
_MAGNITUDES = ("interest", "taxes", "capex")
_SHOWN = 5

_LOCATED = "base {key} states no amount, so it names no row, period or column"
_NAMED = (
    "base {key} must name the `row` label and either the `period` header "
    "or the `column` header it was read from"
)
_NONE = "base {key}: no table cell of CP-1 is at {where}"
_MANY = "base {key}: {where} is not one number in CP-1 ({count} cells: {shown}{more})"
_OTHER = "base {key} {amount} is not CP-1's cell at {where} ({cell})"


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


def _walk(sections: tuple[Section, ...], left_out: set[int]) -> list[Table]:
    found: list[Table] = []
    for section in sections:
        if section.line in left_out:
            continue
        found.extend(block for block in section.blocks if isinstance(block, Table))
        found.extend(_walk(section.sections, left_out))
    return found


def foundation_tables(document: HandoffDocument) -> tuple[Table, ...]:
    """Every table of the foundation except Sources, forecast sections and reader passages."""
    return tuple(_walk(document.sections, _left_out(document)))


def _cells(tables: tuple[Table, ...], row: str, header: str) -> list[str]:
    found: set[str] = set()
    for table in tables:
        columns = [
            index
            for index, column in enumerate(table.columns)
            if index >= 1 and _plain(column) == _plain(header)
        ]
        for line in table.rows:
            if _plain(line.cells[0]) == _plain(row):
                found.update(line.cells[column] for column in columns)
    return list(found)


def _many(key: str, where: str, cells: list[str]) -> str:
    shown = sorted(echo(cell) for cell in cells)
    more = f" and {len(shown) - _SHOWN} more" if len(shown) > _SHOWN else ""
    return _MANY.format(key=key, where=where, count=len(cells), shown=shown[:_SHOWN], more=more)


def _problem(
    key: str, operand: Operand, stated: Mapping[str, str], scale: int, tables: tuple[Table, ...]
) -> str | None:
    if operand.amount is None:
        located = (operand.row, operand.period, operand.column) != (None, None, None)
        return _LOCATED.format(key=key) if located else None
    amount = stated[f"base {key}"] if scale == 1000 else operand.amount
    header = operand.period if operand.period is not None else operand.column
    row = operand.row
    if row is None or header is None or not _plain(row) or not _plain(header):
        return _NAMED.format(key=key)
    kind = "period" if operand.period is not None else "column"
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
    return _OTHER.format(key=key, amount=amount, where=where, cell=echo(min(cells)))


def check_base(
    inputs: ForecastInputs, stated: Mapping[str, str], foundation: HandoffDocument
) -> None:
    """Refuse the first base operand whose amount is not the foundation's cell it names."""
    tables = foundation_tables(foundation)
    for key in OPERANDS:
        message = _problem(key, inputs.base[key], stated, inputs.scale, tables)
        if message is not None:
            raise ForecastRefused(RefusalKind.CELL, f"base {key}", message)
