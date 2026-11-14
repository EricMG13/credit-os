from typing import Any

import pytest
from checks_context_support import build_context

from credit_os.checks.findings import CheckContext


@pytest.mark.parametrize(
    ("base", "case"),
    [
        ({"kind": "prose", "scorred": True}, {}),
        ({"kind": "prose"}, {"scorred": True}),
    ],
)
def test_unknown_context_field_is_an_error_naming_it(
    base: dict[str, Any], case: dict[str, Any]
) -> None:
    with pytest.raises(ValueError, match="scorred"):
        build_context(base, case)


def test_scored_in_a_case_is_read() -> None:
    context = build_context({"kind": "prose"}, {"scored": True})
    assert isinstance(context, CheckContext)
    assert context.scored is True


def test_key_only_names_in_a_case_are_not_context_fields() -> None:
    context = build_context({"kind": "data"}, {"name": "a case", "expect": [], "findings": "x"})
    assert context.kind == "data"
