"""The forecast engine against the answer key, hostile contexts, input checks and properties."""

import dataclasses
import decimal
import json
from decimal import Context, Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from credit_os.model import forecast as fc
from credit_os.model.forecast import Drivers, Operands, Shock, Year, forecast
from credit_os.model.value import Missing, MissingCode, Value, amount_text

KEY = json.loads((Path(__file__).parent / "expected" / "pr2.json").read_text("utf-8"))
CASES = KEY["cases"]
DRIVER_NAMES = KEY["drivers"]
OPERAND_NAMES = ("revenue", "debt", "cash", "undrawn")


def build(item: Any) -> Value:
    if isinstance(item, str):
        return Value(amount=Decimal(item))
    return Value(missing=Missing(MissingCode(item["code"]), item["text"]))


def run_case(case: dict[str, Any]) -> tuple[dict[str, Value], tuple[Year, ...]]:
    given_operands = {name: build(case["operands"][name]) for name in OPERAND_NAMES}
    drivers = Drivers(**{n: tuple(Decimal(t) for t in case["drivers"][n]) for n in DRIVER_NAMES})
    shock = Shock(*(Decimal(t) for t in case["shock"])) if "shock" in case else None
    schedule = (
        tuple((Decimal(a), Decimal(b)) for a, b in case["schedule"]) if "schedule" in case else None
    )
    return given_operands, forecast(Operands(**given_operands), drivers, shock=shock, schedule=schedule)


def check_case(case: dict[str, Any]) -> None:
    operands, years = run_case(case)
    assert len(years) == 3
    for year, expected_row in zip(years, case["years"], strict=True):
        assert len(expected_row) == len(KEY["fields"])
        for name, expected in zip(KEY["fields"], expected_row, strict=True):
            value = getattr(year, name)
            where = f"{case['name']} {name}"
            if isinstance(expected, str):
                assert value.missing is None, where
                assert value.amount is not None, where
                assert amount_text(value.amount) == expected, where
            elif isinstance(expected["missing"], str):
                refused = Missing(MissingCode.ZERO_OR_NEGATIVE_DENOMINATOR, KEY["reasons"][expected["missing"]])
                assert value == Value(missing=refused), where
            else:
                carried = [v for v in operands.values() if v.missing is not None
                           and v.missing.text == expected["missing"]["text"]]
                assert len(carried) == 1
                assert value is carried[0], where


def test_field_orders_match_the_key() -> None:
    assert [f.name for f in dataclasses.fields(Year)] == KEY["fields"]
    assert [f.name for f in dataclasses.fields(Drivers)] == DRIVER_NAMES


def test_reason_texts_match_the_key() -> None:
    assert fc.NC_EBITDA == KEY["reasons"]["NC_EBITDA"]
    assert fc.NC_INTEREST == KEY["reasons"]["NC_INTEREST"]
    assert fc.NC_DEBT == KEY["reasons"]["NC_DEBT"]


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_key_case(case: dict[str, Any]) -> None:
    check_case(case)


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_key_case_under_a_hostile_local_context(case: dict[str, Any]) -> None:
    with decimal.localcontext(Context(prec=5, rounding=decimal.ROUND_UP)):
        check_case(case)


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_key_case_under_a_changed_default_context(case: dict[str, Any]) -> None:
    saved = (
        decimal.DefaultContext.prec,
        decimal.DefaultContext.rounding,
        decimal.DefaultContext.Emax,
        decimal.DefaultContext.Emin,
    )
    decimal.DefaultContext.prec = 5
    decimal.DefaultContext.rounding = decimal.ROUND_UP
    decimal.DefaultContext.Emax = 10
    decimal.DefaultContext.Emin = -10
    try:
        check_case(case)
    finally:
        (
            decimal.DefaultContext.prec,
            decimal.DefaultContext.rounding,
            decimal.DefaultContext.Emax,
            decimal.DefaultContext.Emin,
        ) = saved


D = Decimal


def bad(value: Any) -> Any:
    """A deliberately wrongly typed argument."""
    return value
TRIPLE = (D("0.1"), D("0.1"), D("0.1"))


def good_drivers(**changes: Any) -> Drivers:
    base = {name: TRIPLE for name in DRIVER_NAMES}
    return Drivers(**{**base, **changes})


def good_operands() -> Operands:
    return Operands(*(Value(amount=D(10)) for _ in OPERAND_NAMES))


def test_a_result_needing_more_than_38_digits_is_refused() -> None:
    big = Operands(Value(amount=D("9" * 38)), *(Value(amount=D(1)) for _ in range(3)))
    with pytest.raises(decimal.Inexact):
        forecast(big, good_drivers(revenue_growth=(D("0.20"),) * 3))


SCHEDULE = ((D(1), D(2)), (D(1), D(2)), (D(1), D(2)))
REFUSED: list[tuple[str, type[Exception], Any]] = [
    ("operands is a dict", TypeError, lambda: forecast(bad({}), good_drivers())),
    ("operand is a bare Decimal", TypeError, lambda: Operands(bad(D(1)), *[Value(amount=D(1))] * 3)),
    ("drivers is a dict", TypeError, lambda: forecast(good_operands(), bad({}))),
    ("driver is a list", TypeError, lambda: good_drivers(dividends=bad([D(1)] * 3))),
    ("driver has two", ValueError, lambda: good_drivers(dividends=(D(1), D(1)))),
    ("driver has four", ValueError, lambda: good_drivers(dividends=(D(1),) * 4)),
    ("driver has a float", TypeError, lambda: good_drivers(dividends=bad((D(1), D(1), 1.5)))),
    ("driver has an int", TypeError, lambda: good_drivers(dividends=bad((D(1), D(1), 1)))),
    ("driver has NaN", ValueError, lambda: good_drivers(dividends=(D(1), D(1), D("NaN")))),
    ("driver has Infinity", ValueError, lambda: good_drivers(dividends=(D(1), D(1), D("Infinity")))),
    ("shock is a tuple", TypeError, lambda: forecast(good_operands(), good_drivers(), shock=bad((D(0), D(0))))),
    ("shock has a float", TypeError, lambda: Shock(bad(0.2), D(0))),
    ("shock has an int", TypeError, lambda: Shock(D(0), bad(1))),
    ("shock has NaN", ValueError, lambda: Shock(D("NaN"), D(0))),
    ("shock has Infinity", ValueError, lambda: Shock(D(0), D("Infinity"))),
    ("schedule is a list", TypeError, lambda: forecast(good_operands(), good_drivers(), schedule=bad(list(SCHEDULE)))),
    ("schedule has two pairs", ValueError, lambda: forecast(good_operands(), good_drivers(), schedule=bad(SCHEDULE[:2]))),
    ("schedule has four pairs", ValueError, lambda: forecast(good_operands(), good_drivers(), schedule=bad(SCHEDULE + SCHEDULE[:1]))),
    ("schedule pair of three", ValueError, lambda: forecast(good_operands(), good_drivers(), schedule=bad((SCHEDULE[0], SCHEDULE[1], (D(1),) * 3)))),
    ("schedule pair is a list", TypeError, lambda: forecast(good_operands(), good_drivers(), schedule=bad((SCHEDULE[0], SCHEDULE[1], [D(1), D(2)])))),
    ("schedule has a float", TypeError, lambda: forecast(good_operands(), good_drivers(), schedule=bad((SCHEDULE[0], SCHEDULE[1], (D(1), 2.5))))),
    ("schedule has an int", TypeError, lambda: forecast(good_operands(), good_drivers(), schedule=bad((SCHEDULE[0], SCHEDULE[1], (D(1), 2))))),
    ("schedule has NaN", ValueError, lambda: forecast(good_operands(), good_drivers(), schedule=bad((SCHEDULE[0], SCHEDULE[1], (D("NaN"), D(2)))))),
    ("schedule has Infinity", ValueError, lambda: forecast(good_operands(), good_drivers(), schedule=bad((SCHEDULE[0], SCHEDULE[1], (D(1), D("-Infinity")))))),
]


@pytest.mark.parametrize(("row", "error", "act"), REFUSED, ids=[r[0] for r in REFUSED])
def test_input_is_refused(row: str, error: type[Exception], act: Any) -> None:
    with pytest.raises(error):
        act()


def test_good_inputs_run() -> None:
    assert len(forecast(good_operands(), good_drivers(), shock=Shock(D(0), D(0)), schedule=SCHEDULE)) == 3


# Properties: the oracle is Fraction arithmetic on the generated integers.


def dec(n: int, places: int) -> Decimal:
    return Decimal(f"{n}E-{places}")


def frac(n: int, places: int) -> Fraction:
    return Fraction(n, 10**places)


share = st.integers(0, 10_000)
growth = st.integers(-10_000, 10_000)
money = st.integers(0, 10**11 - 1)
amount = st.integers(0, 999_999)
def triple(s: Any) -> Any:
    return st.tuples(s, s, s)


@st.composite
def inputs(draw: Any) -> dict[str, Any]:
    return {
        "operands": [draw(money) for _ in OPERAND_NAMES],
        "growth": draw(triple(growth)),
        "margin": draw(triple(share)),
        "capex": draw(triple(share)),
        "taxwc": draw(triple(share)),
        "rate": draw(triple(share)),
        "dividends": draw(triple(amount)),
        "repayment": draw(triple(amount)),
        "shock": draw(st.tuples(share, share)),
    }


def make(raw: dict[str, Any], *, shock: bool = False) -> tuple[Operands, Drivers, Shock | None]:
    operands = Operands(*(Value(amount=dec(n, 2)) for n in raw["operands"]))
    drivers = Drivers(
        revenue_growth=tuple(dec(n, 4) for n in raw["growth"]),
        ebitda_margin=tuple(dec(n, 4) for n in raw["margin"]),
        capex_pct_revenue=tuple(dec(n, 4) for n in raw["capex"]),
        tax_wc_pct_revenue=tuple(dec(n, 4) for n in raw["taxwc"]),
        interest_rate=tuple(dec(n, 4) for n in raw["rate"]),
        dividends=tuple(Decimal(n) for n in raw["dividends"]),
        debt_repayment=tuple(Decimal(n) for n in raw["repayment"]),
    )
    return operands, drivers, (Shock(dec(raw["shock"][0], 4), dec(raw["shock"][1], 4)) if shock else None)


def amounts(year: Year) -> dict[str, Fraction]:
    return {
        f.name: Fraction(v.amount)
        for f in dataclasses.fields(Year)
        if (v := getattr(year, f.name)).amount is not None
    }


@settings(max_examples=150, deadline=None)
@given(inputs())
def test_zero_shock_equals_no_shock(raw: dict[str, Any]) -> None:
    operands, drivers, _ = make(raw)
    assert forecast(operands, drivers, shock=Shock(D(0), D(0))) == forecast(operands, drivers)


@settings(max_examples=150, deadline=None)
@given(inputs())
def test_years_chain_and_identities_hold(raw: dict[str, Any]) -> None:
    operands, drivers, _ = make(raw)
    years = forecast(operands, drivers)
    assert years[0].opening_debt == operands.debt
    assert years[0].opening_cash == operands.cash
    for before, after in zip(years, years[1:], strict=False):
        assert after.opening_debt == before.closing_debt
        assert after.opening_cash == before.closing_cash
    assert years[0].undrawn == years[1].undrawn == years[2].undrawn == operands.undrawn
    revenue = Fraction(operands.revenue.amount or 0)
    for index, year in enumerate(years):
        a = amounts(year)
        assert a["revenue"] == revenue * (1 + frac(raw["growth"][index], 4))
        revenue = a["revenue"]
        assert a["closing_debt"] == a["opening_debt"] - a["repayment"]
        assert a["closing_cash"] == a["opening_cash"] + a["fcf"] - a["dividends"] - a["repayment"]
        assert a["fcf"] == a["ebitda"] - a["interest"] - a["tax_wc"] - a["capex"]
        assert a["net_debt"] == a["closing_debt"] - a["closing_cash"]
        assert a["liquidity"] == a["closing_cash"] + a["undrawn"]


def close(value: Value, num: Fraction, den: Fraction) -> bool:
    if den <= 0:
        return value.missing is not None
    return value.amount is not None and abs(Fraction(value.amount) - num / den) <= abs(num / den) / 10**37


@settings(max_examples=150, deadline=None)
@given(inputs(), st.booleans())
def test_year_one_matches_the_formulas(raw: dict[str, Any], shocked: bool) -> None:
    operands, drivers, shock = make(raw, shock=shocked)
    year = forecast(operands, drivers, shock=shock)[0]
    s, k = (frac(raw["shock"][0], 4), frac(raw["shock"][1], 4)) if shocked else (0, 0)
    rev0, debt, cash, undrawn = (frac(n, 2) for n in raw["operands"])
    revenue = rev0 * (1 + frac(raw["growth"][0], 4))
    ebitda = revenue * frac(raw["margin"][0], 4) * (1 - s)
    interest = debt * frac(raw["rate"][0], 4) * (1 + k)
    tax_wc = revenue * frac(raw["taxwc"][0], 4)
    capex = revenue * frac(raw["capex"][0], 4)
    fcf = ebitda - interest - tax_wc - capex
    closing_debt = debt - raw["repayment"][0]
    closing_cash = cash + fcf - raw["dividends"][0] - raw["repayment"][0]
    net_debt = closing_debt - closing_cash
    exact = {
        "revenue": revenue, "ebitda": ebitda, "interest": interest, "tax_wc": tax_wc,
        "capex": capex, "cfo": ebitda - interest - tax_wc, "fcf": fcf,
        "opening_debt": debt, "repayment": Fraction(raw["repayment"][0]),
        "closing_debt": closing_debt, "opening_cash": cash,
        "dividends": Fraction(raw["dividends"][0]), "closing_cash": closing_cash,
        "undrawn": undrawn, "liquidity": closing_cash + undrawn, "net_debt": net_debt,
    }
    for name, expected in exact.items():
        assert amounts(year)[name] == expected, name
    assert close(year.total_leverage, closing_debt, ebitda)
    assert close(year.net_leverage, net_debt, ebitda)
    assert close(year.coverage, ebitda, interest)
    assert close(year.fcf_to_debt, fcf, closing_debt)


@settings(max_examples=150, deadline=None)
@given(inputs(), st.booleans())
def test_a_schedule_equal_to_the_drivers_changes_nothing(raw: dict[str, Any], shocked: bool) -> None:
    operands, drivers, shock = make(raw, shock=shocked)
    plain = forecast(operands, drivers, shock=shock)
    with decimal.localcontext(Context(prec=100)):
        pairs = tuple(
            (bad(y.opening_debt.amount) * drivers.interest_rate[i], drivers.debt_repayment[i])
            for i, y in enumerate(plain)
        )
    scheduled = forecast(operands, drivers, shock=shock, schedule=bad(pairs))
    assert scheduled == plain
