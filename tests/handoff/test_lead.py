import json
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from credit_os.handoff.basis import read_basis
from credit_os.handoff.blocks import ListItem, Paragraph
from credit_os.handoff.document import Section, parse
from credit_os.handoff.lead import Lead, read_lead

HERE = Path(__file__).resolve().parent
HANDOFFS = HERE.parent / "fixtures" / "handoffs"
CASES: list[dict[str, Any]] = json.loads(
    (HERE / "expected" / "lead-labels.json").read_text(encoding="utf-8")
)["cases"]


def _block(case: dict[str, Any]) -> Paragraph | ListItem:
    lines = tuple(case["lines"])
    if case["block"] == "paragraph":
        return Paragraph(line=7, lines=lines)
    return ListItem(line=7, marker="-", lines=lines)


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_key_case(case: dict[str, Any]) -> None:
    expected = case["expected"]
    want = (
        None
        if expected is None
        else Lead(line=7, label=expected["label"], rest=tuple(expected["rest"]))
    )
    assert read_lead(_block(case)) == want


def _walk(sections: tuple[Section, ...]) -> list[Section]:
    out: list[Section] = []
    for section in sections:
        out.append(section)
        out.extend(_walk(section.sections))
    return out


def test_fixture_invariants() -> None:
    seen = 0
    for path in sorted(HANDOFFS.glob("*/*.md")):
        if path.parent.name == "fragments":
            continue
        for section in _walk(parse(path.read_bytes()).sections):
            for block in section.blocks:
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
