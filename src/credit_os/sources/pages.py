"""Pages of a source file and the one rule that cuts text into them."""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Page(BaseModel):
    """One numbered page of a source file."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    number: int = Field(ge=1)
    text: str
    state: Literal["text", "empty", "unreadable"]


class SourcePages(BaseModel):
    """The pages of one source file and the encoding its text was decoded with, if any."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    pages: tuple[Page, ...]
    encoding: str | None

    @model_validator(mode="after")
    def _numbers_run_from_one(self) -> Self:
        if not self.pages:
            raise ValueError("a source has at least one page")
        if [page.number for page in self.pages] != list(range(1, len(self.pages) + 1)):
            raise ValueError("page numbers must be 1, 2, 3, ... in order")
        return self


def cut_pages(text: str, size: int) -> tuple[str, ...]:
    """Cut text into consecutive slices of at most size characters that rejoin to it exactly.

    A full page ends just after the last line feed in it, else just after the last space,
    else it holds all size characters.
    """
    if size < 1:
        raise ValueError("size must be at least 1")
    pieces: list[str] = []
    start = 0
    while len(text) - start > size:
        window = text[start : start + size]
        end = window.rfind("\n") + 1 or window.rfind(" ") + 1 or size
        pieces.append(window[:end])
        start += end
    if start < len(text):
        pieces.append(text[start:])
    return tuple(pieces)


def text_state_pages(pieces: tuple[str, ...], encoding: str | None) -> SourcePages:
    """Number page texts from 1, each in state "text"."""
    return SourcePages(
        pages=tuple(
            Page(number=number, text=piece, state="text")
            for number, piece in enumerate(pieces, start=1)
        ),
        encoding=encoding,
    )
