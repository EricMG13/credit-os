"""Value type, operand text and amount text, against the controller's answer key."""

import ast
import dataclasses
import decimal
import json
import re
from collections.abc import Callable
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from credit_os.model.value import (
    Missing,
    MissingCode,
    Value,
    amount_text,
    exact_context,
    parse_operand,
    ratio_context,
)

KEY = json.loads((Path(__file__).parent / "expected" / "pr1.json").read_text("utf-8"))
OPERAND = KEY["operand_text"]
VALUE = KEY["value"]
TEXT = KEY["amount_text"]["cases"]
RAISES = {
    "Inexact": decimal.Inexact,
    "Overflow": decimal.Overflow,
    "Underflow": decimal.Underflow,
    "ValueError": ValueError,
}


def shape(d: Decimal) -> list[object]:
    sign, digits, exponent = d.as_tuple()
    assert isinstance(exponent, int)
    return [sign, "".join(map(str, digits)), exponent]


def stored(text: str) -> Decimal:
    amount = Value(amount=Decimal(text)).amount
    assert amount is not None
    return amount


def run_key_rows() -> list[object]:
    out: list[object] = []
    out += [shape(parse_operand(t)) for t in OPERAND["accepted"]]
    for text in OPERAND["refused"]:
        with pytest.raises(ValueError):
            parse_operand(text)
        out.append("refused")
    out += [shape(stored(t)) for t in VALUE["stored"]]
    for text, name in VALUE["raises"].items():
        with pytest.raises(RAISES[name]) as error:
            Value(amount=Decimal(text))
        out.append(type(error.value).__name__)
    out += [amount_text(Decimal(t)) for t in TEXT]
    return out


@pytest.mark.parametrize("text", list(OPERAND["accepted"]))
def test_operand_accepted(text: str) -> None:
    assert shape(parse_operand(text)) == OPERAND["accepted"][text]


@pytest.mark.parametrize("text", OPERAND["refused"])
def test_operand_refused(text: str) -> None:
    with pytest.raises(ValueError) as error:
        parse_operand(text)
    assert str(error.value) == OPERAND["refused_message"]


@pytest.mark.parametrize("text", list(VALUE["stored"]))
def test_value_stored(text: str) -> None:
    assert shape(stored(text)) == VALUE["stored"][text]


@pytest.mark.parametrize("text", list(VALUE["raises"]))
def test_value_raises(text: str) -> None:
    expected = RAISES[VALUE["raises"][text]]
    with pytest.raises(expected) as error:
        Value(amount=Decimal(text))
    assert type(error.value) is expected


@pytest.mark.parametrize("text", list(VALUE["raises"]))
def test_amount_text_refuses_like_value(text: str) -> None:
    expected = RAISES[VALUE["raises"][text]]
    with pytest.raises(expected) as error:
        amount_text(Decimal(text))
    assert type(error.value) is expected


@pytest.mark.parametrize("text", list(TEXT))
def test_amount_text_cases(text: str) -> None:
    assert amount_text(Decimal(text)) == TEXT[text]


class Sub(Decimal):
    pass


GOOD = Missing(MissingCode.NOT_SOURCED, "x")


@pytest.mark.parametrize("bad", [1.5, 1, True, "1", Sub("1")])
def test_value_refuses_wrong_amount_type(bad: Any) -> None:
    with pytest.raises(TypeError):
        Value(amount=bad)


def test_value_one_of_two() -> None:
    text: Any = "NOT_SOURCED"
    with pytest.raises(ValueError):
        Value(amount=Decimal(1), missing=GOOD)
    with pytest.raises(ValueError):
        Value()
    with pytest.raises(TypeError):
        Value(missing=text)
    assert Value(missing=GOOD).amount is None


@pytest.mark.parametrize(
    ("code", "text", "error"),
    [
        ("NOT_SOURCED", "x", TypeError),
        (MissingCode.NOT_SOURCED, 5, TypeError),
        (MissingCode.NOT_SOURCED, b"x", TypeError),
        (MissingCode.NOT_SOURCED, "", ValueError),
        (MissingCode.NOT_SOURCED, " \t\n", ValueError),
    ],
)
def test_missing_refusals(code: Any, text: Any, error: type[Exception]) -> None:
    with pytest.raises(error):
        Missing(code, text)


@pytest.mark.parametrize("bad", [None, 5, 1.5, b"5", Decimal(5)])
def test_parse_operand_refuses_non_str(bad: Any) -> None:
    with pytest.raises(TypeError):
        parse_operand(bad)


def test_value_frozen_and_equal() -> None:
    value: Any = Value(Decimal("1.50"))
    with pytest.raises(dataclasses.FrozenInstanceError):
        value.amount = Decimal(2)
    for a, b in [("1.50", "1.5"), ("-0", "0")]:
        assert Value(Decimal(a)) == Value(Decimal(b))
        assert hash(Value(Decimal(a))) == hash(Value(Decimal(b)))
    assert Value(Decimal(1)) != Value(Decimal(2))


def check_context(make: Callable[[], decimal.Context]) -> None:
    c = make()
    assert (c.prec, c.rounding) == (38, decimal.ROUND_HALF_EVEN)
    assert (c.Emax, c.Emin, c.capitals, c.clamp) == (999999, -999999, 1, 0)
    assert not any(c.flags.values())
    on = {decimal.InvalidOperation, decimal.DivisionByZero, decimal.Overflow}
    if make is exact_context:
        on.add(decimal.Inexact)
    assert {s for s, v in c.traps.items() if v} == on
    assert make() is not c
    c.prec = 5
    assert make().prec == 38


@pytest.mark.parametrize("make", [ratio_context, exact_context])
def test_contexts(make: Callable[[], decimal.Context]) -> None:
    check_context(make)
    with decimal.localcontext(decimal.Context(prec=5, rounding=decimal.ROUND_UP, Emax=9)):
        check_context(make)


@pytest.mark.parametrize("make", [ratio_context, exact_context])
def test_contexts_ignore_changed_default_context(make: Callable[[], decimal.Context]) -> None:
    d = decimal.DefaultContext
    saved = (
        d.prec,
        d.rounding,
        d.Emax,
        d.Emin,
        d.clamp,
        d.flags.copy(),
        d.traps.copy(),
        d.capitals,
    )
    try:
        d.prec, d.rounding, d.Emax, d.Emin, d.clamp = 7, decimal.ROUND_DOWN, 50, -20, 1
        d.capitals = 0
        d.flags[decimal.Inexact] = True
        d.traps[decimal.Underflow] = True
        check_context(make)
    finally:
        d.prec, d.rounding, d.Emax, d.Emin, d.clamp = saved[:5]
        d.flags.update(saved[5])
        d.traps.update(saved[6])
        d.capitals = saved[7]


def test_hostile_ambient_context() -> None:
    outside = run_key_rows()
    with decimal.localcontext(decimal.Context(prec=5, rounding=decimal.ROUND_UP)):
        assert run_key_rows() == outside


def build(sign: int, coefficient: int, exponent: int) -> Decimal:
    return Decimal((sign, tuple(map(int, str(coefficient))), exponent))


@given(
    st.integers(0, 1),
    st.integers(0, 10**38 - 1),
    st.integers(-60, 60),
)
def test_amount_text_property(sign: int, coefficient: int, exponent: int) -> None:
    x = build(sign, coefficient, exponent)
    text = amount_text(x)
    oracle = Fraction((-1) ** sign * coefficient) * Fraction(10) ** exponent
    assert Fraction(text) == oracle
    assert re.fullmatch(r"-?(0|[1-9][0-9]*)(\.[0-9]+)?", text)
    assert not re.fullmatch(r"-0(\.0*)?", text)
    assert len(text.partition(".")[2]) == max(-exponent, 0)
    stored = Value(amount=x).amount
    assert stored is not None
    assert not re.search(r"\.[0-9]*0$", amount_text(stored))
    printed_digits = len(str(coefficient)) + max(exponent, 0)
    assume(len(text) <= 64 and printed_digits <= 38)
    assert parse_operand(text) == x


@pytest.mark.parametrize("zero", ["-0", "-0E+3", "0E+3"])
def test_zero_text_has_no_sign_or_exponent(zero: str) -> None:
    assert amount_text(Decimal(zero)) == "0"


@pytest.mark.parametrize("zero", ["0E-101", "-0E-100000"])
def test_zero_text_is_bounded(zero: str) -> None:
    assert amount_text(Decimal("0E-100")) == "0." + "0" * 100
    with pytest.raises(decimal.Underflow) as error:
        amount_text(Decimal(zero))
    assert type(error.value) is decimal.Underflow
    assert Value(amount=Decimal(zero)).amount == 0


class StrSub(str):
    pass


def test_str_subclasses_refused() -> None:
    with pytest.raises(TypeError):
        parse_operand(StrSub("5"))
    with pytest.raises(TypeError):
        Missing(MissingCode.NOT_SOURCED, StrSub("x"))


def test_operand_refuses_amount_text_of_39_digits() -> None:
    with pytest.raises(ValueError):
        parse_operand(amount_text(Decimal("1E+38")))


@given(st.integers(0, 1), st.integers(10**37, 10**60), st.integers(1, 9), st.integers(-60, 60))
def test_too_many_digits_inexact(sign: int, head: int, last: int, exponent: int) -> None:
    x = build(sign, head * 10 + last, exponent)
    with pytest.raises(decimal.Inexact) as error:
        Value(amount=x)
    assert type(error.value) is decimal.Inexact


def test_no_float_in_model_layer() -> None:
    root = Path(__file__).parents[2] / "src" / "credit_os" / "model"
    files = list(root.rglob("*.py"))
    assert files
    for path in files:
        for node in ast.walk(ast.parse(path.read_text("utf-8"))):
            assert not (isinstance(node, ast.Constant) and isinstance(node.value, float))
            assert not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "float"
            )
            assert not (isinstance(node, ast.Import) and any(a.name == "math" for a in node.names))
            assert not (isinstance(node, ast.ImportFrom) and node.module == "math")
