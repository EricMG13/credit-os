"""The pieces a forecast case is built from (R60, the plan's D1-D17).

- `base_operands`: revenue, debt, cash and undrawn from the base block. A stated amount is an
  exact `Value`; an operand with a reason is `NOT_SOURCED` carrying that reason verbatim.
- `case_drivers`: one `forecast.Drivers`, field by field: the case's driver where it states one,
  else the base driver. No case gives the base drivers. Nothing is copied or mutated (D6).
- `unallocated`: base debt less the stated facility balances, exact through the kernel. Zero and
  negative are amounts; missing base debt is returned unchanged; no facilities gives `None`.
- `with_negative_cash`: when closing cash is an amount below zero, net debt, net leverage and
  liquidity are `NEGATIVE_CASH` (replacing any reason of their own); everything else is kept (D7).

- `_run` turns a `decimal.Inexact` from the engine (Overflow and Underflow are subclasses) into
  `ForecastRefused(RefusalKind.SIZE, <case name>, ...)`: a documented fail-closed refusal (D9, R61).
  A figure of more than 38 significant digits is never rounded into a forecast. Nothing else is
  caught here, and `run_cases`'s signature is unchanged.
- `run_cases`: Reference, Upside, Downside and Downside stress, in that order, each through the
  engine and the overlay. Debt outside the stated facilities pays the case's own rate and is
  never repaid.

The engine in `forecast.py` is not touched (D17).
"""

from dataclasses import dataclass, fields, replace
from decimal import Decimal, Inexact
from enum import StrEnum

from credit_os.model import facilities
from credit_os.model.arithmetic import difference, product, total
from credit_os.model.forecast import Drivers, Operands, Shock, Triple, Year, forecast
from credit_os.model.inputs import BaseDrivers, CaseDrivers, ForecastInputs, Operand
from credit_os.model.refusals import ForecastRefused, RefusalKind
from credit_os.model.value import Missing, MissingCode, Value, parse_operand


class CaseName(StrEnum):
    REFERENCE = "reference"
    UPSIDE = "upside"
    DOWNSIDE = "downside"
    DOWNSIDE_STRESS = "downside_stress"


class StressBasis(StrEnum):
    BASE = "base"
    DOWNSIDE = "downside"


@dataclass(frozen=True, slots=True)
class Case:
    name: CaseName
    years: tuple[Year, Year, Year]


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


Scheduled = tuple[Decimal, Decimal]
_NO_SHOCK = Shock(Decimal(0), Decimal(0))


def _scheduled(
    inputs: ForecastInputs, drivers: Drivers
) -> tuple[Scheduled, Scheduled, Scheduled] | None:
    """Facility totals, plus unallocated debt at the case's own rate (never repaid)."""
    if inputs.facilities is None:
        return None
    first, second, third = facilities.schedule(inputs.facilities).totals()
    remainder = unallocated(inputs)
    if remainder is None or remainder.amount is None or remainder.amount <= 0:
        return first, second, third
    pairs = []
    for index, (interest, repaid) in enumerate((first, second, third)):
        extra = product([remainder, Value(amount=drivers.interest_rate[index])])
        added = total([Value(amount=interest), extra]).amount
        if added is None:
            raise ValueError("a stated interest amount sums to an amount")
        pairs.append((added, repaid))
    return pairs[0], pairs[1], pairs[2]


def _run(inputs: ForecastInputs, name: CaseName, case: CaseDrivers | None, shock: Shock) -> Case:
    drivers = case_drivers(inputs.base_drivers, case)
    try:
        one, two, three = forecast(
            base_operands(inputs),
            drivers,
            shock=shock,
            schedule=_scheduled(inputs, drivers),
        )
    except Inexact as error:
        text = (
            f"the {name.value} case needs a figure of more than 38 significant digits; "
            "no forecast was computed"
        )
        raise ForecastRefused(RefusalKind.SIZE, name.value, text) from error
    return Case(name, (with_negative_cash(one), with_negative_cash(two), with_negative_cash(three)))


def run_cases(inputs: ForecastInputs) -> tuple[tuple[Case, ...], StressBasis | None]:
    cases = [_run(inputs, CaseName.REFERENCE, None, _NO_SHOCK)]
    if inputs.upside_drivers is not None:
        cases.append(_run(inputs, CaseName.UPSIDE, inputs.upside_drivers, _NO_SHOCK))
    if inputs.downside_drivers is not None:
        cases.append(_run(inputs, CaseName.DOWNSIDE, inputs.downside_drivers, _NO_SHOCK))
    stated = inputs.downside_shock
    if stated is None:
        return tuple(cases), None
    shock = Shock(Decimal(stated.ebitda_decline), Decimal(stated.rate_increase))
    cases.append(_run(inputs, CaseName.DOWNSIDE_STRESS, inputs.downside_drivers, shock))
    basis = StressBasis.BASE if inputs.downside_drivers is None else StressBasis.DOWNSIDE
    return tuple(cases), basis
