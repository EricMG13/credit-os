"""The budget: totals, admission and refused data, against the controller's answer key
(`orchestrator_budget_key.py`) and three property tests."""

from decimal import Decimal
from fractions import Fraction
from typing import Any

import orchestrator_budget_key as key
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from credit_os.orchestrator.budget import (
    Admission,
    BudgetDataError,
    BudgetStop,
    CallLine,
    CompactionLine,
    Total,
    admit_call,
    total,
)


def _amount(value: Any) -> Any:
    """A key amount: ("decimal", text) is Decimal(text); text is Decimal(text); else as is."""
    if isinstance(value, tuple) and value[0] == "decimal":
        return Decimal(value[1])
    return value


def _money(text: str | None) -> Decimal | None:
    """A key row carries an amount as text, or None."""
    return None if text is None else Decimal(text)


def _line(row: key.Line) -> CallLine | CompactionLine:
    if row[0] == "call":
        _, call, state, hold, billed = row
        return CallLine(
            call=call,
            state=state,
            hold_usd=_money(hold),  # type: ignore[arg-type]
            billed_usd=_money(billed),
        )
    _, call, event_id, outcome, supersedes, billed = row
    return CompactionLine(
        call=call,
        event_id=event_id,
        outcome=outcome,
        supersedes=supersedes,
        billed_usd=_money(billed),
    )


def _lines(rows: list[key.Line]) -> list[CallLine | CompactionLine]:
    return [_line(row) for row in rows]


def _build_with_amount(field: str, value: Any) -> None:
    """Put one already-built amount into the named field of an otherwise valid case."""
    if field == "call.hold_usd":
        CallLine(call="CP-0/0", state="ok", hold_usd=value, billed_usd=Decimal(1))
    elif field == "call.billed_usd":
        CallLine(call="CP-0/0", state="ok", hold_usd=Decimal(1), billed_usd=value)
    elif field == "compaction.billed_usd":
        CompactionLine(
            call="CP-0/0", event_id="ev-1", outcome="done", supersedes=None, billed_usd=value
        )
    elif field == "cap":
        admit_call([], cap_usd=value, next_hold_usd=Decimal(1))
    else:
        admit_call([], cap_usd=Decimal(1), next_hold_usd=value)


@pytest.mark.parametrize("name", list(key.TOTALS), ids=list(key.TOTALS))
def test_d6_d7_totals_follow_the_key(name: str) -> None:
    rows, spent, unknown = key.TOTALS[name]
    lines = _lines(rows)
    result = total(lines)
    assert isinstance(result, Total)
    if spent is None:
        assert result.spent_usd is None
    else:
        assert result.spent_usd is not None
        assert result.spent_usd == Decimal(spent)
    assert len(result.unknown) == len(unknown)
    assert all(got is lines[i] for got, i in zip(result.unknown, unknown, strict=True))


@pytest.mark.parametrize("name", list(key.ADMISSIONS), ids=list(key.ADMISSIONS))
def test_g5_admissions_follow_the_key(name: str) -> None:
    rows, cap, next_hold, admitted, stop, over = key.ADMISSIONS[name]
    lines = _lines(rows)
    result = admit_call(lines, cap_usd=Decimal(cap), next_hold_usd=Decimal(next_hold))
    assert isinstance(result, Admission)
    assert result.admitted is admitted
    assert (None if result.stop is None else result.stop.value) == stop
    assert len(result.over_hold) == len(over)
    assert all(got is lines[i] for got, i in zip(result.over_hold, over, strict=True))


def test_d9_stops_are_the_keys_store_identifiers() -> None:
    assert tuple(stop.value for stop in BudgetStop) == key.STOPS


_BAD = [(name, field) for name in key.BAD_AMOUNTS for field in key.AMOUNT_FIELDS]
_GOOD = [(text, field) for text in key.GOOD_AMOUNTS for field in key.AMOUNT_FIELDS]


@pytest.mark.parametrize(("name", "field"), _BAD, ids=[f"{name}-{field}" for name, field in _BAD])
def test_d9_bad_amounts_are_refused(name: str, field: str) -> None:
    with pytest.raises(BudgetDataError):
        _build_with_amount(field, _amount(key.BAD_AMOUNTS[name]))


@pytest.mark.parametrize(
    ("text", "field"), _GOOD, ids=[f"{text[:8]}-{field}" for text, field in _GOOD]
)
def test_d9_good_amounts_are_accepted(text: str, field: str) -> None:
    _build_with_amount(field, Decimal(text))


@pytest.mark.parametrize("name", list(key.BAD_LINES), ids=list(key.BAD_LINES))
def test_d6_bad_lines_are_refused(name: str) -> None:
    with pytest.raises(BudgetDataError):
        _line(key.BAD_LINES[name])


@pytest.mark.parametrize("name", list(key.BAD_SETS), ids=list(key.BAD_SETS))
def test_d6_bad_sets_are_refused(name: str) -> None:
    lines = _lines(key.BAD_SETS[name])
    with pytest.raises(BudgetDataError):
        total(lines)
    with pytest.raises(BudgetDataError):
        admit_call(lines, cap_usd=Decimal(1000), next_hold_usd=Decimal(1))


def test_d9_a_foreign_item_in_the_lines_is_refused() -> None:
    with pytest.raises(BudgetDataError):
        total([("call", "CP-0/0", "ok", Decimal(1), Decimal(1))])  # type: ignore[list-item]


def test_d9_the_valid_key_rows_build() -> None:
    _line(key.VALID_CALL)
    _line(key.VALID_COMPACTION)


# ------------------------------------------------------------------ properties

# Known amounts across the store's bounds: up to 40 digits, exponent -62..23 keeps the
# digits within 64 while spanning many magnitudes.
_amounts = st.builds(
    lambda digits, exponent: Decimal(digits).scaleb(exponent),
    st.integers(min_value=0, max_value=10**40),
    st.integers(min_value=-62, max_value=23),
)
_known_states = st.sampled_from(["ok", "sent_usage", "sent_unknown"])
_known_calls = st.builds(
    lambda charge, state, hold: CallLine(
        call="CP-0/0", state=state, hold_usd=hold, billed_usd=charge
    ),
    _amounts,
    _known_states,
    _amounts,
)
_known_calls_list = st.lists(_known_calls, max_size=30)
_unknown_lines = st.sampled_from(
    [
        CallLine(call="CP-9/9", state="open", hold_usd=Decimal(1), billed_usd=None),
        CallLine(call="CP-9/9", state="ok", hold_usd=Decimal(1), billed_usd=None),
        CompactionLine(
            call="CP-9/9", event_id="ev-x", outcome="failed", supersedes=None, billed_usd=None
        ),
    ]
)


def _exact(lines: list[CallLine]) -> Fraction:
    return sum(
        (Fraction(line.billed_usd) for line in lines if line.billed_usd is not None), Fraction(0)
    )


@settings(max_examples=200, deadline=None)
@given(lines=_known_calls_list, data=st.data())
def test_d6_total_is_exact_and_independent_of_order(lines: list[CallLine], data: Any) -> None:
    shuffled = data.draw(st.permutations(lines))
    first, second = total(lines), total(shuffled)
    assert first.spent_usd is not None
    assert second.spent_usd is not None
    assert Fraction(first.spent_usd) == _exact(lines)
    assert Fraction(second.spent_usd) == _exact(lines)
    assert first.unknown == () == second.unknown


@settings(max_examples=200, deadline=None)
@given(lines=_known_calls_list, odd=_unknown_lines, data=st.data())
def test_d7_one_unknown_line_anywhere_makes_the_total_unknown(
    lines: list[CallLine], odd: CallLine | CompactionLine, data: Any
) -> None:
    at = data.draw(st.integers(min_value=0, max_value=len(lines)))
    mixed = [*lines[:at], odd, *lines[at:]]
    result = total(mixed)
    assert result.spent_usd is None
    assert len(result.unknown) == 1
    assert result.unknown[0] is mixed[at]


@settings(max_examples=200, deadline=None)
@given(
    lines=st.lists(_known_calls, max_size=30),
    cap=_amounts,
    next_hold=_amounts,
)
def test_g5_admission_is_the_exact_comparison(
    lines: list[CallLine], cap: Decimal, next_hold: Decimal
) -> None:
    # Give every call a hold at least its charge, so no line is over its hold.
    held = [
        CallLine(call=ln.call, state=ln.state, hold_usd=ln.billed_usd, billed_usd=ln.billed_usd)
        for ln in lines
        if ln.billed_usd is not None
    ]
    result = admit_call(held, cap_usd=cap, next_hold_usd=next_hold)
    assert result.over_hold == ()
    assert result.admitted is (_exact(held) + Fraction(next_hold) <= Fraction(cap))
    assert (result.stop is None) is result.admitted
