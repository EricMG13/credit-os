"""Facility terms and their three-year schedule, against the answer key."""

import dataclasses
import decimal
import json
from collections import deque
from decimal import Context, Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any, cast

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from credit_os.model.facilities import Facility, _plain, schedule
from credit_os.model.value import Missing, MissingCode, Value, amount_text

KEY = json.loads((Path(__file__).parent / "expected" / "pr3.json").read_text("utf-8"))
SCHEDULES = KEY["schedules"]
REFUSED = KEY["refused"]
ALL_IN = [row for row in REFUSED if str(row[4]).startswith("all-in")]


def figures(sched: Any) -> tuple[list[Any], list[Any]]:
    rows = [
        [
            [
                amount_text(getattr(y, f))
                for f in ("opening", "rate", "interest", "repaid", "closing")
            ]
            for y in row
        ]
        for row in sched.rows
    ]
    totals = [[amount_text(i), amount_text(r)] for i, r in sched.totals()]
    return rows, totals


def build(facilities: list[dict[str, Any]], *, as_json: bool) -> list[Facility]:
    if as_json:
        return [Facility.model_validate_json(json.dumps(f)) for f in facilities]
    return [Facility.model_validate(f) for f in facilities]


def check_schedule(case: dict[str, Any], *, as_json: bool) -> None:
    rows, totals = figures(schedule(build(case["facilities"], as_json=as_json)))
    assert rows == case["rows"]
    assert totals == case["totals"]


@pytest.mark.parametrize("name", list(SCHEDULES))
@pytest.mark.parametrize("as_json", [False, True])
def test_key_schedules(name: str, as_json: bool) -> None:
    check_schedule(SCHEDULES[name], as_json=as_json)


def refusal(facility: dict[str, Any], *, as_json: bool) -> list[Any]:
    with pytest.raises(ValidationError) as caught:
        if as_json:
            Facility.model_validate_json(json.dumps(facility))
        else:
            Facility.model_validate(facility)
    return list(caught.value.errors())


@pytest.mark.parametrize("as_json", [False, True])
@pytest.mark.parametrize("row", REFUSED, ids=[row[0] for row in REFUSED])
def test_key_refusals(row: list[Any], as_json: bool) -> None:
    _, facility, loc, kind, text = row
    errors = refusal(facility, as_json=as_json)
    assert len(errors) == 1
    assert errors[0]["loc"] == tuple(loc)
    assert errors[0]["type"] == kind
    if text is not None:
        assert str(errors[0]["ctx"]["error"]) == text


def terms(**changes: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "name": "Term loan A",
        "balance": "400",
        "fixed_rate_pct": "6.5",
        "spread_pct": None,
        "floor_pct": None,
        "reference_rate": None,
        "annual_amortisation": "25",
        "maturity": None,
    }
    return base | changes


def test_validator_order() -> None:
    rules_1_and_2 = terms(fixed_rate_pct="30.5", spread_pct="1")
    assert str(refusal(rules_1_and_2, as_json=False)[0]["ctx"]["error"]) == (
        "fixed_rate_pct 30.5 is above 30"
    )
    rules_2_and_4 = terms(name=" x", spread_pct="1")
    assert str(refusal(rules_2_and_4, as_json=False)[0]["ctx"]["error"]) == (
        "a facility states a fixed rate or a floating one, not both"
    )


def test_record_is_frozen() -> None:
    facility = Facility.model_validate(terms())
    with pytest.raises(ValidationError):
        facility.name = "other"


def test_schedule_input_types() -> None:
    facility = Facility.model_validate(terms())
    with pytest.raises(TypeError, match=r"^facilities must be a list or a tuple of Facility$"):
        schedule(cast(Any, (f for f in [facility])))
    with pytest.raises(TypeError, match=r"^every facility must be a Facility$"):
        schedule(cast(Any, [terms()]))
    with pytest.raises(TypeError, match=r"^facilities must be a list or a tuple of Facility$"):
        schedule(cast(Any, facility))
    assert len(schedule((facility,)).rows) == 1


def test_unvalidated_floating_facility_is_refused() -> None:
    for reference, spread in ((None, "1"), (["0.01", "0.01", "0.01"], None)):
        bad = Facility.model_construct(
            **terms(fixed_rate_pct=None, reference_rate=reference, spread_pct=spread)
        )
        with pytest.raises(
            ValueError, match=r"^a floating facility needs a reference rate and a spread$"
        ):
            schedule([bad])


def test_missing_figure_is_refused() -> None:
    missing = Value(missing=Missing(MissingCode.NOT_SOURCED, "no source"))
    with pytest.raises(ValueError, match=r"^a facility figure is missing$"):
        _plain(missing)


@pytest.fixture
def hostile(request: pytest.FixtureRequest) -> Any:
    if request.param == "local":
        with decimal.localcontext(Context(prec=5, rounding=decimal.ROUND_UP)):
            yield
        return
    default = decimal.DefaultContext
    saved = (default.prec, default.rounding, default.Emax, default.Emin)
    default.prec, default.rounding, default.Emax, default.Emin = 3, decimal.ROUND_UP, 5, -5
    try:
        with decimal.localcontext(default):
            yield
    finally:
        default.prec, default.rounding, default.Emax, default.Emin = saved


@pytest.mark.parametrize("hostile", ["local", "default"], indirect=True)
@pytest.mark.usefixtures("hostile")
def test_hostile_contexts() -> None:
    for case in SCHEDULES.values():
        check_schedule(case, as_json=False)
    for row in ALL_IN:
        errors = refusal(row[1], as_json=False)
        assert str(errors[0]["ctx"]["error"]) == row[4]


def test_totals_are_plain_decimals() -> None:
    sched = schedule(build(SCHEDULES["all"]["facilities"], as_json=False))
    for year in sched.rows[0]:
        assert all(type(getattr(year, f.name)) is Decimal for f in dataclasses.fields(year))
    assert all(type(x) is Decimal for pair in sched.totals() for x in pair)


def units(n: int, places: int = 4) -> str:
    sign = "-" if n < 0 else ""
    whole, frac = divmod(abs(n), 10**places)
    return f"{sign}{whole}.{frac:0{places}d}"


AMOUNT = st.integers(0, 10**10 - 1)
FIXED = st.fixed_dictionaries(
    {"balance": AMOUNT, "amort": st.none() | AMOUNT, "fixed": st.integers(0, 300000)}
)
FLOATING = st.fixed_dictionaries(
    {
        "balance": AMOUNT,
        "amort": st.none() | AMOUNT,
        "ref": st.tuples(*[st.integers(-300, 10000)] * 3),
        "floor": st.none() | st.integers(0, 100000),
        "spread": st.integers(0, 200000),
    }
)


def record(g: dict[str, Any]) -> dict[str, Any]:
    fixed = "fixed" in g
    return terms(
        balance=units(g["balance"]),
        annual_amortisation=None if g["amort"] is None else units(g["amort"]),
        fixed_rate_pct=units(g["fixed"]) if fixed else None,
        spread_pct=None if fixed else units(g["spread"]),
        floor_pct=None if fixed or g["floor"] is None else units(g["floor"]),
        reference_rate=None if fixed else [units(n) for n in g["ref"]],
    )


def oracle_rates(g: dict[str, Any]) -> list[Fraction]:
    if "fixed" in g:
        return [Fraction(g["fixed"], 10**6)] * 3
    floor = None if g["floor"] is None else Fraction(g["floor"], 10**6)
    out = []
    for n in g["ref"]:
        ref = Fraction(n, 10**4)
        out.append((ref if floor is None else max(ref, floor)) + Fraction(g["spread"], 10**6))
    return out


def accepted(g: dict[str, Any]) -> bool:
    return all(0 <= r <= Fraction(3, 10) for r in oracle_rates(g))


def oracle_years(g: dict[str, Any]) -> list[tuple[Fraction, Fraction, Fraction, Fraction]]:
    """Per year: opening, interest, repaid, closing, in Fraction from the generated integers."""
    opening = Fraction(g["balance"], 10**4)
    amort = Fraction(g["amort"] or 0, 10**4)
    out = []
    for rate in oracle_rates(g):
        repaid = min(amort, opening)
        out.append((opening, opening * rate, repaid, opening - repaid))
        opening -= repaid
    return out


@settings(max_examples=200)
@given(st.one_of(FIXED, FLOATING))
def test_schedule_properties(g: dict[str, Any]) -> None:
    if not accepted(g):
        with pytest.raises(ValidationError):
            Facility.model_validate(record(g))
        return
    row = schedule([Facility.model_validate(record(g))]).rows[0]
    want = oracle_years(g)
    for year, rate, (opening, interest, repaid, closing) in zip(
        row, oracle_rates(g), want, strict=True
    ):
        assert Fraction(year.opening) == opening
        assert Fraction(year.rate) == rate
        assert Fraction(year.interest) == interest
        assert Fraction(year.repaid) == repaid
        assert Fraction(year.closing) == closing
        assert year.closing >= 0
        assert year.repaid <= year.opening
    amort = Fraction(g["amort"] or 0, 10**4)
    assert sum(Fraction(y.repaid) for y in row) == min(3 * amort, Fraction(g["balance"], 10**4))


@settings(max_examples=200)
@given(st.lists(st.one_of(FIXED, FLOATING).filter(accepted), max_size=5))
def test_totals_are_column_sums(gs: list[dict[str, Any]]) -> None:
    sched = schedule([Facility.model_validate(record(g)) for g in gs])
    assert len(sched.rows) == len(gs)
    want = [oracle_years(g) for g in gs]
    for n, (interest, repaid) in enumerate(sched.totals()):
        assert Fraction(interest) == sum((w[n][1] for w in want), Fraction(0))
        assert Fraction(repaid) == sum((w[n][2] for w in want), Fraction(0))


def test_reference_rate_accepts_only_list_or_tuple() -> None:
    texts = ["0.01", "0.02", "0.03"]
    base = terms(fixed_rate_pct=None, spread_pct="1", reference_rate=texts)
    from_list = Facility.model_validate(base)
    assert Facility.model_validate(base | {"reference_rate": tuple(texts)}) == from_list
    assert Facility.model_validate_json(json.dumps(base)) == from_list
    for bad in (set(texts), frozenset(texts), (t for t in texts), deque(texts)):
        errors = refusal(base | {"reference_rate": bad}, as_json=False)
        assert [(e["loc"], e["type"]) for e in errors] == [(("reference_rate",), "tuple_type")]


def message(facility: dict[str, Any]) -> str:
    return str(refusal(facility, as_json=False)[0]["ctx"]["error"])


def test_validator_order_remaining_rules() -> None:
    date_text = "maturity 2027-02-30 is not a calendar date"
    name_text = "facility name must not start or end with whitespace"
    floating = {
        "fixed_rate_pct": None,
        "spread_pct": "20",
        "floor_pct": "10",
        "reference_rate": ["0.2", "0.2", "0.2"],
    }
    assert message(terms(name=" x", maturity="2027-02-30")) == date_text
    assert message(terms(name=" x", **floating)) == name_text
    assert message(terms(maturity="2027-02-30", **floating)) == date_text
    zeros = ["0", "0", "0"]
    over = {"fixed_rate_pct": None, "reference_rate": zeros, "floor_pct": "10.5"}
    assert message(terms(spread_pct="20.5", **over)) == "spread_pct 20.5 is above 20"
    assert message(terms(spread_pct="1", **over)) == "floor_pct 10.5 is above 10"
    assert (
        message(terms(fixed_rate_pct="30.5", floor_pct="10.5")) == "fixed_rate_pct 30.5 is above 30"
    )


def test_all_in_bounds_are_inclusive() -> None:
    zero = terms(
        fixed_rate_pct=None, spread_pct="0", floor_pct=None, reference_rate=["0", "0.0000", "-0"]
    )
    top = terms(
        fixed_rate_pct=None,
        spread_pct="20",
        floor_pct=None,
        reference_rate=["0.1", "0.1000", "0.10"],
    )
    zeros = schedule([Facility.model_validate(zero)]).rows[0]
    tops = schedule([Facility.model_validate(top)]).rows[0]
    assert [amount_text(y.rate) for y in zeros] == ["0", "0", "0"]
    assert [amount_text(y.rate) for y in tops] == ["0.3", "0.3", "0.3"]


@pytest.mark.parametrize("hostile", ["local", "default"], indirect=True)
@pytest.mark.usefixtures("hostile")
def test_stored_forms_under_hostile_contexts() -> None:
    year = schedule([Facility.model_validate(terms(fixed_rate_pct="16.1234"))]).rows[0][0]
    assert amount_text(year.rate) == "0.161234"
    year = schedule([Facility.model_validate(terms(balance="400.00"))]).rows[0][0]
    assert amount_text(year.opening) == "400"
    year = schedule([Facility.model_validate(terms(annual_amortisation="25.50"))]).rows[0][0]
    assert amount_text(year.repaid) == "25.5"


def test_fixed_rate_with_reference_rate_alone_is_refused() -> None:
    facility = terms(reference_rate=["0.01", "0.01", "0.01"])
    assert message(facility) == "a facility states a fixed rate or a floating one, not both"


def test_facility_year_is_frozen() -> None:
    year = schedule([Facility.model_validate(terms())]).rows[0][0]
    with pytest.raises(dataclasses.FrozenInstanceError):
        cast(Any, year).opening = Decimal(1)
