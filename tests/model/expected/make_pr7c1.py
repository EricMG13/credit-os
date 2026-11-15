"""Answer key for 1B PR 7c1 (the run entry), written by the answer-key author.

An oracle in json, re, hashlib and fractions only: not the code under test, never imported by it.
It loads `make_pr7a2.py` and `make_pr7b.py` (and through them the PR 2, PR 3 and 7a1 oracles) by
path, and `make_pr7c2.py` loads this file for its document builder. A document is a committed
fixture with text edits and block ops applied. A row names the module that wrote the block (CP-2G
or CP-1), the foundation document and the forward document (null on layer 1) and the expected
outcome. A refusal's outcome is fixed independently: by the PR 6 key (`pr6a.json`, `pr6b.json`) for
the same block and foundation pair, by PR 4b's key texts, or by the reasoning in the row's comment
below. `render()` returns the key's text; run this file to write `pr7c1.json` next to it.
"""

import importlib.util
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
FIXTURES = HERE.parents[1] / "fixtures" / "model"


def load(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


A7, B7 = load("make_pr7a2"), load("make_pr7b")
A, line = A7.P1, A7.line
FENCE = re.compile(r"(```json\n)(.*?)(\n```)", re.DOTALL)
FWD, L1 = "CP-2G", "CP-1"
FWD_FILE, FND_FILE = "forward-model.md", "foundation.md"
THOUSANDS = ("forward-model-thousands.md", "foundation-thousands.md")
Spec = dict[str, Any]


def doc(name: str, edits: list[Any] | None = None, ops: list[Any] | None = None) -> Spec:
    return {"file": name} | ({"edits": edits} if edits else {}) | ({"ops": ops} if ops else {})


def data(spec: Spec) -> bytes:
    """The document's bytes: the fixture, its text edits, then its block ops."""
    text: str = (FIXTURES / spec["file"]).read_bytes().decode("ascii")
    for old, new, *every in spec.get("edits", []):
        if old == "cut":  # drop the section headed `new`, up to the next level-2 heading
            start = text.index(new)
            text = text[:start] + text[text.index("\n## ", start) + 1 :]
            continue
        assert every == ["all"] and old in text or text.count(old) == 1, old
        text = text.replace(old, new)
    if spec.get("ops"):
        found = FENCE.search(text)
        assert found is not None
        block = json.loads(found.group(2))
        for path, value in spec["ops"]:
            A.put(block, path, value)
        text = text[: found.start(2)] + json.dumps(block) + text[found.end(2) :]
    return text.encode("ascii")


def raw_block(spec: Spec) -> dict[str, Any]:
    found = FENCE.search(data(spec).decode("ascii"))
    assert found is not None
    block: dict[str, Any] = json.loads(found.group(2))
    return block


def row(
    kind: str, name: str, source: str, foundation: Spec, forward: Spec | None, **rest: Any
) -> Any:
    return {
        "kind": kind,
        "name": name,
        "source": source,
        "foundation": foundation,
        "forward": forward,
    } | rest


FWD_BLOCK = raw_block(doc(FWD_FILE))
SHOCK_MSG = "a layer-1 forecast states no shock and no cases"
FACILITIES_MSG = "a layer-1 forecast states no facilities"
NULLS = [[f"base_drivers.{n}.values", [None] * 3] for n in A.DRIVERS]
RUN = [["base_drivers.debt_repayment.values", ["1000", "200", "100"]]]
SHOCK = ["downside_shock", {"ebitda_decline": "0.1", "rate_increase": "0.2"}]
UPSIDE = ["upside_drivers", FWD_BLOCK["upside_drivers"]]
DOWNSIDE = ["downside_drivers", FWD_BLOCK["downside_drivers"]]
FACILITIES = ["facilities", FWD_BLOCK["facilities"]]
REPAYMENT = (
    "base case: debt_repayment through forecast year 3 totals 1300, more than base debt 1250"
)
SCALE = "`scale` must be 1 (CP-1 prints USD millions) or 1000 (USD thousands)"
SCHEMA = "forecast inputs: schema_version: Input should be 'cpos-forecast-inputs/1'"
STOP = "the handoff gives no forecast drivers, so no forecast was computed ({})"


def refused(kind: str, subject: str, message: str) -> dict[str, Any]:
    return {"outcome": [kind, subject, message]}


def stated_of(block: dict[str, Any]) -> dict[str, str]:
    """A thousands block's amounts as printed, by slot name (a millions block states none)."""
    if block["scale"] != 1000:
        return {}
    out = {f"base {k}": o["amount"] for k, o in block["base"].items() if o["amount"]}
    for group in ("base_drivers", "upside_drivers", "downside_drivers"):
        for name in ("dividends", "debt_repayment"):
            driver = (block[group] or {}).get(name)
            for i, text in enumerate(driver["values"] if driver else (), 1):
                out[f"{group} {name} year {i}"] = text
    for n, fac in enumerate(block["facilities"] or (), 1):
        out |= {f"facility {n} {k}": fac[k] for k in ("balance", "annual_amortisation") if fac[k]}
    return out


def accepted() -> list[dict[str, Any]]:
    plan = [
        ("forward_millions", FWD, doc(FND_FILE), doc(FWD_FILE)),
        ("forward_thousands", FWD, doc(THOUSANDS[1]), doc(THOUSANDS[0])),
        ("layer1_millions", L1, doc(FND_FILE), None),
        ("layer1_thousands", L1, doc(THOUSANDS[1]), None),
    ]
    out = []
    for name, source, foundation, forward in plan:
        block = raw_block(foundation if forward is None else forward)
        shown = {
            "scale": block["scale"],
            "currency": block["currency"],
            "facilities": [f["name"] for f in block["facilities"] or ()],
            "upside": block["upside_drivers"] is not None,
            "downside": block["downside_drivers"] is not None,
            "shock": block["downside_shock"] is not None,
            "stated": stated_of(block),
        }
        out.append(row("accepted", name, source, foundation, forward, expected=shown))
    return out


def layer1() -> list[dict[str, Any]]:
    """P1 (the plan's behaviour 10): the first of shock, upside, downside, else facilities."""
    named = [
        ("source_shock", [SHOCK], "downside_shock", SHOCK_MSG),
        ("source_upside", [UPSIDE], "upside_drivers", SHOCK_MSG),
        ("source_downside", [DOWNSIDE], "downside_drivers", SHOCK_MSG),
        ("source_upside_and_downside", [DOWNSIDE, UPSIDE], "upside_drivers", SHOCK_MSG),
        ("source_facilities", [FACILITIES], "facilities", FACILITIES_MSG),
        ("source_shock_and_facilities", [FACILITIES, SHOCK], "downside_shock", SHOCK_MSG),
        ("source_downside_and_facilities", [FACILITIES, DOWNSIDE], "downside_drivers", SHOCK_MSG),
        # the source check runs before the foundation checks: a wrong revenue cell is not reached
        (
            "source_before_cell",
            [FACILITIES, ["base.revenue.amount", "1457"]],
            "facilities",
            FACILITIES_MSG,
        ),
    ]
    out = [
        row("refused", n, L1, doc(FND_FILE, None, o), None, **refused("source", s, m))
        for n, o, s, m in named
    ]
    thousands = doc(THOUSANDS[1], None, [SHOCK])
    out.append(
        row(
            "refused",
            "source_shock_thousands",
            L1,
            thousands,
            None,
            **refused("source", "downside_shock", SHOCK_MSG),
        )
    )
    # known difference from legacy: the repayment check is inside the block's parse, so it comes first
    repayment = doc(FND_FILE, None, RUN + [SHOCK])
    out.append(
        row(
            "refused",
            "repayment_before_source",
            L1,
            repayment,
            None,
            **refused("repayment", "debt_repayment", REPAYMENT),
        )
    )
    return out


def stages() -> list[dict[str, Any]]:
    """Scale, schema and repayment come from the block's parse: PR 4b's key texts, and the sums
    worked here (1000 + 200 + 100 = 1300 against base debt 1250, USD from the block)."""
    cases: list[tuple[str, list[Any], dict[str, Any]]] = [
        ("scale", [["scale", 7]], refused("scale", "scale", SCALE)),
        (
            "schema",
            [["schema_version", "cpos-forecast-inputs/2"]],
            refused("schema", "forecast inputs", SCHEMA),
        ),
        ("repayment", RUN, refused("repayment", "debt_repayment", REPAYMENT)),
    ]
    out = []
    for stage, ops, outcome in cases:
        out.append(
            row(
                "refused",
                f"{stage}_forward_no_fallback",
                FWD,
                doc(FND_FILE),
                doc(FWD_FILE, None, ops),
                **outcome,
            )
        )
        out.append(row("refused", f"{stage}_layer1", L1, doc(FND_FILE, None, ops), None, **outcome))
    # every driver null: declined with the first scope limit as its reason; no layer-1 fallback
    for name, source, foundation, forward, reason in (
        (
            "declined_forward_no_fallback",
            FWD,
            doc(FND_FILE),
            doc(FWD_FILE, None, NULLS),
            "Invented fixture: no issuer is forecast.",
        ),
        (
            "declined_layer1",
            L1,
            doc(FND_FILE, None, NULLS),
            None,
            "Invented fixture: run-rate drivers only.",
        ),
    ):
        out.append(row("declined", name, source, foundation, forward, message=STOP.format(reason)))
    return out


def pr6() -> list[dict[str, Any]]:
    """PR 6 rows run through the entry on the key's own block and foundation pair."""
    keys = {
        n: json.loads((HERE / f"{n}.json").read_text("utf-8"))["rows"] for n in ("pr6a", "pr6b")
    }
    out = []
    for key, label in (
        ("pr6a", "a period header compares with its case"),
        ("pr6a", "another cell of the row names the other unit"),
        ("pr6a", "a currency the foundation never names"),
        ("pr6a", "USD named only in the block's own section"),
        ("pr6a", "a EUR foundation does not name USD"),
        ("pr6b", "a balance that is not printed"),
        ("pr6b", "the base cell before the facilities"),
        ("pr6b", "scheduled repayments over base debt in year 1"),
    ):
        (item,) = [r for r in keys[key] if r["label"] == label]
        ops = [[".".join(map(str, p)), *v] for p, *v in item.get("ops", [])] or None
        found = doc(item.get("foundation", FND_FILE), item.get("edits"))
        name = f"{key}_{label.replace(' ', '_').replace(chr(39), '')}"
        if "source" in item:  # the key's own forward-mode pair
            out.append(
                row(
                    "refused",
                    name,
                    FWD,
                    found,
                    doc(item["source"], None, ops),
                    **refused(*item["outcome"]),
                )
            )
        else:  # a layer-1 block in the foundation's own handoff
            found = doc(found["file"], item.get("edits"), ops)
            out.append(row("refused", name, L1, found, None, **refused(*item["outcome"])))
    return out


def rows() -> list[dict[str, Any]]:
    return accepted() + layer1() + stages() + pr6()


ABOUT = (
    "Step 1B PR 7c1 answer key, written by the answer-key author. Every figure, name and text is "
    "invented. Made by make_pr7c1.py (not the code under test). A row names `source` (the module "
    "that wrote the block: CP-2G or CP-1), a `foundation` document and a `forward` document (null "
    "on layer 1): a fixture `file`, its text `edits` ([old, new] or [old, new, 'all']; ['cut', "
    "heading] drops a section) and its block `ops` ([dotted path, value], applied in order). An "
    "accepted row's `expected` is what read_checked returns: scale, currency, facility names, "
    "whether each case and the shock are stated, and the stated-in-thousands map. A refused row's "
    "`outcome` is [kind, subject, message]; a declined row's `message` is the exception text. "
    "Implementers do not edit this file."
)


def render() -> str:
    done = rows()
    kinds = Counter(r["kind"] for r in done)
    body = ",\n".join("  " + line(r) for r in done)
    return f'{{\n "about": {line(ABOUT)},\n "kinds": {line(dict(kinds))},\n "rows": [\n{body}\n ]\n}}\n'


if __name__ == "__main__":
    Path(__file__).with_name("pr7c1.json").write_text(render(), "utf-8")
