"""The source tools and their dispatch (3A PR 4a), against the controller's answer key."""

from typing import Any, cast

import orchestrator_tools_key as key
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from credit_os.orchestrator.tools import SOURCE_TOOLS, PagedSource, dispatch_source_tool
from credit_os.provider.types import ToolCall
from credit_os.sources.pages import Page, SourcePages
from credit_os.sources.pins import SourceKind, SourcePin


def _paged(fields: tuple[str, str, int, str], pages: list[tuple[str, str]]) -> PagedSource:
    name, sha, size, kind = fields
    return PagedSource(
        pin=SourcePin(name=name, sha256=sha, size_bytes=size, kind=SourceKind(kind)),
        pages=SourcePages(
            pages=tuple(
                Page(number=n, text=text, state=cast(Any, state))
                for n, (text, state) in enumerate(pages, start=1)
            ),
            encoding=None,
        ),
    )


SOURCES = [_paged(fields, pages) for fields, pages in key.SOURCES]


def _call(name: str, arguments: dict[str, Any], bad: str | None = None) -> ToolCall:
    return ToolCall(call_id="c1", name=name, arguments=arguments, bad_arguments=bad)


@pytest.mark.parametrize("row", list(key.CALLS), ids=list(key.CALLS))
def test_d12_every_key_row_returns_the_exact_text(row: str) -> None:
    name, arguments, bad, expected = key.CALLS[row]
    got = dispatch_source_tool(_call(name, arguments, bad), SOURCES)
    assert got == expected
    if expected.startswith("ERROR: "):
        assert "\n" not in got
        assert len(got) <= 300


def test_d12_source_tools_match_the_key() -> None:
    assert [spec.name for spec in SOURCE_TOOLS] == ["list_sources", "read_pages", "search_source"]
    for spec in SOURCE_TOOLS:
        assert spec.parameters == key.SPECS[spec.name]
        assert "\n" not in spec.description
        assert 0 < len(spec.description) <= 600


def test_d12_two_sources_with_one_name_are_a_callers_error() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        dispatch_source_tool(_call("list_sources", {}), [SOURCES[1], SOURCES[1]])


_scalars = st.none() | st.booleans() | st.integers() | st.text(max_size=40)
_values = st.recursive(_scalars, lambda inner: st.lists(inner, max_size=3), max_leaves=6)
_names = st.sampled_from(["list_sources", "read_pages", "search_source"]) | st.text(max_size=30)
_arguments = st.dictionaries(
    st.sampled_from(["source_id", "first", "last", "query"]) | st.text(max_size=10),
    _values | st.sampled_from([s.pin.name for s in SOURCES]),
    max_size=5,
)


@settings(max_examples=200, deadline=None)
@given(name=_names, arguments=_arguments, bad=st.none() | st.text(max_size=40))
def test_d10_any_call_returns_text_and_errors_are_one_short_line(
    name: str, arguments: dict[str, Any], bad: str | None
) -> None:
    got = dispatch_source_tool(_call(name, arguments, bad), SOURCES)
    assert isinstance(got, str)
    if got.startswith("ERROR: "):
        assert "\n" not in got
        assert len(got) <= 300


@settings(max_examples=200, deadline=None)
@given(text=st.text(alphabet="<>a \n", max_size=60))
def test_d17_a_page_cannot_forge_a_frame(text: str) -> None:
    source = _paged(("p.txt", key.SHA_A, 1, "text"), [(text, "text")])
    got = dispatch_source_tool(
        _call("read_pages", {"source_id": "p.txt", "first": 1, "last": 1}), [source]
    )
    head, _, rest = got.partition("\n")
    assert head == key.frame("p.txt", key.SHA_A, 1, "text", "").split("\n")[0]
    body = rest.removesuffix("\n<<<END>>>")
    assert "<<<" not in body
    assert ">>>" not in body
    assert got.endswith("\n<<<END>>>")
