import json
import random
import re
import time
from pathlib import Path
from typing import Any

import pytest
from checks_context_support import build_context

from credit_os.checks import prose
from credit_os.checks.findings import CheckContext, Finding, ordered
from credit_os.checks.run import check_handoff
from credit_os.handoff.document import HandoffDocument, parse
from credit_os.handoff.errors import HandoffError
from credit_os.handoff.reader import read_reader

KEY: dict[str, Any] = json.loads(
    (Path(__file__).resolve().parent / "expected" / "prose.json").read_text("utf-8")
)
CASES: dict[str, dict[str, Any]] = {case["name"]: case for case in KEY["cases"]}

_KEY_ONLY = (
    "name",
    "findings",
    "front",
    "tail",
    "expect",
    "reason_has",
    "reason_lacks",
    "known_false_refusal",
)
_MACRO = re.compile(r"\{(words|z):(\d+)\}")

ALL_CHECKS = (
    prose.check_bottom_line,
    prose.check_bottom_line_length,
    prose.check_module_code,
    prose.check_page,
    prose.check_hash,
    prose.check_bracket,
    prose.check_pipeline_wording,
    prose.check_provider_marker,
)


def _expand(text: str) -> str:
    def one(found: re.Match[str]) -> str:
        count = int(found.group(2))
        return " ".join(["word"] * count) if found.group(1) == "words" else "z" * count

    return _MACRO.sub(one, text)


def _build(case: dict[str, Any]) -> tuple[HandoffDocument, CheckContext]:
    text = (
        case.get("front", "")
        + KEY["head"]
        + _expand(case["findings"])
        + _expand(case.get("tail", KEY["tail"]))
    )
    return parse(text.encode("utf-8")), build_context(
        {"kind": "data", **KEY["context"]}, case, _KEY_ONLY
    )


def _document(text: str) -> HandoffDocument:
    return parse((KEY["head"] + text + KEY["tail"]).encode("utf-8"))


def _row(finding: Finding) -> list[Any]:
    return [finding.check, finding.severity, finding.line, finding.quoted]


def _expected(case: dict[str, Any]) -> list[list[Any]]:
    return [[*row[:3], _expand(row[3])] for row in case["expect"]]


@pytest.mark.parametrize("name", list(CASES))
def test_case(name: str) -> None:
    case = CASES[name]
    document, context = _build(case)
    found = check_handoff(document, context)
    assert [_row(finding) for finding in found] == _expected(case)
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
        assert "\n" not in finding.reason
        if finding.check != "structure.reader":  # the parser's message, unchanged
            assert finding.reason.endswith(".")


@pytest.mark.parametrize("name", list(CASES))
def test_deterministic(name: str) -> None:
    document, context = _build(CASES[name])
    assert check_handoff(document, context) == check_handoff(document, context)


def test_columns() -> None:
    found = prose.check_module_code(
        _document("### Bottom line\nThe CP-1 data feeds CP-2A.\n"), _ctx()
    )
    assert [(f.line, f.column) for f in found] == [(8, 5), (8, 21)]


def test_column_in_second_table_cell() -> None:
    document = parse(
        (
            KEY["head"]
            + "### Bottom line\nThe view holds.\n"
            + "## Calculations\nNone.\n## Gaps\n| Gap | Effect |\n| --- | --- |\n"
            + "| g | abc\ue200 |\n## Next module\nNone.\n"
        ).encode("utf-8")
    )
    found = prose.check_provider_marker(document, _ctx())
    assert [(f.line, f.column, f.quoted) for f in found] == [(14, 4, "U+E200")]


@pytest.mark.parametrize(
    ("text", "columns"),
    [
        ("The view [a] holds and then [b] ends.", [10, 29]),
        ("The view holds [ here.", [16]),
    ],
)
def test_bracket_finding_columns(text: str, columns: list[int]) -> None:
    found = prose.check_bracket(_document("### Bottom line\n" + text + "\n"), _ctx())
    assert [finding.column for finding in found] == columns


def test_bottom_line_length_reasons_state_the_count() -> None:
    document, context = _build(CASES["long first sentence and long passage"])
    found = ordered(prose.check_bottom_line_length(document, context))
    assert "186 words" in found[0].reason
    assert "46 words" in found[1].reason
    assert all(finding.reason != "" for finding in found)


@pytest.mark.parametrize(
    ("line", "check", "expected"),
    [
        ("[" * 1000, prose.check_bracket, 1000),
        ("CP-1 " * 1000, prose.check_module_code, 1000),
    ],
)
def test_no_cap_at_one_thousand(line: str, check: Any, expected: int) -> None:
    document = _document("### Bottom line\n" + line + "\n")
    assert len(check(document, _ctx())) == expected


def _ctx() -> CheckContext:
    return build_context({"kind": "data", **KEY["context"]}, {})


def test_each_check_alone_on_earlier_format() -> None:
    document, context = _build(CASES["earlier format: one refusal, no prose check"])
    for check in ALL_CHECKS:
        check(document, context)
    assert prose.check_bottom_line(document, context) == ()
    assert prose.check_bottom_line_length(document, context) == ()


def test_each_check_alone_when_the_reader_raises() -> None:
    document, context = _build(
        CASES["repeated passage heading: the checks that need no reader view still run"]
    )
    with pytest.raises(HandoffError):
        read_reader(document)
    for check in ALL_CHECKS:
        check(document, context)
    assert prose.check_bottom_line(document, context) == ()
    assert prose.check_bottom_line_length(document, context) == ()


@pytest.mark.parametrize("filler", ["a", "9"])
def test_long_word_run_gives_no_wording_finding(filler: str) -> None:
    document = _document("### Bottom line\n" + filler * 5000 + "\n")
    assert prose.check_pipeline_wording(document, _ctx()) == ()


# The plan wrote the snake-case alternative without the leading `\b`; production anchors it so the
# match is linear. The two must find the same spans.
_PLAN_WORDING = re.compile(
    r"(?i:\bhandoffs?\b|\bthis transport\b|\bthe pack\b|\bfact pack\b|\bsource pack\b"
    r"|\bcanonical\b|\bre-anchor\w*|\bhelper scripts?\b|\bupstream modules?\b"
    r"|\bdownstream (?:modules?|owners?|work|analys[ie]s|use)\b)"
    r"|\w*[a-z]_[a-z]\w*"
    r"|\b(?=[A-Z0-9_]*[A-Z])[A-Z0-9]+(?:_[A-Z0-9]+)+\b"
)
_LINE_CAP = 400
_FIXTURE_LINES = 1000
_GENERATED = 1000
_ALPHABET = ["a", "b", "A", "Z", "_", "1", "-", " ", "."]


def _fixture_lines() -> list[str]:
    lines = [
        line[:_LINE_CAP]
        for path in sorted(
            (Path(__file__).resolve().parents[1] / "fixtures" / "handoffs").rglob("*.md")
        )
        for line in path.read_text("utf-8").splitlines()
    ]
    if len(lines) <= _FIXTURE_LINES:
        return lines
    return [lines[index * len(lines) // _FIXTURE_LINES] for index in range(_FIXTURE_LINES)]


def _generated_strings() -> list[str]:
    rng = random.Random(20261114)
    return ["".join(rng.choices(_ALPHABET, k=rng.randint(0, 40))) for _ in range(_GENERATED)]


def _spans(pattern: re.Pattern[str], text: str) -> list[tuple[int, int]]:
    return [found.span() for found in pattern.finditer(text)]


def test_wording_pattern_matches_the_plans_on_fixture_lines() -> None:
    lines = _fixture_lines()
    assert len(lines) == 1000  # evenly taken from every line of every fixture *.md file
    for text in lines:
        assert _spans(prose._WORDING, text) == _spans(_PLAN_WORDING, text)


def test_wording_pattern_matches_the_plans_on_generated_strings() -> None:
    strings = _generated_strings()
    assert len(strings) == 1000  # Random(20261114), lengths 0 to 40
    for text in strings:
        assert _spans(prose._WORDING, text) == _spans(_PLAN_WORDING, text)


@pytest.mark.parametrize("line", ["a" * 10000, "9" * 10000, "a_" * 5000])
def test_pipeline_wording_runs_in_bounded_time(line: str) -> None:
    document = _document("### Bottom line\n" + line + "\n")
    start = time.perf_counter()
    check_handoff(document, _ctx())
    assert time.perf_counter() - start < 2.0
