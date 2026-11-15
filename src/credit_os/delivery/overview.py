"""The lead module of a run and the Overview page written from it.

The lead is the first code of the run's pathway list (`LEAD_TABLE`, the back-end coordinator's
ruling R2) that is a module of the run, accepted, not blocked and has a Bottom line. There is
no fallback beyond the list. The Overview copies the lead's delivered body values (they already
carry their trace keys); delivery adds no analysis.

R24 condition 1: the run is left out (`DeliveryRefused`, naming the rule only) when no module
can lead (R2), when no module has a dated item (R1), or when the metrics or dates builder
refuses a document it reads. The caller leaves that run out with the reason.
"""

from collections.abc import Mapping, Sequence
from typing import cast

from credit_os.checks.structure import is_blocked
from credit_os.delivery import names
from credit_os.delivery.dates import overview_dates
from credit_os.delivery.errors import DeliveryRefused
from credit_os.delivery.facts import ModuleFacts, RunFacts
from credit_os.delivery.metrics import overview_metrics
from credit_os.delivery.modules import module_items
from credit_os.delivery.wording import Wording
from credit_os.handoff.document import HandoffDocument
from credit_os.handoff.reader import read_reader

LEAD_TABLE: Mapping[str, tuple[str, ...]] = {
    "credit_snapshot": ("CP-6", "CP-2"),
    "portfolio_decision": ("CP-6", "CP-2"),
    "relative_value": ("CP-2",),
    "covenant_refinancing": ("CP-2",),
    "distressed_restructuring": ("CP-2",),
    "lite_credit_assessment": ("CP-2",),
    "earnings_update": ("CP-1B",),
}
_FOUNDATION = "CP-1"
_DELIVERED_STATES = frozenset({"Delivered", "Delivered with gaps"})


def _usable(
    facts: ModuleFacts, documents: Mapping[str, HandoffDocument], bottom_line: bool
) -> bool:
    """Accepted, with a document that is not blocked (and, when asked, has a Bottom line)."""
    document = documents.get(facts.code)
    if facts.outcome != "accepted" or document is None:
        return False
    reader = read_reader(document)
    if is_blocked(document, reader):
        return False
    return reader.bottom_line is not None or not bottom_line


def find_lead(facts: RunFacts, documents: Mapping[str, HandoffDocument]) -> str | None:
    """The lead module's code under R2, or None when the pathway's list gives none."""
    by_code = {module.code: module for module in facts.modules}
    for code in LEAD_TABLE.get(facts.pathway, ()):
        module = by_code.get(code)
        if module is not None and _usable(module, documents, True):
            return code
    return None


def _metrics(
    facts: RunFacts, documents: Mapping[str, HandoffDocument], wording: Wording
) -> list[dict[str, object]]:
    for module in facts.modules:
        if module.code == _FOUNDATION and _usable(module, documents, False):
            return overview_metrics(documents[module.code], wording)
    return []


def _dates(
    facts: RunFacts,
    as_of: str,
    lead: str,
    documents: Mapping[str, HandoffDocument],
    wording: Wording,
) -> list[dict[str, object]]:
    """The first non-empty dated list: the lead's document, then the others in plan order."""
    order = [lead] + [
        m.code for m in facts.modules if m.code != lead and _usable(m, documents, False)
    ]
    for code in order:
        found = overview_dates(documents[code], as_of, wording)
        if found:
            return found
    raise DeliveryRefused("no dated item (R1)")


def build_overview(
    facts: RunFacts,
    as_of: str,
    documents: Mapping[str, HandoffDocument],
    modules: Sequence[Mapping[str, object]],
    gap_total: int,
    wording: Wording,
) -> dict[str, object]:
    """The Overview of a run in the slice's key order; `modules` are `run_modules` bodies."""
    lead = find_lead(facts, documents)
    if lead is None:
        raise DeliveryRefused("no lead module (R2)")
    slug = names.module(lead).slug
    body = next(cast(Mapping[str, object], m["body"]) for m in modules if m["id"] == slug)
    limits = cast(Mapping[str, object], body["limitations"])
    delivered = sum(1 for m in modules if m["state"] in _DELIVERED_STATES)
    return {
        "bottomLine": body["bottomLine"],
        "metricsLabel": wording.fill("overview.metrics_label", {}),
        "metrics": _metrics(facts, documents, wording),
        "sides": None,
        "findings": body["findings"],
        "changeView": body["changeView"],
        "dates": _dates(facts, as_of, lead, documents, wording),
        "modules": {
            "summary": wording.fill(
                "overview.modules_summary", {"delivered": delivered, "total": len(modules)}
            ),
            "items": module_items(modules),
        },
        "limitations": {
            "count": limits["count"],
            "gapsLink": {"label": wording.fill("overview.gaps_link", {"count": gap_total})},
            "items": limits["items"],
        },
    }
