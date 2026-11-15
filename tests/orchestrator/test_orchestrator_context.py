"""3A PR 9a-1: the context loader's guards and shape, and `amount` (decision D24)."""

from decimal import Decimal
from typing import Any

import orchestrator_context_key as key
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from pydantic import BaseModel

from credit_os.orchestrator.context import ContextRefused, amount, load_context


@pytest.mark.parametrize(("data", "problems"), list(key.GUARDS.values()), ids=list(key.GUARDS))
def test_d24_guards_refuse_before_shape(data: bytes, problems: tuple[str, ...]) -> None:
    with pytest.raises(ContextRefused) as caught:
        load_context(data)
    assert caught.value.problems == problems
    assert str(caught.value) == "; ".join(problems)


@pytest.mark.parametrize(("data", "problems"), list(key.SHAPE.values()), ids=list(key.SHAPE))
def test_d24_shape_problems_in_order(data: bytes, problems: tuple[str, ...]) -> None:
    with pytest.raises(ContextRefused) as caught:
        load_context(data)
    assert caught.value.problems == problems


def _read(obj: Any, path: str) -> Any:
    for step in path.split("."):
        obj = obj[int(step)] if step.isdigit() else getattr(obj, step)
    return obj


@pytest.mark.parametrize(("data", "checks"), list(key.ACCEPTED.values()), ids=list(key.ACCEPTED))
def test_d24_accepted_files_load(data: bytes, checks: dict[str, Any]) -> None:
    context = load_context(data)
    for path, expected in checks.items():
        assert _read(context, path) == expected, path


@pytest.mark.parametrize(("text", "expected"), list(key.AMOUNTS.items()), ids=list(key.AMOUNTS))
def test_d24_amount_missing_is_never_zero(text: str, expected: str | None) -> None:
    if expected == "refused":
        with pytest.raises(ValueError):
            amount(text)
        return
    result = amount(text)
    if expected is None:
        assert result is None
    else:
        assert result is not None
        assert str(result) == expected
        assert result == Decimal(text)


def test_d24_loaded_models_are_frozen() -> None:
    context = load_context(key.raw(key.FULL))
    for model in (context, context.run, context.deal_terms[0], context.valuation.issuer_market):
        field = next(iter(type(model).model_fields))
        with pytest.raises(ValueError):
            setattr(model, field, getattr(model, field))


def _floats(value: object) -> list[float]:
    found: list[float] = []
    stack = [value]
    while stack:
        item = stack.pop()
        if isinstance(item, float):
            found.append(item)
        elif isinstance(item, tuple):
            stack.extend(item)
        elif isinstance(item, BaseModel):
            stack.extend(getattr(item, name) for name in type(item).model_fields)
    return found


def test_d24_no_float_in_a_loaded_context() -> None:
    assert _floats(load_context(key.raw(key.FULL))) == []


@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(st.binary(max_size=4096))
def test_d24_any_bytes_load_or_are_refused(data: bytes) -> None:
    try:
        load_context(data)
    except ContextRefused as refused:
        assert refused.problems
