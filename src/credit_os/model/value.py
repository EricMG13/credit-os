"""The one value type of the model layer: an exact amount or the reason it is missing."""

import decimal
import re
from dataclasses import dataclass
from decimal import Context, Decimal
from enum import StrEnum

_DIGITS = 38
_MAX_TEXT = 64
_MAX_ADJUSTED = 100
OPERAND_REFUSED = (
    "an operand is a plain decimal such as -1234.5: an optional minus, digits, and an optional "
    "point with digits after it, at most 38 digits and 64 characters"
)
_OPERAND = re.compile(r"-?[0-9]+(\.[0-9]+)?")


class MissingCode(StrEnum):
    NOT_SOURCED = "NOT_SOURCED"
    ZERO_OR_NEGATIVE_DENOMINATOR = "ZERO_OR_NEGATIVE_DENOMINATOR"


@dataclass(frozen=True, slots=True)
class Missing:
    code: MissingCode
    text: str

    def __post_init__(self) -> None:
        if type(self.code) is not MissingCode:
            raise TypeError("Missing.code must be a MissingCode")
        if type(self.text) is not str:
            raise TypeError("Missing.text must be a str")
        if not self.text.strip():
            raise ValueError("Missing.text must not be blank")


def _context(*, exact: bool) -> Context:
    traps = [decimal.InvalidOperation, decimal.DivisionByZero, decimal.Overflow]
    if exact:
        traps.append(decimal.Inexact)
    return Context(
        prec=_DIGITS,
        rounding=decimal.ROUND_HALF_EVEN,
        Emin=-999999,
        Emax=999999,
        capitals=1,
        clamp=0,
        flags=[],
        traps=traps,
    )


def ratio_context() -> Context:
    return _context(exact=False)


def exact_context() -> Context:
    return _context(exact=True)


def _carried(amount: object) -> tuple[int, str, int]:
    """Validate; return sign, digits and exponent as carried (zero without sign)."""
    if type(amount) is not Decimal:
        raise TypeError("amount must be a Decimal")
    if not amount.is_finite():
        raise ValueError("amount must be finite")
    sign, digits, exponent = amount.as_tuple()
    if not isinstance(exponent, int):
        raise TypeError("amount exponent must be an int")
    text = "".join(map(str, digits))
    if not any(digits):
        return 0, "0", exponent
    kept = text.rstrip("0")
    stripped = exponent + len(text) - len(kept)
    if len(kept) > _DIGITS:
        raise decimal.Inexact("more than 38 significant digits")
    adjusted = stripped + len(kept) - 1
    if adjusted > _MAX_ADJUSTED:
        raise decimal.Overflow("adjusted exponent above 100")
    if adjusted < -_MAX_ADJUSTED:
        raise decimal.Underflow("adjusted exponent below -100")
    return sign, text, exponent


def _stored(amount: object) -> Decimal:
    sign, text, exponent = _carried(amount)
    if not text.strip("0"):
        return Decimal(0)
    kept = text.rstrip("0")
    return Decimal((sign, tuple(map(int, kept)), exponent + len(text) - len(kept)))


@dataclass(frozen=True, slots=True)
class Value:
    amount: Decimal | None = None
    missing: Missing | None = None

    def __post_init__(self) -> None:
        if (self.amount is None) == (self.missing is None):
            raise ValueError("exactly one of amount and missing must be set")
        if self.missing is not None and type(self.missing) is not Missing:
            raise TypeError("missing must be a Missing")
        if self.amount is not None:
            object.__setattr__(self, "amount", _stored(self.amount))


def parse_operand(text: str) -> Decimal:
    """Bounded operand text to a Decimal as printed (trailing zeros kept)."""
    if type(text) is not str:
        raise TypeError("operand text must be a str")
    refusal = ValueError(OPERAND_REFUSED)
    if len(text) > _MAX_TEXT or _OPERAND.fullmatch(text) is None:
        raise refusal
    unsigned = text.removeprefix("-")
    significant = unsigned.replace(".", "").lstrip("0")
    if len(significant) > _DIGITS:
        raise refusal
    return Decimal(unsigned if not significant else text)


def amount_text(amount: Decimal) -> str:
    """Plain digits at the scale the Decimal carries: no exponent, no digit added or dropped."""
    sign, digits, exponent = _carried(amount)
    if exponent < -_MAX_ADJUSTED and digits == "0":
        raise decimal.Underflow("zero scale below -100")
    if exponent >= 0:
        text = digits if digits == "0" else digits + "0" * exponent
    else:
        padded = digits.rjust(1 - exponent, "0")
        text = padded[:exponent] + "." + padded[exponent:]
    return "-" + text if sign else text
