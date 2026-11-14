"""Pin every source file of an issuer folder, listing what is skipped and why."""

import hashlib
import os
import unicodedata
from collections.abc import Iterable
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from credit_os.sources.errors import SourceRefused, SourceUnreadable, shown_name
from credit_os.sources.files import read_capped, source_path
from credit_os.sources.pins import SourceKind, SourcePin, check_kind, kind_of, validate_name

_EXCLUDED_PREFIXES = ("_", "~$")


class Skipped(BaseModel):
    """One entry the walk did not pin and the reason. A skipped directory is listed once."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    name: str
    reason: str


def refuse_case_collisions(names: Iterable[str]) -> None:
    """Refuse two names that match after Unicode (NFC) normalisation and case folding.

    The first name, in plain string order, that matches an earlier one decides the message.
    """
    first_seen: dict[str, str] = {}
    for name in sorted(names):
        key = unicodedata.normalize("NFC", name).casefold()
        if key not in first_seen:
            first_seen[key] = name
            continue
        earlier = first_seen[key]
        shown_a, shown_b = shown_name(earlier), shown_name(name)
        if earlier == name:
            raise SourceRefused(f"{shown_a} is listed twice")
        if earlier.casefold() == name.casefold():
            raise SourceRefused(f"{shown_a} and {shown_b} differ only by case")
        raise SourceRefused(f"{shown_a} and {shown_b} differ only by case or Unicode form")


class PinnedFolder(BaseModel):
    """The pins of a folder, sorted by name, and its skipped entries, sorted by written name."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    pins: tuple[SourcePin, ...]
    skipped: tuple[Skipped, ...]

    @model_validator(mode="after")
    def _names_do_not_collide(self) -> Self:
        refuse_case_collisions(pin.name for pin in self.pins)
        return self


def _written(name: str) -> str:
    """Return the name for a skipped row: unchanged when it is a valid source name, else
    written with ASCII backslash escapes (control, format and bidi characters, every
    non-ASCII character, lone surrogates and the backslash itself), which reverses with
    ``.encode("ascii").decode("unicode_escape")``.
    """
    try:
        return validate_name(name)
    except SourceRefused:
        return name.encode("unicode_escape").decode("ascii")


def _listing(directory: Path) -> list[os.DirEntry[str]]:
    try:
        with os.scandir(directory) as entries:
            return list(entries)
    except OSError as error:
        reason = error.strerror or str(error)
        raise SourceUnreadable(f"{directory}: cannot list ({reason})") from error


def _classify(directory: Path, entry: os.DirEntry[str], name: str) -> tuple[str, str | None]:
    """Return (action, reason) for one entry: skip, skip_dir, enter, or file."""
    try:
        if entry.is_symlink() or entry.is_junction():
            return "skip", "symbolic link"
        is_dir = entry.is_dir(follow_symlinks=False)
        is_file = entry.is_file(follow_symlinks=False)
    except OSError as error:
        reason = error.strerror or str(error)
        raise SourceUnreadable(f"{directory}: cannot list ({reason})") from error
    base = entry.name
    skip_reason = None
    if base.startswith("."):
        skip_reason = "hidden name"
    elif base.startswith(_EXCLUDED_PREFIXES):
        skip_reason = "excluded name"
    if skip_reason is not None:
        return ("skip_dir" if is_dir else "skip"), skip_reason
    if is_dir:
        return "enter", None
    if not is_file:
        return "skip", "not a regular file"
    return "file", None


def _pin_file(folder: Path, name: str, kind: SourceKind) -> SourcePin:
    validate_name(name)
    source_path(folder, name)
    raw = read_capped(folder / name)
    check_kind(name, kind, raw)
    return SourcePin(
        name=name, sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw), kind=kind
    )


def _visit(
    folder: Path,
    directory: Path,
    prefix: str,
    entry: os.DirEntry[str],
    pending: list[tuple[Path, str]],
    pins: list[SourcePin],
    skipped: list[Skipped],
) -> None:
    name = prefix + entry.name
    action, reason = _classify(directory, entry, name)
    if action == "enter":
        pending.append((directory / entry.name, name + "/"))
    elif action == "file" and (kind := kind_of(name)) is not None:
        pins.append(_pin_file(folder, name, kind))
    else:
        suffix = "/" if action == "skip_dir" else ""
        skipped.append(Skipped(name=_written(name) + suffix, reason=reason or "unsupported suffix"))


def pin_folder(folder: Path) -> PinnedFolder:
    """Pin every supported file under the folder, never following links.

    Symbolic links and junctions, hidden (``.``) and excluded (``_``, ``~$``) names, other
    suffixes and non-regular files are skipped and listed; a skipped directory is listed once
    with a trailing ``/`` and not entered. A name that fails ``validate_name`` is written in
    ``Skipped`` with ASCII backslash escapes, so every row is printable. A file that would be
    pinned and has a bad name, a wrong signature or a read error stops the walk.
    """
    if not folder.is_dir():
        raise SourceRefused(f"{folder}: not a folder")
    pins: list[SourcePin] = []
    skipped: list[Skipped] = []
    pending: list[tuple[Path, str]] = [(folder, "")]
    while pending:
        directory, prefix = pending.pop()
        for entry in _listing(directory):
            _visit(folder, directory, prefix, entry, pending, pins, skipped)
    refuse_case_collisions(pin.name for pin in pins)
    return PinnedFolder(
        pins=tuple(sorted(pins, key=lambda pin: pin.name)),
        skipped=tuple(sorted(skipped, key=lambda row: row.name)),
    )
