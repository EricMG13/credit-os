"""Display text of a kernel Value and the JSON number token of a Decimal."""

from decimal import ROUND_HALF_UP, Context, Decimal

from credit_os.model.value import Value, _carried, amount_text

_MAX_PLACES = 6
# A stored amount has at most 38 digits and an adjusted exponent within +/-100;
# rounding to 6 places adds at most one digit, so 400 never rounds or traps.
_WIDE = Context(prec=400, rounding=ROUND_HALF_UP, traps=[])


def display_text(value: Value, places: int) -> str | None:
    """Half-up rounded text with grouped thousands; None for a missing value."""
    if type(value) is not Value:
        raise TypeError("value must be a Value")
    if type(places) is not int:
        raise TypeError("places must be an int")
    if not 0 <= places <= _MAX_PLACES:
        raise ValueError("places must be 0..6")
    if value.amount is None:
        return None
    rounded = value.amount.quantize(Decimal(1).scaleb(-places), context=_WIDE)
    digits = amount_text(rounded.copy_abs()).replace(".", "")
    whole = digits[: len(digits) - places] if places else digits
    grouped = f"{int(whole):,}"
    text = grouped + "." + digits[len(digits) - places :] if places else grouped
    return "-" + text if rounded < 0 else text


def json_number(amount: Decimal) -> str:
    """Plain-digit JSON number token: no exponent, no trailing fraction zeros."""
    _carried(amount)
    if amount == 0:
        return "0"
    text = amount_text(amount)
    return text.rstrip("0").rstrip(".") if "." in text else text
