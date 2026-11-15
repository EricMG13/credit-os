import json
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from credit_os.handoff.basis import read_basis
from credit_os.handoff.blocks import ListItem, Paragraph, read_blocks
from credit_os.handoff.lead import Lead, read_lead
from credit_os.handoff.lines import split_lines
from credit_os.handoff.scan import scan

HERE = Path(__file__).resolve().parent
HANDOFFS = HERE.parent / "fixtures" / "handoffs"
CASES: list[dict[str, Any]] = json.loads(
    (HERE / "expected" / "lead-labels.json").read_text(encoding="utf-8")
)["cases"]


def _block(case: dict[str, Any]) -> Paragraph | ListItem:
    lines = tuple(case["lines"])
    if case["block"] == "paragraph":
        return Paragraph(line=7, lines=lines)
    if case["block"] == "list":
        return ListItem(line=7, marker="-", lines=lines)
    raise ValueError(case["block"])


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_key_case(case: dict[str, Any]) -> None:
    expected = case["expected"]
    want = (
        None
        if expected is None
        else Lead(line=7, label=expected["label"], rest=tuple(expected["rest"]))
    )
    block = _block(case)
    assert read_lead(block) == want
    if "basis_line" in case:
        rest = expected["rest"]
        label = expected["label"]
        assert [f"**{label}** {rest[0]}", *rest[1:], case["basis_line"]] == list(case["lines"])
        assert read_basis(block) is not None


GENERATED: list[dict[str, Any]] = json.loads(
    (HERE / "expected" / "lead-labels.json").read_text(encoding="utf-8")
)["generated"]


@pytest.mark.parametrize("row", GENERATED, ids=[r["id"] for r in GENERATED])
def test_generated_case(row: dict[str, Any]) -> None:
    line = row["prefix"] + row["fill"] * row["count"] + row["suffix"]
    expected = row["expected"]
    if expected is None:
        want = None
    else:
        label = expected["label_fill"] * expected["label_count"]
        rest = (
            tuple(expected["rest"])
            if "rest" in expected
            else (expected["rest_fill"] * expected["rest_count"],)
        )
        want = Lead(line=1, label=label, rest=rest)
    assert read_lead(Paragraph(line=1, lines=(line,))) == want


def test_fixture_invariants() -> None:
    seen = 0
    for path in sorted(HANDOFFS.glob("*/*.md")):
        text = path.read_text(encoding="utf-8")
        for block in read_blocks(scan(split_lines(text))):
            if not isinstance(block, Paragraph | ListItem):
                continue
            seen += 1
            lead = read_lead(block)
            if lead is None:
                continue
            basis = read_basis(block)
            lines = basis.body if basis is not None else block.lines
            assert lines[0].startswith("**" + lead.label + "**")
    assert seen > 0


@given(st.text())
def test_property_no_raise_no_star(text: str) -> None:
    lead = read_lead(Paragraph(line=1, lines=(text,)))
    assert lead is None or "*" not in lead.label
