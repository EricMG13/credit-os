"""Exact sum, difference and product; one rounded ratio; two rounding comparisons."""

import decimal
from collections.abc import Iterable, Sequence
from decimal import Decimal

from credit_os.model.value import Missing, MissingCode, Value, exact_context, ratio_context

_HALF = Decimal("0.5")


def _operands(values: Sequence[Value]) -> tuple[Value, ...]:
    if type(values) not in (list, tuple):
        raise TypeError("operands must be a list or a tuple of Value")
    operands = tuple(values)
    if not operands:
        raise ValueError("at least one operand is required")
    if any(type(item) is not Value for item in operands):
        raise TypeError("every operand must be a Value")
    return operands


def _first_missing(operands: Iterable[Value]) -> Value | None:
    return next((item for item in operands if item.missing is not None), None)


def _parts(value: Value) -> tuple[int, int]:
    """Signed integer coefficient and exponent of a present amount."""
    amount = value.amount
    if amount is None:
        raise ValueError("operand is missing")
    sign, digits, exponent = amount.as_tuple()
    if not isinstance(exponent, int):
        raise TypeError("amount exponent must be an int")
    coefficient = int("".join(map(str, digits)))
    return (-coefficient if sign else coefficient), exponent


_CHUNKS = ((10**1024, 1024), (10**64, 64), (10**8, 8), (10, 1))
_LIMIT = 10**38


def _exact(coefficient: int, exponent: int) -> Value:
    """Strip trailing zeros and refuse a long result by integer arithmetic, so no big
    int is ever turned into text (Python limits that, process-wide)."""
    if coefficient == 0:
        return Value(amount=Decimal(0))
    for chunk, places in _CHUNKS:
        while coefficient % chunk == 0:
            coefficient //= chunk
            exponent += places
    if abs(coefficient) >= _LIMIT:
        raise decimal.Inexact("more than 38 significant digits")
    digits = tuple(map(int, str(abs(coefficient))))
    return Value(amount=Decimal((int(coefficient < 0), digits, exponent)))


def total(values: Sequence[Value]) -> Value:
    operands = _operands(values)
    missing = _first_missing(operands)
    if missing is not None:
        return missing
    parts = [_parts(item) for item in operands]
    floor = min(exponent for _, exponent in parts)
    return _exact(sum(c * 10 ** (e - floor) for c, e in parts), floor)


def difference(minuend: Value, subtrahend: Value) -> Value:
    operands = _operands((minuend, subtrahend))
    missing = _first_missing(operands)
    if missing is not None:
        return missing
    (c1, e1), (c2, e2) = _parts(minuend), _parts(subtrahend)
    floor = min(e1, e2)
    return _exact(c1 * 10 ** (e1 - floor) - c2 * 10 ** (e2 - floor), floor)


def product(values: Sequence[Value]) -> Value:
    operands = _operands(values)
    missing = _first_missing(operands)
    if missing is not None:
        return missing
    coefficient, exponent = 1, 0
    for item in operands:
        c, e = _parts(item)
        coefficient *= c
        exponent += e
    return _exact(coefficient, exponent)


def ratio(numerator: Value, denominator: Value, *, non_positive: str) -> Value:
    refusal = Missing(MissingCode.ZERO_OR_NEGATIVE_DENOMINATOR, non_positive)
    operands = _operands((numerator, denominator))
    missing = _first_missing(operands)
    if missing is not None:
        return missing
    top, bottom = numerator.amount, denominator.amount
    if top is None or bottom is None:
        raise ValueError("operand is missing")
    if bottom <= 0:
        return Value(missing=refusal)
    with decimal.localcontext(ratio_context()):
        return Value(amount=top / bottom)


def _exponent(amount: Decimal) -> int:
    exponent = amount.as_tuple().exponent
    if not isinstance(exponent, int):
        raise TypeError("amount exponent must be an int")
    return exponent


def _decimals(amounts: Iterable[Decimal]) -> tuple[Decimal, ...]:
    checked = tuple(amounts)
    for amount in checked:
        if type(amount) is not Decimal:
            raise TypeError("every amount must be a Decimal")
        if not amount.is_finite():
            raise ValueError("every amount must be finite")
    return checked


def half_unit(amounts: Iterable[Decimal]) -> Decimal:
    """Half a unit in the finest last place any of `amounts` is written to, at most 0.5."""
    exponents = [_exponent(amount) for amount in _decimals(amounts)]
    with decimal.localcontext(exact_context()):
        return _HALF.scaleb(min(min(exponents, default=0), 0))


def beyond_rounding(
    stated: Decimal, host: Decimal, printed: Iterable[Decimal] | None = None
) -> bool:
    """Whether `host` differs from `stated` by strictly more than half a unit in the finest
    place among `stated` and `printed` (`host` itself when `printed` is None)."""
    figures = _decimals((stated, host))
    places = (host,) if printed is None else _decimals(printed)
    with decimal.localcontext(exact_context()):
        return abs(figures[0] - figures[1]) > half_unit((stated, *places))
