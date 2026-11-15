"""The Overview's dates, compared row by row with the controller's key."""

import json
from pathlib import Path
from typing import cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

from credit_os.delivery.dates import overview_dates
from credit_os.delivery.errors import DeliveryRefused
from credit_os.delivery.wording import load_wording
from credit_os.handoff.document import HandoffDocument, parse

ROOT = Path(__file__).resolve().parents[2]
KEY = json.loads((Path(__file__).parent / "expected" / "overview-figures.json").read_text("utf-8"))
FIXTURES = ROOT / KEY["fixtures"]
ROWS: list[dict[str, object]] = KEY["dates"]
WORDING = load_wording()
CP_1A = (FIXTURES / "synthetic-new-format/SYNTHETIC-CP-1A.md").read_text("utf-8")
CP_1A_KEY = next(r for r in ROWS if r["id"] == "cp-1a")
EVENT_ROW_PREFIX = "| 20"


def document_for(row: dict[str, object]) -> HandoffDocument:
    text = (FIXTURES / str(row["file"])).read_text("utf-8")
    for old, new in cast(list[list[str]], row["replace"]):
        assert text.count(old) == 1
        text = text.replace(old, new, 1)
    return parse(text.encode("utf-8"))


@pytest.mark.parametrize(
    "row",
    [r for r in ROWS if "refused" not in r],
    ids=[str(r["id"]) for r in ROWS if "refused" not in r],
)
def test_dates(row: dict[str, object]) -> None:
    built = overview_dates(document_for(row), str(row["as_of"]), WORDING)
    assert built == row["expected"]
    for item in built or []:
        assert list(item) == ["date", "state", "title", "text"]


@pytest.mark.parametrize(
    "row", [r for r in ROWS if "refused" in r], ids=[str(r["id"]) for r in ROWS if "refused" in r]
)
def test_refused(row: dict[str, object]) -> None:
    with pytest.raises(DeliveryRefused) as raised:
        overview_dates(document_for(row), str(row["as_of"]), WORDING)
    assert str(raised.value)
    for fragment in ("NBG_2025", "CP-2", "Coupon", "Cash interest"):
        assert fragment not in str(raised.value)


def event_lines() -> list[str]:
    lines = [line for line in CP_1A.split("\n") if line.startswith(EVENT_ROW_PREFIX)]
    assert len(lines) == 9
    return lines


@given(st.permutations(event_lines()))
def test_row_order_in_the_source_does_not_change_the_items(rows: list[str]) -> None:
    lines = CP_1A.split("\n")
    first = next(i for i, line in enumerate(lines) if line.startswith(EVENT_ROW_PREFIX))
    shuffled = [*lines[:first], *rows, *lines[first + len(rows) :]]
    document = parse("\n".join(shuffled).encode("utf-8"))
    built = overview_dates(document, str(CP_1A_KEY["as_of"]), WORDING)
    assert built == CP_1A_KEY["expected"]
