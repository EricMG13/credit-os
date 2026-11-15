"""ForecastResult and run_forecast against the answer key (R60, R61)."""

import dataclasses
import decimal
import importlib.util
import json
from pathlib import Path
from typing import Any, cast

import pytest

from credit_os.handoff.document import HandoffDocument, parse
from credit_os.model import run
from credit_os.model.cases import StressBasis, run_cases
from credit_os.model.forecast import forecast
from credit_os.model.refusals import ForecastRefused, RefusalKind
from credit_os.model.value import Missing, MissingCode, Value, amount_text

ForecastResult, ForecastSource = run.ForecastResult, run.ForecastSource
LIMIT, LAYER1_LIMIT, scale_limit = run.LIMIT, run.LAYER1_LIMIT, run.scale_limit
read_checked, run_forecast = run.read_checked, run.run_forecast

EXPECTED = Path(__file__).parent / "expected"
KEY = json.loads((EXPECTED / "pr7c2.json").read_text("utf-8"))
ROWS = KEY["rows"]
FIELDS = KEY["fields"]
DETAIL_FIELDS = ("opening", "rate", "interest", "repaid", "closing")
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "model"

HELPERS = importlib.util.spec_from_file_location(
    "case_key_helpers", EXPECTED / "case_key_helpers.py"
)
assert HELPERS is not None and HELPERS.loader is not None
H = importlib.util.module_from_spec(HELPERS)
HELPERS.loader.exec_module(H)
ORACLE = H.load_oracle("make_pr7c2")
HOSTILE, ids = H.HOSTILE, H.ids
CASH_TEXT = "Not calculable: cash is negative before funding"
GAP = Value(missing=Missing(MissingCode.NEGATIVE_CASH, CASH_TEXT))


def document(spec: dict[str, Any] | None) -> HandoffDocument | None:
    return None if spec is None else parse(ORACLE.C1.data(spec))


def documents(
    row: dict[str, Any],
) -> tuple[HandoffDocument, Any, HandoffDocument | None]:
    foundation = document(row["foundation"])
    assert foundation is not None
    return foundation, ForecastSource(row["source"]), document(row["forward"])


def run_row(row: dict[str, Any]) -> Any:
    foundation, source, forward = documents(row)
    return run_forecast(foundation, source, forward)


def same_value(got: Value, item: Any, where: str) -> None:
    H.same_value(KEY["reasons"], got, item, where)


def check_detail(result: Any, exp: dict[str, Any] | None, where: str) -> None:
    if exp is None:
        assert result.facilities is None, where
        return
    assert type(result.facilities.facilities) is tuple, where
    assert len(result.facilities.facilities) == len(exp["facilities"]), where
    for got, item in zip(result.facilities.facilities, exp["facilities"], strict=True):
        assert got.facility.name == item["name"], where
        for (year, pair), (want_year, figures) in zip(got.years, item["years"], strict=True):
            assert year == want_year, where
            texts = [amount_text(getattr(pair, f)) for f in DETAIL_FIELDS]
            assert texts == figures, f"{where} {item['name']} {year}"
    same_value(result.facilities.unallocated, exp["unallocated"], where)


def check_result(result: Any, exp: dict[str, Any], where: str) -> None:
    assert type(result) is ForecastResult, where
    assert result.foundation_sha256 == exp["foundation_sha256"], where
    assert result.forward_sha256 == exp["forward_sha256"], where
    assert (result.currency, result.scale) == (exp["currency"], exp["scale"]), where
    assert type(result.spans) is tuple, where
    assert [(s.year, s.start, s.end) for s in result.spans] == [tuple(s) for s in exp["spans"]]
    assert (result.stress_basis is None) == (exp["stress_basis"] is None), where
    if result.stress_basis is not None:
        assert result.stress_basis is StressBasis(exp["stress_basis"]), where
    assert type(result.cases) is tuple, where
    assert [c.name.value for c in result.cases] == [c["name"] for c in exp["cases"]], where
    for got, key in zip(result.cases, exp["cases"], strict=True):
        assert type(got.years) is tuple and len(got.years) == 3, where
        for t, (year, items) in enumerate(zip(got.years, key["years"], strict=True)):
            for name, item in zip(FIELDS, items, strict=True):
                same_value(getattr(year, name), item, f"{where} {key['name']} y{t + 1} {name}")
    check_detail(result, exp["facilities"], where)
    assert type(result.limits) is tuple, where
    assert list(result.limits) == exp["limits"], where


def check_row(row: dict[str, Any]) -> None:
    result = run_row(row)
    assert result.source is ForecastSource(row["source"]), row["name"]
    check_result(result, row["expected"], row["name"])


@pytest.mark.parametrize("row", ROWS, ids=ids(ROWS))
def test_key_row(row: dict[str, Any]) -> None:
    check_row(row)


@pytest.mark.parametrize("row", ROWS, ids=ids(ROWS))
def test_key_row_under_a_hostile_local_context(row: dict[str, Any]) -> None:
    with decimal.localcontext(HOSTILE):
        check_row(row)


def test_row_counts() -> None:
    assert len(ROWS) == 13
    assert KEY["kinds"] == {"accepted": 13}
    assert len({r["name"] for r in ROWS}) == 13


def test_fixture_rows_carry_the_committed_hashes() -> None:
    sums = {}
    for text in (FIXTURES / "SHA256SUMS").read_text("ascii").splitlines():
        digest, name = text.split("  ")
        sums[name] = digest
    seen = 0
    for row in ROWS:
        for key, hash_key in (("foundation", "foundation_sha256"), ("forward", "forward_sha256")):
            spec = row[key]
            if spec is not None and set(spec) == {"file"}:
                assert row["expected"][hash_key] == sums[spec["file"]], row["name"]
                seen += 1
    assert seen >= 8


def test_texts_and_fields_match_the_key() -> None:
    assert LIMIT == KEY["limit"] and LAYER1_LIMIT == KEY["layer1_limit"]
    assert scale_limit("USD") == KEY["scale_limit"].format(currency="USD")
    assert scale_limit("EUR") == KEY["scale_limit"].format(currency="EUR")
    assert scale_limit("EUR").count("EUR") == 2 and "USD" not in scale_limit("EUR")
    assert [k.value for k in RefusalKind][-2:] == ["source", "size"]
    assert [f.name for f in dataclasses.fields(ForecastResult)] == [
        "source",
        "foundation_sha256",
        "forward_sha256",
        "currency",
        "scale",
        "spans",
        "cases",
        "stress_basis",
        "facilities",
        "limits",
    ]


def by_name(name: str) -> dict[str, Any]:
    return next(r for r in ROWS if r["name"] == name)


def result_of(name: str) -> Any:
    return run_row(by_name(name))


def with_year(result: Any, **changes: Value) -> Any:
    first = result.cases[0]
    year = dataclasses.replace(first.years[0], **changes)
    case = dataclasses.replace(first, years=(year, *first.years[1:]))
    return dataclasses.replace(result, cases=(case, *result.cases[1:]))


NEGATIVE = {"closing_cash": Value(amount=decimal.Decimal(-1))}
THREE = ("net_debt", "net_leverage", "liquidity")
D8_TEXT = "a year with negative closing cash carries the negative-cash gap"


def test_a_negative_cash_year_with_the_gap_is_accepted() -> None:
    result = with_year(result_of("forward_millions"), **NEGATIVE, **dict.fromkeys(THREE, GAP))
    assert result.cases[0].years[0].closing_cash == NEGATIVE["closing_cash"]


@pytest.mark.parametrize("field", THREE)
@pytest.mark.parametrize(
    "value",
    [
        Value(amount=decimal.Decimal(5)),
        Value(missing=Missing(MissingCode.NOT_SOURCED, "x")),
        Value(missing=Missing(MissingCode.NEGATIVE_CASH, "another text")),
        Value(missing=Missing(MissingCode.ZERO_OR_NEGATIVE_DENOMINATOR, CASH_TEXT)),
    ],
    ids=["amount", "not_sourced", "other_text", "other_code"],
)
def test_a_negative_cash_year_without_the_gap_is_refused(field: str, value: Value) -> None:
    gap = dict.fromkeys(THREE, GAP) | {field: value}
    with pytest.raises(ValueError, match=f"^{D8_TEXT}$"):
        with_year(result_of("forward_millions"), **NEGATIVE, **gap)


@pytest.mark.parametrize(
    "cash",
    [
        Value(amount=decimal.Decimal(0)),
        Value(amount=decimal.Decimal("-0")),
        Value(amount=decimal.Decimal("0.0001")),
        Value(missing=Missing(MissingCode.NOT_SOURCED, "no cash")),
    ],
    ids=["zero", "minus_zero", "positive", "missing"],
)
def test_a_year_that_is_not_below_zero_needs_no_gap(cash: Value) -> None:
    other = Value(amount=decimal.Decimal(5))
    with_year(result_of("forward_millions"), closing_cash=cash, **dict.fromkeys(THREE, other))


def test_the_gap_is_refused_in_the_last_case_and_year_too() -> None:
    result = result_of("forward_millions")
    last = result.cases[-1]
    bad = dataclasses.replace(last.years[2], **NEGATIVE)
    case = dataclasses.replace(last, years=(*last.years[:2], bad))
    with pytest.raises(ValueError, match=f"^{D8_TEXT}$"):
        dataclasses.replace(result, cases=(*result.cases[:-1], case))


def test_the_result_is_frozen() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        cast(Any, result_of("forward_millions")).currency = "EUR"


SIZE_TEXT = (
    "the {} case needs a figure of more than 38 significant digits; no forecast was computed"
)


def fail_nth(monkeypatch: pytest.MonkeyPatch, nth: int, error: Exception) -> list[int]:
    calls: list[int] = []

    def patched(*args: Any, **kwargs: Any) -> Any:
        calls.append(1)
        if len(calls) == nth:
            raise error
        return forecast(*args, **kwargs)

    monkeypatch.setattr("credit_os.model.cases.forecast", patched)
    return calls


@pytest.mark.parametrize(
    "error", [decimal.Inexact, decimal.Overflow, decimal.Underflow], ids=lambda e: e.__name__
)
@pytest.mark.parametrize(
    ("nth", "name"),
    [(1, "reference"), (2, "upside"), (3, "downside"), (4, "downside_stress")],
)
def test_an_engine_overflow_is_a_size_refusal_naming_the_case(
    monkeypatch: pytest.MonkeyPatch, nth: int, name: str, error: type[Exception]
) -> None:
    calls = fail_nth(monkeypatch, nth, error("too wide"))
    with pytest.raises(ForecastRefused) as refused:
        result_of("forward_millions")
    assert refused.value.kind is RefusalKind.SIZE
    assert refused.value.subject == name
    assert refused.value.message == SIZE_TEXT.format(name)
    assert len(calls) == nth


def test_run_cases_alone_refuses_the_same_way(monkeypatch: pytest.MonkeyPatch) -> None:
    foundation, source, forward = documents(by_name("forward_millions"))
    inputs, _ = read_checked(foundation, source, forward)
    fail_nth(monkeypatch, 4, decimal.Inexact("too wide"))
    with pytest.raises(ForecastRefused) as refused:
        run_cases(inputs)
    assert (refused.value.kind, refused.value.subject) == (RefusalKind.SIZE, "downside_stress")


def test_a_layer_1_size_refusal_names_the_reference_case(monkeypatch: pytest.MonkeyPatch) -> None:
    fail_nth(monkeypatch, 1, decimal.Overflow("too wide"))
    with pytest.raises(ForecastRefused) as refused:
        result_of("layer1_millions")
    assert refused.value.subject == "reference"
    assert refused.value.message == SIZE_TEXT.format("reference")


@pytest.mark.parametrize("error", [decimal.InvalidOperation, ValueError, ZeroDivisionError])
def test_any_other_engine_failure_is_not_a_size_refusal(
    monkeypatch: pytest.MonkeyPatch, error: type[Exception]
) -> None:
    fail_nth(monkeypatch, 2, error("not a size"))
    with pytest.raises(error) as caught:
        result_of("forward_millions")
    assert not isinstance(caught.value, ForecastRefused)
