"""The Overview's headline figures, compared row by row with the controller's key."""

import json
from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest

from credit_os.delivery.errors import DeliveryRefused
from credit_os.delivery.metrics import overview_metrics
from credit_os.delivery.wording import load_wording
from credit_os.handoff.document import HandoffDocument, parse

ROOT = Path(__file__).resolve().parents[2]
KEY = json.loads((Path(__file__).parent / "expected" / "overview-figures.json").read_text("utf-8"))
FIXTURE = (ROOT / KEY["metrics_fixture"]).read_text("utf-8")
ANCHOR: str = KEY["anchor"]
ROWS: list[dict[str, object]] = KEY["metrics"]
WORDING = load_wording()


def document_with(insert: str) -> HandoffDocument:
    assert FIXTURE.count(ANCHOR) == 1
    return parse(FIXTURE.replace(ANCHOR, insert + ANCHOR).encode("utf-8"))


def exact(metric: dict[str, object]) -> dict[str, object]:
    """A key metric with its value's `at` read as a Decimal, so the whole list compares exactly."""
    value = metric["value"]
    if isinstance(value, dict) and isinstance(value.get("at"), str):
        return {**metric, "value": {**value, "at": Decimal(value["at"])}}
    return metric


@pytest.mark.parametrize(
    "row",
    [r for r in ROWS if "refused" not in r],
    ids=[str(r["id"]) for r in ROWS if "refused" not in r],
)
def test_metrics(row: dict[str, object]) -> None:
    built = overview_metrics(document_with(str(row["insert"])), WORDING)
    want = [exact(metric) for metric in cast(list[dict[str, object]], row["expected"])]
    assert built == want
    assert [list(metric) for metric in built] == [list(metric) for metric in want]
    for metric in built:
        value = cast(dict[str, object] | None, metric["value"])
        if value is not None and value["kind"] == "value" and value["at"] is not None:
            assert type(value["at"]) is Decimal


@pytest.mark.parametrize(
    "row", [r for r in ROWS if "refused" in r], ids=[str(r["id"]) for r in ROWS if "refused" in r]
)
def test_refused(row: dict[str, object]) -> None:
    with pytest.raises(DeliveryRefused) as raised:
        overview_metrics(document_with(str(row["insert"])), WORDING)
    assert str(raised.value)
    assert str(row["insert"]).strip() not in str(raised.value)
    for fragment in ("CP-2", "NBG_2025"):
        assert fragment not in str(raised.value)
