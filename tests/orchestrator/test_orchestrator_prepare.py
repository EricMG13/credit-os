"""Launch admission (PR 9b) against the controller's answer key (`orchestrator_prepare_key.py`):
the request bytes, the refusals, the cap against the first hold, and W1's two hash seeds."""

import hashlib
import json
import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any, get_args

import orchestrator_prepare_key as key
import pytest

from credit_os.orchestrator import catalogue
from credit_os.orchestrator.budget import BudgetDataError, PriceRow
from credit_os.orchestrator.context import PathwayId
from credit_os.orchestrator.plan import producers
from credit_os.orchestrator.prepare import DEACTIVATED, LaunchRefused, Prepared, Reason, prepare


def _price() -> PriceRow:
    config_id, inputs, outputs, context_tokens, floor = key.LAUNCH_PRICE
    rates = (tuple(Decimal(t) for t in inputs), tuple(Decimal(t) for t in outputs))
    return PriceRow(config_id, *rates, context_tokens, floor)


def _launch(raw: bytes, modules: tuple[Any, ...] | None = None, cap: Any = Decimal(20)) -> Prepared:
    return prepare(
        raw, modules=modules, cap_usd=cap, price=_price(), max_output_tokens=key.LAUNCH_OUTPUT
    )


def _cap(value: Any) -> Any:
    if isinstance(value, tuple) and value[0] == "decimal":
        return Decimal(value[1])
    return value


@pytest.mark.parametrize("name", list(key.REQUESTS), ids=list(key.REQUESTS))
def test_d25_a_launch_gives_the_bytes_of_the_key(name: str) -> None:
    raw, modules, request, digest, order = key.REQUESTS[name]
    prepared = _launch(raw, modules)
    assert prepared.request == request
    assert hashlib.sha256(prepared.request).hexdigest() == digest
    assert prepared.ordered == order
    assert prepared.config_id == key.LAUNCH_PRICE[0]
    assert prepared.cap_usd == Decimal(20)
    assert prepared.hold_usd == Decimal("2.284")
    assert prepared.context.identity.issuer_id == key.ISSUER_ID


_CHILD = """
import sys
sys.path.insert(0, sys.argv[1])
from decimal import Decimal
import orchestrator_prepare_key as key
from credit_os.orchestrator.budget import PriceRow
from credit_os.orchestrator.prepare import prepare
c, i, o, n, f = key.LAUNCH_PRICE
price = PriceRow(c, tuple(map(Decimal, i)), tuple(map(Decimal, o)), n, f)
for name in key.SEEDED_ROWS:
    raw, modules = key.REQUESTS[name][:2]
    print(prepare(raw, modules=modules, cap_usd=Decimal("20"), price=price,
                  max_output_tokens=key.LAUNCH_OUTPUT).request.hex())
"""


@pytest.mark.parametrize("seed", key.HASH_SEEDS, ids=[f"seed_{s}" for s in key.HASH_SEEDS])
def test_w1_the_bytes_do_not_depend_on_the_hash_seed(seed: str) -> None:
    env = {**os.environ, "PYTHONHASHSEED": seed}
    here = str(Path(__file__).parent)
    done = subprocess.run(
        [sys.executable, "-c", _CHILD, here],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    expected = [key.REQUESTS[name][2].hex() for name in key.SEEDED_ROWS]
    assert done.stdout.split() == expected


@pytest.mark.parametrize("name", list(key.REQUESTS), ids=list(key.REQUESTS))
def test_w1_producers_come_in_catalogue_order_at_both_levels(name: str) -> None:
    request = json.loads(key.REQUESTS[name][2])
    got = producers(request["requested"])
    assert [[m, [[p, r] for p, r in edges.items()]] for m, edges in got.items()] == request[
        "producers"
    ]


@pytest.mark.parametrize("name", list(key.CAPS), ids=list(key.CAPS))
def test_d6_the_cap_is_set_against_the_first_hold(name: str) -> None:
    text, admitted = key.CAPS[name]
    cap = Decimal(text)
    if admitted:
        assert _launch(key.LITE, None, cap).cap_usd == cap
        return
    with pytest.raises(LaunchRefused) as refused:
        _launch(key.LITE, None, cap)
    assert (refused.value.reason, str(refused.value)) == key.CAP_BELOW


@pytest.mark.parametrize("name", list(key.BAD_CAPS), ids=list(key.BAD_CAPS))
def test_d6_a_cap_that_is_not_positive_is_refused_before_the_context(name: str) -> None:
    with pytest.raises(LaunchRefused) as refused:
        _launch(key.NOT_A_CONTEXT, None, _cap(key.BAD_CAPS[name]))
    assert (refused.value.reason, str(refused.value)) == key.CAP_NOT_POSITIVE


def test_d6_a_cap_the_budget_refuses_is_its_own_error() -> None:
    with pytest.raises(BudgetDataError):
        _launch(key.LITE, None, _cap(key.CAP_BUDGET_REFUSES))


@pytest.mark.parametrize("name", list(key.REFUSED), ids=list(key.REFUSED))
def test_d2_a_refused_launch_gives_its_reason_and_text(name: str) -> None:
    raw, modules, cap, reason, text = key.REFUSED[name]
    with pytest.raises(LaunchRefused) as refused:
        _launch(raw, modules, Decimal(cap))
    assert (refused.value.reason, str(refused.value)) == (reason, text)
    assert "\n" not in str(refused.value)


@pytest.mark.parametrize("index", range(len(key.NOT_TEXT_ENTRIES)))
def test_d2_an_entry_that_is_not_text_is_refused_unshown(index: int) -> None:
    with pytest.raises(LaunchRefused) as refused:
        _launch(key.LITE, (key.NOT_TEXT_ENTRIES[index],))
    assert (refused.value.reason, str(refused.value)) == key.NOT_TEXT


def test_d2_the_reasons_are_the_closed_set_of_the_key() -> None:
    assert key.REASONS == get_args(Reason)


def test_d2_the_pathways_are_held_in_every_place() -> None:
    offered = set(catalogue.PATHWAYS)
    assert set(DEACTIVATED) == set(catalogue.PATHWAYS_NOT_OFFERED)
    assert set(DEACTIVATED).isdisjoint(offered)
    assert set(get_args(PathwayId)) == set(key.PATHWAY_IDS) == offered | set(DEACTIVATED)
    assert DEACTIVATED["short_snapshot"] == key.DEACTIVATED


def test_d2_the_names_of_the_key_are_the_catalogue_not_offered() -> None:
    held = set(catalogue.NOT_OFFERED)
    for aliases in catalogue.NOT_OFFERED.values():
        held.update(aliases)
    assert {*key.NOT_OFFERED_NAMES, "CP-MODEL"} == held
