"""Stated debt facility terms and their three-year interest and repayment schedule."""

import datetime
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

from credit_os.model.arithmetic import difference, product, total
from credit_os.model.value import Value, amount_text, parse_operand

AMOUNT_PATTERN = r"^[0-9]{1,6}(\.[0-9]{1,4})?$"
PERCENT_PATTERN = r"^[0-9]{1,2}(\.[0-9]{1,4})?$"
FRACTION_PATTERN = r"^-?(0|1|0\.[0-9]{1,4}|1\.0{1,4})$"
DATE_PATTERN = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$"

Amount = Annotated[str, Field(pattern=AMOUNT_PATTERN)]
Percent = Annotated[str, Field(pattern=PERCENT_PATTERN)]
Fractional = Annotated[str, Field(pattern=FRACTION_PATTERN)]


def _listed(value: Any) -> Any:
    return tuple(value) if type(value) is list else value


LIST_AS_TUPLE = BeforeValidator(_listed)
_CEILINGS = (("fixed_rate_pct", 30), ("spread_pct", 20), ("floor_pct", 10))
_BOTH = "a facility states a fixed rate or a floating one, not both"
_NEITHER = "a facility states a fixed rate, or a reference rate with a spread"
_CENT = Value(amount=Decimal("0.01"))
_MAX_RATE = Decimal("0.30")


def _plain(value: Value) -> Decimal:
    if value.amount is None:
        raise ValueError("a facility figure is missing")
    return value.amount


def _number(text: str) -> Value:
    return Value(amount=parse_operand(text))


def _percent(text: str) -> Decimal:
    return _plain(product([_number(text), _CENT]))


def _check_ceilings(facility: "Facility") -> None:
    for field, ceiling in _CEILINGS:
        stated: str | None = getattr(facility, field)
        if stated is not None and parse_operand(stated) > ceiling:
            raise ValueError(f"{field} {stated} is above {ceiling}")


def _check_one_form(facility: "Facility") -> None:
    if facility.fixed_rate_pct is not None:
        if any(
            x is not None
            for x in (facility.reference_rate, facility.spread_pct, facility.floor_pct)
        ):
            raise ValueError(_BOTH)
    elif facility.reference_rate is None or facility.spread_pct is None:
        raise ValueError(_NEITHER)


def _check_maturity(facility: "Facility") -> None:
    if facility.maturity is None:
        return
    try:
        datetime.date.fromisoformat(facility.maturity)
    except ValueError:
        raise ValueError(f"maturity {facility.maturity} is not a calendar date") from None


def _check_name(facility: "Facility") -> None:
    if facility.name != facility.name.strip():
        raise ValueError("facility name must not start or end with whitespace")


def _rates(facility: "Facility") -> tuple[Decimal, Decimal, Decimal]:
    if facility.fixed_rate_pct is not None:
        fixed = _percent(facility.fixed_rate_pct)
        return (fixed, fixed, fixed)
    if facility.reference_rate is None or facility.spread_pct is None:
        raise ValueError("a floating facility needs a reference rate and a spread")
    floor = None if facility.floor_pct is None else _percent(facility.floor_pct)
    spread = Value(amount=_percent(facility.spread_pct))
    all_in = []
    for text in facility.reference_rate:
        reference = parse_operand(text)
        base = reference if floor is None else max(reference, floor)
        all_in.append(_plain(total([Value(amount=base), spread])))
    return (all_in[0], all_in[1], all_in[2])


def _check_all_in(facility: "Facility") -> None:
    if facility.fixed_rate_pct is not None:
        return
    for year, rate in enumerate(_rates(facility), start=1):
        if not 0 <= rate <= _MAX_RATE:
            raise ValueError(
                f"all-in rate {amount_text(rate)} in forecast year {year} is outside 0 to 0.30; "
                "reference_rate is a decimal fraction (0.04 is 4%)"
            )


class Facility(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)

    name: Annotated[str, Field(min_length=1, max_length=120)]
    balance: Amount
    fixed_rate_pct: Percent | None
    spread_pct: Percent | None
    floor_pct: Percent | None
    reference_rate: Annotated[tuple[Fractional, Fractional, Fractional], LIST_AS_TUPLE] | None
    annual_amortisation: Amount | None
    maturity: Annotated[str, Field(pattern=DATE_PATTERN)] | None

    @model_validator(mode="after")
    def _rules(self) -> "Facility":
        for rule in (_check_ceilings, _check_one_form, _check_maturity, _check_name, _check_all_in):
            rule(self)
        return self


@dataclass(frozen=True, slots=True)
class FacilityYear:
    opening: Decimal
    rate: Decimal
    interest: Decimal
    repaid: Decimal
    closing: Decimal


Years = tuple[FacilityYear, FacilityYear, FacilityYear]
Pair = tuple[Decimal, Decimal]


@dataclass(frozen=True, slots=True)
class Schedule:
    rows: tuple[Years, ...]

    def totals(self) -> tuple[Pair, Pair, Pair]:
        def column(year: int, field: str) -> Decimal:
            parts = [Value(amount=Decimal(0))]
            parts += [Value(amount=getattr(row[year], field)) for row in self.rows]
            return _plain(total(parts))

        return (
            (column(0, "interest"), column(0, "repaid")),
            (column(1, "interest"), column(1, "repaid")),
            (column(2, "interest"), column(2, "repaid")),
        )


def _stored(amount: Decimal) -> Decimal:
    return _plain(Value(amount=amount))


def _years(facility: Facility) -> Years:
    opening = _stored(parse_operand(facility.balance))
    stated = facility.annual_amortisation
    amortisation = Decimal(0) if stated is None else _stored(parse_operand(stated))
    built: list[FacilityYear] = []
    for rate in _rates(facility):
        interest = _plain(product([Value(amount=opening), Value(amount=rate)]))
        repaid = min(amortisation, opening)
        closing = _plain(difference(Value(amount=opening), Value(amount=repaid)))
        built.append(FacilityYear(opening, rate, interest, repaid, closing))
        opening = closing
    return (built[0], built[1], built[2])


def schedule(facilities: Sequence[Facility]) -> Schedule:
    if type(facilities) not in (list, tuple):
        raise TypeError("facilities must be a list or a tuple of Facility")
    if any(type(item) is not Facility for item in facilities):
        raise TypeError("every facility must be a Facility")
    return Schedule(rows=tuple(_years(item) for item in facilities))
