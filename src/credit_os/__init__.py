"""credit-os: issuer source files in, an issuer library out."""

__version__ = "0.1.0"

LAYERS: tuple[str, ...] = (
    "sources",
    "handoff",
    "model",
    "provider",
    "store",
    "checks",
    "orchestrator",
    "delivery",
    "signal",
)
# An isolated package imports no other layer and no other layer imports it (decision 0009).
ISOLATED: frozenset[str] = frozenset({"signal"})
