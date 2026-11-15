"""The run entry (`read_checked`) against the answer key (R60, P1)."""

import decimal
import importlib.util
import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from credit_os.handoff.document import HandoffDocument, parse
from credit_os.model import run
from credit_os.model.refusals import ForecastDeclined, ForecastRefused, RefusalKind

ForecastSource, read_checked = run.ForecastSource, run.read_checked

EXPECTED = Path(__file__).parent / "expected"
KEY = json.loads((EXPECTED / "pr7c1.json").read_text("utf-8"))
ROWS = KEY["rows"]
KINDS = {"accepted": 4, "refused": 24, "declined": 2}
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "model"

HELPERS = importlib.util.spec_from_file_location(
    "case_key_helpers", EXPECTED / "case_key_helpers.py"
)
assert HELPERS is not None and HELPERS.loader is not None
H = importlib.util.module_from_spec(HELPERS)
HELPERS.loader.exec_module(H)
ORACLE = H.load_oracle("make_pr7c1")
HOSTILE, ids = H.HOSTILE, H.ids


def document(spec: dict[str, Any] | None) -> HandoffDocument | None:
    return None if spec is None else parse(ORACLE.data(spec))


def read_row(row: dict[str, Any]) -> Any:
    foundation = document(row["foundation"])
    assert foundation is not None
    return read_checked(foundation, ForecastSource(row["source"]), document(row["forward"]))


def check_outcome(row: dict[str, Any]) -> None:
    where = row["name"]
    if row["kind"] == "accepted":
        inputs, stated = read_row(row)
        exp = row["expected"]
        assert (inputs.scale, inputs.currency) == (exp["scale"], exp["currency"]), where
        assert [f.name for f in inputs.facilities or ()] == exp["facilities"], where
        assert (inputs.upside_drivers is not None) is exp["upside"], where
        assert (inputs.downside_drivers is not None) is exp["downside"], where
        assert (inputs.downside_shock is not None) is exp["shock"], where
        assert stated == exp["stated"], where
    elif row["kind"] == "declined":
        with pytest.raises(ForecastDeclined) as declined:
            read_row(row)
        assert str(declined.value) == row["message"], where
    else:
        with pytest.raises(ForecastRefused) as refused:
            read_row(row)
        kind, subject, message = row["outcome"]
        assert refused.value.kind is RefusalKind(kind), where
        assert (refused.value.subject, refused.value.message) == (subject, message), where


@pytest.mark.parametrize("row", ROWS, ids=ids(ROWS))
def test_key_row(row: dict[str, Any]) -> None:
    check_outcome(row)


@pytest.mark.parametrize("row", ROWS, ids=ids(ROWS))
def test_key_row_under_a_hostile_local_context(row: dict[str, Any]) -> None:
    with decimal.localcontext(HOSTILE):
        check_outcome(row)


def test_row_counts() -> None:
    assert len(ROWS) == 30
    assert Counter(r["kind"] for r in ROWS) == KINDS
    assert KEY["kinds"] == KINDS
    assert len({r["name"] for r in ROWS}) == 30


def test_the_surface_matches_the_key() -> None:
    assert [(m.name, m.value) for m in ForecastSource] == [
        ("FORWARD_MODEL", "CP-2G"),
        ("FOUNDATION", "CP-1"),
    ]
    assert [k.value for k in RefusalKind][-1] == "source"


def test_the_source_is_the_callers_word_not_read_from_the_text() -> None:
    """The same layer-1 block in the foundation is read when asked for, and refused as forward."""
    foundation = parse((FIXTURES / "foundation.md").read_bytes())
    forward = parse((FIXTURES / "forward-model.md").read_bytes())
    own, _ = read_checked(foundation, ForecastSource.FOUNDATION)
    assert own.facilities is None and own.upside_drivers is None
    both, _ = read_checked(foundation, ForecastSource.FORWARD_MODEL, forward)
    assert both.facilities is not None and both.upside_drivers is not None


CALLER_TEXT = {
    "source": "source must be a ForecastSource",
    "missing": "a forward model forecast needs the forward model's handoff",
    "given": "a layer-1 forecast reads the foundation's own block; no forward handoff is given",
    "same": "the forward model's handoff is the foundation's own handoff",
}


@pytest.mark.parametrize(
    ("source", "forward", "error", "text"),
    [
        ("CP-2G", "forward", TypeError, "source"),
        (None, None, TypeError, "source"),
        (ForecastSource.FORWARD_MODEL, None, ValueError, "missing"),
        (ForecastSource.FOUNDATION, "forward", ValueError, "given"),
        (ForecastSource.FORWARD_MODEL, "same", ValueError, "same"),
    ],
    ids=["str_source", "none_source", "no_forward", "layer1_with_forward", "same_document"],
)
def test_caller_errors_come_first_and_read_nothing(
    source: Any, forward: str | None, error: type[Exception], text: str
) -> None:
    """The foundation here has no forecast block: a read of it would refuse, not raise this."""
    data = (FIXTURES / "foundation-eur.md").read_bytes()
    other = (FIXTURES / "forward-model.md").read_bytes()
    second = None if forward is None else parse(data if forward == "same" else other)
    with pytest.raises(error) as caught:
        read_checked(parse(data), source, second)
    assert type(caught.value) is error
    assert str(caught.value) == CALLER_TEXT[text]
