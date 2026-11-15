import json
import re
from pathlib import Path
from typing import Any

import pytest
from checks_context_support import HANDOFFS, build_context, expand_digests

from credit_os.checks import request, sources
from credit_os.checks.findings import CheckContext, Finding
from credit_os.checks.run import check_handoff
from credit_os.handoff.document import HandoffDocument, parse

_KEY_ONLY = ("name", "front", "title", "request", "sources", "findings", "tail", "expect", "reason")
KEY: dict[str, Any] = json.loads(
    (Path(__file__).resolve().parent / "expected" / "anchors.json").read_text("utf-8")
)
CASES: dict[str, dict[str, Any]] = {case["name"]: case for case in KEY["cases"]}
_SHA = re.compile(r"\{sha:(CP-[A-Z0-9]+)\}")


def _expand(text: str, context: CheckContext) -> str:
    def one(found: re.Match[str]) -> str:
        return context.upstream[found.group(1)].sha256

    return _SHA.sub(one, expand_digests(text))


def _build(case: dict[str, Any]) -> tuple[HandoffDocument, CheckContext]:
    context = build_context(KEY["context"], case, _KEY_ONLY)
    parts = (
        case.get("front", ""),
        case.get("title", ""),
        "## Request\n",
        case.get("request", KEY["request"]),
        "## Sources\n",
        _expand(case.get("sources", KEY["sources"]), context),
        "## Findings\n",
        case.get("findings", KEY["findings"]),
        case.get("tail", KEY["tail"]),
    )
    return parse("".join(parts).encode("utf-8")), context


def _row(finding: Finding) -> list[Any]:
    return [finding.check, finding.severity, finding.line, finding.quoted]


@pytest.mark.parametrize("name", list(CASES))
def test_case(name: str) -> None:
    case = CASES[name]
    document, context = _build(case)
    found = check_handoff(document, context)
    expected = [[*row[:3], _expand(row[3], context)] for row in case["expect"]]
    assert [_row(finding) for finding in found] == expected
    for index, text in case.get("reason", {}).items():
        assert found[int(index)].reason == text


@pytest.mark.parametrize("name", list(CASES))
def test_finding_shape(name: str) -> None:
    document, context = _build(CASES[name])
    for finding in check_handoff(document, context):
        assert finding.reason.count("\n") == 0
        assert finding.reason.endswith(".")
        assert not re.search(r"\. [A-Z]", finding.reason)
        assert finding.column == 1


@pytest.mark.parametrize("name", list(CASES))
def test_deterministic(name: str) -> None:
    document, context = _build(CASES[name])
    assert check_handoff(document, context) == check_handoff(document, context)


def test_each_check_callable_alone() -> None:
    document, context = _build(CASES["both missing, in the order of the check list"])
    assert [_row(f) for f in request.check_as_of(document, context)] == [
        ["request.as-of", "refusal", 1, "Request"]
    ]
    assert [_row(f) for f in request.check_issuer(document, context)] == [
        ["request.issuer", "refusal", 1, "Request"]
    ]
    assert sources.check_sha256_required(document, context) == ()


def test_fixtures_exist() -> None:
    for case in CASES.values():
        for path in case.get("upstream", {}).values():
            assert (HANDOFFS / path).is_file()
