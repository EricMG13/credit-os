"""The trace builder of delivery, compared case by case with the controller's key."""

import json
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

from credit_os.delivery import traces
from credit_os.delivery.errors import DeliveryRefused
from credit_os.delivery.wording import load_wording
from credit_os.handoff.document import HandoffDocument, parse

ROOT = Path(__file__).resolve().parents[2]
KEY: dict[str, Any] = json.loads(
    (Path(__file__).parent / "expected" / "traces.json").read_text("utf-8")
)
FIXTURES = ROOT / KEY["fixtures"]
W = load_wording()
CASES: list[dict[str, Any]] = KEY["cases"]
BUILT = [c for c in CASES if "expect" in c]
REFUSED = [c for c in CASES if c.get("refused")]
PARTS = ("traces", "table", "jump", "items")


def case_ids(rows: list[dict[str, Any]]) -> list[str]:
    return [str(row["id"]) for row in rows]


def edited(file: str, replace: list[list[str]]) -> HandoffDocument:
    text = (FIXTURES / file).read_text("utf-8")
    for old, new in replace:
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    return parse(text.encode("utf-8"))


def build(case: dict[str, Any]) -> dict[str, object]:
    modules = [(m["code"], edited(m["file"], m["replace"])) for m in case["modules"]]
    return traces.build_traces(modules, case["as_of"], W)


def with_decimal(value: object) -> object:
    """The key's value cells hold `at` as a decimal string: read it as a Decimal."""
    if isinstance(value, dict):
        out = {k: with_decimal(v) for k, v in value.items()}
        at = out.get("at")
        if out.get("kind") == "value" and isinstance(at, str):
            out["at"] = Decimal(at)
        return out
    if isinstance(value, list):
        return [with_decimal(v) for v in value]
    return value


def same_decimals(got: object, want: object) -> None:
    """Each `at` is a Decimal equal to the key's, and nothing else is a float."""
    if isinstance(want, dict):
        assert isinstance(got, dict)
        for name, item in want.items():
            same_decimals(got[name], item)
    elif isinstance(want, list):
        assert isinstance(got, list | tuple)
        for g, w in zip(got, want, strict=True):
            same_decimals(g, w)
    elif isinstance(want, Decimal):
        assert isinstance(got, Decimal)
        assert got == want
    assert not isinstance(got, float)


@pytest.mark.parametrize("case", BUILT, ids=case_ids(BUILT))
def test_built(case: dict[str, Any]) -> None:
    got = build(case)
    assert list(got) == list(PARTS)
    for part, want in case["expect"].items():
        want = with_decimal(want)
        assert got[part] == want
        same_decimals(got[part], want)
    if "traces" in case["expect"]:
        assert list(cast(dict[str, object], got["traces"])) == list(case["expect"]["traces"])
    if "jump" in case["expect"]:
        assert [i["target"]["item"] for i in cast(list[dict[str, Any]], got["jump"])] == [
            i["target"]["item"] for i in case["expect"]["jump"]
        ]


@pytest.mark.parametrize("case", REFUSED, ids=case_ids(REFUSED))
def test_refused(case: dict[str, Any]) -> None:
    with pytest.raises(DeliveryRefused) as raised:
        build(case)
    message = str(raised.value)
    assert message
    for fixture in ("Northbridge", "NBG_", "Net debt", "K1", "Interest cover", "CP-99"):
        assert fixture not in message


OLD_ROW = (
    "| K1 | Net debt to EBITDA | Gross debt 1,700 less cash 310 gives net debt 1,390;"
    " divided by EBITDA 331 |"
)
FREE = st.text(alphabet="abcdefg XYZ.,;:-_*{}$", min_size=1, max_size=24).map(str.strip)


@given(FREE, FREE)
def test_cell_text_is_only_ever_a_value(calculation: str, steps: str) -> None:
    if not calculation or not steps:
        return
    document = edited(
        "synthetic-new-format/SYNTHETIC-CP-2.md",
        [
            [
                OLD_ROW,
                f"| K1 | {calculation} | {steps} |",
            ],
        ],
    )
    got = traces.build_traces([("CP-2", document)], "2025-03-31", W)
    seen: set[str] = set()

    def keys(value: object) -> None:
        if isinstance(value, dict):
            for name, item in value.items():
                seen.add(str(name))
                keys(item)
        elif isinstance(value, list | tuple):
            for item in value:
                keys(item)

    keys(got)
    assert calculation not in seen
    assert steps not in seen
    table = cast(dict[str, Any], got["table"])
    assert table["rows"][-1]["calc"]["label"] == calculation
    assert table["rows"][-1]["calc"]["note"] == steps
