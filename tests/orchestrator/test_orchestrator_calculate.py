"""D10 and D11: the calculate tool, against the controller's answer key."""

import json
from typing import Any

import orchestrator_calculate_key as key
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from credit_os.orchestrator.calculate import CALCULATE, calculate

_SCALARS = st.none() | st.booleans() | st.integers() | st.floats() | st.text(max_size=20)
_ANY = st.recursive(
    _SCALARS,
    lambda inner: st.lists(inner, max_size=4) | st.dictionaries(st.text(max_size=10), inner),
    max_leaves=8,
)
_NAMED = st.fixed_dictionaries({"operation": _ANY, "values": _ANY})


@pytest.mark.parametrize(
    ("arguments", "expected"), list(key.ROWS.values()), ids=list(key.ROWS.keys())
)
def test_d11_rows_match_the_answer_key(arguments: dict[str, Any], expected: str) -> None:
    assert calculate(arguments) == expected


@pytest.mark.parametrize("arguments", [None, "sum", 3, ["sum", ["1"]], 1.5, True])
def test_d11_arguments_that_are_not_a_mapping_are_bad_keys(arguments: object) -> None:
    assert calculate(arguments) == key.BAD_KEYS


def test_d10_spec_matches_the_key() -> None:
    assert CALCULATE.name == key.NAME
    assert CALCULATE.parameters == key.PARAMETERS
    description = CALCULATE.description
    assert "\n" not in description
    assert len(description) <= 600
    assert "null" in description
    assert "38" in description


def _is_result_or_one_line_error(text: str) -> bool:
    if text.startswith("ERROR: "):
        return "\n" not in text and len(text) <= 300
    parsed = json.loads(text)
    return isinstance(parsed, dict) and list(parsed) == ["value", "reason"]


@settings(max_examples=200, deadline=None)
@given(arguments=_ANY | _NAMED)
def test_d10_any_arguments_give_a_result_or_a_one_line_error(arguments: object) -> None:
    assert _is_result_or_one_line_error(calculate(arguments))


@settings(max_examples=200, deadline=None)
@given(
    operation=st.sampled_from(["sum", "difference", "product", "ratio"]),
    values=st.lists(st.none() | st.text(max_size=70), max_size=130),
)
def test_d10_any_operand_strings_give_a_result_or_a_one_line_error(
    operation: str, values: list[str | None]
) -> None:
    assert _is_result_or_one_line_error(calculate({"operation": operation, "values": values}))
