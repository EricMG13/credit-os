import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from credit_os.checks.findings import CHECKS, Finding
from credit_os.checks.lost import LostValue, lost_values
from credit_os.handoff.document import HandoffDocument, parse

KEY: dict[str, Any] = json.loads(
    (Path(__file__).resolve().parent / "expected" / "lost.json").read_text("utf-8")
)
CASES: list[dict[str, Any]] = KEY["cases"]


def _document(case: dict[str, Any], side: str) -> HandoffDocument:
    text = (
        case.get(f"{side}_front", "")
        + case.get(f"{side}_title", "")
        + KEY["head"]
        + case[side]
        + KEY["tail"]
    )
    return parse(text.encode("utf-8"))


def _named(case: dict[str, Any]) -> list[Finding]:
    reasons = case.get("reason", {})
    return [
        Finding(
            check=check,
            severity=severity,
            line=line,
            quoted=quoted,
            reason=reasons.get(str(position), "Synthetic reason."),
        )
        for position, (check, severity, line, quoted) in enumerate(case.get("named", []))
    ]


def _ids() -> list[str]:
    return [f"case{n:02d}" for n in range(len(CASES))]


@pytest.mark.parametrize("case", CASES, ids=_ids())
def test_lost_values_match_the_key(case: dict[str, Any]) -> None:
    previous, new = _document(case, "previous"), _document(case, "new")
    named = _named(case)
    result = lost_values(previous, new, named)
    assert isinstance(result, tuple)
    assert [[v.line, v.value, v.label] for v in result] == case["lost"]
    assert lost_values(previous, new, named) == result
    assert lost_values(previous, previous, ()) == ()
    for value in result:
        assert "\n" not in value.value
        assert "\n" not in value.label


def test_the_key_has_every_case_named() -> None:
    assert len(CASES) == 46
    assert sum(len(case["lost"]) for case in CASES) == 51


def test_lost_value_rows() -> None:
    with pytest.raises(ValidationError):
        LostValue(line=0, value="x", label="y")
    cut = LostValue(line=1, value="v" * 81, label="l" * 81)
    assert cut.value == "v" * 80 + "…"
    assert cut.label == "l" * 80 + "…"
    flat = LostValue(line=1, value="a\nb\tc d", label="a\nb\tc d")
    assert flat.value == "a b c d"
    assert flat.label == "a b c d"
    with pytest.raises(ValidationError):
        flat.__setattr__("line", 2)
    with pytest.raises(ValidationError):
        LostValue.model_validate({"line": 1, "value": "x", "label": "y", "extra": 1})


def test_lost_values_add_no_check_id() -> None:
    assert len(CHECKS) == 35
    assert not any("lost" in check for check in CHECKS)
