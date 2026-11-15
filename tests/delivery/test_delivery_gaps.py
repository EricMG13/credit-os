"""The gaps builder of delivery, compared case by case with the controller's key."""

import json
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from credit_os.delivery import gaps
from credit_os.delivery.errors import DeliveryRefused
from credit_os.delivery.wording import load_wording
from credit_os.handoff.document import HandoffDocument, parse

ROOT = Path(__file__).resolve().parents[2]
KEY: dict[str, Any] = json.loads(
    (Path(__file__).parent / "expected" / "gaps.json").read_text("utf-8")
)
FIXTURES = ROOT / KEY["fixtures"]
W = load_wording()
CASES: list[dict[str, Any]] = KEY["cases"]
BUILT = [c for c in CASES if "expect" in c]
REFUSED = [c for c in CASES if c.get("refused")]
PARTS = ("table", "jump", "count", "modules")
CP2 = "synthetic-new-format/SYNTHETIC-CP-2.md"
ROW = "| No peer set supplied | Leverage is not benchmarked. |\n"


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
    return gaps.build_gaps(modules, W)


@pytest.mark.parametrize("case", BUILT, ids=case_ids(BUILT))
def test_built(case: dict[str, Any]) -> None:
    got = build(case)
    assert list(got) == list(PARTS)
    for part, want in case["expect"].items():
        assert got[part] == want, part


@pytest.mark.parametrize("case", BUILT, ids=case_ids(BUILT))
def test_key_order(case: dict[str, Any]) -> None:
    """Dict key order follows the slice types, so the serialised text equals the key's."""
    assert json.dumps(build(case)) == json.dumps(case["expect"])


@pytest.mark.parametrize("case", REFUSED, ids=case_ids(REFUSED))
def test_refused(case: dict[str, Any]) -> None:
    with pytest.raises(DeliveryRefused) as info:
        build(case)
    message = str(info.value)
    for text in ("peer", "Leverage", "Covenant", "Desk", "Sub", "None", "tdg", "SYNTHETIC"):
        assert text not in message


def _word(prefix: str) -> st.SearchStrategy[str]:
    return st.text(alphabet="abcdefgh01234_.,:;{}", max_size=8).map(lambda s: prefix + s)


GAP_CELL = st.lists(_word("Qz"), min_size=1, max_size=4).map(" ".join)
EFFECT_CELL = st.lists(_word("Qy"), min_size=1, max_size=4).map(" ".join)


def strings(value: object, path: str = "") -> list[tuple[str, str]]:
    """Every dict key (path ending in <key>) and every string value, with its path."""
    found: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for name, item in value.items():
            found.append((f"{path}/<key>", str(name)))
            found.extend(strings(item, f"{path}/{name}"))
    elif isinstance(value, list):
        for item in value:
            found.extend(strings(item, path))
    elif isinstance(value, str):
        found.append((path, value))
    return found


@given(gap=GAP_CELL, effect=EFFECT_CELL)
def test_cell_text_is_only_a_value(gap: str, effect: str) -> None:
    document = edited(CP2, [[ROW, f"| {gap} | {effect} |\n"]])
    got = gaps.build_gaps([("CP-2", document)], W)
    found = strings(got)
    assert sorted(p for p, t in found if t == gap) == [
        "/jump/label",
        "/table/groups/rows/gap",
    ]
    assert [p for p, t in found if t == effect] == ["/table/groups/rows/reason"]
    assert not any(t in (gap, effect) for p, t in found if p.endswith("<key>"))
