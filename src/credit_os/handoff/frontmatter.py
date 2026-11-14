"""Front matter: `key: value` lines between `---` lines at the very top, kept as strings."""

import re
from collections.abc import Sequence

from credit_os.handoff.errors import HandoffError
from credit_os.handoff.scan import Node

_MARKER = re.compile(r"^---[ \t]*$")
_ENTRY = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):(?:$|[ \t]+(.*)$)")


class Entry(Node):
    key: str
    value: str
    line: int


class FrontMatter(Node):
    line: int
    end: int
    entries: tuple[Entry, ...]


def _entry(text: str, number: int) -> Entry:
    found = _ENTRY.match(text)
    if found is None:
        raise HandoffError(number, "front matter line is not `key: value`")
    return Entry(key=found.group(1), value=(found.group(2) or "").strip(" \t"), line=number)


def read_front_matter(lines: Sequence[str]) -> FrontMatter | None:
    if not lines or not _MARKER.match(lines[0]):
        return None
    entries: list[Entry] = []
    seen: set[str] = set()
    for number, text in enumerate(lines[1:], 2):
        if _MARKER.match(text):
            return FrontMatter(line=1, end=number, entries=tuple(entries))
        entry = _entry(text, number)
        if entry.key in seen:
            raise HandoffError(number, f"front matter key `{entry.key}` is repeated")
        seen.add(entry.key)
        entries.append(entry)
    raise HandoffError(1, "the front matter opened here is never closed by ---")
