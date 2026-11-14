"""The foundation's tables, the named cell and the sign rule, against the controller's key."""

import decimal
import json
from pathlib import Path
from typing import Any

import pytest

from credit_os.handoff.document import parse
from credit_os.handoff.errors import HandoffError
from credit_os.model.foundation import check_base, foundation_tables
from credit_os.model.inputs import parse_inputs
from credit_os.model.inputs_json import read_forecast_document
from credit_os.model.refusals import ForecastRefused

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "model"
KEY = json.loads((Path(__file__).with_name("expected") / "pr5.json").read_text("utf-8"))
ROWS = KEY["rows"]
LABELS = [row["label"] for row in ROWS]


def _foundation(row: dict[str, Any]) -> Any:
    text = (FIXTURES / row.get("foundation", "foundation.md")).read_text("utf-8")
    for old, new in row.get("edits", []):
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    return parse(text.encode("utf-8"))


def _block(row: dict[str, Any]) -> dict[str, object]:
    name = row.get("source", row.get("foundation", "foundation.md"))
    document = read_forecast_document(parse((FIXTURES / name).read_bytes()))
    for path, *value in row.get("ops", []):
        holder: Any = document
        for step in path[:-1]:
            holder = holder[step]
        if value:
            holder[path[-1]] = value[0]
        else:
            del holder[path[-1]]
    return document


def _outcome(row: dict[str, Any]) -> list[str] | None:
    try:
        foundation = _foundation(row)
        inputs, stated = parse_inputs(_block(row))
        check_base(inputs, stated, foundation)
    except ForecastRefused as error:
        return [error.kind.value, error.subject, error.message]
    except HandoffError as error:
        return ["HandoffError", str(error)]
    return None


@pytest.mark.parametrize("label", LABELS)
def test_row(label: str) -> None:
    row = ROWS[LABELS.index(label)]
    assert _outcome(row) == row["outcome"]


@pytest.mark.parametrize("label", LABELS)
def test_row_under_a_hostile_context(label: str) -> None:
    row = ROWS[LABELS.index(label)]
    with decimal.localcontext(decimal.Context(prec=5, rounding=decimal.ROUND_UP)):
        assert _outcome(row) == row["outcome"]


@pytest.mark.parametrize("label", LABELS)
def test_arguments_are_unchanged(label: str) -> None:
    row = ROWS[LABELS.index(label)]
    foundation = _foundation(row)
    inputs, stated = parse_inputs(_block(row))
    before = (inputs.model_dump(), dict(stated), foundation.model_dump())
    try:
        check_base(inputs, stated, foundation)
    except (ForecastRefused, HandoffError):
        pass
    assert (inputs.model_dump(), dict(stated), foundation.model_dump()) == before


@pytest.mark.parametrize("name", list(KEY["tables"]))
def test_tables(name: str) -> None:
    document = parse((FIXTURES / name).read_bytes())
    assert [table.line for table in foundation_tables(document)] == KEY["tables"][name]


def test_a_stated_map_missing_a_key_at_scale_1000_is_a_key_error() -> None:
    row = {"foundation": "foundation-thousands.md"}
    inputs, stated = parse_inputs(_block(row))
    assert inputs.scale == 1000
    del stated["base revenue"]
    with pytest.raises(KeyError):
        check_base(inputs, stated, _foundation(row))


def _base(fixture: dict[str, Any], **changes: Any) -> Any:
    """The accepted foundation row's inputs with the revenue operand's fields replaced."""
    inputs, stated = parse_inputs(_block(fixture))
    operand = inputs.base["revenue"].model_copy(update=changes)
    return inputs.model_copy(update={"base": {**inputs.base, "revenue": operand}}), stated


def _refusal(fixture: dict[str, Any], **changes: Any) -> list[str]:
    inputs, stated = _base(fixture, **changes)
    with pytest.raises(ForecastRefused) as caught:
        check_base(inputs, stated, _foundation(fixture))
    error = caught.value
    return [error.kind.value, error.subject, error.message]


_NAMED = (
    "base revenue must name the `row` label and either the `period` header "
    "or the `column` header it was read from"
)


@pytest.mark.parametrize("changes", [{"row": None}, {"period": None, "column": None}])
def test_a_missing_name_is_refused_as_unnamed(changes: dict[str, Any]) -> None:
    assert _refusal({}, **changes) == ["cell", "base revenue", _NAMED]


def test_a_missing_row_with_a_blank_header_is_unnamed() -> None:
    assert _refusal({}, row=None, period=" ") == ["cell", "base revenue", _NAMED]


def test_only_emphasis_marks_are_stripped_from_a_label() -> None:
    assert _refusal({}, row="XRevenueX")[2].startswith("base revenue: no table cell of CP-1 is at")


def test_a_bracketed_cell_with_a_thousands_comma_is_a_negative_number() -> None:
    row = {"edits": [["| Revenue | 1,318 | 1,456 |", "| Revenue | 1,318 | (1,456) |"]]}
    inputs, stated = _base(row, amount="-1456")
    check_base(inputs, stated, _foundation(row))


def test_exactly_five_cells_have_no_more_clause() -> None:
    extra = "".join(f"| Revenue | 1,40{n} |\n" for n in range(4))
    calc = "Net debt is Total Debt less Cash & Equivalents.\n"
    table = "| Line item | FY2024 |\n| --- | --- |\n"
    row = {"edits": [[calc, f"{calc}\n{table}{extra}"]]}
    message = _refusal(row)[2]
    assert "(5 cells: " in message
    assert message.endswith("'])")
    assert " more" not in message
