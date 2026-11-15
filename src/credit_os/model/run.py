"""The forecast run entry: which handoff the inputs come from, and what is checked first (R60).

`read_checked` reads one forecast block and returns it with the figures the reader restated.

- The source is the caller's word, never inferred from the text (D2). `FORWARD_MODEL` reads the
  forward credit model's handoff; `FOUNDATION` reads the block in the foundation's own handoff
  (layer 1). Nothing is guessed, and a failed forward read never falls back to layer 1.
- Caller errors come first, before anything is read: a source that is not a `ForecastSource`, a
  forward run without its handoff, a layer-1 run given one, and a forward handoff that is the
  foundation's own.
- The layer-1 ruling (P1): a layer-1 block states no shock and no cases, and no facilities. The
  first of `downside_shock`, `upside_drivers`, `downside_drivers` that it states is refused as
  the subject; failing those, `facilities`.
- Known ordering: a repayment refusal is raised inside `read_inputs`, so it comes before the
  source refusal. Then `check_foundation` runs once, against the foundation.

`ForecastDeclined` and `ForecastRefused` pass through untouched.

`run_forecast` returns a `ForecastResult`: the source, both document hashes (`None` for the
forward one on layer 1), currency, scale, the three spans, every case, the stress basis, the
facility detail and the limits. It carries no base figures, no drivers and no shock (D10): the
inputs stay in the handoff. Its `__post_init__` refuses a result in which a case year has
negative closing cash but net debt, net leverage or liquidity is not the negative-cash gap (D8).
A figure too wide for 38 digits is refused as `RefusalKind.SIZE` by `cases.run_cases` (D9).
"""

from dataclasses import dataclass
from enum import StrEnum

from credit_os.handoff.document import HandoffDocument
from credit_os.model.cases import NEGATIVE_CASH, Case, StressBasis, run_cases
from credit_os.model.detail import Detail, facility_detail, facility_limits
from credit_os.model.foundation import check_foundation
from credit_os.model.inputs import ForecastInputs, Span, read_inputs
from credit_os.model.refusals import ForecastRefused, RefusalKind
from credit_os.model.value import Missing, MissingCode, Value


class ForecastSource(StrEnum):
    FORWARD_MODEL = "CP-2G"
    FOUNDATION = "CP-1"


_NO_CASES = "a layer-1 forecast states no shock and no cases"
_NO_FACILITIES = "a layer-1 forecast states no facilities"


def _caller_errors(
    foundation: HandoffDocument, source: ForecastSource, forward: HandoffDocument | None
) -> None:
    if not isinstance(source, ForecastSource):
        raise TypeError("source must be a ForecastSource")
    if source is ForecastSource.FORWARD_MODEL:
        if forward is None:
            raise ValueError("a forward model forecast needs the forward model's handoff")
        if forward.sha256 == foundation.sha256:
            raise ValueError("the forward model's handoff is the foundation's own handoff")
    elif forward is not None:
        raise ValueError(
            "a layer-1 forecast reads the foundation's own block; no forward handoff is given"
        )


def _layer1_restriction(inputs: ForecastInputs) -> None:
    for name in ("downside_shock", "upside_drivers", "downside_drivers"):
        if getattr(inputs, name) is not None:
            raise ForecastRefused(RefusalKind.SOURCE, name, _NO_CASES)
    if inputs.facilities is not None:
        raise ForecastRefused(RefusalKind.SOURCE, "facilities", _NO_FACILITIES)


def read_checked(
    foundation: HandoffDocument,
    source: ForecastSource,
    forward: HandoffDocument | None = None,
) -> tuple[ForecastInputs, dict[str, str]]:
    _caller_errors(foundation, source, forward)
    if source is ForecastSource.FORWARD_MODEL and forward is not None:
        inputs, stated = read_inputs(forward)
    else:
        inputs, stated = read_inputs(foundation)
        _layer1_restriction(inputs)
    check_foundation(inputs, stated, foundation)
    return inputs, stated


LIMIT = (
    "Every figure is Python's arithmetic over inputs the forward credit model stated; "
    "the inputs, not the arithmetic, are unreviewed. Not analytical review."
)
LAYER1_LIMIT = (
    "Every figure is Python's arithmetic over run-rate inputs the financial foundation stated, "
    "from its own figures; no forward credit model, case or shock was run. "
    "The inputs, not the arithmetic, are unreviewed. Not analytical review."
)


def scale_limit(currency: str) -> str:
    return (
        f"The forecast inputs state base amounts, amount drivers and facility amounts in "
        f"{currency} thousands, as the financial foundation prints them (scale 1000); "
        f"Python divided each by 1,000 before any calculation. "
        f"Every figure here is {currency} millions."
    )


_GAP = Value(missing=Missing(MissingCode.NEGATIVE_CASH, NEGATIVE_CASH))
_OVERLAID = ("net_debt", "net_leverage", "liquidity")


@dataclass(frozen=True, slots=True)
class ForecastResult:
    source: ForecastSource
    foundation_sha256: str
    forward_sha256: str | None
    currency: str
    scale: int
    spans: tuple[Span, Span, Span]
    cases: tuple[Case, ...]
    stress_basis: StressBasis | None
    facilities: Detail | None
    limits: tuple[str, ...]

    def __post_init__(self) -> None:
        for case in self.cases:
            for year in case.years:
                cash = year.closing_cash.amount
                if cash is None or cash >= 0:
                    continue
                if any(getattr(year, name) != _GAP for name in _OVERLAID):
                    raise ValueError(
                        "a year with negative closing cash carries the negative-cash gap"
                    )


def run_forecast(
    foundation: HandoffDocument,
    source: ForecastSource,
    forward: HandoffDocument | None = None,
) -> ForecastResult:
    inputs, _ = read_checked(foundation, source, forward)
    cases, basis = run_cases(inputs)
    forward_source = source is ForecastSource.FORWARD_MODEL
    limits = [LIMIT if forward_source else LAYER1_LIMIT]
    if inputs.scale == 1000:
        limits.append(scale_limit(inputs.currency))
    limits.extend(inputs.scope_limits)
    limits.extend(facility_limits(inputs))
    return ForecastResult(
        source=source,
        foundation_sha256=foundation.sha256,
        forward_sha256=None if forward is None else forward.sha256,
        currency=inputs.currency,
        scale=inputs.scale,
        spans=inputs.years,
        cases=cases,
        stress_basis=basis,
        facilities=facility_detail(inputs),
        limits=tuple(limits),
    )
