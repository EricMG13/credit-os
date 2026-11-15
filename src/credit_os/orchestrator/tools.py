"""The source tools a module may call, and the one function that runs them.

The pages are given in; nothing here reads a file, builds a path or compiles a pattern from
model text. Every error is one fixed line, with no model text in it (decision 0012, D10).
"""

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Any

from credit_os.provider.types import ToolCall, ToolSpec
from credit_os.sources.pages import SourcePages
from credit_os.sources.pins import SourcePin

_READ_LIMIT = 8
_HIT_LIMIT = 20
_CONTEXT = 80
_QUERY_LIMIT = 1000

_E_UNKNOWN_TOOL = (
    "ERROR: unknown tool; the source tools are list_sources, read_pages, search_source"
)
_E_BAD_ARGUMENTS = "ERROR: the arguments could not be read as a JSON object"
_E_NO_SOURCE = "ERROR: source_id must be the exact name of a source from list_sources"
_E_PAGES = (
    "ERROR: first and last must be whole page numbers with 1 <= first <= last and first at "
    "most {count}, the source's page count"
)
_E_QUERY = "ERROR: query must be text of 1 to 1,000 characters that is not only spaces"
_E_KEYS = {
    "list_sources": "ERROR: list_sources takes no arguments",
    "read_pages": "ERROR: read_pages takes exactly source_id, first and last",
    "search_source": "ERROR: search_source takes exactly source_id and query",
}
_KEYS = {
    "list_sources": frozenset[str](),
    "read_pages": frozenset({"source_id", "first", "last"}),
    "search_source": frozenset({"source_id", "query"}),
}
_NOTE_EIGHT = "NOTE: a read stops after 8 pages; pages {start} to {end} were not read"
_NOTE_TWENTY = "NOTE: a search stops at 20 hits"
_NO_MATCH = "no match in this source"


@dataclass(frozen=True, slots=True)
class PagedSource:
    """A pinned source and its pages, as the tools see it."""

    pin: SourcePin
    pages: SourcePages


def _object(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


SOURCE_TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="list_sources",
        description="List every source: its exact name, sha256 digest and page count.",
        parameters=_object({}),
    ),
    ToolSpec(
        name="read_pages",
        description=(
            "Read pages first to last of one source, numbered from 1; at most eight pages "
            "a call, each shown with its number and state."
        ),
        parameters=_object(
            {
                "source_id": {"type": "string"},
                "first": {"type": "integer"},
                "last": {"type": "integer"},
            }
        ),
    ),
    ToolSpec(
        name="search_source",
        description=(
            "Search one source for exact, case-sensitive text, not a pattern; up to twenty "
            "hits, each with its page number and the text around it."
        ),
        parameters=_object({"source_id": {"type": "string"}, "query": {"type": "string"}}),
    ),
)


def _neutralise(text: str) -> str:
    """Break every frame marker so a source cannot forge one."""
    while "<<<" in text or ">>>" in text:
        text = text.replace("<<<", "<< <").replace(">>>", "> >>")
    return text


def _list(sources: Sequence[PagedSource]) -> str:
    return "\n".join(
        f"{s.pin.name}: sha256 {s.pin.sha256} | {len(s.pages.pages)} pages" for s in sources
    )


def _is_page_number(value: Any) -> bool:
    return type(value) is int


def _read(source: PagedSource, arguments: dict[str, Any]) -> str:
    pages = source.pages.pages
    count = len(pages)
    first, last = arguments["first"], arguments["last"]
    if not (_is_page_number(first) and _is_page_number(last)) or not 1 <= first <= last:
        return _E_PAGES.format(count=count)
    if first > count:
        return _E_PAGES.format(count=count)
    end = min(last, first + _READ_LIMIT - 1, count)
    lines = [
        f"<<<SOURCE id={source.pin.name} sha256={source.pin.sha256} "
        f"page={page.number} state={page.state}>>>\n{_neutralise(page.text)}\n<<<END>>>"
        for page in pages[first - 1 : end]
    ]
    if end < min(last, count):
        lines.append(_NOTE_EIGHT.format(start=end + 1, end=min(last, count)))
    return "\n".join(lines)


_LINE_BREAKS = {ord(c): " " for c in "\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029"}


def _matches(source: PagedSource, query: str) -> Iterator[str]:
    for page in source.pages.pages:
        text = page.text
        at = text.find(query)
        while at != -1:
            stop = at + len(query)
            snippet = text[max(0, at - _CONTEXT) : stop + _CONTEXT].translate(_LINE_BREAKS)
            yield f"page {page.number}: …{_neutralise(snippet)}…"
            at = text.find(query, stop)


def _search(source: PagedSource, arguments: dict[str, Any]) -> str:
    query = arguments["query"]
    if not isinstance(query, str) or not 1 <= len(query) <= _QUERY_LIMIT or not query.strip():
        return _E_QUERY
    hits: list[str] = []
    more = False
    for hit in _matches(source, query.strip()):
        if len(hits) == _HIT_LIMIT:
            more = True
            break
        hits.append(hit)
    if not hits:
        return _NO_MATCH
    if more:
        hits.append(_NOTE_TWENTY)
    return "\n".join(hits)


def dispatch_source_tool(call: ToolCall, sources: Sequence[PagedSource]) -> str:
    """Run one source tool call and return its result text, or one fixed ERROR line."""
    names = [s.pin.name for s in sources]
    if len(set(names)) != len(names):
        raise ValueError("duplicate source name")
    if call.bad_arguments is not None:
        return _E_BAD_ARGUMENTS
    if call.name not in _KEYS:
        return _E_UNKNOWN_TOOL
    if set(call.arguments) != _KEYS[call.name]:
        return _E_KEYS[call.name]
    if call.name == "list_sources":
        return _list(sources)
    source_id = call.arguments["source_id"]
    if not isinstance(source_id, str) or source_id not in names:
        return _E_NO_SOURCE
    source = sources[names.index(source_id)]
    if call.name == "read_pages":
        return _read(source, call.arguments)
    return _search(source, call.arguments)
