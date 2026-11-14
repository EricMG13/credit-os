"""Pages, the paging rule and the page models."""

from collections.abc import Iterator
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from credit_os.sources.pages import Page, SourcePages, cut_pages, cut_stream


def _p(number: int, text: str) -> Page:
    return Page(number=number, text=text, state="text")


@pytest.mark.parametrize(
    ("text", "size", "pages"),
    [
        ("", 5, ()),
        ("abc", 3, ("abc",)),
        ("abc\ndef\nghi\n", 8, ("abc\ndef\n", "ghi\n")),
        ("aaaa bbbb cccc", 6, ("aaaa ", "bbbb ", "cccc")),
        ("abcdefghij", 4, ("abcd", "efgh", "ij")),
        ("ab\ncdefghij", 5, ("ab\n", "cdefg", "hij")),
        ("a\nb c d e", 6, ("a\n", "b c d ", "e")),
        ("a\r\nb\r\n", 3, ("a\r\n", "b\r\n")),
        ("ab\tcd", 3, ("ab\t", "cd")),
        ("ab cd", 5, ("ab cd",)),
        ("a\nb", 3, ("a\nb",)),
    ],
)
def test_cut_pages_rows(text: str, size: int, pages: tuple[str, ...]) -> None:
    assert cut_pages(text, size) == pages
    assert tuple(cut_stream([text], size)) == pages
    assert tuple(cut_stream(list(text), size)) == pages


def test_cut_stream_pieces() -> None:
    assert tuple(cut_stream([], 5)) == ()
    assert tuple(cut_stream(["", ""], 5)) == ()
    assert tuple(cut_stream(["ab", "", " cd"], 5)) == ("ab cd",)


def test_cut_stream_size_below_one_raises() -> None:
    with pytest.raises(ValueError, match="^size must be at least 1$"):
        tuple(cut_stream(["x" * 5], 0))


@given(
    pieces=st.lists(
        st.text(alphabet="abc xyz\n\r\N{LATIN SMALL LETTER E WITH ACUTE}", max_size=30),
        max_size=12,
    ),
    size=st.integers(min_value=1, max_value=40),
)
def test_cut_stream_property(pieces: list[str], size: int) -> None:
    assert tuple(cut_stream(pieces, size)) == cut_pages("".join(pieces), size)


def test_cut_stream_is_lazy() -> None:
    def pieces() -> Iterator[str]:
        for _ in range(5):
            yield "a\n"
        raise RuntimeError("read on")

    pages = cut_stream(pieces(), 4)
    assert next(pages) == "a\na\n"
    assert next(pages) == "a\na\n"
    with pytest.raises(RuntimeError):
        next(pages)


def test_cut_pages_size_below_one_raises() -> None:
    with pytest.raises(ValueError) as caught:
        cut_pages("x" * 5, 0)
    assert str(caught.value) == "size must be at least 1"


@given(
    text=st.text(alphabet="abc xyz\n\r\N{LATIN SMALL LETTER E WITH ACUTE}", max_size=200),
    size=st.integers(min_value=1, max_value=40),
)
def test_cut_pages_property(text: str, size: int) -> None:
    pages = cut_pages(text, size)
    assert "".join(pages) == text
    for index, page in enumerate(pages):
        assert 1 <= len(page) <= size
        if index < len(pages) - 1 and "\n" in page:
            assert page.endswith("\n")


def test_source_pages_round_trip() -> None:
    value = SourcePages(pages=(_p(1, "a"), _p(2, "b")), encoding="utf-8")
    assert SourcePages.model_validate_json(value.model_dump_json()) == value


@pytest.mark.parametrize(
    "build",
    [
        lambda: Page(number=0, text="a", state="text"),
        lambda: Page.model_validate({"number": 1, "text": "a", "state": "other"}),
        lambda: SourcePages(pages=(), encoding=None),
        lambda: SourcePages(pages=(_p(2, "a"),), encoding=None),
        lambda: SourcePages(pages=(_p(1, "a"), _p(1, "b")), encoding=None),
        lambda: SourcePages(pages=(_p(2, "a"), _p(1, "b")), encoding=None),
        lambda: Page(number=True, text="a", state="text"),
        lambda: Page.model_validate_json('{"number":"1","text":"a","state":"text"}'),
    ],
)
def test_models_refuse(build: Any) -> None:
    with pytest.raises(ValidationError):
        build()


@pytest.mark.parametrize(
    "build",
    [
        lambda: Page.model_validate({"number": 1, "text": "a", "state": "text", "x": 1}),
        lambda: SourcePages.model_validate({"pages": (_p(1, "a"),), "encoding": None, "x": 1}),
    ],
)
def test_models_refuse_an_extra_field(build: Any) -> None:
    with pytest.raises(ValidationError) as caught:
        build()
    assert [error["type"] for error in caught.value.errors()] == ["extra_forbidden"]


def test_other_states_are_accepted() -> None:
    empty = Page(number=1, text="", state="empty")
    unreadable = Page(number=2, text="", state="unreadable")
    assert (empty.state, unreadable.state) == ("empty", "unreadable")
    assert SourcePages(pages=(_p(1, "a"), unreadable), encoding=None).pages[1] == unreadable


def test_models_are_frozen() -> None:
    page = _p(1, "a")
    with pytest.raises(ValidationError):
        page.text = "b"
    pages = SourcePages(pages=(page,), encoding=None)
    with pytest.raises(ValidationError):
        pages.encoding = "utf-8"
