"""Facility detail and its limits (R60, D11, D12).

The detail is each stated facility with its three-year schedule (opening balance, all-in rate,
cash interest, scheduled repayment and closing balance), each year paired with the fiscal year
it falls in, plus the debt that sits outside the stated facilities. It is the same in every
case: the schedule is not shocked. It is absent when no facilities are stated.

The limits are, in order, when facilities are stated:

- the facility limit: interest and repayment come from the stated facility terms, not from the
  analyst's repayment assumption;
- the unallocated limit: base debt above the stated balances (the excess), stated balances above
  base debt (by how much), or base debt missing; none when the two agree exactly;
- one maturity limit per facility, in facility order, for a stated maturity before the forecast
  or inside it (bounds inclusive); none for a later or absent maturity.

Rulings D11 and D12: a facility maturing before or inside the forecast is assumed refinanced,
and no repayment at maturity is modelled. The texts name no module.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from credit_os.model.arithmetic import difference
from credit_os.model.cases import unallocated
from credit_os.model.facilities import Facility, FacilityYear, schedule
from credit_os.model.inputs import ForecastInputs
from credit_os.model.value import Value, amount_text

FACILITY_LIMIT = (
    "Cash interest on the stated facilities and scheduled repayment are computed from the "
    "facility terms the forward credit model stated; the analyst's repayment assumption is "
    "not used."
)
_MISSING_DEBT = "Base debt is missing, so debt outside the stated facilities is not known."
_ZERO = Value(amount=Decimal(0))

YearPair = tuple[int, FacilityYear]


@dataclass(frozen=True, slots=True)
class FacilityDetail:
    facility: Facility
    years: tuple[YearPair, YearPair, YearPair]


@dataclass(frozen=True, slots=True)
class Detail:
    facilities: tuple[FacilityDetail, ...]
    unallocated: Value


def _left(inputs: ForecastInputs) -> Value:
    left = unallocated(inputs)
    if left is None:
        raise ValueError("unallocated debt is asked for with no facilities stated")
    return left


def facility_detail(inputs: ForecastInputs) -> Detail | None:
    if inputs.facilities is None or len(inputs.facilities) == 0:
        return None
    left = _left(inputs)
    one, two, three = (span.year for span in inputs.years)
    rows = schedule(inputs.facilities).rows
    items = tuple(
        FacilityDetail(facility, ((one, row[0]), (two, row[1]), (three, row[2])))
        for facility, row in zip(inputs.facilities, rows, strict=True)
    )
    return Detail(facilities=items, unallocated=left)


def _unallocated_limit(left: Value) -> tuple[str, ...]:
    amount = left.amount
    if amount is None:
        return (_MISSING_DEBT,)
    if amount > 0:
        return (
            (
                f"Debt of {amount_text(amount)} is not in a stated facility; it bears interest "
                "at the analyst's assumed rate and is not repaid in this forecast."
            ),
        )
    if amount < 0:
        magnitude = difference(_ZERO, left).amount
        if magnitude is None:
            raise ValueError("the magnitude of an amount is an amount")
        return (
            (
                f"Stated facility balances exceed base debt by {amount_text(magnitude)}; "
                "interest is computed on the stated balances."
            ),
        )
    return ()


def _maturity_limit(facility: Facility, inputs: ForecastInputs) -> tuple[str, ...]:
    if facility.maturity is None:
        return ()
    due = date.fromisoformat(facility.maturity)
    spans = inputs.years
    if due < date.fromisoformat(spans[0].start):
        return (
            (
                f"{facility.name} has a stated maturity of {facility.maturity}, before the "
                "forecast; it is assumed refinanced and no repayment at maturity is modelled."
            ),
        )
    for span in spans:
        if date.fromisoformat(span.start) <= due <= date.fromisoformat(span.end):
            return (
                (
                    f"{facility.name} matures in FY{span.year} and is assumed refinanced; "
                    "no repayment at maturity is modelled."
                ),
            )
    return ()


def facility_limits(inputs: ForecastInputs) -> tuple[str, ...]:
    if inputs.facilities is None or len(inputs.facilities) == 0:
        return ()
    limits = (FACILITY_LIMIT,) + _unallocated_limit(_left(inputs))
    for facility in inputs.facilities:
        limits += _maturity_limit(facility, inputs)
    return limits
