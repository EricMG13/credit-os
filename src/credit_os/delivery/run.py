"""One run of delivery: the head, the Overview and the module bodies, or the reason it is left out.

R24 condition 1: a run is left out (`LeftOut`, the rule only) when it has not ended, its state has
no word, its pathway has no lead list, it has no module or no real as-of date, its id is outside
the id grammar, or a builder refuses it (`DeliveryRefused`: see `traces`, `gaps`, `modules`,
`metrics`, `dates` and `overview`). Only `DeliveryRefused` is caught; a caller defect
(`ValueError`, an accepted module with no document) propagates.

The output depends only on the order of `facts.modules`, never on the documents mapping's order.
"""

import datetime
import re
from collections.abc import Mapping
from typing import NamedTuple, cast

from credit_os.delivery import names
from credit_os.delivery.errors import DeliveryRefused
from credit_os.delivery.facts import RunFacts
from credit_os.delivery.gaps import build_gaps
from credit_os.delivery.modules import run_modules
from credit_os.delivery.overview import LEAD_TABLE, build_overview
from credit_os.delivery.traces import build_traces
from credit_os.delivery.wording import Wording
from credit_os.handoff.document import HandoffDocument

_ISO = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", re.ASCII)
_NOT_ENDED = frozenset({"created", "running"})


class RunParts(NamedTuple):
    id: str
    head: dict[str, object]
    traces: object
    overview: dict[str, object]
    modules: tuple[dict[str, object], ...]
    trace_table: object
    jump: object
    gaps: dict[str, object]


class LeftOut(NamedTuple):
    run_id: str
    rule: str


def _real_date(text: str) -> bool:
    if _ISO.fullmatch(text) is None:
        return False
    try:
        datetime.date.fromisoformat(text)
    except ValueError:
        return False
    return True


def _precheck(facts: RunFacts, wording: Wording) -> tuple[str, str]:
    """The state word and the as-of date, or a `DeliveryRefused` naming the rule."""
    if facts.status in _NOT_ENDED:
        raise DeliveryRefused("the run has not ended")
    word = wording.state_word(facts.status, facts.end_reason)
    if word is None:
        raise DeliveryRefused("the run's state has no word (R6)")
    if facts.pathway not in LEAD_TABLE:
        raise DeliveryRefused(f"the pathway is outside the lead table (R2): {facts.pathway}")
    if not facts.modules:
        raise DeliveryRefused("the run has no module (R1)")
    if facts.as_of is None:
        raise DeliveryRefused("the run has no as-of date (R1)")
    if not _real_date(facts.as_of):
        raise DeliveryRefused("the as-of date is not a real date")
    names.check_id(facts.run_id)
    return word, facts.as_of


def _build(facts: RunFacts, documents: Mapping[str, HandoffDocument], wording: Wording) -> RunParts:
    word, as_of = _precheck(facts, wording)
    pairs: list[tuple[str, HandoffDocument]] = []
    for module in facts.modules:
        if module.outcome == "accepted":
            document = documents.get(module.code)
            if document is None:
                raise ValueError("an accepted module needs its document")
            pairs.append((module.code, document))
    traced = build_traces(pairs, as_of, wording)
    gaps = build_gaps(pairs, wording)
    gap_rows = cast(Mapping[str, int], gaps["modules"])
    items = cast(Mapping[str, Mapping[str, object]], traced["items"])
    modules = run_modules(facts, documents, items, gap_rows, wording)
    overview = build_overview(facts, as_of, documents, modules, sum(gap_rows.values()), wording)
    head: dict[str, object] = {
        "issuerName": facts.issuer_name,
        "asOf": wording.fill("card.as_of", {"date": wording.display_date(as_of)}),
        "pathway": wording.fill(f"pathway.{facts.pathway}", {}),
        "state": word,
        "tabs": {"modulesCount": str(len(modules))},
        "firstModule": modules[0]["id"],
        "forecastHref": None,
    }
    return RunParts(
        facts.run_id,
        head,
        traced["traces"],
        overview,
        modules,
        traced["table"],
        traced["jump"],
        gaps,
    )


def build_run(
    facts: RunFacts, documents: Mapping[str, HandoffDocument], wording: Wording
) -> RunParts | LeftOut:
    """The parts of one run, or `LeftOut` with the rule that left it out."""
    try:
        return _build(facts, documents, wording)
    except DeliveryRefused as refused:
        return LeftOut(facts.run_id, str(refused))
