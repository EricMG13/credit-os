"""The pieces a forecast case is built from (R60, the plan's D1-D17).

- `base_operands`: revenue, debt, cash and undrawn from the base block. A stated amount is an
  exact `Value`; an operand with a reason is `NOT_SOURCED` carrying that reason verbatim.
- `case_drivers`: one `forecast.Drivers`, field by field: the case's driver where it states one,
  else the base driver. No case gives the base drivers. Nothing is copied or mutated (D6).
- `unallocated`: base debt less the stated facility balances, exact through the kernel. Zero and
  negative are amounts; missing base debt is returned unchanged; no facilities gives `None`.
- `with_negative_cash`: when closing cash is an amount below zero, net debt, net leverage and
  liquidity are `NEGATIVE_CASH` (replacing any reason of their own); everything else is kept (D7).

The engine in `forecast.py` is not touched (D17).
"""

from dataclasses import fields, replace
from decimal import Decimal

from credit_os.model.arithmetic import difference, total
from credit_os.model.forecast import Drivers, Operands, Triple, Year
from credit_os.model.inputs import BaseDrivers, CaseDrivers, ForecastInputs, Operand
from credit_os.model.value import Missing, MissingCode, Value, parse_operand

NEGATIVE_CASH: str = "Not calculable: cash is negative before funding"

_OVERLAID = ("net_debt", "net_leverage", "liquidity")


def _operand(operand: Operand) -> Value:
    if operand.amount is not None:
        return Value(amount=parse_operand(operand.amount))
    if operand.reason is None:
        raise ValueError("an operand states an amount or a reason")
    return Value(missing=Missing(MissingCode.NOT_SOURCED, operand.reason))


def base_operands(inputs: ForecastInputs) -> Operands:
    base = inputs.base
    return Operands(
        revenue=_operand(base["revenue"]),
        debt=_operand(base["debt"]),
        cash=_operand(base["cash"]),
        undrawn=_operand(base["undrawn"]),
    )


def _triple(values: tuple[str, str, str]) -> Triple:
    return (Decimal(values[0]), Decimal(values[1]), Decimal(values[2]))


def case_drivers(base: BaseDrivers, case: CaseDrivers | None) -> Drivers:
    chosen: dict[str, Triple] = {}
    for field in fields(Drivers):
        stated = None if case is None else getattr(case, field.name)
        driver = stated if stated is not None else getattr(base, field.name)
        chosen[field.name] = _triple(driver.values)
    return Drivers(**chosen)


def unallocated(inputs: ForecastInputs) -> Value | None:
    if inputs.facilities is None:
        return None
    debt = _operand(inputs.base["debt"])
    balances = [Value(amount=parse_operand(item.balance)) for item in inputs.facilities]
    return difference(debt, total(balances))


def with_negative_cash(year: Year) -> Year:
    cash = year.closing_cash.amount
    if cash is None or cash >= 0:
        return year
    refused = Value(missing=Missing(MissingCode.NEGATIVE_CASH, NEGATIVE_CASH))
    return replace(year, **{name: refused for name in _OVERLAID})
