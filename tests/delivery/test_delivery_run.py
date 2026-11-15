"""The run of delivery (lead, Overview, head), compared row by row with the controller's key."""

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from credit_os.checks.figures import CODE
from credit_os.delivery import run
from credit_os.delivery.facts import ModuleFacts, RunFacts
from credit_os.delivery.run import LeftOut, RunParts
from credit_os.delivery.wording import load_wording
from credit_os.handoff.document import HandoffDocument, parse

ROOT = Path(__file__).resolve().parents[2]
KEY: dict[str, Any] = json.loads(
    (Path(__file__).parent / "expected" / "overview.json").read_text("utf-8")
)
FIXTURES = ROOT / KEY["fixtures"]
W = load_wording()
ROWS: list[dict[str, Any]] = KEY["rows"]
BUILT = [r for r in ROWS if r.get("expected") is not None]
EXACT = [r for r in ROWS if r.get("left_out") is not None]
ANY_RULE = [r for r in ROWS if r.get("expected") is None and r.get("left_out") is None]
MAIN = next(r for r in ROWS if r["id"] == "main")


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
    f = row["facts"]
    return RunFacts(
        f["run_id"],
        f["issuer_name"],
        f["pathway"],
        f["status"],
        f["end_reason"],
        f["as_of"],
        tuple(ModuleFacts(m["code"], m["outcome"], m["reason"]) for m in f["modules"]),
    )


def build(row: dict[str, Any]) -> RunParts | LeftOut:
    return run.build_run(facts_of(row), documents_of(row), W)


def decimals(value: object) -> object:
    """The key's `at` strings as Decimal, so the comparison is on Decimal values."""
    if isinstance(value, dict):
        return {
            k: Decimal(v) if k == "at" and isinstance(v, str) else decimals(v)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [decimals(v) for v in value]
    return value


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
    elif isinstance(want, Decimal):
        assert isinstance(got, Decimal)


@pytest.mark.parametrize("row", BUILT, ids=row_ids(BUILT))
def test_built(row: dict[str, Any]) -> None:
    got = build(row)
    assert isinstance(got, RunParts)
    want = row["expected"]
    assert got.id == want["id"]
    assert got.head == want["head"]
    same_order(got.head, want["head"])
    overview = decimals(want["overview"])
    assert got.overview == overview
    same_order(got.overview, overview)
    assert [[m["id"], m["state"]] for m in got.modules] == want["module_states"]


@pytest.mark.parametrize("row", EXACT, ids=row_ids(EXACT))
def test_left_out_with_the_exact_rule(row: dict[str, Any]) -> None:
    got = build(row)
    assert got == LeftOut(row["facts"]["run_id"], row["left_out"])


@pytest.mark.parametrize("row", ANY_RULE, ids=row_ids(ANY_RULE))
def test_left_out_by_a_builder_names_the_rule_only(row: dict[str, Any]) -> None:
    got = build(row)
    assert isinstance(got, LeftOut)
    assert got.run_id == row["facts"]["run_id"]
    message = got.rule
    assert message
    assert CODE.search(message) is None
    for doc in row["documents"].values():
        for line in text_of(doc["file"], doc["replace"]).splitlines():
            if len(line) >= 8:
                assert line not in message
    for fact in row["facts"]["modules"]:
        assert fact["code"] not in message
    assert "NBG_" not in message


def test_an_accepted_module_without_a_document_is_a_caller_defect() -> None:
    documents = documents_of(MAIN)
    del documents["CP-2"]
    with pytest.raises(ValueError):
        run.build_run(facts_of(MAIN), documents, W)


@pytest.mark.parametrize(
    "as_of", ["2025-3-31", "2025-03-31 ", "٢٠٢٥-03-31"], ids=["short", "pad", "arabic"]
)
def test_an_as_of_that_is_not_plain_iso_is_not_a_real_date(as_of: str) -> None:
    f = MAIN["facts"]
    facts = RunFacts(
        f["run_id"],
        f["issuer_name"],
        f["pathway"],
        f["status"],
        f["end_reason"],
        as_of,
        facts_of(MAIN).modules,
    )
    assert run.build_run(facts, documents_of(MAIN), W) == LeftOut(
        f["run_id"], "the as-of date is not a real date"
    )


@settings(max_examples=25, deadline=None)
@given(st.permutations(list(MAIN["documents"])))
def test_output_ignores_the_mapping_order(order: list[str]) -> None:
    documents = documents_of(MAIN)
    shuffled = {code: documents[code] for code in order}
    assert run.build_run(facts_of(MAIN), shuffled, W) == run.build_run(facts_of(MAIN), documents, W)
