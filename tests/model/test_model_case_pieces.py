"""The case pieces against the answer key: operands, drivers, unallocated debt, negative cash."""

import dataclasses
import decimal
import importlib.util
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from credit_os.model.cases import (
    NEGATIVE_CASH,
    base_operands,
    case_drivers,
    unallocated,
    with_negative_cash,
)
from hypothesis import given, settings
from hypothesis import strategies as st

from credit_os.model.forecast import Year
from credit_os.model.inputs import ForecastInputs
from credit_os.model.value import Missing, MissingCode, Value

EXPECTED = Path(__file__).parent / "expected"
KEY = json.loads((EXPECTED / "pr7a1.json").read_text("utf-8"))
FIELDS = KEY["fields"]
COUNTS = {"operands": 3, "drivers": 5, "unallocated": 6, "overlay": 6}


HELPERS = importlib.util.spec_from_file_location(
    "case_key_helpers", EXPECTED / "case_key_helpers.py"
)
assert HELPERS is not None and HELPERS.loader is not None
H = importlib.util.module_from_spec(HELPERS)
HELPERS.loader.exec_module(H)
ORACLE = H.load_oracle("make_pr7a1")
HOSTILE, ids = H.HOSTILE, H.ids


def inputs_of(edits: list[Any]) -> ForecastInputs:
    inputs: ForecastInputs = H.inputs_of(ORACLE, edits)
    return inputs


def same_value(got: Value, item: Any, where: str) -> None:
    H.same_value(KEY["reasons"], got, item, where)


def test_row_counts() -> None:
    assert {k: len(KEY[k]) for k in COUNTS} == COUNTS


def test_names_and_texts_match_the_key() -> None:
    assert NEGATIVE_CASH == KEY["reasons"]["NEGATIVE_CASH"][1]
    assert MissingCode.NEGATIVE_CASH == "NEGATIVE_CASH"
    assert [f.name for f in dataclasses.fields(Year)] == FIELDS


@pytest.mark.parametrize("row", KEY["operands"], ids=ids(KEY["operands"]))
def test_base_operands(row: dict[str, Any]) -> None:
    for context in (decimal.getcontext(), HOSTILE):
        with decimal.localcontext(context):
            got = base_operands(inputs_of(row["edits"]))
            for name, item in row["expected"].items():
                same_value(getattr(got, name), item, f"{row['name']} {name}")


@pytest.mark.parametrize("row", KEY["drivers"], ids=ids(KEY["drivers"]))
def test_case_drivers(row: dict[str, Any]) -> None:
    inputs = inputs_of(row["edits"])
    group = row["group"]
    got = case_drivers(inputs.base_drivers, getattr(inputs, group) if group else None)
    for name, texts in row["expected"].items():
        assert getattr(got, name) == tuple(Decimal(t) for t in texts), f"{row['name']} {name}"


def test_case_drivers_none_is_base_and_leaves_inputs_alone() -> None:
    inputs = inputs_of([])
    before = inputs.model_dump()
    case_drivers(inputs.base_drivers, inputs.downside_drivers)
    assert inputs.model_dump() == before


@pytest.mark.parametrize("row", KEY["unallocated"], ids=ids(KEY["unallocated"]))
def test_unallocated(row: dict[str, Any]) -> None:
    for context in (decimal.getcontext(), HOSTILE):
        with decimal.localcontext(context):
            got = unallocated(inputs_of(row["edits"]))
            if row["expected"] is None:
                assert got is None
            else:
                assert got is not None
                same_value(got, row["expected"], row["name"])


def year_from(shown: dict[str, Any], cash_text: str | None) -> Year:
    values = {f: H.want(KEY["reasons"], shown[f]) for f in FIELDS}
    built = {f: Value(amount=Decimal(v)) if isinstance(v, str) else v for f, v in values.items()}
    if cash_text is not None:
        built["closing_cash"] = Value(amount=Decimal(cash_text))
    return Year(**built)


@pytest.mark.parametrize("row", KEY["overlay"], ids=ids(KEY["overlay"]))
def test_with_negative_cash(row: dict[str, Any]) -> None:
    for context in (decimal.getcontext(), HOSTILE):
        with decimal.localcontext(context):
            got = with_negative_cash(year_from(row["year"], row["closing_cash_text"]))
            for name in FIELDS:
                same_value(getattr(got, name), row["expected"][name], f"{row['name']} {name}")


CELLS = st.one_of(st.none(), st.integers(-300, 300))


@settings(max_examples=300, deadline=None)
@given(st.lists(CELLS, min_size=len(FIELDS), max_size=len(FIELDS)))
def test_overlay_changes_exactly_three_fields_iff_cash_is_negative(cells: list[int | None]) -> None:
    year = Year(
        **{
            f: Value(amount=Decimal(f"{n}e-2"))
            if n is not None
            else Value(missing=Missing(MissingCode.NOT_SOURCED, f"{f} missing"))
            for f, n in zip(FIELDS, cells, strict=True)
        }
    )
    cash = cells[FIELDS.index("closing_cash")]
    got = with_negative_cash(year)
    gap = Value(
        missing=Missing(
            MissingCode.NEGATIVE_CASH, "Not calculable: cash is negative before funding"
        )
    )
    changed = {f for f in FIELDS if getattr(got, f) != getattr(year, f)}
    if cash is not None and cash < 0:
        for name in ("net_debt", "net_leverage", "liquidity"):
            assert getattr(got, name) == gap
        for name in set(FIELDS) - {"net_debt", "net_leverage", "liquidity"}:
            assert getattr(got, name) == getattr(year, name)
    else:
        assert not changed
