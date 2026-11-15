"""What the store says about one run, as delivery reads it: plain, immutable facts.

The caller (the adapter in a later PR) builds these from the store; delivery never reads the
store. A fact the caller got wrong (an outcome outside the four words, a module code given twice)
is a caller defect and raises `ValueError`, not `DeliveryRefused`: no run is being left out, the
input was never a run's facts. There are no placeholder defaults: every field is required.
"""

from dataclasses import dataclass
from typing import Literal, get_args

Outcome = Literal["accepted", "failed", "not_started", "producer_missing"]
_OUTCOMES = frozenset(get_args(Outcome))


@dataclass(frozen=True, slots=True)
class ModuleFacts:
    """One module of a run: its code, what became of it and the store's reason, if any."""

    code: str
    outcome: Outcome
    reason: str | None

    def __post_init__(self) -> None:
        if self.outcome not in _OUTCOMES:
            raise ValueError("a module outcome must be one of the four outcome words")


@dataclass(frozen=True, slots=True)
class RunFacts:
    """One run as the store holds it, with its modules in plan order."""

    run_id: str
    issuer_name: str
    pathway: str
    status: str
    end_reason: str | None
    as_of: str | None
    modules: tuple[ModuleFacts, ...]

    def __post_init__(self) -> None:
        codes = [module.code for module in self.modules]
        if len(set(codes)) != len(codes):
            raise ValueError("a module code is given twice")
