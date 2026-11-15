"""The chart-table and gap record blocks of delivery, compared row by row with the controller's key."""

import json
from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

from credit_os.delivery.errors import DeliveryRefused
from credit_os.delivery.records import chart_records
from credit_os.delivery.wording import load_wording
from credit_os.handoff.document import HandoffDocument, parse

ROOT = Path(__file__).resolve().parents[2]
KEY = json.loads((Path(__file__).parent / "expected" / "records.json").read_text("utf-8"))
FIXTURE = (ROOT / KEY["fixture"]).read_text("utf-8")
ROWS: list[dict[str, object]] = KEY["rows"]
WORDING = load_wording()


def document_with(insert: str, anchor: str = KEY["anchor"]) -> HandoffDocument:
    assert FIXTURE.count(anchor) == 1
    return parse(FIXTURE.replace(anchor, insert + anchor).encode("utf-8"))


def exact(cell: object) -> object:
    """A key cell with its `at` read as a Decimal, so the whole block compares exactly."""
    if isinstance(cell, dict) and isinstance(cell.get("at"), str):
        return {**cell, "at": Decimal(cell["at"])}
    return cell


def exact_block(block: dict[str, object]) -> dict[str, object]:
    if block["kind"] != "chartTable":
        return block
    rows = [
        {**row, "cells": [exact(cell) for cell in cast(list[object], row["cells"])]}
        for row in cast(list[dict[str, object]], block["rows"])
    ]
    return {**block, "rows": rows}


def positions(blocks: tuple[dict[str, object], ...]) -> list[object]:
    found: list[object] = []
    for block in blocks:
        if block["kind"] != "chartTable":
            continue
        for row in cast(list[dict[str, object]], block["rows"]):
            for cell in cast(list[object], row["cells"]):
                if isinstance(cell, dict) and cell["kind"] == "value":
                    found.append(cell["at"])
    return found


@pytest.mark.parametrize(
    "row",
    [r for r in ROWS if "refused" not in r],
    ids=[str(r["id"]) for r in ROWS if "refused" not in r],
)
def test_blocks(row: dict[str, object]) -> None:
    built = chart_records(document_with(str(row["insert"])), WORDING)
    want = [exact_block(block) for block in cast(list[dict[str, object]], row["expected"])]
    assert list(built) == want
    assert all(at is None or type(at) is Decimal for at in positions(built))
    assert [list(block.keys()) for block in built] == [
        list(block.keys()) for block in cast(list[dict[str, object]], row["expected"])
    ]


@pytest.mark.parametrize(
    "row", [r for r in ROWS if "refused" in r], ids=[str(r["id"]) for r in ROWS if "refused" in r]
)
def test_refused(row: dict[str, object]) -> None:
    with pytest.raises(DeliveryRefused) as raised:
        chart_records(document_with(str(row["insert"])), WORDING)
    assert str(raised.value)
    assert str(row["insert"]).strip() not in str(raised.value)


_PREFIX = st.sampled_from(["", "(", "-", "US$", "EUR ", "CP-"])
_SUFFIX = st.sampled_from(["", ")", "x", "%", "m", " million", "bn", " NBG_2025.pdf"])
_FIGURE = st.builds(
    lambda prefix, whole, fraction, suffix: f"{prefix}{whole}{fraction}{suffix}",
    _PREFIX,
    st.text(alphabet="0123456789,", min_size=1, max_size=9).map(lambda s: "1" + s),
    st.one_of(
        st.just(""), st.text(alphabet="0123456789", min_size=1, max_size=4).map(lambda d: "." + d)
    ),
    _SUFFIX,
)


@given(_FIGURE)
def test_figure_text_is_kept_or_refused(text: str) -> None:
    table = (
        "### Chart data: property\n\n"
        "| Period | Cash | Reporting unit | Basis and limitation |\n"
        "| --- | --- | --- | --- |\n"
        f"| FY2024 | {text} | US$m | Reported |\n\n"
    )
    try:
        blocks = chart_records(document_with(table), WORDING)
    except DeliveryRefused:
        return
    row = cast(list[dict[str, object]], blocks[0]["rows"])[0]
    got = cast(dict[str, object], cast(list[object], row["cells"])[1])
    assert got["kind"] == "value"
    assert got["text"] == text
