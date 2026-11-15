"""The module catalogue: which analytical modules are offered, what each reads, and how."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

EdgeRule = Literal["block", "restricted"]


@dataclass(frozen=True, slots=True)
class Module:
    id: str
    aliases: tuple[str, ...]
    kind: Literal["prose", "data"]
    scored: bool
    required: tuple[str, ...]
    optional: tuple[str, ...]
    edge_rules: Mapping[str, EdgeRule]

    def __post_init__(self) -> None:
        object.__setattr__(self, "edge_rules", MappingProxyType(dict(self.edge_rules)))


def _row(
    id: str,
    aliases: str,
    kind: Literal["prose", "data"],
    required: str,
    optional: str,
    edge_rules: Mapping[str, EdgeRule],
) -> Module:
    """One catalogue row; the id lists are space separated. Every offered module is scored."""
    return Module(
        id,
        tuple(aliases.split()),
        kind,
        True,
        tuple(required.split()),
        tuple(optional.split()),
        edge_rules,
    )


CATALOGUE: tuple[Module, ...] = (
    _row("CP-0", "CP-PARSE", "data", "", "", {}),
    _row("CP-1", "", "data", "CP-0", "", {}),
    _row("CP-1A", "CP-2C", "prose", "CP-0", "", {}),
    _row("CP-1B", "", "prose", "CP-0 CP-1", "", {}),
    _row("CP-DR", "", "prose", "CP-0 CP-1", "", {}),
    _row("CP-1C", "", "data", "CP-0 CP-1", "CP-DR", {}),
    _row("CP-1D", "CP-1E", "prose", "CP-0 CP-1", "CP-1B", {}),
    _row(
        "CP-2", "", "prose", "CP-0 CP-1 CP-1A", "CP-1B CP-1C CP-1D CP-DR", {"CP-1A": "restricted"}
    ),
    _row("CP-2A", "CP-2B", "prose", "CP-0 CP-1", "CP-1B CP-2", {}),
    _row("CP-2E", "CP-2F", "prose", "CP-0", "CP-1 CP-1A CP-2", {}),
    _row("CP-2G", "", "prose", "CP-0 CP-1 CP-2A", "CP-1D CP-2D", {}),
    _row("CP-2H", "", "prose", "CP-0 CP-1 CP-2G", "CP-1D", {}),
    _row(
        "CP-3",
        "CP-3A CP-3B",
        "prose",
        "CP-0 CP-1 CP-2",
        "CP-1C CP-2H CP-2G CP-1A CP-1D CP-4 CP-3D CP-3C CP-4C CP-2D",
        {},
    ),
    _row("CP-4", "CP-4A CP-4B CP-4D", "prose", "CP-0 CP-1", "CP-1D CP-1A", {"CP-1": "restricted"}),
    _row("CP-4C", "", "prose", "CP-0 CP-1 CP-2G CP-4 CP-2A", "CP-3C CP-1C", {}),
    _row(
        "CP-5",
        "CP-5A",
        "prose",
        "CP-0",
        "CP-1 CP-1A CP-1B CP-1C CP-2 CP-2A CP-2G CP-2E CP-2H CP-3 CP-4C CP-4 CP-2D CP-3C CP-3D",
        {},
    ),
    _row(
        "CP-6",
        "CP-6A",
        "prose",
        "CP-0 CP-1 CP-2 CP-3 CP-5",
        "CP-2A CP-1A CP-2E CP-2D CP-3C CP-3D CP-1B CP-1C CP-4",
        {},
    ),
    _row("CP-2D", "", "prose", "CP-0 CP-1 CP-2", "", {}),
    _row("CP-3D", "", "prose", "CP-0", "CP-2H", {}),
    _row("CP-3C", "", "prose", "CP-0 CP-1 CP-2D", "CP-1A CP-2A CP-4 CP-3D", {}),
)

NOT_OFFERED: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "CP-8": (),
        "CP-L10": ("CP-L20", "CP-L23", "CP-L30", "CP-L40"),
        "CP-MEMO": (),
        "CP-MODEL": (),
        "CP-OS": (),
    }
)

PATHWAYS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "credit_snapshot": (
            "CP-0",
            "CP-1",
            "CP-1A",
            "CP-DR",
            "CP-2",
            "CP-2A",
            "CP-2E",
            "CP-2G",
            "CP-4",
            "CP-3",
            "CP-5",
            "CP-6",
        ),
        "earnings_update": ("CP-0", "CP-1", "CP-1B", "CP-1D", "CP-DR", "CP-2E", "CP-5"),
        "relative_value": (
            "CP-0",
            "CP-1",
            "CP-1C",
            "CP-DR",
            "CP-2",
            "CP-2D",
            "CP-2E",
            "CP-3",
            "CP-3C",
            "CP-3D",
            "CP-5",
        ),
        "covenant_refinancing": (
            "CP-0",
            "CP-1",
            "CP-1A",
            "CP-DR",
            "CP-2",
            "CP-2A",
            "CP-2D",
            "CP-2E",
            "CP-2G",
            "CP-4",
            "CP-3C",
            "CP-5",
        ),
        "distressed_restructuring": (
            "CP-0",
            "CP-1",
            "CP-1A",
            "CP-1C",
            "CP-DR",
            "CP-2",
            "CP-2A",
            "CP-2E",
            "CP-2G",
            "CP-2H",
            "CP-4",
            "CP-4C",
            "CP-5",
        ),
        "portfolio_decision": ("CP-0", "CP-1", "CP-DR", "CP-2", "CP-2E", "CP-3", "CP-5", "CP-6"),
        "lite_credit_assessment": ("CP-0", "CP-1", "CP-1A", "CP-2", "CP-2A"),
    }
)
PATHWAYS_NOT_OFFERED: frozenset[str] = frozenset({"short_snapshot"})

CP5_FAN_IN_EXCLUDES: frozenset[str] = frozenset({"CP-5", "CP-6"})
