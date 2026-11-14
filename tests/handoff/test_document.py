import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from credit_os.handoff.blocks import CodeBlock, ListItem, Paragraph, read_blocks
from credit_os.handoff.document import HandoffDocument, Section, parse
from credit_os.handoff.errors import HandoffError
from credit_os.handoff.lines import split_lines
from credit_os.handoff.scan import Heading, scan
from credit_os.handoff.tables import Table

HERE = Path(__file__).resolve().parent
HANDOFFS = HERE.parent / "fixtures" / "handoffs"


def _key(name: str) -> Any:
    return json.loads((HERE / "expected" / name).read_text(encoding="utf-8"))


KEY = _key("document.json")
BLOCKS = _key("blocks.json")
LINES = _key("lines-and-headings.json")
SUMS = {
    line.split("  ", 1)[1]: line.split("  ", 1)[0]
    for line in (HANDOFFS / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
}
OK = (
    "## Request\nr\n## Sources\n## Findings\n### A\nx\n#### B\ny\n### C\n"
    "## Calculations\n## Gaps\n## Next module\nz\n"
)
TREE = [
    [2, "Request", 1, 2],
    [2, "Sources", 3, 3],
    [2, "Findings", 4, 9],
    [3, "A", 5, 8],
    [4, "B", 7, 8],
    [3, "C", 9, 9],
    [2, "Calculations", 10, 10],
    [2, "Gaps", 11, 11],
    [2, "Next module", 12, 13],
]
BT = "`" * 3


def _walk(sections: tuple[Section, ...]) -> list[Section]:
    out: list[Section] = []
    for section in sections:
        out.append(section)
        out.extend(_walk(section.sections))
    return out


def _tree(document: HandoffDocument) -> list[list[Any]]:
    return [[s.level, s.title, s.line, s.end] for s in _walk(document.sections)]


def _kind(block: object) -> str:
    for kind, name in ((Paragraph, "paragraph"), (ListItem, "item"), (Table, "table")):
        if isinstance(block, kind):
            return name
    return "code"


def _find(document: HandoffDocument, title: str) -> Section:
    return next(s for s in _walk(document.sections) if s.title == title)


def test_ok_document() -> None:
    data = OK.encode()
    document = parse(data)
    assert document.sha256 == hashlib.sha256(data).hexdigest()
    assert document.line_count == 13
    assert document.title is None
    assert document.front_matter is None
    assert _tree(document) == TREE
    assert len(document.sections) == 6
    for title, line, text in (("Request", 2, "r"), ("A", 6, "x"), ("B", 8, "y")):
        blocks = _find(document, title).blocks
        assert len(blocks) == 1
        assert isinstance(blocks[0], Paragraph)
        assert (blocks[0].line, blocks[0].lines) == (line, (text,))


def test_bom_and_crlf() -> None:
    bom = ("\ufeff" + OK).encode()
    assert bom.startswith(b"\xef\xbb\xbf")
    document = parse(bom)
    assert _tree(document) == TREE
    assert document.line_count == 13
    assert document.sha256 == hashlib.sha256(bom).hexdigest()
    crlf = parse(OK.replace("\n", "\r\n").encode())
    assert _tree(crlf) == TREE
    assert crlf.line_count == 13


def test_front_matter_and_title() -> None:
    document = parse(("---\nk: ## Request\n---\n# T\n\n<!-- c -->\n" + OK).encode())
    assert document.front_matter is not None
    assert document.front_matter.end == 3
    assert [(e.key, e.value, e.line) for e in document.front_matter.entries] == [
        ("k", "## Request", 2)
    ]
    assert document.title == Heading(level=1, title="T", line=4)
    assert document.sections[0].line == 7


def test_skipped_level_makes_siblings() -> None:
    document = parse(OK.replace("### A", "#### A").encode())
    findings = _find(document, "Findings")
    assert [(s.level, s.title) for s in findings.sections] == [(4, "A"), (4, "B"), (3, "C")]
    assert _find(document, "A").sections == ()


def _oneline(text: str, old: str, new: str) -> str:
    assert old in text
    return text.replace(old, new)


MISSING_FINDINGS = "level-2 heading `Findings` is missing"
LONG = "A" * 81
REFUSED: list[tuple[bytes, int, str]] = [
    (b"", 1, "level-2 heading `Request` is missing"),
    (
        f"## {LONG}\n".encode(),
        1,
        "level-2 heading `" + "A" * 80 + "\u2026` found where `Request` is required",
    ),
    (
        f"## {'B' * 80}\n".encode(),
        1,
        "level-2 heading `" + "B" * 80 + "` found where `Request` is required",
    ),
    (
        (OK + f"## {LONG} tail\n").encode(),
        14,
        "level-2 heading `" + "A" * 80 + "\u2026` is not allowed after `Next module`",
    ),
    (b"## Request\n## Sources\n", 2, "level-2 heading `Findings` is missing"),
    (
        _oneline(OK, "## Gaps\n", "").encode(),
        11,
        "level-2 heading `Next module` found where `Gaps` is required",
    ),
    (
        _oneline(_oneline(OK, "## Sources", "## X"), "## Findings", "## Sources")
        .replace("## X", "## Findings")
        .encode(),
        3,
        "level-2 heading `Findings` found where `Sources` is required",
    ),
    (
        (OK + "## Request\n").encode(),
        14,
        "level-2 heading `Request` is not allowed after `Next module`",
    ),
    (
        _oneline(OK, "## Request", "## request").encode(),
        1,
        "level-2 heading `request` found where `Request` is required",
    ),
    (
        _oneline(OK, "\nx\n", f"\n{BT}\n## Notes\n{BT}\n").encode(),
        7,
        "level-2 heading `Notes` found where `Calculations` is required",
    ),
    (("intro\n" + OK).encode(), 1, "text before `## Request` belongs to no section"),
    (("### Early\n" + OK).encode(), 1, "heading before `## Request` belongs to no section"),
    (
        ("# T\n# U\n" + OK).encode(),
        2,
        "a level-1 heading is allowed only once, before `## Request`",
    ),
    (
        (OK + "# Late\n").encode(),
        14,
        "a level-1 heading is allowed only once, before `## Request`",
    ),
    (b"## Request\n\xff\n", 2, "the file is not valid UTF-8"),
    (b"a\r\xff", 2, "the file is not valid UTF-8"),
    (b"a\r\n\xff", 2, "the file is not valid UTF-8"),
    (b"intro\n## Request\n## Sources\n", 3, MISSING_FINDINGS),
    (b"## Request\n| a | b |\n| 1 |\n## Sources\n", 4, MISSING_FINDINGS),
    (
        ("### Early\nintro\n# T\n# U\n" + OK).encode(),
        4,
        "a level-1 heading is allowed only once, before `## Request`",
    ),
    (
        ("# T\n# U\n" + _oneline(OK, "## Gaps\n", "")).encode(),
        13,
        "level-2 heading `Next module` found where `Gaps` is required",
    ),
    (("intro\n### Early\n" + OK).encode(), 2, "heading before `## Request` belongs to no section"),
]


@pytest.mark.parametrize(("data", "line", "message"), REFUSED)
def test_refused(data: bytes, line: int, message: str) -> None:
    with pytest.raises(HandoffError) as caught:
        parse(data)
    assert caught.value.line == line
    assert caught.value.message == message


def test_table_error_passes_through() -> None:
    text = OK.replace("\nr\n", "\n| a | b |\n| 1 |\n")
    with pytest.raises(HandoffError) as direct:
        read_blocks(scan(split_lines(text)), 1)
    with pytest.raises(HandoffError) as caught:
        parse(text.encode())
    assert caught.value.line == direct.value.line == 2
    assert caught.value.message == direct.value.message
    assert (
        caught.value.message == "the table header is not followed by a separator row of --- cells"
    )


FRAGMENTS = [
    "## Request", "## Sources", "## Findings", "### A", "---", "k: v", BT, "<!--", "-->",
    "| a | b |", "| --- | --- |", "| 1 |", "# T", "text", "\r", "\r\n", "\n", "\xff",
]  # fmt: skip


@given(st.binary() | st.lists(st.sampled_from(FRAGMENTS)).map("\n".join).map(str.encode))
def test_only_handoff_error_leaves_parse(data: bytes) -> None:
    try:
        result = parse(data)
    except HandoffError:
        return
    assert isinstance(result, HandoffDocument)


def test_many_subsections() -> None:
    text = OK.replace("### C\n", "### S\n\ntext\n\n" * 4000 + "### C\n")
    document = parse(text.encode())
    findings = _find(document, "Findings")
    subs = [s for s in findings.sections if s.title == "S"]
    assert len(subs) == 4000
    assert all(len(s.blocks) == 1 and isinstance(s.blocks[0], Paragraph) for s in subs)


@pytest.mark.parametrize("name", sorted(KEY["files"]))
def test_golden_file(name: str) -> None:
    data = (HANDOFFS / name).read_bytes()
    expected = KEY["files"][name]
    document = parse(data)
    assert document.sha256 == SUMS[name]
    assert document.line_count == LINES[name]["lines"]
    if expected["front_matter"] is None:
        assert document.front_matter is None
    else:
        assert document.front_matter is not None
        assert document.front_matter.end == expected["front_matter"]["end"]
        assert [e.key for e in document.front_matter.entries] == expected["front_matter"]["keys"]
    title = None if document.title is None else [document.title.title, document.title.line]
    assert title == expected["title"]
    assert _tree(document) == expected["sections"]
    assert len(document.sections) == 6
    counts = {"table": 0, "paragraph": 0, "item": 0, "code": 0}
    for section in _walk(document.sections):
        for block in section.blocks:
            counts[_kind(block)] += 1
    row = BLOCKS["counts"][name]
    assert counts == {
        "table": row["tables"],
        "paragraph": row["paragraphs"],
        "item": row["items"],
        "code": row["code"],
    }


def test_golden_section_blocks() -> None:
    for name, expected in KEY["section_blocks"].items():
        document = parse((HANDOFFS / name).read_bytes())
        sections = _walk(document.sections)
        assert [
            [s.title, s.line, [[_kind(b), b.line] for b in s.blocks]] for s in sections
        ] == expected


def test_golden_last_lines() -> None:
    for name, title, index, text in KEY["last_lines"]:
        block = _find(parse((HANDOFFS / name).read_bytes()), title).blocks[index]
        assert not isinstance(block, CodeBlock | Table)
        assert block.lines[-1] == text


@pytest.mark.parametrize("name", sorted(KEY["refused"]))
def test_golden_refused(name: str) -> None:
    with pytest.raises(HandoffError) as caught:
        parse((HANDOFFS / name).read_bytes())
    assert caught.value.line == KEY["refused"][name]["line"]
    assert caught.value.message == KEY["refused"][name]["message"]
