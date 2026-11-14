"""Typed errors of the sources layer; each message names the file and the reason."""

_SHOWN_NAME_CHARACTERS = 120


def shown_name(name: str) -> str:
    """Return the name for a message: its first 120 characters, then an ellipsis when cut."""
    if len(name) <= _SHOWN_NAME_CHARACTERS:
        return name
    return name[:_SHOWN_NAME_CHARACTERS] + "\u2026"


def reason_of(error: BaseException) -> str:
    """Return the error's strerror, else its text, else its class name (the one reason rule)."""
    return getattr(error, "strerror", None) or str(error) or type(error).__name__


class SourceError(Exception):
    """Base of every sources error."""


class SourceRefused(SourceError, ValueError):
    """A name, path or folder rule refused the source."""


class SourceUnreadable(SourceError):
    """The file cannot be opened or read, or its content does not match its kind."""


class SourceTooLarge(SourceUnreadable):
    """The file is larger than the byte cap."""


class SourceChanged(SourceError):
    """The file's bytes no longer match the pin."""
