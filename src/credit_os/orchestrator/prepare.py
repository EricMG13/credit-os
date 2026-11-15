"""Launch admission: from the context file's bytes, the modules asked for, the cap and a price
row, either one refusal with one line of text or the typed context, the run order, the request
bytes, the cap and the first hold. Pure: it opens no file and touches no store or model."""

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from credit_os.handoff.errors import echo
from credit_os.orchestrator.budget import PriceRow, admit_call, call_hold
from credit_os.orchestrator.catalogue import CATALOGUE, PATHWAYS
from credit_os.orchestrator.context import RunContext, load_context
from credit_os.orchestrator.plan import PlanRefused, canonical, pathway_modules, plan, producers

Reason = Literal[
    "cap_not_positive",
    "pathway_not_offered",
    "no_module",
    "module_unknown",
    "module_not_offered",
    "cap_below_hold",
]
# Pathways not offered, each with the sentence a launch is refused with (D2).
DEACTIVATED = {
    "short_snapshot": "The short credit snapshot is deactivated. Use the lite credit assessment.",
}
SCHEMA = "request/1"


class LaunchRefused(ValueError):
    def __init__(self, reason: Reason, text: str) -> None:
        super().__init__(text)
        self.reason: Reason = reason


@dataclass(frozen=True, slots=True)
class Prepared:
    context: RunContext
    ordered: tuple[str, ...]  # the run order
    request: bytes  # what the store keeps as the run's request
    config_id: str
    cap_usd: Decimal
    hold_usd: Decimal  # the first hold


def _canonical_entries(entries: Sequence[object]) -> list[str]:
    if not entries:
        raise LaunchRefused("no_module", "modules: none selected")
    names: list[str] = []
    for entry in entries:
        if type(entry) is not str:
            raise LaunchRefused("module_unknown", "modules: an entry is not text")
        try:
            names.append(canonical(entry))
        except PlanRefused as refused:
            if refused.reason == "not_offered":
                raise LaunchRefused("module_not_offered", f"modules: {entry} is not offered")
            raise LaunchRefused(
                "module_unknown", f"modules: {echo(entry)!r} is not a module"
            ) from None
    return names


def _request(raw: bytes, pathway: str, selection: str, requested: list[str]) -> bytes:
    needs = producers(requested)
    fields = {
        "schema": SCHEMA,
        "context_sha256": hashlib.sha256(raw).hexdigest(),
        "pathway": pathway,
        "selection": selection,
        "requested": requested,
        "ordered": list(plan(requested)),
        "producers": [
            [name, [[p, rule] for p, rule in edges.items()]] for name, edges in needs.items()
        ],
    }
    return json.dumps(
        fields, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def prepare(
    raw_context: bytes,
    *,
    modules: Sequence[str] | None = None,
    cap_usd: Decimal,
    price: PriceRow,
    max_output_tokens: int,
) -> Prepared:
    if type(cap_usd) is not Decimal or not cap_usd.is_finite() or cap_usd <= 0:
        raise LaunchRefused("cap_not_positive", "the cap must be a positive amount in USD")
    context = load_context(raw_context)
    pathway = context.run.pathway
    if pathway in DEACTIVATED:
        raise LaunchRefused("pathway_not_offered", DEACTIVATED[pathway])
    entries = pathway_modules(pathway) if modules is None else modules
    chosen = set(_canonical_entries(entries))
    requested = [module.id for module in CATALOGUE if module.id in chosen]
    selection = "preset" if chosen == set(PATHWAYS[pathway]) else "explicit"
    ordered = plan(requested)
    hold = call_hold(price, max_output_tokens=max_output_tokens)
    if not admit_call((), cap_usd=cap_usd, next_hold_usd=hold).admitted:
        raise LaunchRefused(
            "cap_below_hold",
            f"cap USD {cap_usd:f}: one {price.config_id} call holds up to USD {hold:f}",
        )
    request = _request(raw_context, pathway, selection, requested)
    return Prepared(context, ordered, request, price.config_id, cap_usd, hold)
