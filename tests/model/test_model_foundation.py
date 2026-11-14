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


_REV = ("| 1,318 | 1,456 |", "| 1,318 | {} |")
_WHERE = "row `{}`, period `FY2024`"


def _cell_edit(old: str, new: str) -> list[list[str]]:
    return [[old, new]]


def _many_message(cell: str) -> list[str]:
    where = _WHERE.format("Revenue")
    text = f"base revenue: {where} is not one number in CP-1 (1 cells: ['{cell}'])"
    return ["cell", "base revenue", text]


def _other(key: str, amount: str, row: str, cell: str) -> list[str]:
    where = _WHERE.format(row)
    text = f"base {key} {amount} is not CP-1's cell at {where} ({cell})"
    return ["cell", f"base {key}", text]


_BOTH_CONTEXTS = (
    decimal.getcontext,
    lambda: decimal.Context(prec=5, rounding=decimal.ROUND_UP),
)


def _both(row: dict[str, Any]) -> list[list[str] | None]:
    found = []
    for make in _BOTH_CONTEXTS:
        with decimal.localcontext(make()):
            found.append(_outcome(row))
    return found


@pytest.mark.parametrize(
    "cell",
    [".5", "+", "1,00", "1,0000", "1.", "١٤٥٦", "1.456.000", "1,456000", "1 456", "–1,456"]
    + ["+-1,456", "(-1,456)", "(1,456"],
)
def test_a_cell_form_that_is_not_a_number_is_not_one_number(cell: str) -> None:
    row = {"edits": _cell_edit(_REV[0], _REV[1].format(cell))}
    assert _both(row) == [_many_message(cell)] * 2


@pytest.mark.parametrize(
    ("old", "new", "key", "label", "amount", "cell"),
    [
        ("| 250 | 320 |", "| 250 | -320 |", "ebitda", "EBITDA (Reported)", "320", "-320"),
        (
            "| Cash & Equivalents | 197 | 283 |",
            "| Cash & Equivalents | 197 | -283 |",
            "cash",
            "Cash & Equivalents",
            "283",
            "-283",
        ),
        (
            "documents read | 175 | 175",
            "documents read | -175 | 175",
            "undrawn",
            "Undrawn committed facilities",
            "175",
            "-175",
        ),
    ],
)
def test_a_signed_operand_is_not_its_cell_printed_negative(
    old: str, new: str, key: str, label: str, amount: str, cell: str
) -> None:
    row = {"edits": _cell_edit(old, new)}
    assert _both(row) == [_other(key, amount, label, cell)] * 2


def test_debt_printed_negative_is_not_the_debt_amount() -> None:
    edits = [
        ["| Total Debt | 1,280 | 1,250 |", "| Total Debt | 1,280 | -1,250 |"],
        ["| Total Debt | 1,250 |  |", "| Total Debt | -1,250 |  |"],
    ]
    assert _both({"edits": edits}) == [_other("debt", "1250", "Total Debt", "-1,250")] * 2


def test_a_bracketed_cell_past_28_digits_is_exact() -> None:
    long = "(37.00000000000000000000000000001)"
    row = {"edits": _cell_edit("| -29 | -37 |", f"| -29 | {long} |")}
    want = _other("taxes", "37", "Income taxes paid", long)
    assert _both(row) == [want] * 2


def _revenue_row(row: str, amount: str = "1456") -> list[list[Any]]:
    return [[["base", "revenue", "row"], row], [["base", "revenue", "amount"], amount]]


def test_plain_strips_spaces_inside_and_outside_the_marks() -> None:
    assert _outcome({"edits": _cell_edit(_REV[0], _REV[1].format("** 1,456 **"))}) is None
    assert _outcome({"ops": _revenue_row(" **Revenue** ")}) is None
    assert _outcome({"ops": _revenue_row("Revenue ")}) is None


def test_plain_does_not_strip_a_tilde() -> None:
    where = "row `~Revenue~`, period `FY2024`"
    text = f"base revenue: no table cell of CP-1 is at {where}"
    assert _outcome({"ops": _revenue_row("~Revenue~")}) == ["cell", "base revenue", text]


@pytest.mark.parametrize("named", [{"period": "FY2024"}, {"row": "Undrawn"}, {"column": "Cash"}])
def test_a_reason_naming_any_one_of_row_period_column_is_located(named: dict[str, str]) -> None:
    operand = {"amount": None, "reason": "Not read.", "row": None, "period": None, "column": None}
    row = {"ops": [[["base", "undrawn"], {**operand, **named}]]}
    text = "base undrawn states no amount, so it names no row, period or column"
    assert _outcome(row) == ["cell", "base undrawn", text]


def test_the_other_message_shows_the_smallest_cell_text() -> None:
    edits = _cell_edit("| Total Debt | 1,250 |  |", "| Total Debt | 1250 |  |")
    ops = [[["base", "debt", "amount"], "1251"]]
    assert _outcome({"edits": edits, "ops": ops}) == _other("debt", "1251", "Total Debt", "1,250")


def test_the_where_clause_shows_the_row_as_stated() -> None:
    row = {"ops": _revenue_row("**Revenue**", "1457")}
    assert _outcome(row) == _other("revenue", "1457", "**Revenue**", "1,456")


def test_equal_texts_in_two_tables_are_one_cell() -> None:
    calc = "Net debt is Total Debt less Cash & Equivalents.\n"
    table = "| Line item | FY2024 |\n| --- | --- |\n| Total Debt | 1,251 |\n"
    edits = [["| Total Debt | 1,250 |  |", "| Total Debt | 1,251 |  |"], [calc, f"{calc}\n{table}"]]
    where = _WHERE.format("Total Debt")
    text = f"base debt: {where} is not one number in CP-1 (2 cells: ['1,250', '1,251'])"
    assert _outcome({"edits": edits}) == ["cell", "base debt", text]
