"""The tables a module owes: one specification per heading, and which module owes which.

`SPECS` is the closed catalogue, keyed by heading; `OWED` lists, module by module, every table
that module owes, in the order its checks ask for them. A heading in `OWED` with no entry in
`SPECS` has no check yet (its pull request adds the row). This module imports nothing from
`checks/`, so `findings` can validate against it.
"""

from collections.abc import Mapping
from types import MappingProxyType

from credit_os.handoff.scan import Node


class TableSpec(Node):
    """A period table: `Period`, the value columns, `Reporting unit`, `Basis and limitation`."""

    heading: str
    value_columns: tuple[str, ...]
    chart_unit: str

    @property
    def header(self) -> tuple[str, ...]:
        return ("Period", *self.value_columns, "Reporting unit", "Basis and limitation")


def _period(heading: str, unit: str, *value_columns: str) -> TableSpec:
    return TableSpec(heading=heading, value_columns=value_columns, chart_unit=unit)


_PERIOD = (
    _period("Chart data: leverage", "x", "Total debt / EBITDA", "Net debt / EBITDA"),
    _period("Chart data: interest cover", "x", "EBITDA / cash interest"),
    _period("Chart data: liquidity", "US$m", "Cash", "Undrawn committed facilities"),
    _period("Chart data: debt maturities", "US$m", "Debt maturing"),
    _period("Chart data: revenue and EBITDA", "US$m", "Revenue", "Adjusted EBITDA"),
    _period("Chart data: refinancing need", "US$m", "Debt maturing", "Committed resources"),
    _period("Net debt data", "US$m", "Gross debt", "Cash", "Net debt"),
)

SPECS: Mapping[str, TableSpec] = MappingProxyType({spec.heading: spec for spec in _PERIOD})

OWED: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "CP-0": ("Events: Sources",),
        "CP-1": (
            "Chart data: leverage",
            "Chart data: interest cover",
            "Chart data: liquidity",
            "Chart data: debt maturities",
            "Net debt data",
            "Post-balance-sheet adjustments",
            "Chart data: revenue and EBITDA",
            "Chart data: debt stack",
            "Chart data: EBITDA bridge",
        ),
        "CP-1A": (
            "Events: Issuer history",
            "Map: ownership and control",
            "Map: operating model to credit",
        ),
        "CP-1B": (
            "Chart data: prior and current results",
            "Chart data: margin and KPI changes",
            "Events: Earnings and guidance",
        ),
        "CP-1C": (
            "Chart data: peer range — percent metrics",
            "Chart data: peer range — multiples",
        ),
        "CP-DR": ("Events: Research catalysts",),
        "CP-2": ("Map: credit-risk transmission",),
        "CP-2A": ("Map: stress scenario",),
        "CP-2D": ("Chart data: liquidity bridge", "Events: Financing"),
        "CP-2E": ("Events: Hedges",),
        "CP-2H": ("Chart data: rating triggers", "Events: Ratings"),
        "CP-3": ("Events: Instruments",),
        "CP-3C": ("Chart data: refinancing need", "Events: Refinancing"),
        "CP-3D": ("Chart data: yield against maturity",),
        "CP-4": (
            "Chart data: covenant headroom",
            "Events: Legal",
            "Map: legal entities",
            "Map: intercreditor",
        ),
        "CP-4C": (
            "Chart data: recovery by class",
            "Chart data: value allocation — scenario 1",
            "Chart data: value allocation — scenario 2",
            "Chart data: value allocation — scenario 3",
        ),
        "CP-5": ("Map: support and contradiction",),
        "CP-6": ("Chart data: portfolio limits", "Events: Decision and watch"),
    }
)
