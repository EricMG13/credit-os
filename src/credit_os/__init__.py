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
)
