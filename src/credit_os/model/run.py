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
"""

from enum import StrEnum

from credit_os.handoff.document import HandoffDocument
from credit_os.model.foundation import check_foundation
from credit_os.model.inputs import ForecastInputs, read_inputs
from credit_os.model.refusals import ForecastRefused, RefusalKind


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
