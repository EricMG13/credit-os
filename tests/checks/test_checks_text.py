import json
from pathlib import Path
from typing import Any

import pytest

from credit_os.checks.text import passage_text, section_blocks, shown_text
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


@pytest.mark.parametrize("name", ["case", "case_nested"])
def test_passage_text_reader_from_equal_reparse(name: str) -> None:
    case = KEY[name]
    data = case["document"].encode("utf-8")
    document_a = parse(data)
    document_b = parse(data)
    passage = passage_text(document_a, read_reader(document_b))
    assert [item.line for item in passage] == case["passage"]


def test_section_blocks_walk_nested_sections_and_skip_data_sections() -> None:
    document = parse(KEY["case_nested"]["document"].encode("utf-8"))
    reader = read_reader(document)
    assert reader.bottom_line is not None
    assert reader.key_findings is not None
    # Bottom line (line 4) holds the paragraph at 7; its data child "Chart data" (and the
    # section under it) gives nothing; "Detail" gives line 13. Key findings gives the item at 15.
    assert [block.line for block in section_blocks(document, reader.bottom_line)] == [7, 13]
    assert [block.line for block in section_blocks(document, reader.key_findings)] == [15]
