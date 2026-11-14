import json
import time
from pathlib import Path
from typing import Any

import pytest
from checks_context_support import build_context
from hypothesis import given, settings
from hypothesis import strategies as st

from credit_os.checks.confidence import confidence_outcome
from credit_os.checks.findings import CheckContext
from credit_os.checks.run import check_handoff
from credit_os.handoff.document import HandoffDocument, parse

KEY: dict[str, Any] = json.loads(
    (Path(__file__).resolve().parent / "expected" / "confidence.json").read_text("utf-8")
)
CASES: list[dict[str, Any]] = KEY["cases"]
SECONDS = 2.0
_KEY_ONLY = ("name", "findings", "front", "tail", "expect", "reason_has", "outcome")
_LINEAGE = (
    "Directly Sourced",
    "Calculated",
    "Assumption-Based",
    "Analyst Inference",
    "Weak Lineage",
    "Untraced",
    "Conflicting",
    "Insufficient Information",
)


def _text(case: dict[str, Any]) -> str:
    text = case.get("front", "") + KEY["head"] + case["findings"] + case.get("tail", KEY["tail"])
    return str(text)


def _context(case: dict[str, Any]) -> CheckContext:
    return build_context({"kind": "data", **KEY["context"]}, case, _KEY_ONLY)


def _document(case: dict[str, Any]) -> HandoffDocument:
    return parse(_text(case).encode("utf-8"))


def test_the_key_is_collected_whole() -> None:
    assert len(CASES) == 52


@pytest.mark.parametrize("case", CASES, ids=[f"case{i}" for i in range(len(CASES))])
def test_case(case: dict[str, Any]) -> None:
    document = _document(case)
    context = _context(case)
    found = check_handoff(document, context)
    assert [[f.check, f.severity, f.line, f.quoted] for f in found] == case["expect"]
    for index, texts in case.get("reason_has", {}).items():
        for text in [texts] if isinstance(texts, str) else texts:
            assert text in found[int(index)].reason
    outcome = confidence_outcome(document, context)
    expected = case["outcome"]
    assert outcome.state == expected["state"]
    assert outcome.value == expected.get("value")
    assert outcome.band == expected.get("band")
    assert outcome.status == expected.get("status")


def _table(
    claims: list[int], present: int, total: int, gate: str, crit: int, material: int, minor: int
) -> str:
    rows: list[tuple[str, int | str]] = [*zip(_LINEAGE, claims, strict=True)]
    rows += [("Fields present", present), ("Fields total", total), ("Source gate", gate)]
    rows += [("CRITICAL", crit), ("MATERIAL", material), ("MINOR", minor)]
    body = "".join(f"| {name} | {value} |\n" for name, value in rows)
    return (
        "### Bottom line\nStable.\n### Confidence inputs\n| Input | Value |\n| --- | --- |\n" + body
    )


def _value(*args: Any) -> int | None:
    case = {"findings": _table(*args)}
    return confidence_outcome(_document(case), _context(case)).value


_COUNT = st.integers(min_value=0, max_value=60)
_CLAIMS = st.lists(_COUNT, min_size=8, max_size=8)
_FIELDS = st.integers(min_value=1, max_value=60).flatmap(
    lambda total: st.tuples(st.integers(min_value=0, max_value=total), st.just(total))
)
_GATE = st.sampled_from(["pass", "partial", "fail"])
_SLOW = settings(max_examples=60, deadline=None)


@_SLOW
@given(_CLAIMS, _FIELDS, _GATE, _COUNT, _COUNT, _COUNT)
def test_value_is_between_0_and_100(
    claims: list[int], fields: tuple[int, int], gate: str, c: int, m: int, n: int
) -> None:
    value = _value(claims, fields[0], fields[1], gate, c, m, n)
    assert value is not None
    assert 0 <= value <= 100


@_SLOW
@given(_CLAIMS, _FIELDS, _GATE, _COUNT, _COUNT, _COUNT, st.sampled_from([0, 1, 2]))
def test_value_never_rises_with_a_finding(
    claims: list[int], fields: tuple[int, int], gate: str, c: int, m: int, n: int, which: int
) -> None:
    more = [c, m, n]
    more[which] += 1
    before = _value(claims, fields[0], fields[1], gate, c, m, n)
    after = _value(claims, fields[0], fields[1], gate, *more)
    assert before is not None
    assert after is not None
    assert after <= before


@_SLOW
@given(_CLAIMS, _FIELDS, _COUNT, _COUNT, _COUNT)
def test_value_is_0_when_the_gate_fails(
    claims: list[int], fields: tuple[int, int], c: int, m: int, n: int
) -> None:
    assert _value(claims, fields[0], fields[1], "fail", c, m, n) == 0


@_SLOW
@given(_CLAIMS, _FIELDS, _GATE, _COUNT, _COUNT, _COUNT, st.integers(min_value=1, max_value=1000))
def test_value_is_unchanged_by_scaling(
    claims: list[int], fields: tuple[int, int], gate: str, c: int, m: int, n: int, factor: int
) -> None:
    base = _value(claims, fields[0], fields[1], gate, c, m, n)
    assert base is not None
    scaled = [factor * x for x in claims]
    assert _value(scaled, fields[0], fields[1], gate, c, m, n) == base
    assert _value(claims, factor * fields[0], factor * fields[1], gate, c, m, n) == base


def test_a_thousand_registers_and_the_inputs_table_run_in_time() -> None:
    registers = "".join(
        f"### R{n} — Item\n| Item | Value |\n| --- | --- |\n| a | {n} |\n" for n in range(1000)
    )
    table = _table([8, 2, 2, 0, 0, 0, 0, 0], 19, 20, "pass", 0, 0, 1)
    case = {
        "findings": table,
        "tail": "## Calculations\n" + registers + "## Gaps\nNone.\n## Next module\nNone.\n",
    }
    document = _document(case)
    context = _context(case)
    start = time.perf_counter()
    check_handoff(document, context)
    assert time.perf_counter() - start < SECONDS


def test_a_level_four_section_directly_under_findings_is_unreadable() -> None:
    inputs = _table([8, 2, 2, 0, 0, 0, 0, 0], 19, 20, "pass", 0, 0, 1)
    table = inputs.split("### Confidence inputs\n")[1]
    findings = "#### Confidence inputs\n" + table + "### Bottom line\nThe view is stable.\n"
    case = {"findings": findings}
    document = _document(case)
    found = check_handoff(document, _context(case))
    got = [
        (f.check, f.severity, f.line, f.quoted) for f in found if f.check.startswith("confidence.")
    ]
    assert got == [("confidence.unreadable", "refusal", 7, "Confidence inputs")]
    assert confidence_outcome(document, _context(case)).state == "refused"
