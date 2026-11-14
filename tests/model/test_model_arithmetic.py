"""Sum, difference, product, ratio and the two rounding comparisons, against the answer key."""

import decimal
import itertools
import json
import math
from collections.abc import Callable, Iterator
from decimal import Context, Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from credit_os.model.arithmetic import (
    beyond_rounding,
    difference,
    half_unit,
    product,
    ratio,
    total,
)
from credit_os.model.value import Missing, MissingCode, Value, amount_text

KEY = json.loads((Path(__file__).parent / "expected" / "pr1.json").read_text("utf-8"))
RAISES = {"Inexact": decimal.Inexact, "Overflow": decimal.Overflow, "Underflow": decimal.Underflow}
NON_POSITIVE = KEY["ratio"]["non_positive"]
SECTIONS = ("total", "difference", "product", "ratio", "half_unit", "beyond_rounding")


def build(item: Any) -> Value:
    if isinstance(item, str):
        return Value(amount=Decimal(item))
    return Value(missing=Missing(MissingCode(item["code"]), item["text"]))


def call(section: str, operands: list[Value]) -> Value:
    if section == "total":
        return total(operands)
    if section == "product":
        return product(operands)
    if section == "difference":
        return difference(*operands)
    return ratio(*operands, non_positive=NON_POSITIVE)


def rows(section: str) -> list[dict[str, Any]]:
    data = KEY[section]
    out: list[dict[str, Any]] = data["cases"] if isinstance(data, dict) else data
    return out


def orders(section: str, operands: list[Value]) -> Iterator[list[Value]]:
    if section in ("total", "product"):
        yield from (list(p) for p in itertools.permutations(operands))
    else:
        yield operands


def outcome(section: str, operands: list[Value]) -> tuple[object, ...]:
    try:
        result = call(section, operands)
    except decimal.DecimalException as error:
        return ("raises", type(error).__name__)
    if result.missing is not None:
        return ("missing", result.missing.code.value, result.missing.text)
    assert result.amount is not None
    return ("amount", amount_text(result.amount))


def expected(row: dict[str, Any]) -> tuple[object, ...]:
    if "raises" in row:
        return ("raises", row["raises"])
    if "missing" in row:
        return ("missing", row["missing"]["code"], row["missing"]["text"])
    return ("amount", row["amount"])


def op_rows() -> list[tuple[str, dict[str, Any]]]:
    return [(s, r) for s in ("total", "difference", "product", "ratio") for r in rows(s)]


@pytest.mark.parametrize(("section", "row"), op_rows())
def test_key_rows_in_every_order(section: str, row: dict[str, Any]) -> None:
    operands = [build(o) for o in row["operands"]]
    for order in orders(section, operands):
        if "raises" in row:
            with pytest.raises(decimal.DecimalException) as error:
                call(section, order)
            assert type(error.value) is RAISES[row["raises"]]
            continue
        result = call(section, order)
        if "missing" in row:
            first = next((v for v in order if v.missing is not None), None)
            assert result.amount is None
            if first is None:
                assert result.missing == build(row["missing"]).missing
            else:
                assert result is first
                if order == operands:
                    assert result.missing == build(row["missing"]).missing
            continue
        assert result.amount is not None
        assert amount_text(result.amount) == row["amount"]
        assert result.missing is None


def half_shape(d: Decimal) -> tuple[Any, ...]:
    return d.as_tuple()[1:]


def all_key_outcomes() -> list[object]:
    out: list[object] = []
    for section, row in op_rows():
        operands = [build(o) for o in row["operands"]]
        out += [outcome(section, order) for order in orders(section, operands)]
    for row in rows("half_unit"):
        out.append(half_shape(half_unit(Decimal(a) for a in row["amounts"])))
    for row in rows("beyond_rounding"):
        printed = None if row["printed"] is None else (Decimal(p) for p in row["printed"])
        out.append(beyond_rounding(Decimal(row["stated"]), Decimal(row["host"]), printed))
    return out


def test_every_key_row_matches_exactly() -> None:
    for section, row in op_rows():
        operands = [build(o) for o in row["operands"]]
        for order in orders(section, operands):
            got = outcome(section, order)
            if "missing" in row:
                assert got[0] == "missing"
            else:
                assert got == expected(row)
    for row in rows("half_unit"):
        amounts = [Decimal(a) for a in row["amounts"]]
        assert half_unit(amounts).as_tuple() == Decimal(row["half"]).as_tuple()
        assert half_unit(a for a in amounts).as_tuple() == Decimal(row["half"]).as_tuple()
    for row in rows("beyond_rounding"):
        stated, host = Decimal(row["stated"]), Decimal(row["host"])
        printed = None if row["printed"] is None else [Decimal(p) for p in row["printed"]]
        assert beyond_rounding(stated, host, printed) is row["beyond"]
        generated = None if printed is None else (p for p in printed)
        assert beyond_rounding(stated, host, generated) is row["beyond"]


def wrong(x: Any) -> Any:
    return x


def test_empty_and_wrong_types() -> None:
    for fn in (total, product):
        with pytest.raises(ValueError):
            fn([])
        with pytest.raises(ValueError):
            fn(())
        with pytest.raises(TypeError):
            fn(wrong([Decimal(1)]))
        with pytest.raises(TypeError):
            wrong(fn)("12")
        with pytest.raises(TypeError):
            wrong(fn)("")
    one = Value(amount=Decimal("1.5"))
    assert total([one]) == one
    assert product([one]) == one
    with pytest.raises(TypeError):
        difference(wrong(Decimal(1)), one)
    with pytest.raises(TypeError):
        ratio(one, wrong(Decimal(1)), non_positive="x")


def test_ratio_non_positive_text() -> None:
    one = Value(amount=Decimal(1))
    for text in ("", "  "):
        with pytest.raises(ValueError):
            ratio(one, one, non_positive=text)
        with pytest.raises(ValueError):
            ratio(Value(missing=Missing(MissingCode.NOT_SOURCED, "n")), one, non_positive=text)
    with pytest.raises(TypeError):
        wrong(ratio)(one, one)
    with pytest.raises(TypeError):
        ratio(one, one, non_positive=wrong(5))


@pytest.mark.parametrize("bad", [1.5, 1, Decimal("NaN"), Decimal("Infinity"), "1"])
def test_half_unit_and_beyond_refuse_bad_amounts(bad: Any) -> None:
    good = Decimal(1)
    error = ValueError if isinstance(bad, Decimal) else TypeError
    for call_ in (
        lambda: half_unit([bad]),
        lambda: beyond_rounding(bad, good),
        lambda: beyond_rounding(good, bad),
        lambda: beyond_rounding(good, good, [bad]),
    ):
        with pytest.raises(error):
            call_()


def test_beyond_rounding_refuses_an_inexact_difference() -> None:
    with pytest.raises(decimal.Inexact):
        beyond_rounding(Decimal(12345678901234567890123456789012345678), Decimal("0.1"))


HOSTILE = [
    Context(prec=5, rounding=decimal.ROUND_UP),
    Context(prec=1, rounding=decimal.ROUND_DOWN, traps=[], flags=[], Emax=5, Emin=-5),
]


@pytest.mark.parametrize("hostile", HOSTILE)
def test_ambient_context_changes_nothing(hostile: Context) -> None:
    baseline = all_key_outcomes()
    with decimal.localcontext(hostile) as ambient:
        before = (ambient.prec, ambient.rounding)
        assert all_key_outcomes() == baseline
        assert (ambient.prec, ambient.rounding) == before


def test_default_context_changes_nothing() -> None:
    baseline = all_key_outcomes()
    default = decimal.DefaultContext
    old = (default.prec, default.rounding, default.Emax, default.Emin, default.clamp)
    default.prec, default.rounding = 3, decimal.ROUND_UP
    default.Emax, default.Emin, default.clamp = 7, -7, 1
    try:
        with decimal.localcontext(Context()):
            assert all_key_outcomes() == baseline
    finally:
        default.prec, default.rounding, default.Emax, default.Emin, default.clamp = old


# ---- properties: Fraction is the oracle ------------------------------------------------------


def decs(exp: int, digits: int = 38) -> st.SearchStrategy[Decimal]:
    return st.builds(
        lambda c, e: Decimal(c).scaleb(e, Context(prec=100, Emin=-999, Emax=999)),
        st.integers(-(10**digits) + 1, 10**digits - 1),
        st.integers(-exp, exp),
    )


def fits(q: Fraction) -> bool:
    if q == 0:
        return True
    digits = 0
    n, d = q.numerator, q.denominator
    if d != 1:
        while d % 2 == 0:
            d //= 2
            n *= 5
        while d % 5 == 0:
            d //= 5
            n *= 2
        if d != 1:
            return False
        scale = 0
        while Fraction(q * 10**scale).denominator != 1:
            scale += 1
        n = int(q * 10**scale)
        exponent = -scale
    else:
        n, exponent = q.numerator, 0
    n = abs(n)
    while n % 10 == 0:
        n //= 10
        exponent += 1
    digits = len(str(n))
    adjusted = exponent + digits - 1
    return digits <= 38 and -100 <= adjusted <= 100


def check(section_fn: Callable[[], Value], exact: Fraction) -> tuple[object, ...]:
    if fits(exact):
        result = section_fn()
        assert result.amount is not None
        assert Fraction(result.amount) == exact
        return ("amount", exact)
    with pytest.raises(decimal.DecimalException) as error:
        section_fn()
    return ("raises", type(error.value))


def val(d: Decimal) -> Value:
    return Value(amount=d)


def safe(d: Decimal) -> bool:
    try:
        val(d)
    except decimal.DecimalException:
        return False
    return True


def agree(
    fn: Callable[[list[Value]], Value], exact: Fraction, one: list[Decimal], two: list[Decimal]
) -> None:
    first = check(lambda: fn([val(d) for d in one]), exact)
    assert first == check(lambda: fn([val(d) for d in two]), exact)


@settings(max_examples=200, deadline=None)
@given(st.lists(decs(8), min_size=1, max_size=6), st.data())
def test_total_and_product_ignore_order(items: list[Decimal], data: st.DataObject) -> None:
    perm = data.draw(st.permutations(items))
    for fn, fold in ((total, sum), (product, math.prod)):
        agree(fn, Fraction(fold([Fraction(d) for d in items])), items, perm)


@settings(max_examples=200, deadline=None)
@given(decs(8), decs(8))
def test_difference_and_product_are_exact_or_refused(a: Decimal, b: Decimal) -> None:
    check(lambda: difference(val(a), val(b)), Fraction(a) - Fraction(b))
    check(lambda: product([val(a), val(b)]), Fraction(a) * Fraction(b))


@settings(max_examples=200, deadline=None)
@given(decs(8), decs(8))
def test_difference_is_total_with_negation(a: Decimal, b: Decimal) -> None:
    def attempt(fn: Callable[[], Value]) -> Value | None:
        try:
            return fn()
        except decimal.DecimalException:
            return None

    left = attempt(lambda: difference(val(a), val(b)))
    right = attempt(lambda: total([val(a), val(b.copy_negate())]))
    assert left == right


@settings(max_examples=200, deadline=None)
@given(decs(20), decs(20), st.booleans())
def test_ratio_is_nearest_38_digits(n: Decimal, d: Decimal, flip: bool) -> None:
    d = abs(d) if not flip else abs(d) + 1
    assume(d != 0)
    result = ratio(val(n), val(d), non_positive="np")
    assert result.amount is not None
    quotient = Fraction(n) / Fraction(d)
    r = result.amount
    if r != 0:
        assert abs(Fraction(r) - quotient) <= Fraction(1, 2) * Fraction(10) ** (r.adjusted() - 37)
    assert (r == 0) == (n == 0)


@settings(max_examples=200, deadline=None)
@given(decs(20), decs(20))
def test_ratio_non_positive_denominator_is_missing(n: Decimal, d: Decimal) -> None:
    result = ratio(val(n), val(-abs(d)), non_positive="np")
    assert result.amount is None
    assert result.missing == Missing(MissingCode.ZERO_OR_NEGATIVE_DENOMINATOR, "np")
