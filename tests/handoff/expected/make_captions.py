"""Answer key for 1B PR 6a4 (R57, R59a): each table's caption line, by the controller's key author.

For every retained fixture that `test_blocks.py` reads (the files of `blocks.json`'s `counts`,
each from its own `from` line), this script reads the fixture text with its own, standard-library
reading of lines, headings, fences, whole-line comments, list items, paragraphs and table rows,
and records for each table its first line, its header cells and its caption: the lines of the
paragraph directly before it (blank lines and whole-line comments between are allowed; a heading,
list item, code block or another table between ends it), stripped as the handoff holds a
paragraph's lines, with the paragraph's first line number; or null. It imports nothing from
`credit_os`. A fixture using a construct this reading does not cover (a comment that is not a
whole line, a pipe line the reader refuses) stops the script. Run this file to write
`captions.json` next to it.
"""

import json
import re
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
HANDOFFS = HERE.parents[1] / "fixtures" / "handoffs"
HEADING = re.compile(r"(#{1,6}) (.*)")
FENCE = re.compile(r" {0,3}(`{3,}|~{3,})(.*)")
MARKER = re.compile(r"[ \t]*(?:[-*+]|\d{1,3}[.)])[ \t]")
ITEM = re.compile(MARKER.pattern + ".*")
ROW = re.compile(r" {0,3}\|.*")
COMMENT_LINE = re.compile(r"\s*<!--(?:(?!-->).)*-->\s*")
Entry = dict[str, Any]


def split_lines(text: str) -> list[str]:
    parts = re.split(r"\r\n|\n|\r", text.removeprefix("﻿"))
    return parts[:-1] if parts[-1] == "" else parts


def classify(lines: list[str]) -> dict[int, str]:
    """Each line's role: `fence` (any line of a code block), `heading`, `blank`, `row` or `text`."""
    roles: dict[int, str] = {}
    fence: tuple[str, int] | None = None
    for number, line in enumerate(lines, 1):
        if fence is not None:
            if line.startswith("## "):  # known limit: a `## ` line ends a fence, unclosed
                fence = None
            else:
                roles[number] = "fence"
                closing = re.fullmatch(r" {0,3}(" + re.escape(fence[0]) + r"+)[ \t]*", line)
                if closing and len(closing[1]) >= fence[1]:
                    fence = None
                continue
        opened = FENCE.fullmatch(line)
        if opened and not (opened[1][0] == "`" and "`" in opened[2]):
            fence = (opened[1][0], len(opened[1]))
            roles[number] = "fence"
        elif "<!--" in line or "-->" in line:
            assert COMMENT_LINE.fullmatch(line), f"line {number}: a comment this key does not read"
            roles[number] = "blank"
        elif HEADING.fullmatch(line):
            roles[number] = "heading"
        elif not line.strip():
            roles[number] = "blank"
        elif ROW.fullmatch(line):
            roles[number] = "row"
        else:
            assert not line.lstrip(" ").startswith("|"), f"line {number}: a refused pipe line"
            roles[number] = "text"
    return roles


def cells(row: str) -> list[str]:
    inner = row.lstrip(" ").rstrip()[1:-1]
    return [cell.strip().replace("\\|", "|") for cell in re.split(r"(?<!\\)\|", inner)]


def captions(lines: list[str], first: int) -> list[Entry]:
    """The tables from line `first` on, each with its header cells and its caption."""
    roles = classify(lines)
    found: list[Entry] = []
    last_kind = ""  # the kind of the last block read: paragraph, item, code or table
    paragraph: tuple[int, list[str]] | None = None  # the last paragraph block, if it is the last
    open_text: tuple[int, str, list[str]] | None = None
    gap = False  # a heading since the last block
    number = first

    def close() -> None:
        nonlocal open_text, last_kind, paragraph, gap
        if open_text is not None:
            line, kind, held = open_text
            last_kind = kind
            paragraph = (line, held) if kind == "paragraph" else None
            open_text = None
            gap = False

    while number <= len(lines):
        role, line = roles[number], lines[number - 1]
        if role == "fence":
            close()
            while number <= len(lines) and roles[number] == "fence":
                number += 1
            last_kind, paragraph, gap = "code", None, False
        elif role == "heading":
            close()
            gap = True
            number += 1
        elif role == "blank":
            close()
            number += 1
        elif role == "row":
            close()
            run = number
            while run <= len(lines) and roles[run] == "row":
                run += 1
            above = paragraph if last_kind == "paragraph" and not gap else None
            found.append(
                {
                    "line": number,
                    "columns": cells(line),
                    "caption": None if above is None else {"line": above[0], "lines": above[1]},
                }
            )
            last_kind, paragraph, gap = "table", None, False
            number = run
        else:
            item = ITEM.fullmatch(line)
            if item:
                close()
                open_text = (number, "item", [])
            elif open_text is None:
                open_text = (number, "paragraph", [])
            open_text[2].append((MARKER.sub("", line, count=1) if item else line).strip())
            number += 1
    close()
    return found


def render() -> str:
    blocks = json.loads((HERE / "blocks.json").read_text("utf-8"))
    files = {}
    for relative, counts in sorted(blocks["counts"].items()):
        text = (HANDOFFS / relative).read_bytes().decode("utf-8")
        found = captions(split_lines(text), counts["from"])
        assert len(found) == counts["tables"], relative
        files[relative] = {"from": counts["from"], "tables": found}
    tables = [entry for held in files.values() for entry in held["tables"]]
    assert sum(entry["caption"] is not None for entry in tables) > 0
    key = {"about": __doc__.split("\n\n")[0], "files": files}
    out = ["{", f' "about": {json.dumps(key["about"], ensure_ascii=True)},', ' "files": {']
    names = list(files)
    for index, name in enumerate(names):
        held = files[name]["tables"]
        body = ",\n".join("   " + json.dumps(entry, ensure_ascii=True) for entry in held)
        head = f'  {json.dumps(name)}: {{"from": {files[name]["from"]}, "tables": ['
        tail = "]}" + ("," if index < len(names) - 1 else "")
        out.append(head + (f"\n{body}\n  " if body else "") + tail)
    return "\n".join(out + [" }", "}"]) + "\n"


if __name__ == "__main__":
    (HERE / "captions.json").write_text(render(), "utf-8")
