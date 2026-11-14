"""Codecs between Python values and what the store keeps: money, time, event detail.

None is missing and stays None; it is never zero. A bad value on write is StoreRefused, a bad
stored value on read is StoreCorrupt. No message contains the value: it names the rule broken
and the value's type, because the input may be hostile or huge.
"""

import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import cast

from credit_os.store.errors import StoreCorrupt, StoreRefused, safe_text

_MONEY_TEXT = re.compile(r"(0|[1-9][0-9]*)(\.[0-9]+)?")
_TIME_TEXT = re.compile(
    r"([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})\.([0-9]{6})Z"
)
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_MONEY_MAXIMUM_CHARACTERS = 64
_MONEY_MAXIMUM_DIGITS = 64
_MONEY_EXPONENTS = range(-62, 64)
_INT_MINIMUM = -(2**63)
_INT_MAXIMUM = 2**63 - 1

DetailValue = str | int | None


def money_to_text(value: Decimal | None) -> str | None:
    """Return the plain, unrounded text of a finite unsigned Decimal; None stays None."""
    if value is None:
        return None
    if type(value) is not Decimal:
        raise StoreRefused(f"money must be a Decimal, got {type(value).__name__}")
    if not value.is_finite():
        raise StoreRefused("money must be finite")
    if value.is_signed():
        raise StoreRefused("money must be unsigned")
    _, digits, exponent = value.as_tuple()
    if len(digits) > _MONEY_MAXIMUM_DIGITS or exponent not in _MONEY_EXPONENTS:
        raise StoreRefused("money has more than 64 digits or an exponent outside -62..63")
    text = format(value, "f")
    if len(text) > _MONEY_MAXIMUM_CHARACTERS:
        raise StoreRefused("money text is longer than 64 characters")
    return text


def money_from_text(stored: object) -> Decimal | None:
    """Return the Decimal of stored money text, keeping its exponent; None stays None."""
    if stored is None:
        return None
    if isinstance(stored, str) and len(stored) > _MONEY_MAXIMUM_CHARACTERS:
        raise StoreCorrupt("stored money is longer than 64 characters (str)")
    if not isinstance(stored, str) or _MONEY_TEXT.fullmatch(stored) is None:
        raise StoreCorrupt(
            f"stored money is not plain digits with an optional fraction ({type(stored).__name__})"
        )
    return Decimal(stored)


def _require_valid_offset(value: datetime) -> None:
    try:
        offset = value.utcoffset()
    except ValueError:
        raise StoreRefused("time zone offset is not valid") from None
    if offset is None:
        raise StoreRefused("time must be timezone-aware")


def _instant(value: datetime | float) -> datetime:
    if isinstance(value, bool) or not isinstance(value, datetime | int | float):
        raise StoreRefused(f"time must be a datetime or epoch seconds, got {type(value).__name__}")
    if isinstance(value, datetime):
        _require_valid_offset(value)
    try:
        if isinstance(value, datetime):
            return value.astimezone(UTC)
        return _EPOCH + timedelta(seconds=value)
    except (OverflowError, ValueError):
        raise StoreRefused("time is outside years 0001 to 9999 or not a number") from None


def time_to_text(value: datetime | float | None) -> str | None:
    """Return YYYY-MM-DDTHH:MM:SS.ffffffZ in UTC for an aware datetime or epoch seconds."""
    if value is None:
        return None
    t = _instant(value)
    return (
        f"{t.year:04d}-{t.month:02d}-{t.day:02d}T"
        f"{t.hour:02d}:{t.minute:02d}:{t.second:02d}.{t.microsecond:06d}Z"
    )


def time_from_text(stored: object) -> datetime | None:
    """Return the aware UTC datetime of stored time text; None stays None."""
    if stored is None:
        return None
    match = _TIME_TEXT.fullmatch(stored) if isinstance(stored, str) else None
    if match is None:
        raise StoreCorrupt(
            f"stored time is not YYYY-MM-DDTHH:MM:SS.ffffffZ ({type(stored).__name__})"
        )
    year, month, day, hour, minute, second, micro = (int(part) for part in match.groups())
    try:
        return datetime(year, month, day, hour, minute, second, micro, tzinfo=UTC)
    except ValueError:
        raise StoreCorrupt("stored time names no real instant") from None


def _detail_value(value: object) -> DetailValue:
    if isinstance(value, bool) or not isinstance(value, str | int | None):
        raise StoreRefused(f"detail values must be str, int or None, got {type(value).__name__}")
    if isinstance(value, int) and not _INT_MINIMUM <= value <= _INT_MAXIMUM:
        raise StoreRefused("detail int is outside 64 signed bits")
    return safe_text(value) if isinstance(value, str) else value


def detail_to_text(detail: Mapping[str, DetailValue]) -> str:
    """Return the canonical ASCII JSON object text of an event's detail."""
    if not isinstance(detail, Mapping):
        raise StoreRefused(f"detail must be a mapping, got {type(detail).__name__}")
    clean: dict[str, DetailValue] = {}
    for name, value in detail.items():
        if not isinstance(name, str):
            raise StoreRefused(f"detail keys must be str, got {type(name).__name__}")
        escaped = safe_text(name)
        if escaped in clean:
            raise StoreRefused("detail keys collide after escaping")
        clean[escaped] = _detail_value(value)
    return json.dumps(
        clean, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False
    )


def detail_from_text(stored: object) -> dict[str, DetailValue]:
    """Return the detail mapping of stored text that is exactly the writer's canonical text."""
    if not isinstance(stored, str):
        raise StoreCorrupt(f"stored detail is not text ({type(stored).__name__})")
    try:
        parsed = json.loads(stored)
        canonical = isinstance(parsed, dict) and detail_to_text(parsed) == stored
    except (StoreRefused, ValueError, RecursionError):
        canonical = False
    if not canonical:
        raise StoreCorrupt(
            f"stored detail is not the canonical text of a detail mapping ({type(stored).__name__})"
        )
    return cast(dict[str, DetailValue], parsed)
