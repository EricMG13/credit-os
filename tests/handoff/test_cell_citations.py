import json
from pathlib import Path
from typing import Any, cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

from credit_os.handoff.basis import BasisItem, read_basis, read_cell
from credit_os.handoff.blocks import Paragraph
from credit_os.handoff.document import Section, parse
from credit_os.handoff.tables import Table

HERE = Path(__file__).resolve().parent
NEW_FORMAT = HERE.parent / "fixtures" / "handoffs" / "synthetic-new-format"
CASES = json.loads((HERE / "expected" / "cell-citations.json").read_text(encoding="utf-8"))["cases"]


def _expected(rows: list[dict[str, Any]]) -> tuple[BasisItem, ...]:
    return tuple(
        BasisItem(**{**row, "pages": tuple((a, b) for a, b in row.get("pages", []))})
        for row in rows
    )


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_key_case(case: dict[str, Any]) -> None:
    want = _expected(case["expected"])
    assert read_cell(case["cell"], case["known"]) == want
    if case.get("basis_too"):
        basis = read_basis(Paragraph(line=1, lines=("Basis: " + case["cell"],)), case["known"])
        assert basis is not None
        assert basis.items == want


def test_non_str_raises() -> None:
    with pytest.raises(TypeError):
        read_cell(cast(Any, 5))


def _walk(sections: tuple[Section, ...]) -> list[Section]:
    out: list[Section] = []
    for section in sections:
        out.append(section)
        out.extend(_walk(section.sections))
    return out


def test_fixture_table_cells() -> None:
    seen = 0
    for path in sorted(NEW_FORMAT.glob("*.md")):
        for section in _walk(parse(path.read_bytes()).sections):
            for block in section.blocks:
                if not isinstance(block, Table):
                    continue
                for row in block.rows:
                    for cell in row.cells:
                        seen += 1
                        for item in read_cell(cell):
                            assert item.text != ""
                            assert item.text in cell
    assert seen > 0


@given(st.text())
def test_any_text(text: str) -> None:
    items = read_cell(text)
    assert isinstance(items, tuple)
    for item in items:
        assert isinstance(item, BasisItem)
        assert item.text != ""
