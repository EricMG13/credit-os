"""The launch caps over a source folder (C3, D13, D16) and the shown and stored form of a source
error (C1, D12).

`pin_sources` refuses a folder before any file is read when it holds more than 200 source files or
400 MiB, and stores nothing: it imports no store, so a refused launch is never a run.

The form is built from the error's class (the first class of its MRO in a closed table), the
name of the pin being read and a fixed reason. The message, `args`, `__cause__` and `__context__`
are never read: they hold absolute paths. Notes are stored masked, never shown."""

import os
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from credit_os.provider.redact import Redactor
from credit_os.sources import (
    MAX_BYTES,
    PinnedFolder,
    SourceChanged,
    SourceError,
    SourceKind,
    SourcePin,
    SourceRefused,
    SourceTooLarge,
    SourceUnreadable,
    kind_of,
    pin_folder,
    validate_name,
)
from credit_os.sources.errors import shown_name

FOLDER_LEAD = "the source folder or a file in it"
NOTE_CHARACTERS = 500
MAX_FILES = 200
MAX_TOTAL_BYTES = 419_430_400  # 400 MiB
MAX_TEXT_BYTES = 16_777_216  # 16 MiB: text and csv (D13); other kinds keep sources.MAX_BYTES
NOT_A_FOLDER = "the source folder is not a folder that can be read"
ROOT_FOLDER = "the source folder cannot be a drive, a share or a filesystem root"
CANNOT_LIST = "the source folder could not be listed"
NO_FILE = "the source folder holds no source file"
_SKIPPED_PREFIXES = (".", "_", "~$")
NOTE_SEPARATOR = "; "

# The closed table; the nearest class is decided by the MRO, not by the order here.
_CLASSES: dict[type[SourceError], tuple[str, str]] = {
    SourceChanged: ("SourceChanged", "its content differs from the pin taken at launch"),
    SourceTooLarge: ("SourceTooLarge", "larger than the byte cap"),
    SourceUnreadable: (
        "SourceUnreadable",
        "cannot be opened or read, or its content does not match its kind",
    ),
    SourceRefused: ("SourceRefused", "refused by a name, path or folder rule"),
    SourceError: ("SourceError", "could not be used"),
}


@dataclass(frozen=True, slots=True)
class SourceProblem:
    """What 3A shows and stores about one source error."""

    error: str
    source: str | None
    reason: str
    note: str | None

    @property
    def shown(self) -> str:
        """The line shown: the pin's name (or the folder lead) and the fixed reason."""
        lead = FOLDER_LEAD if self.source is None else shown_name(self.source)
        return f"{lead}: {self.reason}"

    def detail(self) -> dict[str, str | int | None]:
        """The stored mapping: class name, the pin's whole name, reason and masked note."""
        return {
            "error": self.error,
            "source": self.source,
            "reason": self.reason,
            "note": self.note,
        }


def _known(error: SourceError) -> tuple[str, str]:
    for cls in type(error).__mro__:
        if cls in _CLASSES:
            return _CLASSES[cls]
    raise TypeError("not a source error")


class SourceForms:
    """Builds a `SourceProblem` from an error, masking notes with the source folder known."""

    def __init__(self, root: str | os.PathLike[str], *, known_paths: Iterable[str] = ()) -> None:
        self._redactor = Redactor(known_paths=(os.fspath(root), *known_paths))

    def problem(self, error: SourceError, pin: SourcePin | None) -> SourceProblem:
        """Return the shown and stored form; a non-`SourceError` is a `TypeError`."""
        if not isinstance(error, SourceError):
            raise TypeError(f"a SourceError is required, not {type(error).__name__}")
        name, reason = _known(error)
        return SourceProblem(
            error=name,
            source=None if pin is None else pin.name,
            reason=reason,
            note=self._note(error),
        )

    def _note(self, error: SourceError) -> str | None:
        notes = getattr(error, "__notes__", None)
        if not isinstance(notes, list):
            return None
        masked = [self._redactor.message(item) for item in notes if isinstance(item, str)]
        if not masked:
            return None
        return NOTE_SEPARATOR.join(masked)[:NOTE_CHARACTERS]


class SourcesRefused(ValueError):
    """The source folder cannot start a run. Nothing was stored (D16)."""

    def __init__(self, problems: tuple[str, ...]) -> None:
        super().__init__(NOTE_SEPARATOR.join(problems))
        self.problems = problems


@dataclass(frozen=True, slots=True)
class FolderCount:
    """What a listing found: files a run would read and their bytes."""

    files: int
    total_bytes: int


@dataclass(frozen=True, slots=True)
class LaunchSources:
    """The folder, resolved once, and its pins."""

    root: Path
    pinned: PinnedFolder


def launch_problems(count: FolderCount) -> tuple[str, ...]:
    """The launch rule over a count: files, then bytes, then no file. A cap itself passes."""
    problems: list[str] = []
    if count.files > MAX_FILES:
        problems.append(
            f"the source folder holds {count.files:,} source files; a run takes at most {MAX_FILES}"
        )
    if count.total_bytes > MAX_TOTAL_BYTES:
        problems.append(
            f"the source folder holds {count.total_bytes:,} bytes of source files; "
            f"a run takes at most {MAX_TOTAL_BYTES:,} (400 MiB)"
        )
    if count.files == 0:
        problems.append(NO_FILE)
    return tuple(problems)


def _entries(directory: Path) -> Iterator[os.DirEntry[str]]:
    with os.scandir(directory) as found:
        yield from found


def _step(entry: os.DirEntry[str], prefix: str) -> str | None:
    """Return "enter", "count" or None for one entry, by the rules `pin_folder` walks by."""
    if entry.is_symlink() or entry.is_junction() or entry.name.startswith(_SKIPPED_PREFIXES):
        return None
    name = prefix + entry.name
    if entry.is_dir(follow_symlinks=False):
        validate_name(name)
        return "enter"
    if entry.is_file(follow_symlinks=False) and kind_of(name) is not None:
        return "count"
    return None


def count_folder(root: Path) -> FolderCount:
    """List the folder and count the files `pin_folder` would read; no file is opened."""
    files = total = 0
    pending = [(root, "")]
    try:
        while pending:
            directory, prefix = pending.pop()
            for entry in _entries(directory):
                step = _step(entry, prefix)
                if step == "enter":
                    pending.append((directory / entry.name, f"{prefix}{entry.name}/"))
                elif step == "count":
                    files += 1
                    total += entry.stat(follow_symlinks=False).st_size
    except OSError:
        raise SourcesRefused((CANNOT_LIST,)) from None
    return FolderCount(files=files, total_bytes=total)


def pin_sources(folder: Path) -> LaunchSources:
    """Resolve, count, pin and re-check the folder; raise `SourcesRefused` if it cannot launch."""
    try:
        root = folder.resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        raise SourcesRefused((NOT_A_FOLDER,)) from None
    if not root.is_dir():
        raise SourcesRefused((NOT_A_FOLDER,))
    if root == Path(root.anchor):
        raise SourcesRefused((ROOT_FOLDER,))
    try:
        problems = launch_problems(count_folder(root))
        if problems:
            raise SourcesRefused(problems)
        pinned = pin_folder(root)
    except SourceError as error:
        raise SourcesRefused((f"{FOLDER_LEAD}: {_known(error)[1]}",)) from None
    problems = launch_problems(
        FolderCount(len(pinned.pins), sum(pin.size_bytes for pin in pinned.pins))
    )
    if problems:
        raise SourcesRefused(problems)
    return LaunchSources(root=root, pinned=pinned)


def source_cap(kind: SourceKind) -> int:
    """One source's byte cap (D13): 16 MiB for text and csv, the read cap for every other kind."""
    return MAX_TEXT_BYTES if kind in (SourceKind.TEXT, SourceKind.CSV) else MAX_BYTES


def oversize(pin: SourcePin) -> SourceProblem | None:
    """The problem for a pin over its kind's cap, or None; reads nothing."""
    cap = source_cap(pin.kind)
    if pin.size_bytes <= cap:
        return None
    what = "a text or csv source" if cap == MAX_TEXT_BYTES else "a source of its kind"
    return SourceProblem(
        error="SourceTooLarge",
        source=pin.name,
        reason=f"larger than {cap:,} bytes, the cap for {what}",
        note=None,
    )
