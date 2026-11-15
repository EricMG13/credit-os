"""The bytes of `data.js`: the envelope value as the one script the library page loads.

The script is `window.CREDIT_OS_DATA = JSON.parse("...");` in ASCII. The inner JSON is
written by a small emitter here (never `json.dumps` on the whole value, which cannot write
a `Decimal` exactly and would accept a float). Nothing is written to disk. A refusal names
the rule only, never a value or a key.
"""

from collections.abc import Mapping
from decimal import Decimal
from typing import Final

from credit_os.delivery.errors import DeliveryRefused
from credit_os.model.display import json_number

MAX_BYTES: Final = 16 * 1024 * 1024
SCHEMA: Final = "credit-os-data/1"
MAX_INT: Final = 2**53 - 1
PREFIX: Final = "window.CREDIT_OS_DATA = JSON.parse("
SUFFIX: Final = ");\n"
SHORT_ESCAPES: Final = {
    "\b": "\\b",
    "\f": "\\f",
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
    '"': '\\"',
    "\\": "\\\\",
}


def envelope(issuers: object, library: object, model: object) -> dict[str, object]:
    """The value `data.js` carries; `run` and `signal` are never written."""
    return {"schema": SCHEMA, "issuers": issuers, "library": library, "model": model}


def check_size(size: int) -> None:
    """Refuse a script above the cap; the message states both numbers."""
    if size > MAX_BYTES:
        raise DeliveryRefused(f"data.js is {size} bytes, above the {MAX_BYTES} byte cap")


def _string(text: str) -> str:
    """A JSON string literal; every character outside the required escapes stays as it is."""
    parts = ['"']
    for char in text:
        code = ord(char)
        if 0xD800 <= code <= 0xDFFF:
            raise DeliveryRefused("a string holds a lone surrogate")
        if char in SHORT_ESCAPES:
            parts.append(SHORT_ESCAPES[char])
        elif code < 0x20:
            parts.append(f"\\u{code:04x}")
        else:
            parts.append(char)
    parts.append('"')
    return "".join(parts)


def _number(value: object) -> str | None:
    """The token for an int, bool or Decimal; None when the value is none of them."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        if abs(value) > MAX_INT:
            raise DeliveryRefused("an int is outside the 2^53 - 1 bound")
        return str(value)
    if isinstance(value, Decimal):
        try:
            return json_number(value)
        except ValueError as bound:
            raise DeliveryRefused("a Decimal is outside the value bounds") from bound
    return None


def _mapping(value: Mapping[object, object]) -> str:
    members = []
    for key, item in value.items():
        if not isinstance(key, str):
            raise DeliveryRefused("a mapping key is not a str")
        members.append(_string(key) + ":" + _emit(item))
    return "{" + ",".join(members) + "}"


def _emit(value: object) -> str:
    """The compact JSON text of one value, or a refusal."""
    if value is None:
        return "null"
    if isinstance(value, str):
        return _string(value)
    number = _number(value)
    if number is not None:
        return number
    if isinstance(value, float):
        raise DeliveryRefused("a float is not allowed")
    if isinstance(value, Mapping):
        return _mapping(value)
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_emit(item) for item in value) + "]"
    raise DeliveryRefused("a value has a type the writer does not accept")


def _literal(text: str) -> str:
    """The text as a JSON string literal in ASCII, with `<` written as an escape."""
    parts = ['"']
    for char in text:
        code = ord(char)
        if char in SHORT_ESCAPES:
            parts.append(SHORT_ESCAPES[char])
        elif char == "<":
            parts.append("\\u003c")
        elif code < 0x20:
            parts.append(f"\\u{code:04x}")
        elif code < 0x80:
            parts.append(char)
        elif code < 0x10000:
            parts.append(f"\\u{code:04x}")
        else:
            high, low = divmod(code - 0x10000, 0x400)
            parts.append(f"\\u{0xD800 + high:04x}\\u{0xDC00 + low:04x}")
    parts.append('"')
    return "".join(parts)


def data_js(value: Mapping[str, object]) -> bytes:
    """The exact ASCII bytes of `data.js` for the envelope value."""
    body = (PREFIX + _literal(_emit(value)) + SUFFIX).encode("ascii")
    check_size(len(body))
    return body
