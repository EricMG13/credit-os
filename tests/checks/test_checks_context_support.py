from typing import Any

import pytest
from checks_context_support import build_context

from credit_os.checks.findings import CheckContext

PROSE_NAMES = ("name", "findings", "front", "tail", "expect", "reason_has")
STRUCTURE_NAMES = (*PROSE_NAMES, "reason", "reason_lacks")


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
    context = build_context(
        {"kind": "data"},
        {"name": "a case", "expect": [], "findings": "x"},
        ("name", "expect", "findings"),
    )
    assert context.kind == "data"


@pytest.mark.parametrize("name", ["columns", "reason", "reason_lacks", "sources"])
def test_prose_case_carrying_a_name_its_test_never_reads_is_an_error(name: str) -> None:
    case: dict[str, Any] = {"name": "n", "findings": "", "expect": [], name: {"0": "x"}}
    with pytest.raises(ValueError, match=name):
        build_context({"kind": "data"}, case, PROSE_NAMES)


@pytest.mark.parametrize(
    ("module", "names"),
    [
        ("prose", PROSE_NAMES),
        ("structure", STRUCTURE_NAMES),
        ("fixtures", ()),
    ],
)
def test_each_modules_own_names_load(module: str, names: tuple[str, ...]) -> None:
    case: dict[str, Any] = {name: {} for name in names}
    assert build_context({"kind": "data"}, case, names).kind == "data", module


def test_a_key_only_name_of_another_module_is_an_error() -> None:
    with pytest.raises(ValueError, match="reason_lacks"):
        build_context({"kind": "data"}, {"reason_lacks": {}}, ("name", "reason_has"))
    with pytest.raises(ValueError, match="name"):
        build_context({"kind": "data"}, {"name": "x"})


def test_the_error_names_every_unknown_name() -> None:
    with pytest.raises(ValueError, match=r"'columns'.*'sources'"):
        build_context({"kind": "data"}, {"sources": 1, "columns": 2})
