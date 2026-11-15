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


CATALOGUE: tuple[Module, ...] = (
    Module(
        "CP-0",
        ("CP-PARSE",),
        "data",
        True,
        (),
        (),
        {},
    ),
    Module(
        "CP-1",
        (),
        "data",
        True,
        ("CP-0",),
        (),
        {},
    ),
    Module(
        "CP-1A",
        ("CP-2C",),
        "prose",
        True,
        ("CP-0",),
        (),
        {},
    ),
    Module(
        "CP-1B",
        (),
        "prose",
        True,
        ("CP-0", "CP-1"),
        (),
        {},
    ),
    Module(
        "CP-DR",
        (),
        "prose",
        True,
        ("CP-0", "CP-1"),
        (),
        {},
    ),
    Module(
        "CP-1C",
        (),
        "data",
        True,
        ("CP-0", "CP-1"),
        ("CP-DR",),
        {},
    ),
    Module(
        "CP-1D",
        ("CP-1E",),
        "prose",
        True,
        ("CP-0", "CP-1"),
        ("CP-1B",),
        {},
    ),
    Module(
        "CP-2",
        (),
        "prose",
        True,
        ("CP-0", "CP-1", "CP-1A"),
        ("CP-1B", "CP-1C", "CP-1D", "CP-DR"),
        {"CP-1A": "restricted"},
    ),
    Module(
        "CP-2A",
        ("CP-2B",),
        "prose",
        True,
        ("CP-0", "CP-1"),
        ("CP-1B", "CP-2"),
        {},
    ),
    Module(
        "CP-2E",
        ("CP-2F",),
        "prose",
        True,
        ("CP-0",),
        ("CP-1", "CP-1A", "CP-2"),
        {},
    ),
    Module(
        "CP-2G",
        (),
        "prose",
        True,
        ("CP-0", "CP-1", "CP-2A"),
        ("CP-1D", "CP-2D"),
        {},
    ),
    Module(
        "CP-2H",
        (),
        "prose",
        True,
        ("CP-0", "CP-1", "CP-2G"),
        ("CP-1D",),
        {},
    ),
    Module(
        "CP-3",
        ("CP-3A", "CP-3B"),
        "prose",
        True,
        ("CP-0", "CP-1", "CP-2"),
        ("CP-1C", "CP-2H", "CP-2G", "CP-1A", "CP-1D", "CP-4", "CP-3D", "CP-3C", "CP-4C", "CP-2D"),
        {},
    ),
    Module(
        "CP-4",
        ("CP-4A", "CP-4B", "CP-4D"),
        "prose",
        True,
        ("CP-0", "CP-1"),
        ("CP-1D", "CP-1A"),
        {"CP-1": "restricted"},
    ),
    Module(
        "CP-4C",
        (),
        "prose",
        True,
        ("CP-0", "CP-1", "CP-2G", "CP-4", "CP-2A"),
        ("CP-3C", "CP-1C"),
        {},
    ),
    Module(
        "CP-5",
        ("CP-5A",),
        "prose",
        True,
        ("CP-0",),
        (
            "CP-1",
            "CP-1A",
            "CP-1B",
            "CP-1C",
            "CP-2",
            "CP-2A",
            "CP-2G",
            "CP-2E",
            "CP-2H",
            "CP-3",
            "CP-4C",
            "CP-4",
            "CP-2D",
            "CP-3C",
            "CP-3D",
        ),
        {},
    ),
    Module(
        "CP-6",
        ("CP-6A",),
        "prose",
        True,
        ("CP-0", "CP-1", "CP-2", "CP-3", "CP-5"),
        ("CP-2A", "CP-1A", "CP-2E", "CP-2D", "CP-3C", "CP-3D", "CP-1B", "CP-1C", "CP-4"),
        {},
    ),
    Module(
        "CP-2D",
        (),
        "prose",
        True,
        ("CP-0", "CP-1", "CP-2"),
        (),
        {},
    ),
    Module(
        "CP-3D",
        (),
        "prose",
        True,
        ("CP-0",),
        ("CP-2H",),
        {},
    ),
    Module(
        "CP-3C",
        (),
        "prose",
        True,
        ("CP-0", "CP-1", "CP-2D"),
        ("CP-1A", "CP-2A", "CP-4", "CP-3D"),
        {},
    ),
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
