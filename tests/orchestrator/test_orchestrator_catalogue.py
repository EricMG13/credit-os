import json
from pathlib import Path
from types import MappingProxyType
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from credit_os.orchestrator import catalogue as cat
from credit_os.orchestrator.catalogue import CATALOGUE, Module
from credit_os.orchestrator.plan import (
    PlanRefused,
    canonical,
    edge_rule,
    pathway_modules,
    plan,
    producers,
)

EXPECTED = Path(__file__).parent / "expected"
KEY: dict[str, Any] = json.loads((EXPECTED / "catalogue.json").read_text(encoding="utf-8"))
PLANS: dict[str, Any] = json.loads((EXPECTED / "plans.json").read_text(encoding="utf-8"))
OFFERED_IDS = [module.id for module in CATALOGUE]


def _module(row: dict[str, Any]) -> Module:
    return Module(
        id=row["id"],
        aliases=tuple(row["aliases"]),
        kind=row["kind"],
        scored=row["scored"],
        required=tuple(row["required"]),
        optional=tuple(row["optional"]),
        edge_rules=MappingProxyType(row["edge_rules"]),
    )


def test_d1_catalogue_equals_key() -> None:
    assert CATALOGUE == tuple(_module(row) for row in KEY["modules"])


def test_d1_module_has_no_register_field() -> None:
    assert not any("register" in name for name in Module.__slots__)


def test_d1_edge_rules_are_read_only() -> None:
    rules: Any = CATALOGUE[7].edge_rules
    with pytest.raises(TypeError):
        rules["CP-0"] = "block"


def test_d1_not_offered_equals_key() -> None:
    assert cat.NOT_OFFERED == {k: tuple(v) for k, v in KEY["not_offered"].items()}


def test_d1_pathways_equal_key() -> None:
    assert cat.PATHWAYS == {k: tuple(v) for k, v in KEY["pathways"].items()}
    assert cat.PATHWAYS_NOT_OFFERED == frozenset(KEY["pathways_not_offered"])


def test_d1_cp5_fan_in_excludes_equal_key() -> None:
    assert cat.CP5_FAN_IN_EXCLUDES == frozenset(KEY["cp5_fan_in_excludes"])


def test_d1_mappings_are_read_only() -> None:
    for mapping in (cat.NOT_OFFERED, cat.PATHWAYS):
        assert isinstance(mapping, MappingProxyType)


def test_d1_aliases_resolve_to_ids() -> None:
    assert canonical("CP-PARSE") == "CP-0"
    assert canonical("CP-3B") == "CP-3"


@pytest.mark.parametrize("name", list(PLANS["pathways"]), ids=list(PLANS["pathways"]))
def test_d3_pathway_plan_equals_key(name: str) -> None:
    row = PLANS["pathways"][name]
    requested = pathway_modules(name)
    assert list(plan(requested)) == row["order"]
    assert producers(requested) == row["producers"]


@pytest.mark.parametrize("name", list(PLANS["subsets"]), ids=list(PLANS["subsets"]))
def test_d3_subset_plan_equals_key(name: str) -> None:
    row = PLANS["subsets"][name]
    assert list(plan(row["requested"])) == row["order"]
    assert producers(row["requested"]) == row["producers"]


@pytest.mark.parametrize("name", list(PLANS["refused"]), ids=list(PLANS["refused"]))
def test_d2_refused_request(name: str) -> None:
    row = PLANS["refused"][name]
    for call in (plan, producers):
        with pytest.raises(PlanRefused) as caught:
            call(row["requested"])
        assert caught.value.reason == row["reason"]
        assert caught.value.name == row["name"]
        assert "\n" not in str(caught.value)


@pytest.mark.parametrize(
    "name", list(PLANS["pathways_refused"]), ids=list(PLANS["pathways_refused"])
)
def test_d2_refused_pathway(name: str) -> None:
    with pytest.raises(PlanRefused) as caught:
        pathway_modules(name)
    assert caught.value.reason == PLANS["pathways_refused"][name]
    assert caught.value.name == name


@pytest.mark.parametrize(
    "row",
    PLANS["edge_rules"],
    ids=[f"{c}<-{p}" for c, p, _ in PLANS["edge_rules"]],
)
def test_d3_edge_rule(row: list[str | None]) -> None:
    consumer, producer, expected = row
    assert consumer is not None
    assert producer is not None
    if expected is None:
        with pytest.raises(PlanRefused) as caught:
            edge_rule(consumer, producer)
        assert caught.value.reason == "no_edge"
        assert caught.value.name == f"{consumer} <- {producer}"
    else:
        assert edge_rule(consumer, producer) == expected


@pytest.mark.parametrize("name", [k for k in PLANS["cycles"] if k != "_about"], ids=lambda k: k)
def test_g6_cycle_is_refused(name: str) -> None:
    table = [_module(row) for row in PLANS["cycles"][name]]
    with pytest.raises(PlanRefused) as caught:
        plan(PLANS["cycle_requests"][name], catalogue=table)
    assert caught.value.reason == "cyclic"
    assert caught.value.name == ", ".join(m.id for m in table)


@settings(max_examples=200, deadline=None)
@given(st.lists(st.sampled_from(OFFERED_IDS), max_size=25))
def test_d3_plan_is_a_topological_order_whatever_the_request_order(subset: list[str]) -> None:
    order = plan(subset)
    needs = producers(subset)
    assert sorted(order) == sorted(needs)
    position = {module_id: index for index, module_id in enumerate(order)}
    for consumer, made_by in needs.items():
        assert all(position[p] < position[consumer] for p in made_by)
    assert plan(sorted(set(subset))) == order
