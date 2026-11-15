"""The run's budget: what has been spent, and whether the next call may go (decisions D6, D7,
D9; rule G5). Exact `Decimal` arithmetic; unknown spend is `None`, never zero. Pure: it touches
no store, no file and no model, and it never reads the text of an id."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Context as DecimalContext
from decimal import Decimal, Inexact, Rounded, localcontext
from enum import StrEnum

_MAXIMUM_DIGITS = 64
_EXPONENTS = range(-62, 64)  # the store's money bounds (credit_os.store.codec)
_CALL_STATES = ("open", "not_sent", "ok", "sent_usage", "sent_unknown")
_CHARGED_STATES = ("ok", "sent_usage", "sent_unknown")
_OUTCOMES = ("done", "failed", "unfinished")

# Precision of the sum. One amount spans at most 64 digits within exponents -62..63, so the
# exact sum of two spans 126 digits (10^63 + 10^-62); every further line can add at most one
# carry digit per factor of ten of lines, so 126 + 34 leaves room for 10^34 lines, far beyond
# any run. `Inexact` and `Rounded` are trapped: a sum that did not fit raises, it never rounds.
_SUM_PRECISION = 160


class BudgetDataError(ValueError):
    """A refused amount, line or set of lines."""


class BudgetStop(StrEnum):
    """Why a call may not go. These are store identifiers: callers pass `.value`."""

    CAPPED = "capped"
    HOLD_EXCEEDED = "hold_exceeded"
    SPEND_UNKNOWN = "spend_unknown"


def _check_amount(value: object, what: str) -> None:
    if type(value) is not Decimal:
        raise BudgetDataError(f"{what} must be a Decimal")
    if not value.is_finite() or value.is_signed():
        raise BudgetDataError(f"{what} must be finite and not negative")
    _, digits, exponent = value.as_tuple()
    if len(digits) > _MAXIMUM_DIGITS or exponent not in _EXPONENTS:
        raise BudgetDataError(f"{what} has more than 64 digits or an exponent outside -62..63")


def _check_name(value: object, what: str) -> None:
    if type(value) is not str or not value:
        raise BudgetDataError(f"{what} must be a non-empty string")


@dataclass(frozen=True, slots=True)
class CallLine:
    """One model call. `open`: started, no outcome recorded. `not_sent`: never left. The
    others were sent; `billed_usd` `None` is an unknown charge. `open` and `not_sent` carry
    no charge."""

    call: str
    state: str
    hold_usd: Decimal
    billed_usd: Decimal | None

    def __post_init__(self) -> None:
        _check_name(self.call, "call")
        if type(self.state) is not str or self.state not in _CALL_STATES:
            raise BudgetDataError(f"unknown call state {self.state!r}")
        _check_amount(self.hold_usd, "hold_usd")
        if self.state not in _CHARGED_STATES:
            if self.billed_usd is not None:
                raise BudgetDataError(f"a {self.state} call has no charge")
        elif self.billed_usd is not None:
            _check_amount(self.billed_usd, "billed_usd")


@dataclass(frozen=True, slots=True)
class CompactionLine:
    """One context compaction. `supersedes` is the `event_id` of an unfinished compaction this
    one completes. An `unfinished` line supersedes nothing and has no charge."""

    call: str
    event_id: str
    outcome: str
    supersedes: str | None
    billed_usd: Decimal | None

    def __post_init__(self) -> None:
        _check_name(self.call, "call")
        _check_name(self.event_id, "event_id")
        if type(self.outcome) is not str or self.outcome not in _OUTCOMES:
            raise BudgetDataError(f"unknown compaction outcome {self.outcome!r}")
        if self.supersedes is not None:
            _check_name(self.supersedes, "supersedes")
            if self.supersedes == self.event_id:
                raise BudgetDataError("a compaction cannot supersede itself")
            if self.outcome == "unfinished":
                raise BudgetDataError("an unfinished compaction supersedes nothing")
        if self.outcome == "unfinished" and self.billed_usd is not None:
            raise BudgetDataError("an unfinished compaction has no charge")
        if self.billed_usd is not None:
            _check_amount(self.billed_usd, "billed_usd")


@dataclass(frozen=True)
class Total:
    """`spent_usd` `None` is unknown, never zero; `unknown` are the lines that made it so."""

    spent_usd: Decimal | None
    unknown: tuple[CallLine | CompactionLine, ...]


@dataclass(frozen=True)
class Admission:
    """`stop` is `None` exactly when `admitted`. `over_hold` lists every call line, in order,
    whose known charge is above its own hold, whatever the stop."""

    admitted: bool
    stop: BudgetStop | None
    total: Total
    over_hold: tuple[CallLine, ...]


def _checked_lines(
    lines: Iterable[CallLine | CompactionLine],
) -> tuple[CallLine | CompactionLine, ...]:
    items = tuple(lines)
    for item in items:
        if not isinstance(item, CallLine | CompactionLine):
            raise BudgetDataError(
                f"a budget line must be a CallLine or CompactionLine, not {type(item).__name__}"
            )
    return items


def _superseded_ids(compactions: list[CompactionLine]) -> set[str]:
    """The `event_id`s completed by a successor, after refusing inconsistent sets."""
    own = [c.event_id for c in compactions]
    if len(set(own)) != len(own):
        raise BudgetDataError("two compaction lines share an event_id")
    named = [c.supersedes for c in compactions if c.supersedes is not None]
    if len(set(named)) != len(named):
        raise BudgetDataError("two compaction lines supersede the same event_id")
    by_id = {c.event_id: c for c in compactions}
    for target in named:
        present = by_id.get(target)
        if present is not None and present.outcome != "unfinished":
            raise BudgetDataError("a compaction line supersedes one that is not unfinished")
    return set(named)


def _charge(line: CallLine | CompactionLine, superseded: set[str]) -> tuple[bool, Decimal | None]:
    """(counts, charge): whether the line is part of the sum or of the unknown, and its charge.
    A line that does not count is dropped; a counted line with charge `None` is unknown."""
    if isinstance(line, CallLine):
        if line.state == "not_sent":
            return False, None
        return True, None if line.state == "open" else line.billed_usd
    if line.outcome == "unfinished":
        return line.event_id not in superseded, None
    if line.outcome == "failed":
        return True, None
    return True, line.billed_usd


def total(lines: Iterable[CallLine | CompactionLine]) -> Total:
    """What the lines spent: the exact sum, or unknown with the lines that made it so."""
    items = _checked_lines(lines)
    superseded = _superseded_ids([i for i in items if isinstance(i, CompactionLine)])
    unknown: list[CallLine | CompactionLine] = []
    charges: list[Decimal] = []
    for item in items:
        counts, charge = _charge(item, superseded)
        if not counts:
            continue
        if charge is None:
            unknown.append(item)
        else:
            charges.append(charge)
    if unknown:
        return Total(spent_usd=None, unknown=tuple(unknown))
    return Total(spent_usd=_exact_sum(charges), unknown=())


def _context() -> DecimalContext:
    context = DecimalContext(prec=_SUM_PRECISION)
    context.traps[Inexact] = True
    context.traps[Rounded] = True
    return context


def _exact_sum(amounts: list[Decimal]) -> Decimal:
    with localcontext(_context()) as context:
        try:
            result = Decimal(0)
            for amount in amounts:
                result = context.add(result, amount)
        except (Inexact, Rounded) as error:
            raise BudgetDataError("the sum does not fit exactly") from error
        return result


def admit_call(
    lines: Iterable[CallLine | CompactionLine], *, cap_usd: Decimal, next_hold_usd: Decimal
) -> Admission:
    """May the next call go? `spend_unknown`, then `hold_exceeded`, then `capped`. With no line
    this is the launch check. Spent plus the next hold equal to the cap passes."""
    _check_amount(cap_usd, "cap_usd")
    _check_amount(next_hold_usd, "next_hold_usd")
    items = _checked_lines(lines)
    spent = total(items)
    over_hold = tuple(
        i
        for i in items
        if isinstance(i, CallLine) and i.billed_usd is not None and i.billed_usd > i.hold_usd
    )
    stop = _stop(spent, over_hold, cap_usd, next_hold_usd)
    return Admission(admitted=stop is None, stop=stop, total=spent, over_hold=over_hold)


def _stop(
    spent: Total, over_hold: tuple[CallLine, ...], cap_usd: Decimal, next_hold_usd: Decimal
) -> BudgetStop | None:
    if spent.spent_usd is None:
        return BudgetStop.SPEND_UNKNOWN
    if over_hold:
        return BudgetStop.HOLD_EXCEEDED
    if _exact_sum([spent.spent_usd, next_hold_usd]) > cap_usd:
        return BudgetStop.CAPPED
    return None


@dataclass(frozen=True, slots=True)
class PriceRow:
    """One configuration's published prices, USD per million tokens, and the token counts a
    hold prices: the whole context ceiling in, and at least `output_floor_tokens` out."""

    config_id: str
    input_rates: tuple[Decimal, ...]
    output_rates: tuple[Decimal, ...]
    context_tokens: int
    output_floor_tokens: int

    def __post_init__(self) -> None:
        _check_name(self.config_id, "config_id")
        for rates, what in ((self.input_rates, "input_rates"), (self.output_rates, "output_rates")):
            if type(rates) is not tuple or not rates:
                raise BudgetDataError(f"{what} must be a non-empty tuple")
            for rate in rates:
                _check_amount(rate, what)
        _check_count(self.context_tokens, "context_tokens", least=1)
        _check_count(self.output_floor_tokens, "output_floor_tokens", least=0)


def _check_count(value: object, what: str, *, least: int) -> None:
    if type(value) is not int or value < least:
        raise BudgetDataError(f"{what} must be an int of at least {least}")


def call_hold(price: PriceRow, *, max_output_tokens: int) -> Decimal:
    """What one call holds: the whole context at the dearest input rate plus the larger of
    `max_output_tokens` and the row's floor at the dearest output rate, per million tokens.
    Exact, never rounded; a hold of zero or one the money bounds refuse is `BudgetDataError`."""
    _check_count(max_output_tokens, "max_output_tokens", least=0)
    held_output = max(max_output_tokens, price.output_floor_tokens)
    with localcontext(_context()) as context:
        try:
            held_in = context.multiply(Decimal(price.context_tokens), max(price.input_rates))
            held_out = context.multiply(Decimal(held_output), max(price.output_rates))
            hold = context.add(held_in, held_out).scaleb(-6, context)
        except (Inexact, Rounded) as error:
            raise BudgetDataError("the hold does not fit exactly") from error
    _check_amount(hold, "hold")
    if not hold:
        raise BudgetDataError("a hold of zero bounds nothing")
    return hold
