import json
import re
from pathlib import Path
from typing import Any

import pytest
from checks_context_support import build_context
from pydantic import ValidationError

from credit_os.checks import tables
from credit_os.checks.findings import CheckContext, Finding
from credit_os.checks.run import check_handoff
from credit_os.checks.table_specs import OWED, SPECS, TableSpec
from credit_os.handoff.document import HandoffDocument, parse

_KEY_ONLY = (
    "name",
    "findings",
    "front",
    "tail",
    "lead",
    "sections",
    "replace",
    "expect",
    "reason",
)
_EXPECTED = Path(__file__).resolve().parent / "expected"
KEY: dict[str, Any] = json.loads((_EXPECTED / "tables_period.json").read_text("utf-8"))
OWED_KEY: dict[str, Any] = json.loads((_EXPECTED / "owed.json").read_text("utf-8"))
CASES: dict[str, dict[str, Any]] = {case["name"]: case for case in KEY["cases"]}
CASE_IDS = [f"c{number:02d}" for number in range(len(CASES))]
BY_ID = dict(zip(CASE_IDS, CASES.values(), strict=True))


def _set(target: object, name: str, value: object) -> None:
    setattr(target, name, value)


def _store(target: Any, key: str, value: object) -> None:
    target[key] = value


def _findings(case: dict[str, Any]) -> str:
    if "findings" in case:
        return str(case["findings"])
    sections = case.get("sections", case["owed_tables"])
    parts = [case.get("lead", KEY["lead"])]
    parts.extend(f"### {heading}\n{KEY['tables'][heading]}\n" for heading in sections)
    return "".join(parts)


def _text(case: dict[str, Any]) -> str:
    text = case.get("front", "") + KEY["head"] + _findings(case) + case.get("tail", KEY["tail"])
    for old, new in case.get("replace", []):
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    return str(text)


def _build(case: dict[str, Any]) -> tuple[HandoffDocument, CheckContext]:
    context = build_context({"kind": "data", **KEY["context"]}, case, _KEY_ONLY)
    return parse(_text(case).encode("utf-8")), context


def _row(finding: Finding) -> list[Any]:
    return [finding.check, finding.severity, finding.line, finding.quoted]


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_case(case_id: str) -> None:
    case = BY_ID[case_id]
    document, context = _build(case)
    found = check_handoff(document, context)
    assert [_row(finding) for finding in found] == case["expect"]
    for index, text in case.get("reason", {}).items():
        assert found[int(index)].reason == text


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_finding_shape(case_id: str) -> None:
    document, context = _build(BY_ID[case_id])
    for finding in check_handoff(document, context):
        assert finding.reason.strip() != ""
        assert finding.reason.count("\n") == 0
        if finding.check != "structure.reader":  # the parser's message, no full stop
            assert finding.reason.endswith(".")
        assert finding.column == 1
        assert finding.message.startswith(f'{finding.check}, line {finding.line}: "')


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_deterministic(case_id: str) -> None:
    document, context = _build(BY_ID[case_id])
    assert check_handoff(document, context) == check_handoff(document, context)


def test_each_check_callable_alone() -> None:
    document, context = _build(CASES["cell: a unit written in a number (predecessor)"])
    assert [_row(f) for f in tables.check_cell(document, context)] == [
        ["table.cell", "refusal", 12, "3.85x"]
    ]
    assert tables.check_absent(document, context) == ()
    assert tables.check_header(document, context) == ()
    document, context = _build(CASES["absent: no section"])
    assert [_row(f) for f in tables.check_absent(document, context)] == [
        ["table.absent", "refusal", 6, "Findings"]
    ]
    assert tables.check_header(document, context) == ()
    assert tables.check_cell(document, context) == ()


def test_specifications_are_the_catalogue() -> None:
    catalogue = KEY["catalogue"]
    assert sorted(SPECS) == sorted(catalogue)
    for heading, (columns, unit) in catalogue.items():
        spec = SPECS[heading]
        assert spec.heading == heading
        assert spec.value_columns == tuple(columns)
        assert isinstance(spec.value_columns, tuple)
        assert spec.chart_unit == unit
    assert sorted(SPECS) == sorted(OWED_KEY["period"])


def test_specification_fields_are_the_three() -> None:
    assert tuple(TableSpec.model_fields) == ("heading", "value_columns", "chart_unit")


def test_specification_frozen() -> None:
    spec = SPECS["Chart data: liquidity"]
    with pytest.raises(ValidationError):
        _set(spec, "chart_unit", "x")


@pytest.mark.parametrize("heading", list(KEY["catalogue"]))
def test_specification_header_is_the_keys_table_header(heading: str) -> None:
    header = KEY["tables"][heading].split("\n")[0]
    cells = tuple(cell.strip() for cell in header.strip().strip("|").split("|"))
    spec = SPECS[heading]
    assert cells == ("Period", *spec.value_columns, "Reporting unit", "Basis and limitation")
    assert spec.header == cells


def test_owed_is_the_key() -> None:
    assert {module: list(headings) for module, headings in OWED.items()} == OWED_KEY["owed"]
    assert all(isinstance(headings, tuple) for headings in OWED.values())
    assert list(OWED) == list(OWED_KEY["owed"])


def test_owed_counts_and_no_heading_twice() -> None:
    every = [heading for headings in OWED.values() for heading in headings]
    assert len(OWED) == 18
    assert len(every) == 41
    assert len(set(every)) == 41
    assert [heading for heading in every if heading in SPECS] == [
        heading for heading in every if heading in OWED_KEY["period"]
    ]
    assert re.search("—", "".join(OWED["CP-1C"])) is not None


def test_owed_cannot_be_changed() -> None:
    with pytest.raises(TypeError):
        _store(OWED, "CP-9", ())
