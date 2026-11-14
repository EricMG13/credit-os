"""The forecast inputs schema: validated, typed, in millions, with the repayment bound."""

import datetime
import re
from collections.abc import Iterator, Mapping, Sequence
from decimal import Decimal
from itertools import chain
from itertools import product as pairs
from typing import Annotated, Any, Literal, Self

import pydantic
from pydantic import BaseModel, ConfigDict, Field, model_validator

from credit_os.handoff.document import HandoffDocument
from credit_os.handoff.errors import echo
from credit_os.model import facilities as fac
from credit_os.model.arithmetic import product, total
from credit_os.model.facilities import LIST_AS_TUPLE, Facility
from credit_os.model.inputs_json import read_forecast_document
from credit_os.model.refusals import ForecastRefused, RefusalKind
from credit_os.model.value import Value, amount_text, parse_operand

SCHEMA_VERSION = "cpos-forecast-inputs/1"
_NAMES = "revenue, ebitda, interest, taxes, wc, capex, fcf, debt, cash, undrawn"
OPERANDS = tuple(_NAMES.split(", "))
SHARE_PATTERN = r"^(0|1|0\.[0-9]{1,4}|1\.0{1,4})$"
SIGNED_PATTERN = r"^-?[0-9]{1,6}(\.[0-9]{1,4})?$"
Category = Literal[
    "Documentary Fact", "Management Language", "Analyst Interpretation", "Insufficient Information"
]
Growth = Annotated[str, Field(pattern=fac.FRACTION_PATTERN)]
Share = Annotated[str, Field(pattern=SHARE_PATTERN)]
Amount = Annotated[str, Field(pattern=fac.AMOUNT_PATTERN)]
Date = Annotated[str, Field(pattern=fac.DATE_PATTERN)]
_ONE_OF = "an operand states an amount or a reason, never both or neither"
_BOTH = "an operand names the `period` header or the `column` header, not both"
_UNNAMED = "an operand with an amount names its `row` and its `period` or `column`"
_LENGTH = ("Tuple should have at least", "List should have at least")
_SCALED = ("dividends", "debt_repayment")
_GROUPS = ("base_drivers", "upside_drivers", "downside_drivers")
_PLAIN = (dict, list, str, int, bool, type(None))
_CODE = re.compile(r"[A-Z]{3}")
_THOUSANDS = re.compile(r"-?[0-9]{1,9}(\.[0-9])?")
_MINUS_ZERO = re.compile(r"-0+(\.0)?")
_MILLI = Value(amount=Decimal("0.001"))
_THOUSANDS_TEXT = (
    "{slot} {text} is not an amount in thousands as CP-1 prints it (scale 1000): "
    "at most nine digits and one decimal place, no separators"
)


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


class Operand(_Model):
    amount: Annotated[str, Field(pattern=SIGNED_PATTERN)] | None
    reason: str | None
    row: Annotated[str, Field(min_length=1)] | None = None
    period: Annotated[str, Field(min_length=1)] | None = None
    column: Annotated[str, Field(min_length=1)] | None = None

    @model_validator(mode="after")
    def _rules(self) -> Self:
        if (self.amount is None) == (self.reason is None):
            raise ValueError(_ONE_OF)
        if self.reason is not None and not self.reason.strip():
            raise ValueError("an operand's reason must not be blank")
        if self.period is not None and self.column is not None:
            raise ValueError(_BOTH)
        if self.amount is not None and (
            self.row is None or (self.period, self.column) == (None, None)
        ):
            raise ValueError(_UNNAMED)
        return self


class _Driver(_Model):
    category: Category
    rationale: str
    limitation: str | None


class GrowthDriver(_Driver):
    values: Annotated[tuple[Growth, Growth, Growth], LIST_AS_TUPLE]


class ShareDriver(_Driver):
    values: Annotated[tuple[Share, Share, Share], LIST_AS_TUPLE]


class AmountDriver(_Driver):
    values: Annotated[tuple[Amount, Amount, Amount], LIST_AS_TUPLE]


class BaseDrivers(_Model):
    revenue_growth: GrowthDriver
    ebitda_margin: ShareDriver
    capex_pct_revenue: ShareDriver
    tax_wc_pct_revenue: ShareDriver
    interest_rate: ShareDriver
    dividends: AmountDriver
    debt_repayment: AmountDriver


class CaseDrivers(_Model):
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


class Shock(_Model):
    ebitda_decline: Share
    rate_increase: Share


def _day(text: str, field: str) -> datetime.date:
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        raise ValueError(f"{field} {text} is not a calendar date") from None


class Span(_Model):
    year: Annotated[int, Field(ge=1000, le=9999)]
    start: Date
    end: Date

    @model_validator(mode="after")
    def _rules(self) -> Self:
        first, last = _day(self.start, "start"), _day(self.end, "end")
        if first > last:
            raise ValueError("a year starts after it ends")
        return self


class ForecastInputs(_Model):
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
            raise ValueError("base must state exactly " + _NAMES)
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


def _plain(value: Value) -> Decimal:
    if value.amount is None:
        raise ValueError("an amount is missing")
    return value.amount


def _not_json(path: tuple[str, ...], what: str) -> TypeError:
    where = ".".join(echo(part) for part in path) or "(root)"
    return TypeError(f"document node {where} {what}")


def _copied(node: Any, path: tuple[str, ...] = ()) -> Any:  # tuples become lists
    kind = type(node)
    if kind is tuple:
        node = list(node)
    elif kind not in _PLAIN:
        raise _not_json(path, f"is a {kind.__name__}, not JSON data")
    if isinstance(node, dict):
        for key in node:
            if type(key) is not str:
                raise _not_json(path, f"has a key that is a {type(key).__name__}")
        return {key: _copied(item, (*path, key)) for key, item in node.items()}
    if isinstance(node, list):
        return [_copied(item, (*path, str(index))) for index, item in enumerate(node)]
    return node


def _scale_refused(document: dict[str, Any]) -> ForecastRefused:
    currency = document.get("currency")
    code = f"{currency} " if type(currency) is str and _CODE.fullmatch(currency) else ""
    message = f"`scale` must be 1 (CP-1 prints {code}millions) or 1000 ({code}thousands)"
    return ForecastRefused(RefusalKind.SCALE, "scale", message)


Slot = tuple[str, Any, Any, bool]  # name, holder, key in the holder, whether -0 is allowed


def _base_slots(document: dict[str, Any]) -> Iterator[Slot]:
    base = document.get("base")
    for key, operand in base.items() if isinstance(base, dict) else ():
        if isinstance(operand, dict) and "amount" in operand:
            yield f"base {echo(key)}", operand, "amount", True


def _driver_slots(document: dict[str, Any]) -> Iterator[Slot]:
    for group, name in pairs(_GROUPS, _SCALED):
        drivers = document.get(group)
        driver = drivers.get(name) if isinstance(drivers, dict) else None
        values = driver.get("values") if isinstance(driver, dict) else None
        for index in range(len(values) if isinstance(values, list) else 0):
            yield f"{group} {name} year {index + 1}", values, index, False


def _facility_slots(document: dict[str, Any]) -> Iterator[Slot]:
    facilities = document.get("facilities")
    for number, facility in enumerate(facilities if isinstance(facilities, list) else (), 1):
        for field in ("balance", "annual_amortisation"):
            if isinstance(facility, dict) and field in facility:
                yield f"facility {number} {field}", facility, field, False


def _to_millions(document: dict[str, Any]) -> dict[str, str]:
    stated: dict[str, str] = {}
    slots = chain(_base_slots(document), _driver_slots(document), _facility_slots(document))
    for name, holder, key, minus_zero_ok in slots:
        text = holder[key]
        if type(text) is not str:
            continue
        negative_zero = not minus_zero_ok and _MINUS_ZERO.fullmatch(text) is not None
        if _THOUSANDS.fullmatch(text) is None or negative_zero:
            message = _THOUSANDS_TEXT.format(slot=name, text=echo(text))
            raise ForecastRefused(RefusalKind.SCALE, name, message)
        holder[key] = amount_text(_plain(product([Value(amount=parse_operand(text)), _MILLI])))
        stated[name] = text
    return stated


def _issue(error: Mapping[str, Any]) -> str:
    parts = (echo(part) if isinstance(part, str) else str(part) for part in error["loc"])
    return f"{'.'.join(parts) or '(root)'}: {error['msg']}"


def _echoes(error: Mapping[str, Any], errors: Sequence[Mapping[str, Any]]) -> bool:
    depth = len(error["loc"])
    failed = {
        item["loc"][depth]
        for item in errors
        if len(item["loc"]) > depth and item["loc"][:depth] == error["loc"]
    }
    ctx = error.get("ctx") or {}
    actual, minimum = ctx.get("actual_length"), ctx.get("min_length")
    if not failed or not isinstance(actual, int) or not isinstance(minimum, int):
        return False
    return actual + len(failed) >= minimum


def without_echoes(errors: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    def is_length(item: Mapping[str, Any]) -> bool:
        return bool(item["type"] == "too_short" and item["msg"].startswith(_LENGTH))

    return [item for item in errors if not (is_length(item) and _echoes(item, errors))]


def _validated(document: dict[str, Any]) -> ForecastInputs:
    try:
        return ForecastInputs.model_validate(document)
    except pydantic.ValidationError as error:
        errors = error.errors(include_url=False, include_input=False)
        issues = [_issue(item) for item in without_echoes(errors)]
        first = "; ".join(issues[:3])
        text = f"{len(issues)} problems; first: {first}" if len(issues) > 3 else first
        message = f"forecast inputs: {text}"
        raise ForecastRefused(RefusalKind.SCHEMA, "forecast inputs", message) from None


def _check_repayment(inputs: ForecastInputs) -> None:
    stated = inputs.base["debt"].amount
    if stated is None:
        return
    debt = _plain(Value(amount=parse_operand(stated)))
    cases = (inputs.base_drivers, inputs.upside_drivers, inputs.downside_drivers)
    for case, drivers in zip(("base", "upside", "downside"), cases, strict=True):
        if drivers is None or drivers.debt_repayment is None:
            continue
        values = drivers.debt_repayment.values
        for year in (1, 2, 3):
            running = _plain(total([Value(amount=parse_operand(text)) for text in values[:year]]))
            if running > debt:
                message = f"{case} case: debt_repayment through forecast year {year} totals "
                message += f"{amount_text(running)}, more than base debt {amount_text(debt)}"
                raise ForecastRefused(RefusalKind.REPAYMENT, "debt_repayment", message)


def parse_inputs(document: dict[str, object]) -> tuple[ForecastInputs, dict[str, str]]:
    if type(document) is not dict:
        raise TypeError("document must be a dict")
    work: dict[str, Any] = _copied(document)
    scale = work.get("scale", 1)
    if type(scale) is not int or scale not in (1, 1000):
        raise _scale_refused(work)
    stated = _to_millions(work) if scale == 1000 else {}
    inputs = _validated(work)
    _check_repayment(inputs)
    return inputs, stated


def read_inputs(document: HandoffDocument) -> tuple[ForecastInputs, dict[str, str]]:
    return parse_inputs(read_forecast_document(document))
