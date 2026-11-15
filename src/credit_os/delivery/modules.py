"""The module bodies of a run, in the slice's Module shape, and the module items that name them.

A module is Delivered (an accepted, readable handoff), blocked (an accepted handoff that says
"Not assessable", or a module that failed) or not run. Delivery adds no analysis: a delivered
body is the passages `passages` selects, the records `records` writes and the trace keys
`traces` gave each item, placed. Output follows `facts.modules` order, never a mapping's order.

R24 condition 1: a run is left out (`DeliveryRefused`, naming the rule only and never input text)
when a module has no kind in the catalogue (7b-19; CP-8 is the one fixed prose entry), a handoff is in the earlier format or
cannot be read, a handoff is blocked only by its front matter, a delivered body has no finding or
no limitation (R1, until a later round exempts data modules), a store reason holds a module,
table or digest code (C14), or a passage or record the builders refuse. The caller leaves that run
out with the reason. An accepted module with no document or no traced entry, or a traced entry
that does not match the items shown, is a caller defect and raises `ValueError`.

Values are plain dicts with the slice's camelCase keys, in the slice types' field order.
"""

from collections.abc import Mapping, Sequence
from typing import cast

from credit_os.checks.structure import is_blocked
from credit_os.delivery import names, passages, records
from credit_os.delivery.errors import DeliveryRefused
from credit_os.delivery.facts import ModuleFacts, RunFacts
from credit_os.delivery.wording import Wording
from credit_os.handoff.data import source_names
from credit_os.handoff.document import HandoffDocument
from credit_os.handoff.errors import HandoffError
from credit_os.handoff.reader import Reader, read_reader
from credit_os.orchestrator.catalogue import CATALOGUE

# The slice's Module state set; the web draws these words and the front end owns the set.
_DELIVERED = "Delivered"
_DELIVERED_WITH_GAPS = "Delivered with gaps"
_NOT_ASSESSABLE = "Not assessable"
_NOT_RUN = "Not run"

# Ruling 7b-19: CP-8 has no catalogue kind but writes a Bottom line, so it is delivered as prose.
_KINDS = {module.id: module.kind for module in CATALOGUE} | {"CP-8": "prose"}


def _refuse(rule: str) -> DeliveryRefused:
    return DeliveryRefused(f"modules: {rule}")


def _read(document: HandoffDocument) -> Reader:
    try:
        reader = read_reader(document)
    except HandoffError as error:
        raise _refuse("the passages cannot be read") from error
    if reader.format != "new":
        raise _refuse("the handoff is in the earlier format")
    return reader


def _gaps_link(count: int, wording: Wording) -> dict[str, str]:
    return {"label": wording.fill("module.gaps_link", {"count": count})}


def _blocked(reason: str, count: int, wording: Wording) -> dict[str, object]:
    return {
        "kind": "blocked",
        "reason": reason,
        "note": wording.fill("module.blocked_note", {}),
        "gapsLink": _gaps_link(count, wording),
    }


def _store_reason(facts: ModuleFacts, default: str) -> str:
    """The store's reason word for word, else the owner's sentence; refused when it holds a code."""
    reason = facts.reason
    if not reason:
        return default
    if passages.narrative_leaks(reason, ()):
        raise _refuse("a store reason holds a module, table or digest code")
    return reason


def _keys(slot: object, count: int, what: str) -> list[str | None]:
    if not isinstance(slot, list | tuple) or len(slot) != count:
        raise ValueError(f"traced {what} do not match the items shown")
    return [None if key is None else str(key) for key in slot]


def _single(slot: object) -> str | None:
    return None if slot is None else str(slot)


def _with_trace(item: dict[str, object], key: str | None) -> dict[str, object]:
    return {**item, "trace": key}


def _delivered(
    code: str,
    document: HandoffDocument,
    reader: Reader,
    traced: Mapping[str, object],
    count: int,
    wording: Wording,
) -> dict[str, object]:
    known = source_names(document)
    bottom = passages.bottom_line(reader, known)
    found = passages.findings(reader, known)
    contrary, change = passages.contrary_and_change(reader, known)
    limits = passages.limitations(document, known)
    if not found or not limits:
        raise _refuse("R1: a delivered module has no finding or no limitation")
    finding_keys = _keys(traced.get("findings"), len(found), "findings")
    limit_keys = _keys(traced.get("limitations"), len(limits), "limitations")
    return {
        "kind": "delivered",
        "moduleKind": _KINDS[code],
        "bottomLine": _with_trace(bottom, _single(traced.get("bottomLine"))),
        "findings": [_with_trace(i, k) for i, k in zip(found, finding_keys, strict=True)],
        "contrary": None
        if contrary is None
        else _with_trace(contrary, _single(traced.get("contrary"))),
        "changeView": None
        if change is None
        else _with_trace(change, _single(traced.get("changeView"))),
        "records": list(records.chart_records(document, wording)),
        "limitations": {
            "count": str(len(limits)),
            "gapsLink": _gaps_link(count, wording),
            "items": [_with_trace(i, k) for i, k in zip(limits, limit_keys, strict=True)],
        },
    }


def _accepted(
    facts: ModuleFacts,
    documents: Mapping[str, HandoffDocument],
    traced: Mapping[str, Mapping[str, object]],
    count: int,
    wording: Wording,
) -> tuple[str, dict[str, object]]:
    document = documents.get(facts.code)
    entry = traced.get(facts.code)
    if document is None or entry is None:
        raise ValueError("an accepted module needs its document and its traced entry")
    reader = _read(document)
    if is_blocked(document, reader):
        reason = passages.blocked_reason(reader, source_names(document))
        return _NOT_ASSESSABLE, _blocked(reason, count, wording)
    state = _DELIVERED_WITH_GAPS if count >= 1 else _DELIVERED
    return state, _delivered(facts.code, document, reader, entry, count, wording)


def _module(
    facts: ModuleFacts,
    documents: Mapping[str, HandoffDocument],
    traced: Mapping[str, Mapping[str, object]],
    gap_rows: Mapping[str, int],
    wording: Wording,
) -> dict[str, object]:
    module = names.module(facts.code)
    if facts.code not in _KINDS:
        raise _refuse(f"a module with no kind in the catalogue: {facts.code}")
    count = gap_rows.get(facts.code, 0)
    if facts.outcome == "accepted":
        state, body = _accepted(facts, documents, traced, count, wording)
    elif facts.outcome == "failed":
        reason = _store_reason(facts, wording.fill("module.failed_reason", {}))
        state, body = _NOT_ASSESSABLE, _blocked(reason, count, wording)
    else:
        reason = _store_reason(facts, wording.fill("module.not_run_reason", {}))
        state, body = _NOT_RUN, _blocked(reason, count, wording)
    return {"id": module.slug, "name": module.name, "state": state, "body": body}


def run_modules(
    facts: RunFacts,
    documents: Mapping[str, HandoffDocument],
    traced: Mapping[str, Mapping[str, object]],
    gap_rows: Mapping[str, int],
    wording: Wording,
) -> tuple[dict[str, object], ...]:
    """The run's modules in `facts.modules` order; see the module docstring for refusals.

    `traced` is the `items` map of `traces.build_traces`, `gap_rows` the per-module Gaps row
    counts; a module with no document wrote no Gaps table, so its count is 0.
    """
    return tuple(_module(m, documents, traced, gap_rows, wording) for m in facts.modules)


def _lead(body: Mapping[str, object]) -> str:
    if body["kind"] == "delivered":
        bottom = cast(Mapping[str, str], body["bottomLine"])
        return f"{bottom['lead']} {bottom['rest']}" if bottom["rest"] else bottom["lead"]
    return cast(str, body["reason"])


def module_items(modules: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    """One Overview module item per module, never collapsed.

    The lead is the bottom line as shown (lead, a space, rest; the lead alone when rest is
    empty) for a delivered body and the reason for a blocked one.
    """
    return [
        {
            "title": module["name"],
            "lead": _lead(cast(Mapping[str, object], module["body"])),
            "state": module["state"],
            "module": module["id"],
        }
        for module in modules
    ]
