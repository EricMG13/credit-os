"""Facility terms printed, facility totals against base debt, against the controller's key."""

import decimal
import json
from pathlib import Path
from typing import Any

import pytest

from credit_os.handoff.document import parse
from credit_os.handoff.errors import HandoffError
from credit_os.model.foundation import check_foundation
from credit_os.model.inputs import parse_inputs
from credit_os.model.inputs_json import read_forecast_document
from credit_os.model.refusals import ForecastRefused, RefusalKind

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "model"
KEY = json.loads((Path(__file__).with_name("expected") / "pr6b.json").read_text("utf-8"))
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
    document = read_forecast_document(parse((FIXTURES / row["source"]).read_bytes()))
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


def test_the_key_has_its_rows() -> None:
    assert len(ROWS) == 118
    assert sum(row["outcome"] is None for row in ROWS) == 40


@pytest.mark.parametrize("label", LABELS)
def test_row(label: str) -> None:
    row = ROWS[LABELS.index(label)]
    assert _outcome(row) == row["outcome"]


@pytest.mark.parametrize("label", LABELS)
def test_row_under_a_hostile_context(label: str) -> None:
    row = ROWS[LABELS.index(label)]
    with decimal.localcontext(decimal.Context(prec=5, rounding=decimal.ROUND_UP)):
        assert _outcome(row) == row["outcome"]


def test_the_facility_refusal_kind_follows_currency() -> None:
    kinds = [kind.value for kind in RefusalKind]
    assert kinds[-5:] == ["cell", "unit", "currency", "facility", "source"]
