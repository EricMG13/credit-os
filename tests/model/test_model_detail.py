"""Facility detail and its limits against the answer key (R60, D11, D12)."""

import dataclasses
import decimal
import importlib.util
import json
import re
from pathlib import Path
from typing import Any, cast

import pytest

from credit_os.model.detail import (
    FACILITY_LIMIT,
    Detail,
    FacilityDetail,
    facility_detail,
    facility_limits,
)
from credit_os.model.inputs import ForecastInputs
from credit_os.model.value import Value, amount_text

EXPECTED = Path(__file__).parent / "expected"
KEY = json.loads((EXPECTED / "pr7b.json").read_text("utf-8"))
ROWS = KEY["rows"]
YEAR_FIELDS = ("opening", "rate", "interest", "repaid", "closing")

HELPERS = importlib.util.spec_from_file_location(
    "case_key_helpers", EXPECTED / "case_key_helpers.py"
)
assert HELPERS is not None and HELPERS.loader is not None
H = importlib.util.module_from_spec(HELPERS)
HELPERS.loader.exec_module(H)
ORACLE = H.load_oracle("make_pr7a1")
HOSTILE, ids = H.HOSTILE, H.ids
MODULE_CODE = re.compile(r"CP-\d")


def inputs_of(edits: list[Any]) -> ForecastInputs:
    inputs: ForecastInputs = H.inputs_of(ORACLE, edits)
    return inputs


def shown(detail: Detail) -> list[dict[str, Any]]:
    assert type(detail.facilities) is tuple
    out = []
    for item in detail.facilities:
        assert type(item) is FacilityDetail
        assert type(item.years) is tuple and len(item.years) == 3
        assert all(type(year) is int for year, _ in item.years)
        figures = [
            [year, [amount_text(getattr(fy, f)) for f in YEAR_FIELDS]] for year, fy in item.years
        ]
        out.append({"name": item.facility.name, "years": figures})
    return out


def test_row_count() -> None:
    assert len(ROWS) == 28


def test_the_facility_limit_text_is_the_keys() -> None:
    assert FACILITY_LIMIT == KEY["facility_limit"]
    assert FACILITY_LIMIT == (
        "Cash interest on the stated facilities and scheduled repayment are computed from the "
        "facility terms the forward credit model stated; the analyst's repayment assumption is "
        "not used."
    )


@pytest.mark.parametrize("row", ROWS, ids=ids(ROWS))
def test_detail_and_limits(row: dict[str, Any]) -> None:
    for context in (decimal.getcontext(), HOSTILE):
        with decimal.localcontext(context):
            inputs = inputs_of(row["edits"])
            detail = facility_detail(inputs)
            limits = facility_limits(inputs)
        where = row["name"]
        assert type(limits) is tuple, where
        assert list(limits) == row["limits"], where
        assert all(not MODULE_CODE.search(text) for text in limits), where
        if row["expected"] is None:
            assert detail is None, where
            continue
        assert detail is not None, where
        assert shown(detail) == row["expected"]["facilities"], where
        assert [d.facility for d in detail.facilities] == list(inputs.facilities or ()), where
        assert isinstance(detail.unallocated, Value), where
        H.same_value(KEY["reasons"], detail.unallocated, row["expected"]["unallocated"], where)


def test_the_detail_is_the_same_whatever_cases_the_block_states() -> None:
    plain = ORACLE.FACE + [
        ("downside_shock", None),
        ("upside_drivers", None),
        ("downside_drivers", None),
    ]
    with_cases = inputs_of(ORACLE.FACE)
    assert with_cases.downside_shock is not None and with_cases.upside_drivers is not None
    assert facility_detail(inputs_of(plain)) == facility_detail(with_cases)


def test_the_stated_facility_is_returned_unchanged_and_inputs_are_left_alone() -> None:
    inputs = inputs_of(ORACLE.FACE)
    before = inputs.model_dump()
    detail = facility_detail(inputs)
    facility_limits(inputs)
    assert detail is not None and inputs.facilities is not None
    assert detail.facilities[1].facility is inputs.facilities[1]
    assert inputs.model_dump() == before


def test_the_results_are_frozen() -> None:
    detail = facility_detail(inputs_of(ORACLE.FACE))
    assert detail is not None
    with pytest.raises(dataclasses.FrozenInstanceError):
        cast(Any, detail).unallocated = Value(amount=decimal.Decimal(1))
    with pytest.raises(dataclasses.FrozenInstanceError):
        cast(Any, detail.facilities[0]).years = detail.facilities[1].years
