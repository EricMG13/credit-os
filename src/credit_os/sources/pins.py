"""Source names, kinds and the pin that records one source file."""

import unicodedata
from collections.abc import Mapping
from enum import StrEnum
from pathlib import PurePosixPath, PureWindowsPath
from types import MappingProxyType
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from credit_os.sources.errors import SourceRefused, SourceUnreadable


class SourceKind(StrEnum):
    """The kind of an accepted source file."""

    PDF = "pdf"
    HTML = "html"
    DOCX = "docx"
    XLSX = "xlsx"
    CSV = "csv"
    TEXT = "text"


SUFFIX_KINDS: Mapping[str, SourceKind] = MappingProxyType(
    {
        ".pdf": SourceKind.PDF,
        ".htm": SourceKind.HTML,
        ".html": SourceKind.HTML,
        ".docx": SourceKind.DOCX,
        ".txt": SourceKind.TEXT,
        ".md": SourceKind.TEXT,
        ".xlsx": SourceKind.XLSX,
        ".csv": SourceKind.CSV,
    }
)

_REFUSED_CATEGORIES = frozenset({"Cc", "Cf", "Cs", "Zl", "Zp"})
_PDF_SIGNATURE = b"%PDF-"
_ZIP_SIGNATURE = b"PK\x03\x04"


def _bad_character(char: str) -> bool:
    return char in '\\:<>"|?*' or unicodedata.category(char) in _REFUSED_CATEGORIES


def _bad_segment(segment: str) -> bool:
    return not segment or segment.endswith((".", " ")) or PureWindowsPath(segment).is_reserved()


def validate_name(name: str) -> str:
    """Return the name unchanged, or refuse it as not a portable relative forward-slash path."""
    if any(_bad_character(char) for char in name) or any(
        _bad_segment(segment) for segment in name.split("/")
    ):
        raise SourceRefused(f"{name!r}: not a valid source name")
    return name


def kind_of(name: str) -> SourceKind | None:
    """Return the kind for the name's last suffix, or None when it is not accepted."""
    return SUFFIX_KINDS.get(PurePosixPath(name).suffix.lower())


def check_kind(name: str, kind: SourceKind, raw: bytes) -> None:
    """Refuse bytes whose signature contradicts the kind."""
    is_pdf = raw.startswith(_PDF_SIGNATURE)
    is_zip = raw.startswith(_ZIP_SIGNATURE)
    if kind is SourceKind.PDF:
        if not is_pdf:
            raise SourceUnreadable(f"{name}: does not start with %PDF-")
    elif kind in (SourceKind.DOCX, SourceKind.XLSX):
        if not is_zip:
            raise SourceUnreadable(f"{name}: does not start with a zip signature")
    elif is_pdf:
        raise SourceUnreadable(f"{name}: starts with a PDF signature")
    elif is_zip:
        raise SourceUnreadable(f"{name}: starts with a zip signature")


class SourcePin(BaseModel):
    """The name, digest, size and kind that identify one source file."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    name: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)
    kind: SourceKind

    @field_validator("name", mode="after")
    @classmethod
    def _name_is_valid(cls, name: str) -> str:
        return validate_name(name)

    @model_validator(mode="after")
    def _kind_matches_suffix(self) -> Self:
        if kind_of(self.name) is not self.kind:
            raise ValueError(f"{self.name!r}: kind {self.kind.value!r} does not match the name")
        return self
