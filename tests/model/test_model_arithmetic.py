"""Sum, difference, product, ratio and the two rounding comparisons, against the answer key."""

import decimal
import itertools
import json
import math
import sys
from collections.abc import Callable, Iterator
from decimal import Context, Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest
from hypothesis import assume, event, given, settings
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


def test_beyond_rounding_does_not_refuse_a_long_difference() -> None:
    assert beyond_rounding(Decimal(12345678901234567890123456789012345678), Decimal("0.1"))
    assert beyond_rounding(Decimal(3), Decimal("0." + "3" * 38))


def make(c: int, e: int) -> Decimal:
    return Decimal((int(c < 0), tuple(map(int, str(abs(c)))), e))


PARTS = st.tuples(st.integers(-(10**38) + 1, 10**38 - 1), st.integers(-60, 60))


def beyond_oracle(
    a: tuple[int, int], b: tuple[int, int], printed: list[tuple[int, int]] | None
) -> None:
    stated, host = make(*a), make(*b)
    exponents = [a[1], *([b[1]] if printed is None else [e for _, e in printed])]
    limit = Fraction(1, 2) * Fraction(10) ** min(min(exponents), 0)
    expected = abs(Fraction(stated) - Fraction(host)) > limit
    shown = None if printed is None else [make(c, e) for c, e in printed]
    assert beyond_rounding(stated, host, shown) is expected


PRINTED = st.one_of(st.none(), st.lists(PARTS, max_size=3))


@settings(max_examples=200, deadline=None)
@given(PARTS, PARTS, PRINTED)
def test_beyond_rounding_matches_fractions(
    a: tuple[int, int], b: tuple[int, int], printed: list[tuple[int, int]] | None
) -> None:
    beyond_oracle(a, b, printed)


@settings(max_examples=200, deadline=None)
@given(PARTS, st.integers(0, 3), st.integers(-60, 60), PRINTED)
def test_beyond_rounding_near_ties(
    a: tuple[int, int], places: int, nudge: int, printed: list[tuple[int, int]] | None
) -> None:
    """Host within a few units of stated, at a finer place, so ties and near ties occur."""
    scaled = a[0] * 10**places + nudge % 7 - 3
    beyond_oracle(a, (scaled, a[1] - places), printed)


@pytest.mark.parametrize(
    ("stated", "host", "printed", "beyond"),
    [("1.5", "1.50", None, False), ("1", "1.5", [], False), ("-1", "-1.5001", [], True)],
)
def test_beyond_rounding_written_ties(
    stated: str, host: str, printed: list[str] | None, beyond: bool
) -> None:
    shown = None if printed is None else [Decimal(p) for p in printed]
    assert beyond_rounding(Decimal(stated), Decimal(host), shown) is beyond


def test_beyond_rounding_exponent_spread_is_bounded() -> None:
    assert beyond_rounding(Decimal("1E+1999999"), Decimal(0))
    for stated, host in (("1E+2000000", "0"), ("0", "1E+2000000")):
        with pytest.raises(decimal.Overflow):
            beyond_rounding(Decimal(stated), Decimal(host))


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
    if flip:
        _, digits, exponent = d.as_tuple()
        coefficient = min(int("".join(map(str, digits))) + 1, 10**38 - 1)
        d = Decimal((0, tuple(map(int, str(coefficient))), int(exponent)))
    d = d.copy_abs()
    assume(d != 0)
    event("denominator digits", len(d.as_tuple().digits) // 10 * 10)
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
    result = ratio(val(n), val(-d.copy_abs()), non_positive="np")
    assert result.amount is None
    assert result.missing == Missing(MissingCode.ZERO_OR_NEGATIVE_DENOMINATOR, "np")


def test_half_unit_ignores_a_tight_ambient_range() -> None:
    tight = Context(prec=1, Emin=-3, Emax=3, traps=[], flags=[])
    with decimal.localcontext(tight):
        got = half_unit([Decimal("0.00000")])
    assert got.as_tuple() == Decimal("0.000005").as_tuple()


def test_ratio_reaches_a_38_digit_denominator() -> None:
    d = Decimal(10**38 - 3)
    result = ratio(val(Decimal(1)), val(d), non_positive="np")
    assert result.amount is not None
    assert amount_text(result.amount) == "0." + "0" * 37 + "1"


def power(base: int, n: int, e: int = 0) -> Decimal:
    return Decimal((0, tuple(map(int, str(base**n))), e))


@pytest.mark.parametrize("reverse", [False, True])
def test_product_does_not_depend_on_the_int_str_limit(reverse: bool) -> None:
    small = [power(5, 54, -54)] * 100 + [power(2, 126)] * 42 + [power(2, 108)]
    big = [power(5, 54)] * 100 + [power(2, 126)] * 42 + [power(2, 108)]
    many = [Decimal(10**38 - 1)] * 120
    for items, outcome_ in ((small, "1"), (big, decimal.Overflow), (many, decimal.Inexact)):
        values = [val(d) for d in (items[::-1] if reverse else items)]
        if isinstance(outcome_, str):
            result = product(values)
            assert result.amount is not None
            assert amount_text(result.amount) == outcome_
        else:
            with pytest.raises(decimal.DecimalException) as error:
                product(values)
            assert type(error.value) is outcome_


def test_product_under_the_lowest_int_str_limit() -> None:
    items = [power(5, 54, -54)] * 12 + [power(2, 126)] * 5 + [power(2, 18)]
    old = sys.get_int_max_str_digits()
    try:
        sys.set_int_max_str_digits(640)
        result = product([val(d) for d in items])
    finally:
        sys.set_int_max_str_digits(old)
    assert result.amount is not None
    assert amount_text(result.amount) == "1"


def test_half_unit_is_exact_or_refused() -> None:
    with pytest.raises(decimal.DecimalException):
        half_unit([Decimal((0, (1,), -1000036))])
    assert half_unit([Decimal("1E-200")]).as_tuple() == Decimal("5E-201").as_tuple()


@pytest.mark.parametrize("bad", [{val(Decimal(1))}, {1: 2}, iter([val(Decimal(1))]), "1", b"1"])
def test_operand_collections_are_lists_or_tuples(bad: Any) -> None:
    for fn in (total, product):
        with pytest.raises(TypeError):
            fn(bad)
