"""The foundation's text, units named and the currency named, against the controller's key."""

import decimal
import json
from pathlib import Path
from typing import Any

import pytest

from credit_os.handoff.document import parse
from credit_os.handoff.errors import HandoffError
from credit_os.model.foundation import (
    check_foundation,
    foundation_tables,
    foundation_text,
    names_currency,
    units_named,
)
from credit_os.model.inputs import parse_inputs
from credit_os.model.inputs_json import read_forecast_document
from credit_os.model.refusals import ForecastRefused, RefusalKind

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "model"
KEY = json.loads((Path(__file__).with_name("expected") / "pr6a.json").read_text("utf-8"))
ROWS = KEY["rows"]
LABELS = [row["label"] for row in ROWS]


def _edited(name: str, edits: list[list[str]]) -> str:
    text = (FIXTURES / name).read_text("utf-8")
    for old, new, *every in edits:
        if every == ["all"]:
            assert text.count(old) > 1, old
        else:
            assert every == [] and text.count(old) == 1, old
        text = text.replace(old, new)
    return text


def _foundation(row: dict[str, Any]) -> Any:
    name = row.get("foundation", "foundation.md")
    return parse(_edited(name, row.get("edits", [])).encode("utf-8"))


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
        check_foundation(inputs, stated, foundation)
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


@pytest.mark.parametrize(("text", "named"), KEY["words"])
def test_units_named(text: str, named: list[str]) -> None:
    assert units_named(text) == frozenset(named)


@pytest.mark.parametrize(("text", "code", "named"), KEY["currencies"])
def test_names_currency(text: str, code: str, named: bool) -> None:
    assert names_currency(text, code) is named


def test_the_foundation_text_is_the_kept_tables_and_prose() -> None:
    text = foundation_text(parse((FIXTURES / "foundation.md").read_bytes()))
    joined = "\n".join(text)
    assert "USD millions" in text
    assert "Net debt is Total Debt less Cash & Equivalents." in text
    assert "Annual report" not in joined
    assert "Statements and the debt note." not in joined
    assert "Harrow Vale Synthetic Industries reports earnings" not in joined
    assert "schema_version" not in joined
    assert "Calculations" not in joined


def test_the_foundation_text_holds_labels_columns_cells_and_list_items_in_order() -> None:
    source = (
        "# F\n\n## Request\nr\n\n## Sources\n\n| S | U |\n| --- | --- |\n| a | b |\n\n"
        "## Findings\n\n### Bottom line\n\nbl\n\n### Part\n\npara one\n"
        "- item\n\n**Figures**\n| Col A | Col B |\n| --- | --- |\n| c1 | c2 |\n\n"
        "```\ncode\n```\n\n## Calculations\ncalc\n\n## Gaps\ngap\n\n## Next module\nnext\n"
    )
    text = foundation_text(parse(source.encode("utf-8")))
    assert text == (
        "r",
        "para one",
        "item",
        "**Figures**",
        "Figures",
        "Col A",
        "Col B",
        "c1",
        "c2",
        "calc",
        "gap",
        "next",
    )


def test_foundation_tables_hold_a_section_table_before_its_subsection_table() -> None:
    own = "### Net debt data\n\n| Own | V |\n| --- | --- |\n| own-first | 1 |\n\n"
    sub = "#### Detail\n\n| Sub | V |\n| --- | --- |\n| sub-second | 2 |\n"
    text = _edited("foundation.md", [["### Net debt data\n", own + sub]])
    tables = foundation_tables(parse(text.encode("utf-8")))
    assert [table.rows[0].cells[0] for table in tables] == [
        "Revenue",
        "Net Cash from Operating Activities",
        "Total Assets",
        "Term loan B",
        "own-first",
        "sub-second",
        "FY2024",
        "FY2024",
        "FY2023",
        "Undrawn facilities at FY2023 not supplied",
    ]


def test_the_new_refusal_kinds_follow_cell() -> None:
    kinds = [kind.value for kind in RefusalKind]
    assert kinds[-3:] == ["cell", "unit", "currency"]


_CALC = "Net debt is Total Debt less Cash & Equivalents.\n"


def _with_table(table: str, ops: list[Any]) -> dict[str, Any]:
    return {"edits": [[_CALC, f"{_CALC}\n{table}"]], "ops": ops}


def _unit_message(what: str, cell: str, row: str = "Revenue check") -> list[str]:
    text = (
        f"base revenue: row `{row}` states its {what} as `{cell}`, not the block's unit "
        "(USD millions, scale 1); state a reason instead of an amount"
    )
    return ["unit", "base revenue", text]


def test_a_named_column_header_in_the_other_unit_is_called_a_column_header() -> None:
    table = "| Line item | Cash USD thousands |\n| --- | --- |\n| Revenue check | 1,456 |\n"
    ops = [
        [["base", "revenue", "row"], "Revenue check"],
        [["base", "revenue", "period"], None],
        [["base", "revenue", "column"], "Cash USD thousands"],
    ]
    want = _unit_message("column header", "Cash USD thousands")
    assert _outcome(_with_table(table, ops)) == want


def test_a_unit_cell_naming_the_block_unit_excuses_the_rows_note_in_the_other_unit() -> None:
    table = (
        "| Line item | FY2024 | Unit | Note |\n| --- | --- | --- | --- |\n"
        "| Revenue check | 1,456 | USD millions | in thousands |\n"
    )
    ops = [[["base", "revenue", "row"], "Revenue check"]]
    assert _outcome(_with_table(table, ops)) is None
