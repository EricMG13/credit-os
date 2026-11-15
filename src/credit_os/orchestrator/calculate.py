"""The calculate tool (D10, D11): the model asks, the Decimal kernel answers.

The operands are plain decimal strings or null. This module checks the shape of what the model
sent and turns the kernel's `Value` into one line of JSON; the arithmetic is the kernel's."""

import decimal
import json

from credit_os.model.arithmetic import difference, product, ratio, total
from credit_os.model.value import (
    OPERAND_REFUSED,
    Missing,
    MissingCode,
    Value,
    amount_text,
    parse_operand,
)
from credit_os.provider.types import ToolSpec

_ARITY = {"sum": (1, 128), "difference": (2, 2), "product": (2, 128), "ratio": (2, 2)}
_NEEDS = {
    "sum": "sum needs 1 to 128 operands",
    "difference": "difference needs 2 operands",
    "product": "product needs 2 to 128 operands",
    "ratio": "ratio needs 2 operands",
}
_NULL_OPERAND = Missing(MissingCode.NOT_SOURCED, "an operand was null: it is not sourced")
_NON_POSITIVE = "the denominator is zero or negative"

CALCULATE = ToolSpec(
    name="calculate",
    description=(
        "Exact decimal arithmetic: operation sum, difference, product or ratio over values. "
        "Each operand is a plain decimal string such as -1234.5, or null. A null is missing, "
        "never zero, and the result is then missing. Results keep at most 38 significant "
        "digits and are never rounded, except a ratio, a fraction rounded half to even."
    ),
    parameters={
        "type": "object",
        "properties": {
            "operation": {"type": "string", "enum": ["sum", "difference", "product", "ratio"]},
            "values": {
                "type": "array",
                "minItems": 1,
                "maxItems": 128,
                "items": {"type": ["string", "null"]},
            },
        },
        "required": ["operation", "values"],
        "additionalProperties": False,
    },
)


def _error(text: str) -> str:
    return "ERROR: " + text


def _operand(index: int, item: object) -> Value | str:
    """The operand as a `Value`, or the error line for it."""
    if item is None:
        return Value(missing=_NULL_OPERAND)
    if type(item) is not str:
        return _error(f"values[{index}]: an operand is a decimal string or null")
    try:
        return Value(amount=parse_operand(item))
    except ValueError:
        return _error(f"values[{index}]: {OPERAND_REFUSED}")


def _operands(items: list[object]) -> list[Value] | str:
    operands: list[Value] = []
    for index, item in enumerate(items):
        operand = _operand(index, item)
        if isinstance(operand, str):
            return operand
        operands.append(operand)
    return operands


def _apply(operation: str, operands: list[Value]) -> Value:
    if operation == "sum":
        return total(operands)
    if operation == "product":
        return product(operands)
    if operation == "difference":
        return difference(operands[0], operands[1])
    return ratio(operands[0], operands[1], non_positive=_NON_POSITIVE)


def _text(result: Value) -> str:
    if result.amount is not None:
        return json.dumps({"value": amount_text(result.amount), "reason": None})
    code = result.missing.code.value if result.missing is not None else None
    return json.dumps({"value": None, "reason": code})


def calculate(arguments: object) -> str:
    """Run one calculation for the model: JSON text on success, one `ERROR: ` line otherwise."""
    if type(arguments) is not dict or set(arguments) != {"operation", "values"}:
        return _error("calculate takes exactly operation and values")
    operation = arguments["operation"]
    if type(operation) is not str or operation not in _ARITY:
        return _error("operation must be one of sum, difference, product, ratio")
    items = arguments["values"]
    if type(items) is not list:
        return _error("values must be a list of decimal strings or null")
    low, high = _ARITY[operation]
    if not low <= len(items) <= high:
        return _error(_NEEDS[operation])
    operands = _operands(items)
    if isinstance(operands, str):
        return operands
    try:
        result = _apply(operation, operands)
    except decimal.Inexact:
        return _error(
            f"{operation} result needs more than 38 significant digits or is out of range"
        )
    return _text(result)
