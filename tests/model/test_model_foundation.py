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
