import json
import re
from pathlib import Path
from typing import Any

import pytest
from checks_context_support import build_context, expand_digests, without_held

from credit_os.checks import passages, sources
from credit_os.checks.findings import CheckContext, Finding
from credit_os.checks.run import check_handoff
from credit_os.handoff.document import HandoffDocument, parse
from credit_os.handoff.errors import HandoffError
from credit_os.handoff.reader import read_reader

_COLUMN_CHECKS = ("prose.register-id", "figure.not-held", "figure.mismatch")
KEY: dict[str, Any] = json.loads(
    (Path(__file__).resolve().parent / "expected" / "passages.json").read_text("utf-8")
)
CASES: dict[str, dict[str, Any]] = {case["name"]: case for case in KEY["cases"]}
_SHA = re.compile(r"\{sha:(CP-[A-Z0-9]+)\}")
_KEY_ONLY = ("name", "findings", "front", "tail", "sources", "expect")

NEW_CHECKS = (
    passages.check_register_id,
    passages.check_limitation_repeat,
    sources.check_table,
    sources.check_name,
    sources.check_sha256,
    sources.check_type,
)


def _expand(text: str, context: CheckContext) -> str:
    text = text.replace("{lead}", KEY["lead"])
    text = _SHA.sub(lambda found: context.upstream[found.group(1)].sha256, text)
    return expand_digests(text)


def _context(case: dict[str, Any]) -> CheckContext:
    """The key's `accepted` maps a module code to a whole document's text, not to a fixture path."""
    base = {"kind": "data", **KEY["context"]}
    accepted = case.get("accepted", base.pop("accepted", {}))
    plain = {name: value for name, value in case.items() if name != "accepted"}
    context = build_context(base, plain, _KEY_ONLY)
    fields = {name: getattr(context, name) for name in CheckContext.model_fields}
    fields["accepted"] = {code: parse(text.encode("utf-8")) for code, text in accepted.items()}
    return CheckContext(**fields)


def _build(case: dict[str, Any]) -> tuple[HandoffDocument, CheckContext, list[list[Any]]]:
    context = _context(case)

    def part(name: str) -> str:
        return _expand(case.get(name, KEY.get(name, "")), context)

    text = "".join(part(name) for name in ("front", "top", "sources", "mid", "findings", "tail"))
    expected = [[*row[:3], _expand(row[3], context)] for row in case["expect"]]
    return parse(text.encode("utf-8")), context, expected


def _row(finding: Finding) -> list[Any]:
    return [finding.check, finding.severity, finding.line, finding.quoted]


def _document(findings: str, sources_text: str | None = None) -> HandoffDocument:
    text = (
        KEY["top"]
        + (KEY["sources"] if sources_text is None else sources_text)
        + KEY["mid"]
        + findings
        + KEY["tail"]
    )
    return parse(text.encode("utf-8"))


def _ctx(**fields: Any) -> CheckContext:
    return build_context({"kind": "data", **KEY["context"]}, fields)


@pytest.mark.parametrize("name", list(CASES))
def test_case(name: str) -> None:
    document, context, expected = _build(CASES[name])
    assert [_row(finding) for finding in without_held(check_handoff(document, context))] == expected


@pytest.mark.parametrize("name", list(CASES))
def test_finding_shape(name: str) -> None:
    document, context, _ = _build(CASES[name])
    for finding in check_handoff(document, context):
        assert finding.reason.strip() != ""
        assert "\n" not in finding.reason
        assert finding.column == 1 or finding.check in _COLUMN_CHECKS


@pytest.mark.parametrize("name", list(CASES))
def test_deterministic(name: str) -> None:
    document, context, _ = _build(CASES[name])
    assert check_handoff(document, context) == check_handoff(document, context)


def test_register_id_columns() -> None:
    tail = "## Calculations\n| ID | Value |\n| --- | --- |\n| C-1 | high |\n## Gaps\nNone.\n"
    text = KEY["top"] + KEY["sources"] + KEY["mid"] + "### Bottom line\nSee C-1, then (C-1).\n"
    document = parse((text + tail + "## Next module\nNone.\n").encode("utf-8"))
    found = passages.check_register_id(document, _ctx())
    assert [(f.line, f.column, f.quoted) for f in found] == [(8, 5, "C-1"), (8, 16, "C-1")]


_LIMITS = (
    "### Bottom line\nx\n### Key findings\n- k\n### Contrary evidence and what would change "
    "the view\nc\n### Limitations\n"
    "- Revenue is **unaudited**, so the view could soften.\n"
    "- Revenue is unaudited,\n  so the view could soften.\n  Basis: a.pdf, page 3\n"
    "\nSecond.\n\nBasis: a.pdf\n"
    "#### More\n- Year-on-year data.\n"
)


def test_limitation_texts() -> None:
    assert passages.limitation_texts(_document(_LIMITS)) == (
        "Revenue is **unaudited**, so the view could soften.",
        "Revenue is unaudited, so the view could soften.",
        "Second.",
        "Year-on-year data.",
    )


def test_limitation_texts_without_a_passage() -> None:
    earlier = _document("### Overview\no\n")
    assert passages.limitation_texts(earlier) == ()
    missing = _document("### Bottom line\nx\n")
    assert passages.limitation_texts(missing) == ()
    repeated = _document("### Bottom line\nx\n### Limitations\n- a\n### Limitations\n- b\n")
    with pytest.raises(HandoffError):
        read_reader(repeated)
    assert passages.limitation_texts(repeated) == ()


@pytest.mark.parametrize(
    ("text", "key"),
    [
        (
            "Revenue is **unaudited**, so the view could soften.",
            "revenue is unaudited so the view could soften",
        ),
        ("year-on-year", "yearonyear"),
        ("  A\t\tb  \n c ", "a b c"),
        ("...", ""),
        ("Résumé", "résumé"),
    ],
)
def test_normalise_limitation(text: str, key: str) -> None:
    assert passages.normalise_limitation(text) == key


def test_one_thousand_unknown_names() -> None:
    rows = "".join(f"| unknown{n}.pdf | u |\n" for n in range(1000))
    document = _document("### Bottom line\nx\n", "| Source | Use |\n| --- | --- |\n" + rows)
    found = sources.check_name(document, _ctx())
    assert len(found) == 1000
    assert {finding.check for finding in found} == {"sources.name"}


def test_each_new_check_alone_on_earlier_format() -> None:
    document = _document("### Overview\no\n")
    for check in NEW_CHECKS:
        check(document, _ctx())
    assert passages.check_register_id(document, _ctx()) == ()
    assert passages.check_limitation_repeat(document, _ctx()) == ()
    assert sources.check_table(document, _ctx()) == ()


def test_each_new_check_alone_when_the_reader_raises() -> None:
    document = _document("### Bottom line\nx\n### Limitations\n- a\n### Limitations\n- b\n")
    with pytest.raises(HandoffError):
        read_reader(document)
    for check in NEW_CHECKS:
        check(document, _ctx())
    assert passages.check_register_id(document, _ctx()) == ()
    assert passages.check_limitation_repeat(document, _ctx()) == ()
    assert sources.check_table(document, _ctx()) == ()
