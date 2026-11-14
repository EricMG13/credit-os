"""Find the forecast block of a handoff, read it as strict JSON, recognise a declined block."""

import json
from typing import Any

from credit_os.handoff.data import read_data_sections
from credit_os.handoff.document import HandoffDocument
from credit_os.handoff.errors import echo
from credit_os.model.refusals import ForecastDeclined, ForecastRefused, RefusalKind

MAX_NESTING = 64
MAX_CHARACTERS = 200_000
MAX_INTEGER_DIGITS = 15
_SUBJECT = "forecast inputs"
_BLOCK = "the `Forecast inputs` section needs exactly one closed fenced json block"
_FRACTION = (
    "the forecast inputs block states the number {} with a fraction or an exponent: "
    "write amounts, rates and shares as strings"
)


def _refuse(kind: RefusalKind, message: str) -> ForecastRefused:
    return ForecastRefused(kind, _SUBJECT, message)


def forecast_block(document: HandoffDocument) -> str:
    found = [item for item in read_data_sections(document) if item.kind == "forecast"]
    if len(found) != 1:
        message = f"needs exactly one `Forecast inputs` section, found {len(found)}"
        raise _refuse(RefusalKind.BLOCK, message)
    text = found[0].text
    if text is None:
        raise _refuse(RefusalKind.BLOCK, _BLOCK)
    return text


def _too_deep(text: str) -> bool:
    depth = 0
    in_string = escaped = False
    for char in text:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char in "[{":
            depth += 1
            if depth > MAX_NESTING:
                return True
        elif char in "]}":
            depth -= 1
    return False


def _fraction(token: str) -> Any:
    raise _refuse(RefusalKind.JSON, _FRACTION.format(echo(token)))


def _constant(token: str) -> Any:
    message = f"the forecast inputs block states {echo(token)}, which is not a number"
    raise _refuse(RefusalKind.JSON, message)


def _integer(token: str) -> int:
    if len(token.lstrip("-")) > MAX_INTEGER_DIGITS:
        message = "the forecast inputs block states an integer of more than 15 digits"
        raise _refuse(RefusalKind.JSON, message)
    return int(token)


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            message = f"the forecast inputs block repeats the key `{echo(key)}`"
            raise _refuse(RefusalKind.JSON, message)
        result[key] = value
    return result


def _has_surrogate(value: object) -> bool:
    if isinstance(value, str):
        return any("\ud800" <= char <= "\udfff" for char in value)
    if isinstance(value, dict):
        return any(_has_surrogate(key) or _has_surrogate(item) for key, item in value.items())
    if isinstance(value, list):
        return any(_has_surrogate(item) for item in value)
    return False


def read_object(text: str) -> dict[str, object]:
    if not isinstance(text, str):
        raise TypeError("text must be a str")
    if len(text) > MAX_CHARACTERS:
        raise _refuse(
            RefusalKind.JSON,
            f"the forecast inputs block is longer than {MAX_CHARACTERS} characters",
        )
    if _too_deep(text):
        raise _refuse(
            RefusalKind.JSON, f"the forecast inputs block nests deeper than {MAX_NESTING} levels"
        )
    try:
        value = json.loads(
            text,
            parse_float=_fraction,
            parse_int=_integer,
            parse_constant=_constant,
            object_pairs_hook=_object,
        )
    except json.JSONDecodeError as error:
        raise _refuse(RefusalKind.JSON, "the forecast inputs block is not valid JSON") from error
    if not isinstance(value, dict):
        raise _refuse(RefusalKind.JSON, "the forecast inputs block is not a JSON object")
    if _has_surrogate(value):
        raise _refuse(
            RefusalKind.JSON, "the forecast inputs block holds a string that is not valid Unicode"
        )
    return value


def _all_null(driver: object) -> bool:
    if not isinstance(driver, dict):
        return False
    values = driver.get("values")
    return isinstance(values, list) and bool(values) and all(v is None for v in values)


def check_declined(document: dict[str, object]) -> None:
    drivers = document.get("base_drivers")
    if not isinstance(drivers, dict) or not drivers:
        return
    if not all(_all_null(driver) for driver in drivers.values()):
        return
    limits = document.get("scope_limits")
    reason = ""
    if isinstance(limits, list) and limits and isinstance(limits[0], str):
        reason = limits[0] if len(limits[0]) <= 200 else limits[0][:197] + "..."
    raise ForecastDeclined(reason)


def read_forecast_document(document: HandoffDocument) -> dict[str, object]:
    result = read_object(forecast_block(document))
    check_declined(result)
    return result
