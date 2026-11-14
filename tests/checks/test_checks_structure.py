import json
import re
from pathlib import Path
from typing import Any

import pytest
from checks_context_support import build_context

from credit_os.checks import structure
from credit_os.checks.findings import CheckContext, Finding
from credit_os.checks.run import check_handoff
from credit_os.handoff.document import HandoffDocument, parse
from credit_os.handoff.reader import read_reader

KEY: dict[str, Any] = json.loads(
    (Path(__file__).resolve().parent / "expected" / "structure.json").read_text("utf-8")
)
CASES: dict[str, dict[str, Any]] = {case["name"]: case for case in KEY["cases"]}


def _build(case: dict[str, Any]) -> tuple[HandoffDocument, CheckContext]:
    findings = case["findings"].replace("{prose}", KEY["prose"])
    text = case.get("front", "") + KEY["head"] + findings + case.get("tail", KEY["tail"])
    context = build_context({"kind": "prose", **KEY["context"]}, case)
    return parse(text.encode("utf-8")), context


def _row(finding: Finding) -> list[Any]:
    return [finding.check, finding.severity, finding.line, finding.quoted]


@pytest.mark.parametrize("name", list(CASES))
def test_case(name: str) -> None:
    case = CASES[name]
    document, context = _build(case)
    found = check_handoff(document, context)
    assert [_row(finding) for finding in found] == case["expect"]
    for index, text in case.get("reason", {}).items():
        assert found[int(index)].reason == text
    for index, texts in case.get("reason_has", {}).items():
        for text in texts:
            assert text in found[int(index)].reason
    for index, texts in case.get("reason_lacks", {}).items():
        for text in texts:
            assert text not in found[int(index)].reason


@pytest.mark.parametrize("name", list(CASES))
def test_finding_shape(name: str) -> None:
    document, context = _build(CASES[name])
    for finding in check_handoff(document, context):
        assert finding.reason.strip() != ""
        assert finding.reason.count("\n") == 0
        if finding.check != "structure.reader":  # the parser's message, unchanged, no full stop
            assert finding.reason.endswith(".")
            assert not re.search(r"\. [A-Z]", finding.reason)
        assert finding.column == 1
        assert finding.message.startswith(f'{finding.check}, line {finding.line}: "')


@pytest.mark.parametrize("name", list(CASES))
def test_deterministic(name: str) -> None:
    document, context = _build(CASES[name])
    assert check_handoff(document, context) == check_handoff(document, context)


def test_each_check_callable_alone() -> None:
    case = CASES["two headings with one id"]
    document, context = _build(case)
    assert [_row(f) for f in structure.check_register_id(document, context)] == [
        ["structure.register-id", "refusal", 17, "T1 — B"]
    ]
    assert structure.check_passages(document, context) == ()
    assert structure.check_fence(document, context) == ()
    assert structure.check_registers(document, context) == ()
    assert structure.check_format(document, context) == ()
    assert structure.check_reader_summary(document, context) == ()


def test_checks_on_the_other_format() -> None:
    document, context = _build(CASES["summary unreadable, after another section"])
    assert [_row(f) for f in structure.check_format(document, context)] == [
        ["structure.format", "refusal", 7, "Intro"]
    ]
    assert [_row(f) for f in structure.check_reader_summary(document, context)] == [
        ["structure.reader-summary", "warning", 9, "Reader summary"]
    ]
    assert structure.check_passages(document, context) == ()
    assert structure.check_registers(document, context) == ()


def test_reader_check_alone() -> None:
    document, context = _build(CASES["reader summary heading repeated"])
    found = structure.check_reader(document, context)
    assert [_row(f) for f in found] == [["structure.reader", "refusal", 9, "Reader summary"]]
    clean, clean_context = _build(CASES["clean prose"])
    assert structure.check_reader(clean, clean_context) == ()


def _blocked(text: str) -> bool:
    document = parse(text.encode("utf-8"))
    return structure.is_blocked(document, read_reader(document))


@pytest.mark.parametrize(
    ("front", "blocked"),
    [
        ("", False),
        ("---\nmodule_status: Blocked\n---\n", True),
        ("---\nmodule_status: 'BLOCKED'\n---\n", True),
        ("---\nmodule_status: complete\n---\n", False),
        ("---\nother: blocked\n---\n", False),
    ],
)
def test_is_blocked_front_matter(front: str, blocked: bool) -> None:
    text = front + KEY["head"] + "### Bottom line\nCall.\n" + KEY["tail"]
    assert _blocked(text) is blocked


def test_is_blocked_opening_and_earlier_format() -> None:
    opening = KEY["head"] + "### Bottom line\nNot assessable: x.\n" + KEY["tail"]
    assert _blocked(opening) is True
    earlier = KEY["head"] + "### Overview\no\n" + KEY["tail"]
    assert _blocked(earlier) is False
