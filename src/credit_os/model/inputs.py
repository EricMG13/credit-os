"""The forecast inputs schema: validated, typed, in millions, with the repayment bound."""

import datetime
import re
from collections.abc import Iterator
from decimal import Decimal
from typing import Annotated, Any, Literal, Self

import pydantic
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_core import ErrorDetails

from credit_os.handoff.document import HandoffDocument
from credit_os.handoff.errors import echo
from credit_os.model.arithmetic import product, total
from credit_os.model.facilities import (
    AMOUNT_PATTERN,
    DATE_PATTERN,
    FRACTION_PATTERN,
    LIST_AS_TUPLE,
    Facility,
    _plain,
)
from credit_os.model.inputs_json import read_forecast_document
from credit_os.model.refusals import ForecastRefused, RefusalKind
from credit_os.model.value import Value, amount_text, parse_operand

SCHEMA_VERSION = "cpos-forecast-inputs/1"
OPERANDS = (
    "revenue",
    "ebitda",
    "interest",
    "taxes",
    "wc",
    "capex",
    "fcf",
    "debt",
    "cash",
    "undrawn",
)
SHARE_PATTERN = r"^(0|1|0\.[0-9]{1,4}|1\.0{1,4})$"
SIGNED_PATTERN = r"^-?[0-9]{1,6}(\.[0-9]{1,4})?$"
Category = Literal[
    "Documentary Fact", "Management Language", "Analyst Interpretation", "Insufficient Information"
]
Name = Annotated[str, Field(min_length=1)]
Signed = Annotated[str, Field(pattern=SIGNED_PATTERN)]
Growth = Annotated[str, Field(pattern=FRACTION_PATTERN)]
Share = Annotated[str, Field(pattern=SHARE_PATTERN)]
Amount = Annotated[str, Field(pattern=AMOUNT_PATTERN)]
Date = Annotated[str, Field(pattern=DATE_PATTERN)]
_STRICT = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)
_SUBJECT = "forecast inputs"
_SCALED = ("dividends", "debt_repayment")
_GROUPS = ("base_drivers", "upside_drivers", "downside_drivers")
_CODE = re.compile(r"[A-Z]{3}")
_THOUSANDS = re.compile(r"-?[0-9]{1,9}(\.[0-9])?")
_MINUS_ZERO = re.compile(r"-0+(\.0)?")
_MILLI = Value(amount=Decimal("0.001"))
_THOUSANDS_TEXT = (
    "{slot} {text} is not an amount in thousands as CP-1 prints it (scale 1000): "
    "at most nine digits and one decimal place, no separators"
)


class Operand(BaseModel):
    model_config = _STRICT
    amount: Signed | None
    reason: str | None
    row: Name | None = None
    period: Name | None = None
    column: Name | None = None

    @model_validator(mode="after")
    def _rules(self) -> Self:
        if (self.amount is None) == (self.reason is None):
            raise ValueError("an operand states an amount or a reason, never both or neither")
        if self.reason is not None and not self.reason.strip():
            raise ValueError("an operand's reason must not be blank")
        if self.period is not None and self.column is not None:
            raise ValueError(
                "an operand names the `period` header or the `column` header, not both"
            )
        if self.amount is not None and (
            self.row is None or (self.period, self.column) == (None, None)
        ):
            raise ValueError(
                "an operand with an amount names its `row` and its `period` or `column`"
            )
        return self


class _Driver(BaseModel):
    model_config = _STRICT
    category: Category
    rationale: str
    limitation: str | None


class GrowthDriver(_Driver):
    values: Annotated[tuple[Growth, Growth, Growth], LIST_AS_TUPLE]


class ShareDriver(_Driver):
    values: Annotated[tuple[Share, Share, Share], LIST_AS_TUPLE]


class AmountDriver(_Driver):
    values: Annotated[tuple[Amount, Amount, Amount], LIST_AS_TUPLE]


class BaseDrivers(BaseModel):
    model_config = _STRICT
    revenue_growth: GrowthDriver
    ebitda_margin: ShareDriver
    capex_pct_revenue: ShareDriver
    tax_wc_pct_revenue: ShareDriver
    interest_rate: ShareDriver
    dividends: AmountDriver
    debt_repayment: AmountDriver


class CaseDrivers(BaseModel):
    model_config = _STRICT
    revenue_growth: GrowthDriver | None = None
    ebitda_margin: ShareDriver | None = None
    capex_pct_revenue: ShareDriver | None = None
    tax_wc_pct_revenue: ShareDriver | None = None
    interest_rate: ShareDriver | None = None
    dividends: AmountDriver | None = None
    debt_repayment: AmountDriver | None = None

    @model_validator(mode="after")
    def _rules(self) -> Self:
        if all(getattr(self, name) is None for name in type(self).model_fields):
            raise ValueError("a case names at least one driver; write null for no case")
        return self


class Shock(BaseModel):
    model_config = _STRICT
    ebitda_decline: Share
    rate_increase: Share


def _day(text: str, field: str) -> datetime.date:
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        raise ValueError(f"{field} {text} is not a calendar date") from None


class Span(BaseModel):
    model_config = _STRICT
    year: Annotated[int, Field(ge=1000, le=9999)]
    start: Date
    end: Date

    @model_validator(mode="after")
    def _rules(self) -> Self:
        first, last = _day(self.start, "start"), _day(self.end, "end")
        if first > last:
            raise ValueError("a year starts after it ends")
        return self


class ForecastInputs(BaseModel):
    model_config = _STRICT
    schema_version: Literal["cpos-forecast-inputs/1"]
    base: dict[str, Operand]
    base_drivers: BaseDrivers
    downside_shock: Shock | None
    upside_drivers: CaseDrivers | None = None
    downside_drivers: CaseDrivers | None = None
    years: Annotated[tuple[Span, Span, Span], LIST_AS_TUPLE]
    facilities: (
        Annotated[tuple[Facility, ...], Field(min_length=1, max_length=40), LIST_AS_TUPLE] | None
    ) = None
    scale: Literal[1, 1000]
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
    scope_limits: Annotated[tuple[str, ...], LIST_AS_TUPLE]

    @model_validator(mode="after")
    def _rules(self) -> Self:
        if set(self.base) != set(OPERANDS):
            raise ValueError("base must state exactly " + ", ".join(OPERANDS))
        one, two, three = self.years
        if (two.year, three.year) != (one.year + 1, one.year + 2):
            raise ValueError("years must be three consecutive fiscal years")
        for earlier, later in ((one, two), (two, three)):
            if (_day(later.start, "start") - _day(earlier.end, "end")).days != 1:
                raise ValueError("each year must start the day after the previous one ends")
        names = [facility.name.casefold() for facility in self.facilities or ()]
        if len(set(names)) != len(names):
            raise ValueError("facility names must be unique")
        return self


def _copied(node: Any) -> Any:
    """A copy of the dicts and lists; every other value is shared (and is never changed)."""
    if isinstance(node, dict):
        return {key: _copied(item) for key, item in node.items()}
    if isinstance(node, list):
        return [_copied(item) for item in node]
    return node


def _scale_refused(document: dict[str, Any]) -> ForecastRefused:
    currency = document.get("currency")
    code = f"{currency} " if type(currency) is str and _CODE.fullmatch(currency) else ""
    message = f"`scale` must be 1 (CP-1 prints {code}millions) or 1000 ({code}thousands)"
    return ForecastRefused(RefusalKind.SCALE, "scale", message)


Slot = tuple[str, Any, Any, bool]


def _base_slots(document: dict[str, Any]) -> Iterator[Slot]:
    base = document.get("base")
    for key, operand in base.items() if isinstance(base, dict) else ():
        if isinstance(operand, dict) and "amount" in operand:
            yield f"base {key}", operand, "amount", True


def _values(drivers: object, name: str) -> list[Any]:
    driver = drivers.get(name) if isinstance(drivers, dict) else None
    values = driver.get("values") if isinstance(driver, dict) else None
    return values if isinstance(values, list) else []


def _driver_slots(document: dict[str, Any]) -> Iterator[Slot]:
    for group in _GROUPS:
        for name in _SCALED:
            values = _values(document.get(group), name)
            for index in range(len(values)):
                yield f"{group} {name} year {index + 1}", values, index, False


def _facility_slots(document: dict[str, Any]) -> Iterator[Slot]:
    facilities = document.get("facilities")
    for number, facility in enumerate(facilities if isinstance(facilities, list) else (), 1):
        for field in ("balance", "annual_amortisation"):
            if isinstance(facility, dict) and field in facility:
                yield f"facility {number} {field}", facility, field, False


def _slots(document: dict[str, Any]) -> Iterator[Slot]:
    """Each amount slot: its name, holder, key in the holder, and whether -0 is allowed."""
    yield from _base_slots(document)
    yield from _driver_slots(document)
    yield from _facility_slots(document)


def _millions(name: str, text: str, minus_zero_ok: bool) -> str:
    negative_zero = not minus_zero_ok and _MINUS_ZERO.fullmatch(text) is not None
    if _THOUSANDS.fullmatch(text) is None or negative_zero:
        message = _THOUSANDS_TEXT.format(slot=name, text=echo(text))
        raise ForecastRefused(RefusalKind.SCALE, name, message)
    return amount_text(_plain(product([Value(amount=parse_operand(text)), _MILLI])))


def _to_millions(document: dict[str, Any]) -> dict[str, str]:
    stated: dict[str, str] = {}
    for name, holder, key, minus_zero_ok in _slots(document):
        text = holder[key]
        if type(text) is str:
            holder[key] = _millions(name, text, minus_zero_ok)
            stated[name] = text
    return stated


def _issue(error: ErrorDetails) -> str:
    parts = (echo(part) if isinstance(part, str) else str(part) for part in error["loc"])
    return f"{'.'.join(parts) or '(root)'}: {error['msg']}"


def _validated(document: dict[str, Any]) -> ForecastInputs:
    try:
        return ForecastInputs.model_validate(document)
    except pydantic.ValidationError as error:
        issues = [_issue(item) for item in error.errors(include_url=False, include_input=False)]
        first = "; ".join(issues[:3])
        text = f"{len(issues)} problems; first: {first}" if len(issues) > 3 else first
        raise ForecastRefused(RefusalKind.SCHEMA, _SUBJECT, f"{_SUBJECT}: {text}") from None


def _refuse_over(case: str, values: tuple[str, ...], debt: Value) -> None:
    for year in (1, 2, 3):
        running = total([Value(amount=parse_operand(text)) for text in values[:year]])
        if _plain(running) > _plain(debt):
            message = (
                f"{case} case: debt_repayment through forecast year {year} totals "
                f"{amount_text(_plain(running))}, more than base debt {amount_text(_plain(debt))}"
            )
            raise ForecastRefused(RefusalKind.REPAYMENT, "debt_repayment", message)


def _check_repayment(inputs: ForecastInputs) -> None:
    stated = inputs.base["debt"].amount
    if stated is None:
        return
    debt = Value(amount=parse_operand(stated))
    cases = (inputs.base_drivers, inputs.upside_drivers, inputs.downside_drivers)
    for case, drivers in zip(("base", "upside", "downside"), cases, strict=True):
        if drivers is not None and drivers.debt_repayment is not None:
            _refuse_over(case, drivers.debt_repayment.values, debt)


def parse_inputs(document: dict[str, object]) -> tuple[ForecastInputs, dict[str, str]]:
    if type(document) is not dict:
        raise TypeError("document must be a dict")
    work: dict[str, Any] = _copied(document)
    stated: dict[str, str] = {}
    if "scale" in work:
        scale = work["scale"]
        if type(scale) is not int or scale not in (1, 1000):
            raise _scale_refused(work)
        if scale == 1000:
            stated = _to_millions(work)
    inputs = _validated(work)
    _check_repayment(inputs)
    return inputs, stated


def read_inputs(document: HandoffDocument) -> tuple[ForecastInputs, dict[str, str]]:
    return parse_inputs(read_forecast_document(document))
