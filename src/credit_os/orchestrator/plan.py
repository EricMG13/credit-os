"""The plan: which modules run, their producers and edge rules, and the round order."""

from collections.abc import Sequence
from typing import Literal

from credit_os.orchestrator.catalogue import (
    CATALOGUE,
    CP5_FAN_IN_EXCLUDES,
    NOT_OFFERED,
    PATHWAYS,
    PATHWAYS_NOT_OFFERED,
    EdgeRule,
    Module,
)

Reason = Literal["unknown", "not_offered", "cyclic", "no_edge"]
FAN_IN_MODULE = "CP-5"


class PlanRefused(ValueError):
    def __init__(self, reason: Reason, name: str) -> None:
        super().__init__(f"plan refused ({reason}): {name}")
        self.reason: Reason = reason
        self.name = name


def _table(catalogue: Sequence[Module]) -> dict[str, Module]:
    return {module.id: module for module in catalogue}


def canonical(entry: str, *, catalogue: Sequence[Module] = CATALOGUE) -> str:
    for module in catalogue:
        if entry == module.id or entry in module.aliases:
            return module.id
    if any(entry == key or entry in aliases for key, aliases in NOT_OFFERED.items()):
        raise PlanRefused("not_offered", entry)
    raise PlanRefused("unknown", entry)


def _lookup(table: dict[str, Module], module_id: str) -> Module:
    try:
        return table[module_id]
    except KeyError:
        raise PlanRefused("unknown", module_id) from None


def _selection(requested: Sequence[str], catalogue: Sequence[Module]) -> set[str]:
    table = _table(catalogue)
    pending = [canonical(entry, catalogue=catalogue) for entry in requested]
    selected: set[str] = set()
    while pending:
        module_id = pending.pop()
        if module_id in selected:
            continue
        selected.add(module_id)
        pending.extend(_lookup(table, module_id).required)
    return selected


def edge_rule(consumer: str, producer: str, *, catalogue: Sequence[Module] = CATALOGUE) -> EdgeRule:
    table = _table(catalogue)
    refused = PlanRefused("no_edge", f"{consumer} <- {producer}")
    if consumer not in table or producer not in table:
        raise refused
    module = table[consumer]
    if producer in module.edge_rules:
        return module.edge_rules[producer]
    if producer in module.required:
        return "block"
    fans_in = consumer == FAN_IN_MODULE and producer not in CP5_FAN_IN_EXCLUDES
    if producer in module.optional or fans_in:
        return "restricted"
    raise refused


def _producer_ids(module: Module, selected: set[str], catalogue: Sequence[Module]) -> list[str]:
    ids = [*module.required, *(item for item in module.optional if item in selected)]
    if module.id == FAN_IN_MODULE:
        ids += [
            item.id
            for item in catalogue
            if item.id in selected and item.id not in CP5_FAN_IN_EXCLUDES
        ]
    return list(dict.fromkeys(ids))


def producers(
    requested: Sequence[str], *, catalogue: Sequence[Module] = CATALOGUE
) -> dict[str, dict[str, str]]:
    table = _table(catalogue)
    selected = _selection(requested, catalogue)
    result: dict[str, dict[str, str]] = {}
    for module_id in selected:
        module = table[module_id]
        result[module_id] = {
            item: edge_rule(module_id, item, catalogue=catalogue)
            for item in _producer_ids(module, selected, catalogue)
        }
    return result


def plan(requested: Sequence[str], *, catalogue: Sequence[Module] = CATALOGUE) -> tuple[str, ...]:
    needs = producers(requested, catalogue=catalogue)
    ordered: list[str] = []
    left = [module.id for module in catalogue if module.id in needs]
    while left:
        ready = [item for item in left if all(p in ordered for p in needs[item])]
        if not ready:
            raise PlanRefused("cyclic", ", ".join(left))
        ordered += ready
        left = [item for item in left if item not in ready]
    return tuple(ordered)


def pathway_modules(pathway: str) -> tuple[str, ...]:
    if pathway in PATHWAYS_NOT_OFFERED:
        raise PlanRefused("not_offered", pathway)
    if pathway not in PATHWAYS:
        raise PlanRefused("unknown", pathway)
    return PATHWAYS[pathway]
