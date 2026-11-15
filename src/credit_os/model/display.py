"""Display text of a kernel Value and the JSON number token of a Decimal."""

import decimal
from collections.abc import Sequence
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Context, Decimal
from fractions import Fraction

from credit_os.model.value import Value, _carried, amount_text

_MAX_PLACES = 6
# A stored amount has at most 38 digits and an adjusted exponent within +/-100;
# rounding to 6 places adds at most one digit, so 400 never rounds or traps.
_WIDE = Context(prec=400, rounding=ROUND_HALF_UP, traps=[])


def display_text(value: Value, places: int) -> str | None:
    """Half-up rounded text of a Value; None for a missing value.

    Half-up is applied to the magnitude, so a tie on a negative rounds away from
    zero (-0.05 at 1 place gives "-0.1"). The comma groups the integer part only.
    """
    if type(value) is not Value:
        raise TypeError("value must be a Value")
    if type(places) is not int:
        raise TypeError("places must be an int")
    if not 0 <= places <= _MAX_PLACES:
        raise ValueError("places must be 0..6")
    if value.amount is None:
        return None
    rounded = value.amount.quantize(Decimal((0, (1,), -places)), context=_WIDE)
    digits = amount_text(rounded.copy_abs()).replace(".", "")
    whole = digits[: len(digits) - places] if places else digits
    grouped = f"{int(whole):,}"
    text = grouped + "." + digits[len(digits) - places :] if places else grouped
    return "-" + text if rounded < 0 else text


def json_number(amount: Decimal) -> str:
    """Exact plain-digit JSON number token for a Decimal.

    The token always matches the JSON number grammar: no exponent, no leading "+",
    no leading zero and no bare ".". Fraction trailing zeros are dropped and a zero
    is "0". It is exact, but JSON.parse reads a double, so digits beyond about 17
    are not carried by the browser (accepted: the front end computes nothing and
    positions are not shown as text). More than 38 significant digits or an
    adjusted exponent outside -100..100 is a ValueError; a zero at any exponent is "0".
    """
    try:
        _carried(amount)
    except decimal.DecimalException as bound:
        raise ValueError(f"amount outside the value bounds: {type(bound).__name__}") from bound
    if amount == 0:
        return "0"
    text = amount_text(amount)
    return text.rstrip("0").rstrip(".") if "." in text else text


_STEPS = (100, 125, 150, 200, 250, 300, 400, 500, 600, 750)  # 1, 1.25 ... 7.5, in hundredths
_TICK_INTERVALS = 4
_POSITION_PLACES = 4
_SHARE_BASE = 100


def _digits(number: int) -> tuple[int, ...]:
    return tuple(map(int, str(number)))


def _built(negative: bool, magnitude: int, exponent: int) -> Decimal:
    """A Decimal from a sign, an integer magnitude and an exponent; never a negative zero."""
    sign = 1 if negative and magnitude else 0
    amount = Decimal((sign, _digits(magnitude), exponent))
    try:
        _carried(amount)
    except decimal.DecimalException as bound:
        raise ValueError(f"result outside the value bounds: {type(bound).__name__}") from bound
    return amount


def _half_up(ratio: Fraction, places: int) -> Decimal:
    """The ratio rounded half-up on its magnitude to `places`, in integers only."""
    num, den = abs(ratio.numerator), ratio.denominator
    scaled = (2 * num * 10**places + den) // (2 * den)
    return _built(ratio < 0, scaled, -places)


def _exact(ratio: Fraction) -> Decimal:
    """A Fraction whose denominator divides a power of ten, as an exact Decimal."""
    places = 0
    while (ratio * 10**places).denominator != 1:
        places += 1
        if places > _MAX_PLACES + 200:
            raise ValueError("amount is not a finite decimal")
    return _built(ratio < 0, abs(int(ratio * 10**places)), -places)


def _figures(values: Sequence[Value]) -> list[Value]:
    if isinstance(values, str | bytes) or not isinstance(values, Sequence):
        raise TypeError("values must be a sequence of Value")
    if any(type(value) is not Value for value in values):
        raise TypeError("every item must be a Value")
    return list(values)


def _present(values: Sequence[Value]) -> list[Fraction]:
    return [Fraction(v.amount) for v in _figures(values) if v.amount is not None]


def _whole_count(count: object) -> int:
    if type(count) is not int:
        raise TypeError("a count must be an int")
    if count < 0:
        raise ValueError("a count must not be negative")
    return count


def megabytes_text(size_bytes: int) -> str:
    """bytes / 1,000,000 half-up to one decimal, grouped as display_text, then ' MB' (R8a)."""
    megabytes = _half_up(Fraction(_whole_count(size_bytes), 1_000_000), 1)
    text = display_text(Value(amount=megabytes), 1)
    return f"{text} MB"


def elapsed_minutes(start: datetime | None, end: datetime | None) -> Decimal | None:
    """Exact (end - start) in microseconds / 60,000,000, half-up to one place.

    None when either is None; both must be aware, and end must not precede start.
    """
    for moment in (start, end):
        if moment is not None and type(moment) is not datetime:
            raise TypeError("start and end must be datetime or None")
        if moment is not None and moment.utcoffset() is None:
            raise ValueError("start and end must be timezone-aware")
    if start is None or end is None:
        return None
    gap = end - start
    if gap < timedelta(0):
        raise ValueError("end precedes start")
    micros = (gap.days * 86_400 + gap.seconds) * 1_000_000 + gap.microseconds
    return _half_up(Fraction(micros, 60_000_000), 1)


def token_sum(counts: Sequence[int | None]) -> int | None:
    """The exact sum; None when any count is None. Empty or negative counts are refused."""
    if isinstance(counts, str | bytes) or not isinstance(counts, Sequence):
        raise TypeError("counts must be a sequence")
    if not counts:
        raise ValueError("counts must not be empty")
    present = [_whole_count(count) for count in counts if count is not None]
    return None if len(present) != len(counts) else sum(present)


def row_positions(values: Sequence[Value]) -> tuple[Decimal | None, ...]:
    """Value / the largest present magnitude, half-up on the magnitude to 4 places.

    No negative zero; a missing value gives None; a largest magnitude of 0 gives 0
    for every present value.
    """
    figures = _figures(values)
    top = max((abs(Fraction(v.amount)) for v in figures if v.amount is not None), default=0)
    return tuple(
        None if v.amount is None else _half_up(Fraction(v.amount) / top if top else Fraction(0), 4)
        for v in figures
    )


def shares(parts: Sequence[Value], places: int) -> tuple[Decimal, ...] | None:
    """100 * part / sum, half-up to `places` (0..6) each, no largest-remainder fix.

    None when any part is missing; an empty, zero or negative part is ValueError.
    """
    figures = _figures(parts)
    if type(places) is not int:
        raise TypeError("places must be an int")
    if not 0 <= places <= _MAX_PLACES:
        raise ValueError("places must be 0..6")
    if not figures:
        raise ValueError("parts must not be empty")
    amounts = _present(figures)
    if any(amount <= 0 for amount in amounts):
        raise ValueError("every part must be positive")
    if len(amounts) != len(figures):
        return None
    total = sum(amounts)
    return tuple(_half_up(_SHARE_BASE * amount / total, places) for amount in amounts)


def _step(quarter: Fraction) -> tuple[int, int]:
    """The least s * 10^j >= quarter as (hundredths of s as an integer, exponent of 10 for it)."""
    estimate = len(str(quarter.numerator)) - len(str(quarter.denominator))
    for exponent in range(estimate - 3, estimate + 2):
        for hundredths in _STEPS:
            if Fraction(hundredths) * Fraction(10) ** (exponent - 2) >= quarter:
                return hundredths, exponent - 2
    raise ValueError("no tick step found")


def axis_ticks(values: Sequence[Value]) -> tuple[tuple[Decimal, ...], int] | None:
    """Five ticks 0, step .. 4 step over a zero-based axis, and the step's fraction digits.

    M is the largest present value; step is the least s * 10^j (s in 1, 1.25, 1.5, 2,
    2.5, 3, 4, 5, 6, 7.5; j an integer) >= M/4, or 1 when M = 0. Places over 6, a tick
    outside the value bounds or a negative value is ValueError; no present value gives None.
    """
    amounts = _present(values)
    if not amounts:
        return None
    if min(amounts) < 0:
        raise ValueError("a zero-based axis cannot draw a negative value")
    top = max(amounts)
    hundredths, exponent = (100, -2) if top == 0 else _step(top / _TICK_INTERVALS)
    while hundredths % 10 == 0:
        hundredths, exponent = hundredths // 10, exponent + 1
    places = max(0, -exponent)
    if places > _MAX_PLACES:
        raise ValueError("tick step needs more than 6 places")
    ticks = tuple(_built(False, hundredths * k, exponent) for k in range(_TICK_INTERVALS + 1))
    return ticks, places


def axis_max(values: Sequence[Value]) -> Decimal | None:
    """The largest present value; 1 when every present value is 0; None when none is present.

    A negative value is ValueError.
    """
    amounts = _present(values)
    if not amounts:
        return None
    if min(amounts) < 0:
        raise ValueError("a zero-based axis cannot draw a negative value")
    top = max(amounts)
    return _exact(top) if top else Decimal((0, (1,), 0))


def bridge_positions(
    steps: Sequence[tuple[bool, Value]],
) -> tuple[tuple[Decimal, Decimal] | None, ...] | None:
    """Start and end of each bridge step; True marks a total.

    A total is (0, amount) and sets the running amount; a change is (running,
    running + amount). A missing step gives None and leaves the running amount unknown
    until the next total; a present change while it is unknown makes the whole result
    None. The first step not a total, or any position below 0, is ValueError.
    """
    if isinstance(steps, str | bytes) or not isinstance(steps, Sequence):
        raise TypeError("steps must be a sequence")
    for step in steps:
        if type(step) is not tuple or len(step) != 2:
            raise TypeError("each step is a (bool, Value) pair")
        if type(step[0]) is not bool or type(step[1]) is not Value:
            raise TypeError("each step is a (bool, Value) pair")
    if steps and not steps[0][0]:
        raise ValueError("the first step must be a total")
    spans: list[tuple[Decimal, Decimal] | None] = []
    running: Fraction | None = None
    undefined = False
    for is_total, value in steps:
        if value.amount is None:
            spans.append(None)
            running = None
            continue
        amount = Fraction(value.amount)
        if is_total:
            running = amount
            span = (Fraction(0), amount)
        elif running is None:
            undefined = True
            spans.append(None)
            continue
        else:
            span = (running, running + amount)
            running = span[1]
        if min(span) < 0:
            raise ValueError("a bridge position is below zero")
        spans.append((_exact(span[0]), _exact(span[1])))
    return None if undefined else tuple(spans)
