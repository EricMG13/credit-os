"""The forecast cases against the answer key, hostile contexts and properties."""

import copy
import dataclasses
import decimal
import importlib.util
import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
from credit_os.model.cases import CaseName, StressBasis, run_cases
from hypothesis import given, settings
from hypothesis import strategies as st

from credit_os.model import cases as cs
from credit_os.model.forecast import Year
from credit_os.model.inputs import ForecastInputs, parse_inputs
from credit_os.model.value import Value, amount_text

EXPECTED = Path(__file__).parent / "expected"
KEY = json.loads((EXPECTED / "pr7a2.json").read_text("utf-8"))
ROWS = KEY["rows"]
BY_NAME = {r["name"]: r for r in ROWS}
FIELDS = KEY["fields"]
KINDS = {
    "case_set": 9,
    "drivers": 3,
    "shock": 3,
    "remainder": 7,
    "missing": 5,
    "negative_cash": 10,
    "scale": 3,
}
FIELD_OUTCOMES = {  # over the 37 rows that list their own cases
    "amount": 4293,
    "NOT_SOURCED": 840,
    "NEGATIVE_CASH": 39,
    "NC_INTEREST": 36,
    "NC_EBITDA": 12,
}


HELPERS = importlib.util.spec_from_file_location(
    "case_key_helpers", EXPECTED / "case_key_helpers.py"
)
assert HELPERS is not None and HELPERS.loader is not None
H = importlib.util.module_from_spec(HELPERS)
HELPERS.loader.exec_module(H)
ORACLE = H.load_oracle("make_pr7a2")
HOSTILE, ids = H.HOSTILE, H.ids


def inputs_of(edits: list[Any]) -> ForecastInputs:
    inputs: ForecastInputs = H.inputs_of(ORACLE, edits)
    return inputs


def same_value(got: Value, item: Any, where: str) -> None:
    H.same_value(KEY["reasons"], got, item, where)


def check_row(row: dict[str, Any]) -> None:
    expected = BY_NAME[row["same_as"]] if "same_as" in row else row
    result, basis = run_cases(inputs_of(row["edits"]))
    assert (basis is None) == (expected["basis"] is None), row["name"]
    if basis is not None:
        assert basis is StressBasis(expected["basis"]), row["name"]
    assert [c.name for c in result] == [CaseName(c["name"]) for c in expected["cases"]]
    for got, key in zip(result, expected["cases"], strict=True):
        assert type(got.years) is tuple and len(got.years) == 3
        for t, (year, items) in enumerate(zip(got.years, key["years"], strict=True)):
            assert len(items) == len(FIELDS)
            for name, item in zip(FIELDS, items, strict=True):
                same_value(
                    getattr(year, name), item, f"{row['name']} {key['name']} y{t + 1} {name}"
                )


@pytest.mark.parametrize("row", ROWS, ids=ids(ROWS))
def test_key_row(row: dict[str, Any]) -> None:
    check_row(row)


@pytest.mark.parametrize("row", ROWS, ids=ids(ROWS))
def test_key_row_under_a_hostile_local_context(row: dict[str, Any]) -> None:
    with decimal.localcontext(HOSTILE):
        check_row(row)


def test_row_counts() -> None:
    assert len(ROWS) == 40
    assert Counter(r["kind"] for r in ROWS) == KINDS
    assert KEY["kinds"] == KINDS
    seen: Counter[str] = Counter()
    for row in ROWS:
        for case in row.get("cases", []):
            for year in case["years"]:
                for item in year:
                    missing = item["missing"] if isinstance(item, dict) else None
                    seen[
                        "amount"
                        if missing is None
                        else missing
                        if isinstance(missing, str)
                        else missing["code"]
                    ] += 1
    assert seen == FIELD_OUTCOMES


def test_names_and_texts_match_the_key() -> None:
    assert [m.value for m in CaseName] == ["reference", "upside", "downside", "downside_stress"]
    assert [m.value for m in StressBasis] == ["base", "downside"]
    assert [f.name for f in dataclasses.fields(Year)] == FIELDS
    assert [f.name for f in dataclasses.fields(cs.Case)] == ["name", "years"]


def spec_block(spec: dict[str, Any], scale: int) -> dict[str, Any]:
    """A block from integers: amounts in tenths of a thousand, so both scales print them exactly."""

    def text(tenths: int) -> str:
        sign, tenths = ("-" if tenths < 0 else ""), abs(tenths)
        if scale == 1000:
            return f"{sign}{tenths // 10}.{tenths % 10}"
        return f"{sign}{tenths // 10000}.{tenths % 10000:04d}"

    def share(n: int) -> str:
        return "1" if n == 100 else ("0" if n == 0 else f"0.{n:02d}")

    def growth(n: int) -> str:
        return "-" + share(-n) if n < 0 else share(n)

    block = copy.deepcopy(KEY["block"])
    for name, tenths in spec["operands"].items():
        if tenths is None:
            block["base"][name] = {"amount": None, "reason": f"{name} not stated"}
        else:
            block["base"][name]["amount"] = text(tenths)
    drivers = block["base_drivers"]
    for name, values in spec["drivers"].items():
        convert = (
            text
            if name in ("dividends", "debt_repayment")
            else growth
            if name == "revenue_growth"
            else share
        )
        drivers[name]["values"] = [convert(v) for v in values]
    block["upside_drivers"] = spec["upside"] and {"ebitda_margin": drv(share, spec["upside"])}
    block["downside_drivers"] = spec["downside"] and {"interest_rate": drv(share, spec["downside"])}
    block["downside_shock"] = spec["shock"] and {
        "ebitda_decline": share(spec["shock"][0]),
        "rate_increase": share(spec["shock"][1]),
    }
    block["facilities"] = None
    if spec["facility"] is not None:
        block["facilities"] = [
            {
                "name": "F",
                "balance": text(spec["facility"]),
                "fixed_rate_pct": "7",
                "spread_pct": None,
                "floor_pct": None,
                "reference_rate": None,
                "annual_amortisation": None,
                "maturity": None,
            }
        ]
    block["scale"] = scale
    result: dict[str, Any] = block
    return result


def drv(share: Any, values: list[int]) -> dict[str, Any]:
    return {
        "values": [share(v) for v in values],
        "category": "Analyst Interpretation",
        "rationale": "Invented.",
        "limitation": None,
    }


triples = st.lists(st.integers(0, 100), min_size=3, max_size=3)
tenths = st.integers(-99_999_999, 99_999_999)
SPECS = st.fixed_dictionaries(
    {
        "operands": st.fixed_dictionaries(
            {
                "revenue": st.one_of(st.none(), st.integers(0, 99_999_999)),
                "debt": st.one_of(st.none(), st.integers(1_000_000, 99_999_999)),
                "cash": st.one_of(st.none(), tenths),
                "undrawn": st.one_of(st.none(), st.integers(0, 99_999_999)),
            }
        ),
        "drivers": st.fixed_dictionaries(
            {
                "revenue_growth": st.lists(st.integers(-50, 100), min_size=3, max_size=3),
                "ebitda_margin": triples,
                "capex_pct_revenue": triples,
                "tax_wc_pct_revenue": triples,
                "interest_rate": triples,
                "dividends": st.lists(st.integers(0, 99_999_999), min_size=3, max_size=3),
                "debt_repayment": st.lists(st.integers(0, 3000), min_size=3, max_size=3),
            }
        ),
        "upside": st.one_of(st.none(), triples),
        "downside": st.one_of(st.none(), triples),
        "shock": st.one_of(st.none(), st.tuples(st.integers(0, 100), st.integers(0, 100))),
        "facility": st.one_of(st.none(), st.integers(0, 99_999_999)),
    }
)


def encoded(year: Year) -> list[Any]:
    out: list[Any] = []
    for name in FIELDS:
        value: Value = getattr(year, name)
        out.append(
            amount_text(value.amount)
            if value.amount is not None
            else [value.missing.code.value, value.missing.text]
            if value.missing
            else None
        )
    return out


@settings(max_examples=300, deadline=None)
@given(SPECS)
def test_cases_equal_the_oracle_and_both_scales_agree(spec: dict[str, Any]) -> None:
    oracle = ORACLE
    millions = spec_block(spec, 1)
    cases, basis = oracle.solve(millions)
    ours, stress = run_cases(parse_inputs(millions)[0])
    theirs, stress_thousands = run_cases(parse_inputs(spec_block(spec, 1000))[0])
    assert (stress and stress.value) == basis
    assert stress == stress_thousands
    flat = oracle.flat_cases(cases)
    for run in (ours, theirs):
        got = [(c.name.value, [encoded(y) for y in c.years]) for c in run]
        assert got == flat


@settings(max_examples=300, deadline=None)
@given(SPECS)
def test_zero_shock_equals_its_basis(spec: dict[str, Any]) -> None:
    block = spec_block(spec, 1)
    block["downside_shock"] = {"ebitda_decline": "0", "rate_increase": "0"}
    result, basis = run_cases(parse_inputs(block)[0])
    assert basis is not None
    by_name = {c.name: c.years for c in result}
    name = CaseName.DOWNSIDE if basis is StressBasis.DOWNSIDE else CaseName.REFERENCE
    assert by_name[CaseName.DOWNSIDE_STRESS] == by_name[name]
