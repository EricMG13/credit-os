import json
from pathlib import Path
from typing import Any

import pytest

from credit_os.checks.text import passage_text, shown_text
from credit_os.handoff.document import HandoffDocument, parse
from credit_os.handoff.reader import read_reader

HERE = Path(__file__).resolve().parent
HANDOFFS = HERE.parent / "fixtures" / "handoffs"
KEY: dict[str, Any] = json.loads((HERE / "expected" / "text.json").read_text("utf-8"))


def _compare(document: HandoffDocument, entry: dict[str, Any]) -> None:
    passage = passage_text(document, read_reader(document))
    assert [item.line for item in passage] == entry["passage"]
    shown = shown_text(document)
    if "shown" in entry:
        assert [item.line for item in shown] == entry["shown"]
    by_line: dict[int, str] = {}
    for item in (*passage, *shown):
        by_line[item.line] = item.text
    for number, text in entry.get("texts", {}).items():
        assert by_line[int(number)] == text


@pytest.mark.parametrize("name", sorted(KEY["fixtures"]))
def test_fixture(name: str) -> None:
    document = parse((HANDOFFS / name).read_bytes())
    _compare(document, KEY["fixtures"][name])


def test_case() -> None:
    case = KEY["case"]
    _compare(parse(case["document"].encode("utf-8")), case)


def test_case_nested() -> None:
    case = KEY["case_nested"]
    _compare(parse(case["document"].encode("utf-8")), case)
