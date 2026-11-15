"""The shown and stored form of a source error (C1, D12).

The form is built from the error's class (the first class of its MRO in a closed table), the
name of the pin being read and a fixed reason. The message, `args`, `__cause__` and `__context__`
are never read: they hold absolute paths. Notes are stored masked, never shown."""

import os
from collections.abc import Iterable
from dataclasses import dataclass

from credit_os.provider.redact import Redactor
from credit_os.sources import (
    SourceChanged,
    SourceError,
    SourcePin,
    SourceRefused,
    SourceTooLarge,
    SourceUnreadable,
)
from credit_os.sources.errors import shown_name

FOLDER_LEAD = "the source folder or a file in it"
NOTE_CHARACTERS = 500
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
