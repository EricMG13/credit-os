import json
import subprocess
import sys
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
    assert len(CASES) == 48
    assert sum(len(case["lost"]) for case in CASES) == 53


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
    assert not any("lost" in check for check in CHECKS)


_COUNT_SCRIPT = """
import json, sys
from credit_os.checks.lost import lost_values
from credit_os.handoff.document import parse

head = "## Request\\nSYNTHETIC FIXTURE.\\n## Sources\\nNone.\\n## Findings\\n"
tail = "## Calculations\\nNone.\\n## Gaps\\nNone.\\n## Next module\\nNone.\\n"
counts = {}
for n in (250, 500, 1000):
    body = "; ".join("USD " + str(i) + ".5m" for i in range(n))
    previous = parse((head + body + "\\n" + tail).encode())
    new = parse((head + "none\\n" + tail).encode())
    events = 0

    def profiler(frame, event, arg):
        global events
        if event in ("call", "c_call"):
            events += 1

    sys.setprofile(profiler)
    result = lost_values(previous, new, ())
    sys.setprofile(None)
    counts[str(n)] = [events, len(result)]
print(json.dumps(counts))
"""


def test_lost_values_work_grows_linearly_with_the_figures_in_one_node() -> None:
    done = subprocess.run(
        [sys.executable, "-c", _COUNT_SCRIPT], capture_output=True, text=True, check=True
    )
    counts: dict[str, list[int]] = json.loads(done.stdout)
    assert {size: found for size, (_, found) in counts.items()} == {
        "250": 250,
        "500": 500,
        "1000": 1000,
    }
    assert 10 * counts["1000"][0] <= 22 * counts["500"][0]
    assert 10 * counts["500"][0] <= 22 * counts["250"][0]


_ROW_SCRIPT = """
import json, sys
from credit_os.checks.lost import lost_values
from credit_os.handoff.document import parse

head = "## Request\\nSYNTHETIC FIXTURE.\\n## Sources\\nNone.\\n## Findings\\n"
tail = "## Calculations\\nNone.\\n## Gaps\\nNone.\\n## Next module\\nNone.\\n"


def table(first, cells):
    width = len(cells) + 1
    header = "| " + " | ".join("h" + str(i) for i in range(width)) + " |\\n"
    rule = "|" + " --- |" * width + "\\n"
    return header + rule + "| " + " | ".join([first, *cells]) + " |\\n"


counts = {}
for shape in ("row_empty", "row_long"):
    for n in (250, 500, 1000):
        first = "" if shape == "row_empty" else "a" * (40 * n)
        figures = ["USD " + str(i) + ".5m" for i in range(n)]
        previous = parse((head + table(first, figures) + tail).encode())
        new = parse((head + table(first, ["none"] * n) + tail).encode())
        events = 0

        def profiler(frame, event, arg):
            global events
            if event in ("call", "c_call"):
                events += 1

        sys.setprofile(profiler)
        result = lost_values(previous, new, ())
        sys.setprofile(None)
        counts[shape + str(n)] = [events, len(result)]
print(json.dumps(counts))
"""


@pytest.mark.parametrize("shape", ["row_empty", "row_long"])
def test_lost_values_work_grows_linearly_with_the_cells_in_one_row(shape: str) -> None:
    done = subprocess.run(
        [sys.executable, "-c", _ROW_SCRIPT], capture_output=True, text=True, check=True
    )
    counts: dict[str, list[int]] = json.loads(done.stdout)
    assert {size: counts[shape + size][1] for size in ("250", "500", "1000")} == {
        "250": 250,
        "500": 500,
        "1000": 1000,
    }
    assert 10 * counts[shape + "1000"][0] <= 22 * counts[shape + "500"][0]
    assert 10 * counts[shape + "500"][0] <= 22 * counts[shape + "250"][0]
