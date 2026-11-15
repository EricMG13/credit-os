"""Display text of a kernel Value and the JSON number token of a Decimal."""

import decimal
from decimal import ROUND_HALF_UP, Context, Decimal

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
