"""The module bodies and module items of delivery, compared row by row with the controller's key."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

from credit_os.checks.figures import CODE
from credit_os.delivery import modules
from credit_os.delivery.errors import DeliveryRefused
from credit_os.delivery.facts import ModuleFacts, RunFacts
from credit_os.delivery.wording import load_wording
from credit_os.handoff.document import HandoffDocument, parse

ROOT = Path(__file__).resolve().parents[2]
KEY: dict[str, Any] = json.loads(
    (Path(__file__).parent / "expected" / "modules.json").read_text("utf-8")
)
FIXTURES = ROOT / KEY["fixtures"]
W = load_wording()
ROWS: list[dict[str, Any]] = KEY["rows"]
BUILT = [r for r in ROWS if "expected" in r]
REFUSED = [r for r in ROWS if r.get("refused")]
RAISES = [r for r in ROWS if "raises" in r]
FACTS_REFUSED: list[dict[str, Any]] = KEY["facts_refused"]


def row_ids(rows: list[dict[str, Any]]) -> list[str]:
    return [str(row["id"]) for row in rows]


def text_of(file: str, replace: list[list[str]]) -> str:
    text: str = (FIXTURES / file).read_text("utf-8")
    for old, new in replace:
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    return text


def documents_of(row: dict[str, Any]) -> dict[str, HandoffDocument]:
    return {
        code: parse(text_of(d["file"], d["replace"]).encode("utf-8"))
        for code, d in row["documents"].items()
    }


def facts_of(row: dict[str, Any]) -> RunFacts:
    run = KEY["run"]
    return RunFacts(
        run["run_id"],
        run["issuer_name"],
        run["pathway"],
        run["status"],
        run["end_reason"],
        run["as_of"],
        tuple(ModuleFacts(m["code"], m["outcome"], m["reason"]) for m in row["modules"]),
    )


def run_row(row: dict[str, Any]) -> tuple[dict[str, object], ...]:
    return modules.run_modules(facts_of(row), documents_of(row), row["traced"], row["gap_rows"], W)


def same_order(got: object, want: object) -> None:
    """The same keys in the same order, all the way down; no float anywhere."""
    assert not isinstance(got, float)
    if isinstance(want, dict):
        assert isinstance(got, dict)
        assert list(got) == list(want)
        for name, item in want.items():
            same_order(got[name], item)
    elif isinstance(want, list):
        assert isinstance(got, list | tuple)
        assert len(got) == len(want)
        for g, w in zip(got, want, strict=True):
            same_order(g, w)


@pytest.mark.parametrize("row", BUILT, ids=row_ids(BUILT))
def test_built(row: dict[str, Any]) -> None:
    got = run_row(row)
    want = row["expected"]
    assert [dict(m) for m in got] == want["modules"]
    same_order(list(got), want["modules"])
    items = modules.module_items(got)
    assert items == want["items"]
    same_order(items, want["items"])


@pytest.mark.parametrize("row", REFUSED, ids=row_ids(REFUSED))
def test_refused_names_the_rule_only(row: dict[str, Any]) -> None:
    with pytest.raises(DeliveryRefused) as raised:
        run_row(row)
    message = str(raised.value)
    if "rule" in row:
        assert message == row["rule"]
        return
    assert message
    assert CODE.search(message) is None
    for doc in row["documents"].values():
        for line in text_of(doc["file"], doc["replace"]).splitlines():
            if len(line) >= 8:
                assert line not in message
    for fact in row["modules"]:
        assert fact["code"] not in message
        if fact["reason"]:
            assert fact["reason"] not in message
    assert "NBG_" not in message


@pytest.mark.parametrize("row", RAISES, ids=row_ids(RAISES))
def test_caller_defect_raises(row: dict[str, Any]) -> None:
    with pytest.raises(cast(type[Exception], {"ValueError": ValueError}[row["raises"]])):
        run_row(row)


@pytest.mark.parametrize("row", FACTS_REFUSED, ids=row_ids(FACTS_REFUSED))
def test_facts_refused(row: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        facts_of(row)


def build_facts(modules_: tuple[ModuleFacts, ...]) -> Callable[[], RunFacts]:
    run = KEY["run"]
    return lambda: RunFacts(
        run["run_id"],
        run["issuer_name"],
        run["pathway"],
        run["status"],
        run["end_reason"],
        run["as_of"],
        modules_,
    )


def test_facts_refuse_an_outcome_outside_the_four() -> None:
    wrong = cast(Callable[..., ModuleFacts], ModuleFacts)
    with pytest.raises(ValueError):
        wrong("CP-2", "done", None)


def test_facts_refuse_a_code_given_twice() -> None:
    twice = (ModuleFacts("CP-2", "failed", None), ModuleFacts("CP-2", "not_started", None))
    with pytest.raises(ValueError):
        build_facts(twice)()


def test_facts_accept_the_four_outcomes() -> None:
    four = (
        ModuleFacts("CP-2", "accepted", None),
        ModuleFacts("CP-2D", "failed", "why"),
        ModuleFacts("CP-1", "not_started", None),
        ModuleFacts("CP-0", "producer_missing", None),
    )
    assert [m.outcome for m in build_facts(four)().modules] == [
        "accepted",
        "failed",
        "not_started",
        "producer_missing",
    ]


def keys_of(value: object) -> list[str]:
    if isinstance(value, dict):
        return [str(k) for k in value] + [k for v in value.values() for k in keys_of(v)]
    if isinstance(value, list | tuple):
        return [k for v in value for k in keys_of(v)]
    return []


# Lower-case words and spaces cannot read as a module, table or digest code.
REASONS = st.text(alphabet="abcdefghijklmnopqrstuvwxyz .,", min_size=1, max_size=80)


@given(reason=REASONS)
def test_failed_reason_is_word_for_word_and_never_a_key(reason: str) -> None:
    facts = RunFacts(
        "run-0001",
        "Northbridge Synthetic Group",
        "covenant_refinancing",
        "finished",
        "completed",
        "2025-03-31",
        (ModuleFacts("CP-2", "failed", reason),),
    )
    got = modules.run_modules(facts, {}, {}, {}, W)
    body = cast(dict[str, object], got[0]["body"])
    assert body["kind"] == "blocked"
    assert body["reason"] == reason
    assert modules.module_items(got)[0]["lead"] == reason
    assert reason not in keys_of(list(got))


def test_reason_with_a_code_is_refused_whatever_the_outcome() -> None:
    for outcome in ("failed", "not_started", "producer_missing"):
        facts = RunFacts(
            "run-0001",
            "Northbridge Synthetic Group",
            "covenant_refinancing",
            "finished",
            "completed",
            "2025-03-31",
            (ModuleFacts("CP-2", cast(Any, outcome), "Table T1.2 was not read."),),
        )
        with pytest.raises(DeliveryRefused):
            modules.run_modules(facts, {}, {}, {}, W)


def test_the_trace_count_must_match_the_items_shown() -> None:
    row = next(r for r in ROWS if r["id"] == "cp-2-with-gaps")
    short = {"CP-2": {**row["traced"]["CP-2"], "findings": ["t-0002"]}}
    with pytest.raises(ValueError):
        modules.run_modules(facts_of(row), documents_of(row), short, row["gap_rows"], W)
